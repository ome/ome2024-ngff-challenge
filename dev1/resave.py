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


# remote fails - see below
# path = "https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.4/idr0062A/6001240.zarr"

if os.path.exists(ns.output_path):
    print(f"{ns.output_path} exists. Exiting")
    sys.exit(1)


def convert_array(input_path, output_path):
    read = ts.open({
        'driver': 'zarr',
        'kvstore': {
            'driver': 'file',
            'path': input_path,
        },
    }).result()

    shape = read.shape
    chunks= read.schema.chunk_layout.read_chunk.shape

    write = ts.open({
        "driver": "zarr3",
        "kvstore": {
            "driver": "file",
            "path": output_path
        },
        "metadata": {
            "shape": shape,
            "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": chunks}},
            "chunk_key_encoding": {"name": "default"},
            "codecs": [{"name": "blosc", "configuration": {"cname": "lz4", "clevel": 5}}],
            "data_type": read.dtype,
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
# copy NGFF attrs
for key, value in read_root.attrs.items():
    # update version - needs to happen before writing to root.attrs
    if key == "multiscales":
        value[0]["version"] = "0.5-dev"
    root.attrs[key] = value

# convert arrays
multiscales = read_root.attrs.get("multiscales")
for ds in multiscales[0]["datasets"]:
    ds_path = ds["path"]
    convert_array(
        os.path.join(ns.input_path, ds_path),
        os.path.join(ns.output_path, ds_path)
    )
