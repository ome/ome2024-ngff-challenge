#!/usr/bin/env python
import random
import shutil
import json
import math
import tqdm
import zarr
import time
import sys
import os

import tensorstore as ts

import argparse

from zarr.api.synchronous import sync
from zarr.buffer import Buffer


NGFF_VERSION = "0.5"

#
# Helpers
#


def guess_shards(shape: list, chunks: list):
    """
    Method to calculate best shard sizes. These values can be written to
    a file for the current dataset by using:

    ./resave.py input.zarr output.json --output-write-details
    """
    # TODO: hard-coded to return the full size unless too large
    if math.prod(shape) < 100_000_000:
        return shape
    raise Exception(f"no shard guess: shape={shape}, chunks={chunks}")


class TextBuffer(Buffer):
    """
    Zarr Buffer implementation that simplify saves text at a given location.
    """

    def __init__(self, text):
        self.text = text
        self._data = list(text)


class TSMetrics:
    """
    Instances of this class capture the current tensorstore metrics.

    If an existing instance is passed in on creation, it will be stored
    in order to deduct previous values from those measured by this instance.
    """

    CHUNK_CACHE_READS = "/tensorstore/cache/chunk_cache/reads"
    CHUNK_CACHE_WRITES = "/tensorstore/cache/chunk_cache/writes"

    BATCH_READ = "/tensorstore/kvstore/{store_type}/batch_read"
    BYTES_READ = "/tensorstore/kvstore/{store_type}/bytes_read"
    BYTES_WRITTEN = "/tensorstore/kvstore/{store_type}/bytes_written"

    OTHER = [
        "/tensorstore/cache/hit_count"
        "/tensorstore/cache/kvs_cache_read"
        "/tensorstore/cache/miss_count"
        "/tensorstore/kvstore/{store_type}/delete_range"
        "/tensorstore/kvstore/{store_type}/open_read"
        "/tensorstore/kvstore/{store_type}/read"
        "/tensorstore/kvstore/{store_type}/write"
        "/tensorstore/thread_pool/active"
        "/tensorstore/thread_pool/max_delay_ns"
        "/tensorstore/thread_pool/started"
        "/tensorstore/thread_pool/steal_count"
        "/tensorstore/thread_pool/task_providers"
        "/tensorstore/thread_pool/total_queue_time_ns"
        "/tensorstore/thread_pool/work_time_ns"
    ]

    def __init__(self, read_config, write_config, start=None):
        self.time = time.time()
        self.read_type = read_config["kvstore"]["driver"]
        self.write_type = write_config["kvstore"]["driver"]
        self.start = start
        self.data = ts.experimental_collect_matching_metrics()

    def value(self, key):
        rv = None
        for item in self.data:
            k = item["name"]
            v = item["values"]
            if k == key:
                if len(v) > 1:
                    raise Exception(f"Multiple values for {key}: {v}")
                rv = v[0]["value"]
                break
        if rv is None:
            raise Exception(f"unknown key: {key} from {self.data}")

        if self.start is not None:
            orig = self.start.value(key)
        else:
            orig = 0

        return rv - orig

    def read(self):
        return self.value(self.BYTES_READ.format(store_type=self.read_type))

    def written(self):
        return self.value(self.BYTES_WRITTEN.format(store_type=self.write_type))

    def elapsed(self):
        return self.start is not None and (self.time - self.start.time) or self.time


def create_configs(ns):
    configs = []
    for selection in ("input", "output"):
        anon = getattr(ns, f"{selection}_anon")
        bucket = getattr(ns, f"{selection}_bucket")
        endpoint = getattr(ns, f"{selection}_endpoint")
        region = getattr(ns, f"{selection}_region")

        if bucket:
            store = {
                "driver": "s3",
                "bucket": bucket,
                "aws_region": region,
            }
            if anon:
                store["aws_credentials"] = {"anonymous": anon}
            if endpoint:
                store["endpoint"] = endpoint
        else:
            store = {
                "driver": "file",
            }
        configs.append(store)
    return configs


