#!/usr/bin/env python
import numpy as np
import zarr
import sys
import os

import tensorstore as ts

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("input_path")
parser.add_argument("output_path")
ns = parser.parse_args()


if os.path.exists(ns.output_path):
    print(f"{ns.output_path} exists. Exiting")
    sys.exit(1)


def convert_array(input_path, output_path, dimension_names):
    read = ts.open({
        'driver': 'zarr',
        'kvstore': {
            'driver': 'file',
            'path': input_path,
        },
    }).result()

    shape = read.shape
    chunks = read.schema.chunk_layout.read_chunk.shape

    # bigger_chunk includes 2 of the regular chunks
    bigger_chunk = list(chunks[:])
    bigger_chunk[0] = bigger_chunk[0] * 2

    # sharding breaks bigger_chunk down into regular chunks
    # https://google.github.io/tensorstore/driver/zarr3/index.html#json-driver/zarr3/Codec/sharding_indexed
    sharding_codec = {
        "name": "sharding_indexed",
        "configuration": {
            "chunk_shape": chunks,
            "codecs": [{"name": "bytes", "configuration": {"endian": "little"}},
                       {"name": "gzip", "configuration": {"level": 5}}],
            "index_codecs": [{"name": "bytes", "configuration": {"endian": "little"}},
                             {"name": "crc32c"}],
            "index_location": "end"
        }
    }

    codecs = [sharding_codec]

    # Alternative without sharding...
    # blosc_codec = {"name": "blosc", "configuration": {
    #     "cname": "lz4", "clevel": 5}}
    # codecs = [blosc_codec]

    write = ts.open({
        "driver": "zarr3",
        "kvstore": {
            "driver": "file",
            "path": output_path
        },
        "metadata": {
            "shape": shape,
            "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": bigger_chunk}},
            "chunk_key_encoding": {"name": "default"},
            "codecs": codecs,
            "data_type": read.dtype,
            "dimension_names": dimension_names,
        },
        "create": True,
    }).result()

    future = write.write(read)
    future.result()


store_class = zarr.store.LocalStore
if ns.input_path.startswith("http"):
    # TypeError: Can't instantiate abstract class RemoteStore with abstract methods get_partial_values, list, list_dir, list_prefix, set_partial_values
    store_class = zarr.store.RemoteStore
read_store = store_class(ns.input_path, mode="r")
# Needs zarr_format=2 or we get ValueError("store mode does not support writing")
read_root = zarr.open_group(store=read_store, zarr_format=2)

# Create new Image...
write_store = zarr.store.LocalStore(ns.output_path, mode="w")
root = zarr.Group.create(write_store)
dimension_names = None
# top-level version...
ome_attrs = {"version": "0.5-dev2"}
for key, value in read_root.attrs.items():
    # ...replaces all other versions - remove
    if "version" in value:
        del (value["version"])
    if key == "multiscales":
        dimension_names = [axis["name"] for axis in value[0]["axes"]]
        if "version" in value[0]:
            del (value[0]["version"])
    ome_attrs[key] = value
# dev2: everything is under 'ome' key
root.attrs["ome"] = ome_attrs

# convert arrays
multiscales = read_root.attrs.get("multiscales")
for ds in multiscales[0]["datasets"]:
    ds_path = ds["path"]
    convert_array(
        os.path.join(ns.input_path, ds_path),
        os.path.join(ns.output_path, ds_path),
        dimension_names,
    )
