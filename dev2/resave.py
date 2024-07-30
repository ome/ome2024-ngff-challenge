#!/usr/bin/env python
import pathlib
import random
import shutil
import numpy as np
import json
import tqdm
import zarr
import time
import sys
import os

import tensorstore as ts

import argparse

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


NGFF_VERSION = "0.5"

#
# Helpers
#


class TSMetrics:
    """
    Instances of this class capture the current tensorstore metrics.

    If an existing instance is passed in on creation, it will be stored
    in order to deduct prevoius values from those measured by this instance.
    """

    CHUNK_CACHE_READS = "/tensorstore/cache/chunk_cache/reads"
    CHUNK_CACHE_WRITES = "/tensorstore/cache/chunk_cache/writes"

    FILES_BATCH_READ = "/tensorstore/kvstore/file/batch_read"
    FILES_BYTES_READ = "/tensorstore/kvstore/file/bytes_read"
    FILES_BYTES_WRITTEN = "/tensorstore/kvstore/file/bytes_written"

    OTHER = [
        "/tensorstore/cache/hit_count"
        "/tensorstore/cache/kvs_cache_read"
        "/tensorstore/cache/miss_count"
        "/tensorstore/kvstore/file/delete_range"
        "/tensorstore/kvstore/file/open_read"
        "/tensorstore/kvstore/file/read"
        "/tensorstore/kvstore/file/write"
        "/tensorstore/thread_pool/active"
        "/tensorstore/thread_pool/max_delay_ns"
        "/tensorstore/thread_pool/started"
        "/tensorstore/thread_pool/steal_count"
        "/tensorstore/thread_pool/task_providers"
        "/tensorstore/thread_pool/total_queue_time_ns"
        "/tensorstore/thread_pool/work_time_ns"
    ]

    def __init__(self, start=None):
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
        return self.value(self.FILES_BYTES_READ)

    def written(self):
        return self.value(self.FILES_BYTES_WRITTEN)


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


CONFIGS = create_configs(ns)


def convert_array(
    input_path: str, output_path: str, dimension_names: list, chunks: list, shards: list
):
    CONFIGS[0]["path"] = input_path
    CONFIGS[1]["path"] = output_path

    read = ts.open(
        {
            "driver": "zarr",
            "kvstore": CONFIGS[0],
        }
    ).result()

    shape = read.shape
    if chunks:
        chunks = [int(x) for x in ns.chunks.split(",")]
    else:
        chunks = read.schema.chunk_layout.read_chunk.shape
        print(
            f"Using chunks {chunks} ({[float(shape[x])/chunks[x] for x in range(len(shape))]})"
        )

    if ns.shards:
        if ns.shards == "full":
            shards = shape
        else:
            shards = [
                int(x) for x in ns.shards.split(",")
            ]  # TODO: needs to be per resolution level

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
            "shape": shape,
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

    before = TSMetrics()
    start = time.time()
    future = write.write(read)
    future.result()
    stop = time.time()
    after = TSMetrics(before)

    def get_size(path):
        path = pathlib.Path(path)
        return sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())

    input_size = get_size(input_path)
    output_size = get_size(output_path)

    print(f"""Reencode (tensorstore) {input_path} to {output_path}
        read: {input_size} {after.read()}
        write: {output_size} {after.written()}
        time: {stop - start}
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
    read_root,
    input_path,
    write_root,
    output_path,
    output_read_details: str,
    output_write_details: bool,
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

    if write_root:  # otherwise dry-run
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

        # TODO: calculate shards here
        ds_shards = "TODO"

        if output_write_details:
            details.append(
                {
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
            convert_array(
                os.path.join(input_path, ds_path),
                os.path.join(output_path, ds_path),
                dimension_names,
                ds_chunks,
                ds_shards,
            )


def main():
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
    else:
        write_store = STORES[1]
        write_root = zarr.Group.create(write_store)

    # image...
    if read_root.attrs.get("multiscales"):
        convert_image(
            read_root,
            ns.input_path,
            write_root,
            ns.output_path,
            ns.output_read_details,
            ns.output_write_details,
        )

    # plate...
    elif read_root.attrs.get("plate"):
        ome_attrs = {"version": NGFF_VERSION}
        for key, value in read_root.attrs.items():
            # ...replaces all other versions - remove
            if "version" in value:
                del value["version"]
            ome_attrs[key] = value

        if write_root:  # otherwise dry run
            # dev2: everything is under 'ome' key
            write_root.attrs["ome"] = ome_attrs

        plate_attrs = read_root.attrs.get("plate")
        wells = plate_attrs.get("wells")
        for well in tqdm.tqdm(
            wells, position=0, desc="i", leave=False, colour="green", ncols=80
        ):
            well_path = well["path"]
            well_v2 = zarr.open_group(store=STORES[0], path=well_path, zarr_format=2)

            if write_root:  # otherwise dry-run
                well_group = write_root.create_group(well_path)
                # well_attrs = { k:v for (k,v) in well_v2.attrs.items()}
                # TODO: do we store 'version' in well?
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

                if write_root:  # otherwise dry-run
                    image_group = write_root.create_group(img_path)
                else:
                    image_group = None

                convert_image(
                    img_v2,
                    input_path,
                    image_group,
                    out_path,
                    ns.output_read_details,
                    ns.output_write_details,
                )


if __name__ == "__main__":
    main()