def convert_array(
    CONFIGS: list,
    input_path: str,
    output_path: str,
    dimension_names: list,
    chunks: list,
    shards: list,
):
    CONFIGS[0]["path"] = input_path
    CONFIGS[1]["path"] = output_path

    read_config = {
        "driver": "zarr",
        "kvstore": CONFIGS[0],
    }
    read = ts.open(read_config).result()

    if shards:
        chunk_grid = {
            "name": "regular",
            "configuration": {"chunk_shape": shards},
        }  # write size

        sharding_codec = {
            "name": "sharding_indexed",
            "configuration": {
                "chunk_shape": chunks,  # read size
                "codecs": [
                    {"name": "bytes", "configuration": {"endian": "little"}},
                    {"name": "blosc", "configuration": {"cname": "zstd", "clevel": 5}},
                ],
                "index_codecs": [
                    {"name": "bytes", "configuration": {"endian": "little"}},
                    {"name": "crc32c"},
                ],
                "index_location": "end",
            },
        }
        codecs = [sharding_codec]
    else:
        # Alternative without sharding...
        chunk_grid = {"name": "regular", "configuration": {"chunk_shape": chunks}}
        codecs = [
            {"name": "bytes", "configuration": {"endian": "little"}},
            {"name": "blosc", "configuration": {"cname": "zstd", "clevel": 5}},
        ]

    base_config = {
        "driver": "zarr3",
        "kvstore": CONFIGS[1],
        "metadata": {
            "shape": read.shape,
            "chunk_grid": chunk_grid,
            "chunk_key_encoding": {
                "name": "default"
            },  # "configuration": {"separator": "/"}},
            "codecs": codecs,
            "data_type": read.dtype,
            "dimension_names": dimension_names,
        },
    }

    write_config = base_config.copy()
    write_config["create"] = True
    write_config["delete_existing"] = ns.output_overwrite

    verify_config = base_config.copy()

    write = ts.open(write_config).result()

    before = TSMetrics(read_config, write_config)
    future = write.write(read)
    future.result()
    after = TSMetrics(read_config, write_config, before)

    print(f"""Re-encode (tensorstore) {input_path} to {output_path}
        read: {after.read()}
        write: {after.written()}
        time: {after.elapsed()}
    """)

    verify = ts.open(verify_config).result()
    print(f"Verifying <{output_path}>\t{read.shape}\t", end="")
    for x in range(10):
        r = tuple([random.randint(0, y - 1) for y in read.shape])
        before = read[r].read().result()
        after = verify[r].read().result()
        assert before == after
        print(".", end="")
    print("ok")


def convert_image(
    CONFIGS: list,
    read_root,
    input_path: str,
    write_store,
    write_root,
    output_path: str,
    output_read_details: str,
    output_write_details: bool,
    output_script: bool,
    script_prefix: str = None,
):
    dimension_names = None
    # top-level version...
    ome_attrs = {"version": NGFF_VERSION}
    for key, value in read_root.attrs.items():
        # ...replaces all other versions - remove
        if "version" in value:
            del value["version"]
        if key == "multiscales":
            dimension_names = [axis["name"] for axis in value[0]["axes"]]
            if "version" in value[0]:
                del value[0]["version"]
        ome_attrs[key] = value

    if write_root is not None:  # otherwise dry-run
        # dev2: everything is under 'ome' key
        write_root.attrs["ome"] = ome_attrs

    if output_read_details:
        with open(output_read_details, "r") as o:
            details = json.load(o)
    else:
        details = []  # No resolutions yet

    # convert arrays
    multiscales = read_root.attrs.get("multiscales")
    for idx, ds in enumerate(multiscales[0]["datasets"]):
        ds_path = ds["path"]
        ds_array = read_root[ds_path]
        ds_shape = ds_array.shape
        ds_chunks = ds_array.chunks
        ds_shards = guess_shards(ds_shape, ds_chunks)

        if output_write_details:
            details.append(
                {
                    "shape": ds_shape,
                    "chunks": ds_chunks,
                    "shards": ds_shards,
                }
            )
            with open(output_path, "w") as o:
                json.dump(details, o)
        else:
            if output_read_details:
                # read row by row and overwrite
                ds_chunks = details[idx]["chunks"]
                ds_shards = details[idx]["shards"]

            if output_script:
                chunk_txt = ",".join(map(str, ds_chunks))
                shard_txt = ",".join(map(str, ds_shards))
                dimsn_txt = ",".join(map(str, dimension_names))
                if script_prefix:
                    # Ugly; needs fixing
                    filename = os.path.join(script_prefix, ds_path, "convert.sh")
                else:
                    filename = os.path.join(output_path, ds_path, "convert.sh")
                text = TextBuffer(
                    f"zarrs_reencode --chunk-shape {chunk_txt} --shard-shape {shard_txt} --dimension-names {dimsn_txt} --validate {input_path} {output_path}\n"
                )
                sync(write_store.set(filename, text))
            else:
                convert_array(
                    CONFIGS,
                    os.path.join(input_path, ds_path),
                    os.path.join(output_path, ds_path),
                    dimension_names,
                    ds_chunks,
                    ds_shards,
                )


def write_rocrate(write_store):
    from zarr_crate.zarr_extension import ZarrCrate
    from zarr_crate.rembi_extension import Biosample, Specimen, ImageAcquistion

    crate = ZarrCrate()

    zarr_root = crate.add_dataset(
        "./",
        properties={
            "name": "Light microscopy photo of a fly",
            "description": "Light microscopy photo of a fruit fly.",
            "license": "https://creativecommons.org/licenses/by/4.0/",
        },
    )
    biosample = crate.add(
        Biosample(
            crate, properties={"organism_classification": {"@id": "NCBI:txid7227"}}
        )
    )
    specimen = crate.add(Specimen(crate, biosample))
    image_acquisition = crate.add(
        ImageAcquistion(
            crate, specimen, properties={"fbbi_id": {"@id": "obo:FBbi_00000243"}}
        )
    )
    zarr_root["resultOf"] = image_acquisition

    metadata_dict = crate.metadata.generate()
    filename = "ro-crate-metadata.json"
    text = TextBuffer(json.dumps(metadata_dict, indent=2))
    sync(write_store.set(filename, text))


