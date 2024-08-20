#!/usr/bin/env python
from __future__ import annotations

import argparse
import itertools
import json
import logging
import math
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import tensorstore as ts
import tqdm
import zarr
from zarr.api.synchronous import sync
from zarr.buffer import Buffer, BufferPrototype

from .zarr_crate.rembi_extension import Biosample, ImageAcquistion, Specimen
from .zarr_crate.zarr_extension import ZarrCrate

NGFF_VERSION = "0.5"
LOGGER = logging.getLogger("resave")

#
# Helpers
#


class Batched:
    """
    implementation of itertools.batched for pre-3.12 Python versions
    from https://mathspp.com/blog/itertools-batched
    """

    def __init__(self, iterable, n: int):
        if n < 1:
            msg = f"n must be at least one ({n})"
            raise ValueError(msg)
        self.iter = iter(iterable)
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        batch = tuple(itertools.islice(self.iter, self.n))
        if not batch:
            raise StopIteration()
        return batch


class SafeEncoder(json.JSONEncoder):
    # Handle any TypeErrors so we are safe to use this for logging
    # E.g. dtype obj is not JSON serializable
    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
            return str(o)


def guess_shards(shape: list, chunks: list):
    """
    Method to calculate best shard sizes. These values can be written to
    a file for the current dataset by using:

    ./resave.py input.zarr output.json --output-write-details
    """
    # TODO: hard-coded to return the full size
    assert chunks is not None  # fixes unused parameter
    return shape


