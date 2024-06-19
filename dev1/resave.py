#!/usr/bin/env python
import numpy as np
import zarr
import sys
import os

from zarr.codecs import (
    BloscCodec,
    BytesCodec,
    GzipCodec,
    ShardingCodec,
    ShardingCodecIndexLocation,
    TransposeCodec,
    ZstdCodec,
)

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
for key in read_root.attrs.keys():
    root.attrs[key] = read_root.attrs[key]
# update version
root.attrs["multiscales"][0]["version"] = "0.5-dev"

# convert arrays
multiscales = read_root.attrs.get("multiscales")
for ds in multiscales[0]["datasets"]:
    ds_path = ds["path"]
    data = zarr.load(store=read_store, path=ds_path)
    print('array', ds_path, data.shape)
    shard_shape = [64] * data.ndim
    chunk_shape = [64] * data.ndim
    a = root.create_array(str(ds_path), shape=data.shape, chunk_shape=shard_shape, dtype=data.dtype,
                          codecs=[ShardingCodec(chunk_shape=chunk_shape, codecs=[BytesCodec(), BloscCodec()])])
    # These 2 lines are equivalent to e.g. a[:,:] = data (for any number of dimensions)
    # s = [np.s_[:]] * len
    a[:, :] = data
