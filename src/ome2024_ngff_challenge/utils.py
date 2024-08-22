#!/usr/bin/env python
from __future__ import annotations

import argparse
import itertools
import json
import logging
import shutil
import time
from importlib.metadata import version as lib_version
from pathlib import Path

import numpy as np
import tensorstore as ts
import zarr
from zarr.api.synchronous import sync
from zarr.buffer import Buffer, BufferPrototype


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


def configure_logging(ns: argparse.Namespace, logger: logging.Logger):
    if ns.log.upper() == "TRACE":
        numeric_level = 5
    else:
        numeric_level = getattr(logging, ns.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {ns.log}. Use 'info' or 'debug'")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.setLevel(numeric_level)


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


def add_creator(json_dict: dict, notes: str | None = None) -> None:
    # Add _creator - NB: this will overwrite any existing _creator info
    pkg_version = lib_version("ome2024-ngff-challenge")
    json_dict["_creator"] = {
        "name": "ome2024-ngff-challenge",
        "version": pkg_version,
        "notes": notes,
    }
    if notes:
        json_dict["_creator"]["notes"] = notes


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

    def is_s3(self):
        return bool(self.bucket)

    def s3_endpoint(self):
        """
        Returns a representation of the S3 endpoint set on this configuration.

          * "" if this is not an S3 configuration
          * "default" if no explicit endpoint is set
          * otherwise the URL is returned
        """
        if self.is_s3():
            if self.endpoint:
                return self.endpoint
            return "default"
        return ""

    def __str__(self):
        if self.is_s3():
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
        filename = self.subpath / path if self.subpath else path
        sync(self.zr_store.set(str(filename), text))

    def zr_read_text(self, path: str | Path):
        return sync(
            self.zr_store.get(str(path), prototype=BufferPrototype(TextBuffer, None))
        )