def chunk_iter(shape: list, chunks: list):
    """
    Returns a series of tuples, each containing chunk slice
    E.g. for 2D shape/chunks: ((slice(0, 512, 1), slice(0, 512, 1)), (slice(0, 512, 1), slice(512, 1024, 1))...)
    Thanks to Davis Bennett.
    """
    assert len(shape) == len(chunks)
    chunk_iters = []
    for chunk_size, dim_size in zip(chunks, shape):
        chunk_tuple = tuple(
            slice(
                c_index * chunk_size,
                min(dim_size, c_index * chunk_size + chunk_size),
                1,
            )
            for c_index in range(-(-dim_size // chunk_size))
        )
        chunk_iters.append(chunk_tuple)
    return tuple(itertools.product(*chunk_iters))


def csv_int(vstr, sep=",") -> list:
    """Convert a string of comma separated values to integers
    @returns iterable of floats
    """
    values = []
    for v0 in vstr.split(sep):
        try:
            v = int(v0)
            values.append(v)
        except ValueError as ve:
            raise argparse.ArgumentError(
                message=f"Invalid value {v0}, values must be a number"
            ) from ve
    return values


def strip_version(possible_dict) -> None:
    """
    If argument is a dict with the key "version", remove it
    """
    if isinstance(possible_dict, dict) and "version" in possible_dict:
        del possible_dict["version"]


class TextBuffer(Buffer):
    """
    Zarr Buffer implementation that simplify saves text at a given location.
    """

    def __init__(self, text):
        self.text = text
        if isinstance(text, str):
            text = np.array(text.encode())
        self._data = text


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

    OTHER = (
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
    )

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

        orig = self.start.value(key) if self.start is not None else 0

        return rv - orig

    def read(self):
        return self.value(self.BYTES_READ.format(store_type=self.read_type))

    def written(self):
        return self.value(self.BYTES_WRITTEN.format(store_type=self.write_type))

    def elapsed(self):
        return self.start is not None and (self.time - self.start.time) or self.time


class Config:
    """
    Filesystem and S3 configuration information for both tensorstore and zarr-python
    """

    def __init__(
        self,
        ns: argparse.Namespace,
        selection: str,
        mode: str,
        subpath: Path | str | None = None,
    ):
        self.ns = ns
        self.selection = selection
        self.mode = mode
        self.subpath = None if not subpath else Path(subpath)

        self.overwrite = False
        if selection == "output":
            self.overwrite = ns.output_overwrite

        self.path = getattr(ns, f"{selection}_path")
        self.anon = getattr(ns, f"{selection}_anon")
        self.bucket = getattr(ns, f"{selection}_bucket")
        self.endpoint = getattr(ns, f"{selection}_endpoint")
        self.region = getattr(ns, f"{selection}_region")

        if self.bucket:
            self.ts_store = {
                "driver": "s3",
                "bucket": self.bucket,
                "aws_region": self.region,
            }
            if self.anon:
                self.ts_store["aws_credentials"] = {"anonymous": self.anon}
            if self.endpoint:
                self.ts_store["endpoint"] = self.endpoint

            store_class = zarr.store.RemoteStore
            self.zr_store = store_class(
                url=self.s3_string(),
                anon=self.anon,
                endpoint_url=self.endpoint,
                mode=mode,
            )

        else:
            self.ts_store = {
                "driver": "file",
            }

            store_class = zarr.store.LocalStore
            self.zr_store = store_class(self.fs_string(), mode=mode)

        self.ts_store["path"] = self.fs_string()
        self.ts_config = {
            "driver": "zarr" if selection == "input" else "zarr3",
            "kvstore": self.ts_store,
        }

        self.zr_group = None
        self.zr_attrs = None

    def s3_string(self):
        return f"s3://{self.bucket}/{self.fs_string()}"

    def fs_string(self):
        return str(self.path / self.subpath) if self.subpath else str(self.path)

    def __str__(self):
        if self.bucket:
            return self.s3_string()
        return self.fs_string()

    def __repr__(self):
        return (
            f"Config<{self.__str__()}, {self.selection}, {self.mode}, {self.overwrite}>"
        )

    def check_or_delete_path(self):
        # If this is local, then delete.
        if self.bucket:
            raise Exception(f"bucket set ({self.bucket}). Refusing to delete.")

        if self.path.exists():
            # TODO: This should really be an option on zarr-python
            # as with tensorstore.
            if self.overwrite:
                if self.path.is_file():
                    self.path.unlink()
                else:
                    shutil.rmtree(self.path)
            else:
                raise Exception(
                    f"{self.path} exists. Use --output-overwrite to overwrite"
                )

    def open_group(self):
        # Needs zarr_format=2 or we get ValueError("store mode does not support writing")
        self.zr_group = zarr.open_group(store=self.zr_store, zarr_format=2)
        self.zr_attrs = self.zr_group.attrs

    def create_group(self):
        self.zr_group = zarr.Group.create(self.zr_store)
        self.zr_attrs = self.zr_group.attrs

    def sub_config(self, subpath: str, create_or_open_group: bool = True):
        sub = Config(
            self.ns,
            self.selection,
            self.mode,
            subpath if not self.subpath else self.subpath / subpath,
        )
        if create_or_open_group:
            if sub.selection == "input":
                sub.open_group()
            elif sub.selection == "output":
                sub.create_group()
            else:
                raise Exception(f"unknown selection: {self.selection}")
        return sub

    def ts_read(self):
        return ts.open(self.ts_config).result()

    def zr_write_text(self, path: Path, text: str):
        text = TextBuffer(text)
        filename = self.path / self.subpath / path if self.subpath else self.path / path
        sync(self.zr_store.set(str(filename), text))

    def zr_read_text(self, path: str | Path):
        return sync(
            self.zr_store.get(str(path), prototype=BufferPrototype(TextBuffer, None))
        )


class Location:
    """
    High-level collection of objects and configuration
    options related to a source or target location for conversion.
    """


def convert_array(
    input_config: Config,
    output_config: Config,
    dimension_names: list,
    chunks: list,
    shards: list,
    threads: int,
):
    read = input_config.ts_read()

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

    base_config = output_config.ts_config.copy()
    base_config["metadata"] = {
        "shape": read.shape,
        "chunk_grid": chunk_grid,
        "chunk_key_encoding": {
            "name": "default"
        },  # "configuration": {"separator": "/"}},
        "codecs": codecs,
        "data_type": read.dtype,
        "dimension_names": dimension_names,
    }

    write_config = base_config.copy()
    write_config["create"] = True
    write_config["delete_existing"] = output_config.overwrite

    LOGGER.log(
        5,
        f"""input_config:
{json.dumps(input_config.ts_config, indent=4)}
    """,
    )
    LOGGER.log(
        5,
        f"""write_config:
{json.dumps(write_config, indent=4, cls=SafeEncoder)}
    """,
    )

    verify_config = base_config.copy()

    write = ts.open(write_config).result()

    before = TSMetrics(input_config.ts_config, write_config)

    # read & write a chunk (or shard) at a time:
    blocks = shards if shards is not None else chunks
    for idx, batch in enumerate(Batched(chunk_iter(read.shape, blocks), threads)):
        start = time.time()
        with ts.Transaction() as txn:
            LOGGER.log(5, f"batch {idx:03d}: scheduling transaction size={len(batch)}")
            for slice_tuple in batch:
                write.with_transaction(txn)[slice_tuple] = read[slice_tuple]
                LOGGER.log(
                    5, f"batch {idx:03d}: {slice_tuple} scheduled in transaction"
                )
            LOGGER.log(5, f"batch {idx:03d}: waiting on transaction size={len(batch)}")
        stop = time.time()
        elapsed = stop - start
        avg = float(elapsed) / len(batch)
        LOGGER.debug(
            f"batch {idx:03d}: completed transaction size={len(batch)} in {stop-start:0.2f}s (avg={avg:0.2f})"
        )

    after = TSMetrics(input_config.ts_config, write_config, before)

    LOGGER.info(f"""Re-encode (tensorstore) {input_config} to {output_config}
        read: {after.read()}
        write: {after.written()}
        time: {after.elapsed()}
    """)

    verify = ts.open(verify_config).result()
    LOGGER.info(f"Verifying <{output_config}>\t{read.shape}\t")
    for x in range(10):
        r = tuple([random.randint(0, y - 1) for y in read.shape])
        before = read[r].read().result()
        after = verify[r].read().result()
        assert before == after
        LOGGER.debug(f"{x}")
    LOGGER.info("ok")


def convert_image(
    input_config: Config,
    output_config: Config,
    output_chunks: list[int] | None,
    output_shards: list[int] | None,
    output_read_details: str | None,
    output_write_details: bool,
    output_script: bool,
    threads: int,
):
    dimension_names = None
    # top-level version...
    ome_attrs = {"version": NGFF_VERSION}
    for key, value in input_config.zr_attrs.items():
        # ...replaces all other versions - remove
        strip_version(value)
        if key == "multiscales":
            dimension_names = [axis["name"] for axis in value[0]["axes"]]
            strip_version(value[0])
        ome_attrs[key] = value

    if output_config.zr_group is not None:  # otherwise dry-run
        # dev2: everything is under 'ome' key
        output_config.zr_attrs["ome"] = ome_attrs

    if output_read_details:
        with output_read_details.open() as o:
            details = json.load(o)
    else:
        details = []  # No resolutions yet

    # convert arrays
    multiscales = input_config.zr_attrs.get("multiscales")
    for idx, ds in enumerate(multiscales[0]["datasets"]):
        ds_path = ds["path"]
        ds_array = input_config.zr_group[ds_path]
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
            # Note: not S3 compatible and doesn't use subpath!
            with output_config.path.open(mode="w") as o:
                json.dump(details, o)
        else:
            if output_read_details:
                # read row by row and overwrite
                ds_chunks = details[idx]["chunks"]
                ds_shards = details[idx]["shards"]
            else:
                if output_chunks:
                    ds_chunks = output_chunks
                if output_shards:
                    ds_shards = output_shards
                elif not output_script and math.prod(ds_shards) > 100_000_000:
                    # if we're going to convert, and we guessed the shards,
                    # let's validate the guess...
                    raise ValueError(
                        f"no shard guess: shape={ds_shape}, chunks={ds_chunks}"
                    )

            if output_script:
                chunk_txt = ",".join(map(str, ds_chunks))
                shard_txt = ",".join(map(str, ds_shards))
                dimsn_txt = ",".join(map(str, dimension_names))
                output_config.zr_write_text(
                    Path(ds_path) / "convert.sh",
                    f"zarrs_reencode --chunk-shape {chunk_txt} --shard-shape {shard_txt} --dimension-names {dimsn_txt} --validate {input_config} {output_config}\n",
                )
            else:
                convert_array(
                    input_config.sub_config(ds_path, False),
                    output_config.sub_config(ds_path, False),
                    dimension_names,
                    ds_chunks,
                    ds_shards,
                    threads,
                )

    if not output_write_details:
        # check for labels...
        try:
            labels_config = input_config.sub_config("labels")
        except ValueError:
            # File "../site-packages/zarr/abc/store.py", line 29, in _check_writable
            # raise ValueError("store mode does not support writing")
            LOGGER.debug("No labels group found")
        else:
            labels_attrs = labels_config.zr_attrs.get("labels", [])
            LOGGER.debug("labels_attrs: %s", labels_attrs)
            labels_output_config = output_config.sub_config("labels")
            labels_output_config.zr_attrs["ome"] = dict(labels_config.zr_attrs)

            for label_path in labels_attrs:
                label_config = labels_config.sub_config(label_path)
                label_path_obj = Path("labels") / label_path

                label_output_config = None
                if output_config.zr_group is not None:  # otherwise dry-run
                    label_output_config = output_config.sub_config(label_path_obj)

                convert_image(
                    label_config,
                    label_output_config,
                    output_chunks,
                    output_shards,
                    output_read_details,
                    output_write_details,
                    output_script,
                    threads,
                )


class ROCrateWriter:
    def __init__(
        self,
        name: str = "dataset name",
        description: str = "dataset description",
        data_license: str = "https://creativecommons.org/licenses/by/4.0/",
        organism: str | None = None,
        modality: str | None = None,
    ):
        self.name = name
        self.description = description
        self.data_license = data_license

        # Optional parameters that can be ignored if `process()` is overwritten.
        self.organism = organism
        self.modality = modality

        # Created by generate()
        self.crate = None
        self.zarr_root = None

    def properties(self) -> dict:
        """
        Return a dictionary containing the base properties
        like name, description, and license
        """
        return {
            "name": self.name,
            "description": self.description,
            "licence": self.data_license,
        }

    def generate(self, dataset="./") -> None:
        """
        Create a ZarrCrate object for the given dataset and
        add the default properties.
        """
        self.crate = ZarrCrate()
        self.zarr_root = self.crate.add_dataset(dataset, properties=self.properties())

    def process(self) -> None:
        """
        Post-process the generated ZarrCrate by adding any appropriate metadata.
        By default, if organism and modality were set on construction add those.
        """
        specimen = None
        if self.organism:
            biosample = self.crate.add(
                Biosample(
                    self.crate,
                    properties={"organism_classification": {"@id": self.organism}},
                )
            )
            specimen = self.crate.add(Specimen(self.crate, biosample))

        if specimen and self.modality:
            image_acquisition = self.crate.add(
                ImageAcquistion(
                    self.crate, specimen, properties={"fbbi_id": {"@id": self.modality}}
                )
            )
            self.zarr_root["resultOf"] = image_acquisition

    def write(
        self,
        config: Config,
        filename: str | Path = "ro-crate-metadata.json",
        indent: int = 2,
    ) -> None:
        """
        Use the config location to write a string representation of the metadata to a file.
        """
        self.generate()
        self.process()
        metadata_dict = self.crate.metadata.generate()
        text = json.dumps(metadata_dict, indent=indent)
        config.zr_write_text(filename, text)


def main(ns: argparse.Namespace, rocrate: ROCrateWriter | None = None) -> int:
    """
    Returns the number of images converted
    """
    converted = 0

    input_config = Config(ns, "input", "r")
    output_config = Config(ns, "output", "w")
    output_config.check_or_delete_path()

    input_config.open_group()

    if not ns.output_write_details:
        output_config.create_group()
        if rocrate:
            rocrate.write(output_config)

    # image...
    if input_config.zr_attrs.get("multiscales"):
        convert_image(
            input_config,
            output_config,
            ns.output_chunks,
            ns.output_shards,
            ns.output_read_details,
            ns.output_write_details,
            ns.output_script,
            ns.output_threads,
        )
        converted += 1

    # plate...
    elif plate_attrs := input_config.zr_attrs.get("plate"):
        ome_attrs = {"version": NGFF_VERSION}
        for key, value in input_config.zr_attrs.items():
            # ...replaces all other versions - remove
            strip_version(value)
            ome_attrs[key] = value

        if output_config.zr_group is not None:  # otherwise dry run
            # dev2: everything is under 'ome' key
            output_config.zr_attrs["ome"] = ome_attrs

        wells = plate_attrs.get("wells")

        for well in tqdm.tqdm(
            wells, position=0, desc="i", leave=False, colour="green", ncols=80
        ):
            well_path = well["path"]

            well_input_config = input_config.sub_config(well_path)

            if output_config.zr_group is not None:  # otherwise dry-run
                well_output_config = output_config.sub_config(well_path)
                well_attrs = {}
                for key, value in well_input_config.zr_attrs.items():
                    strip_version(value)
                    well_attrs[key] = value
                    well_attrs["version"] = "0.5"
                well_output_config.zr_attrs["ome"] = well_attrs

            images = well_attrs["well"]["images"]
            for img in tqdm.tqdm(
                images, position=1, desc="j", leave=False, colour="red", ncols=80
            ):
                img_path = Path(well_path) / img["path"]
                img_input_config = input_config.sub_config(img_path)

                if output_config.zr_group is not None:  # otherwise dry-run
                    img_output_config = output_config.sub_config(str(img_path))
                else:
                    img_output_config = None

                convert_image(
                    img_input_config,
                    img_output_config,
                    ns.output_chunks,
                    ns.output_shards,
                    ns.output_read_details,
                    ns.output_write_details,
                    ns.output_script,
                    ns.output_threads,
                )
                converted += 1
    # Note: plates can *also* contain this metadata
    elif layout := input_config.zr_attrs.get("bioformats2raw.layout"):
        assert layout == 3
        ome_attrs = {"version": NGFF_VERSION}
        for key, value in input_config.zr_attrs.items():
            # ...replaces all other versions - remove
            strip_version(value)
            ome_attrs[key] = value

        if output_config.zr_group is not None:  # otherwise dry run
            # dev2: everything is under 'ome' key
            output_config.zr_attrs["ome"] = ome_attrs

        ome_config = input_config.sub_config("OME")
        series = ome_config.zr_attrs.get("series", [])
        assert series  # TODO: support implicit case where OME-XML must be read

        filename = "OME/METADATA.ome.xml"
        ome_xml = input_config.zr_read_text(filename)
        if ome_xml is not None:
            output_config.zr_write_text(filename, ome_xml.text)

        for img_path in tqdm.tqdm(
            series, position=0, desc="i", leave=False, colour="green", ncols=80
        ):
            img_input_config = input_config.sub_config(str(img_path))

            if output_config.zr_group is not None:  # otherwise dry-run
                img_output_config = output_config.sub_config(str(img_path))
            else:
                img_output_config = None

            convert_image(
                img_input_config,
                img_output_config,
                ns.output_chunks,
                ns.output_shards,
                ns.output_read_details,
                ns.output_write_details,
                ns.output_script,
                ns.output_threads,
            )
            converted += 1
    else:
        LOGGER.warning(f"no convertible metadata: {input_config.zr_attrs.keys()}")

    return converted


def cli(args=sys.argv[1:]):
    """
    Parses the arguments contained in `args` and passes
    them to `main`. If no images are converted, raises
    SystemExit. Otherwise, return the number of images.
    """
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
    parser.add_argument(
        "--output-threads",
        type=int,
        default=16,
        help="number of simultaneous write threads",
    )
    parser.add_argument("--rocrate-name", type=str)
    parser.add_argument("--rocrate-description", type=str)
    parser.add_argument("--rocrate-license", type=str)
    parser.add_argument("--rocrate-organism", type=str)
    parser.add_argument("--rocrate-modality", type=str)
    parser.add_argument("--rocrate-skip", action="store_true")
    parser.add_argument(
        "--log", default="warn", help="'error', 'warn', 'info', 'debug' or 'trace'"
    )
    group_ex = parser.add_mutually_exclusive_group()
    group_ex.add_argument(
        "--output-write-details",
        action="store_true",
        help="don't convert array, instead write chunk and proposed shard sizes",
    )
    group_ex.add_argument(
        "--output-read-details", type=Path, help="read chink and shard sizes from file"
    )
    group_ex.add_argument(
        "--output-chunks",
        help="comma separated list of chunk sizes for all subresolutions",
        type=csv_int,
    )
    parser.add_argument(
        "--output-shards",
        help="comma separated list of shards sizes for all subresolutions",
        type=csv_int,
    )
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path)
    ns = parser.parse_args(args)

    # configure logging
    if ns.log.upper() == "TRACE":
        numeric_level = 5
    else:
        numeric_level = getattr(logging, ns.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {ns.log}. Use 'info' or 'debug'")
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    rocrate = None
    if not ns.rocrate_skip:
        setup = {}
        for key in ("name", "description", "license", "organism", "modality"):
            value = getattr(ns, f"rocrate_{key}", None)
            if value:
                setup[key] = value
        rocrate = ROCrateWriter(**setup)

    converted = main(ns, rocrate)
    if converted == 0:
        raise SystemExit(1)
    return converted


if __name__ == "__main__":
    cli(sys.argv[1:])