def main(ns: argparse.Namespace):
    CONFIGS = create_configs(ns)

    STORES = []
    for config, path, mode in (
        (CONFIGS[0], ns.input_path, "r"),
        (CONFIGS[1], ns.output_path, "w"),
    ):
        if "bucket" in config:
            store_class = zarr.store.RemoteStore
            anon = config.get("aws_credentials", {}).get("anonymous", False)
            store = store_class(
                url=f's3://{config["bucket"]}/{path}',
                anon=anon,
                endpoint_url=config.get("endpoint", None),
                mode=mode,
            )
        else:
            store_class = zarr.store.LocalStore
            store = store_class(path, mode=mode)

            if STORES:
                # If more than one element, then we are configuring
                # the output path. If this is local, then delete.
                #
                # TODO: This should really be an option on zarr-python
                # as with tensorstore.
                if os.path.exists(ns.output_path):
                    if ns.output_overwrite:
                        if os.path.isfile(ns.output_path):
                            os.remove(ns.output_path)
                        else:
                            shutil.rmtree(ns.output_path)
                    else:
                        print(f"{ns.output_path} exists. Exiting")
                        sys.exit(1)

        STORES.append(store)

    # Needs zarr_format=2 or we get ValueError("store mode does not support writing")
    read_root = zarr.open_group(store=STORES[0], zarr_format=2)

    if ns.output_write_details:
        write_root = None
        write_store = None
    else:
        write_store = STORES[1]
        write_root = zarr.Group.create(write_store)
        if ns.output_rocrate:
            write_rocrate(write_store)

    # image...
    if read_root.attrs.get("multiscales"):
        convert_image(
            CONFIGS,
            read_root,
            ns.input_path,
            write_store,  # TODO: review
            write_root,
            ns.output_path,
            ns.output_read_details,
            ns.output_write_details,
            ns.output_script,
        )

    # plate...
    elif read_root.attrs.get("plate"):
        ome_attrs = {"version": NGFF_VERSION}
        for key, value in read_root.attrs.items():
            # ...replaces all other versions - remove
            if "version" in value:
                del value["version"]
            ome_attrs[key] = value

        if write_root is not None:  # otherwise dry run
            # dev2: everything is under 'ome' key
            write_root.attrs["ome"] = ome_attrs

        plate_attrs = read_root.attrs.get("plate")
        wells = plate_attrs.get("wells")

        for well in tqdm.tqdm(
            wells, position=0, desc="i", leave=False, colour="green", ncols=80
        ):
            well_path = well["path"]
            well_v2 = zarr.open_group(store=STORES[0], path=well_path, zarr_format=2)

            if write_root is not None:  # otherwise dry-run
                well_group = write_root.create_group(well_path)
                well_attrs = {}
                for key, value in well_v2.attrs.items():
                    if "version" in value:
                        del value["version"]
                    well_attrs[key] = value
                    well_attrs["version"] = "0.5"
                well_group.attrs["ome"] = well_attrs

            images = well_attrs["well"]["images"]
            for img in tqdm.tqdm(
                images, position=1, desc="j", leave=False, colour="red", ncols=80
            ):
                img_path = well_path + "/" + img["path"]
                out_path = os.path.join(ns.output_path, img_path)
                input_path = os.path.join(ns.input_path, img_path)
                img_v2 = zarr.open_group(store=STORES[0], path=img_path, zarr_format=2)

                if write_root is not None:  # otherwise dry-run
                    image_group = write_root.create_group(img_path)
                else:
                    image_group = None

                convert_image(
                    CONFIGS,
                    img_v2,
                    input_path,
                    write_store,  # TODO: review
                    image_group,
                    out_path,
                    ns.output_read_details,
                    ns.output_write_details,
                    ns.output_script,
                    img_path,  # TODO: review
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-bucket")
    parser.add_argument("--input-endpoint")
    parser.add_argument("--input-anon", action="store_true")
    parser.add_argument("--input-region", default="us-east-1")
    parser.add_argument("--output-bucket")
    parser.add_argument("--output-endpoint")
    parser.add_argument("--output-anon", action="store_true")
    parser.add_argument("--output-region", default="us-east-1")
    parser.add_argument("--output-overwrite", action="store_true")
    parser.add_argument("--output-script", action="store_true")
    parser.add_argument("--output-rocrate", action="store_true")
    group_ex = parser.add_mutually_exclusive_group()
    group_ex.add_argument(
        "--output-write-details",
        action="store_true",
        help="don't convert array, instead write chunk and proposed shard sizes",
    )
    group_ex.add_argument(
        "--output-read-details", help="read chink and shard sizes from file"
    )
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    ns = parser.parse_args()

    main(ns)
