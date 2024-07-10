#!/usr/bin/env python
import numpy as np
import zarr
import sys
import os

import tensorstore as ts

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--input-bucket")
parser.add_argument("--input-endpoint")
parser.add_argument("--input-anon", action="store_true")
parser.add_argument("--input-region", default="us-east-1")
parser.add_argument("--input-overwrite", action="store_true")
parser.add_argument("--output-bucket")
parser.add_argument("--output-endpoint")
parser.add_argument("--output-anon", action="store_true")
parser.add_argument("--output-region", default="us-east-1")
parser.add_argument("--output-overwrite", action="store_true")
parser.add_argument("input_path")
parser.add_argument("output_path")
ns = parser.parse_args()


if os.path.exists(ns.output_path):
    if ns.input_overwrite:
        import shutil
        shutil.rmtree(ns.output_path)
    else:
        print(f"{ns.output_path} exists. Exiting")
        sys.exit(1)


def create_configs(ns):
    configs = []
    for selection in ("input", "output"):
        anon = getattr(ns, f"{selection}_anon")
        bucket = getattr(ns, f"{selection}_bucket")
        endpoint = getattr(ns, f"{selection}_endpoint")
        region = getattr(ns, f"{selection}_region")

        if bucket:
            store = {
                'driver': 's3',
                'bucket': bucket,
                'aws_region': region,
            }
            if anon:
                store['aws_credentials'] = { 'anonymous': anon }
            if endpoint:
                store["endpoint"] = endpoint
        else:
            store = {
                'driver': 'file',
            }
        configs.append(store)
    return configs

CONFIGS = create_configs(ns)

def convert_array(input_path: str, output_path: str, dimension_names):

    CONFIGS[0]["path"] = input_path
    CONFIGS[1]["path"] = output_path

    read = ts.open({
        'driver': 'zarr',
        'kvstore': CONFIGS[0],
    }).result()

    shape = read.shape
    chunks = read.schema.chunk_layout.read_chunk.shape

    # # bigger_chunk includes 2 of the regular chunks
    # bigger_chunk = list(chunks[:])
    # bigger_chunk[0] = bigger_chunk[0] * 2

    # # sharding breaks bigger_chunk down into regular chunks
    # # https://google.github.io/tensorstore/driver/zarr3/index.html#json-driver/zarr3/Codec/sharding_indexed
    # sharding_codec = {
    #     "name": "sharding_indexed",
    #     "configuration": {
    #         "chunk_shape": chunks,
    #         "codecs": [{"name": "bytes", "configuration": {"endian": "little"}},
    #                    {"name": "gzip", "configuration": {"level": 5}}],
    #         "index_codecs": [{"name": "bytes", "configuration": {"endian": "little"}},
    #                          {"name": "crc32c"}],
    #         "index_location": "end"
    #     }
    # }

    # codecs = [sharding_codec]
    # chunks = bigger_chunk

    # Alternative without sharding...
    blosc_codec = {"name": "blosc", "configuration": {
        "cname": "lz4", "clevel": 5}}
    codecs = [blosc_codec]

    write = ts.open({
        "driver": "zarr3",
        "kvstore": CONFIGS[1],
        "delete_existing": ns.output_overwrite,
        "metadata": {
            "shape": shape,
            "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": chunks}},
            "chunk_key_encoding": {"name": "default"},
            "codecs": codecs,
            "data_type": read.dtype,
            "dimension_names": dimension_names,
        },
        "create": True,
    }).result()

    future = write.write(read)
    future.result()

def convert_image(read_root, input_path, write_root, output_path):
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
    write_root.attrs["ome"] = ome_attrs

    # convert arrays
    multiscales = read_root.attrs.get("multiscales")
    for ds in multiscales[0]["datasets"]:
        ds_path = ds["path"]
        convert_array(
            os.path.join(input_path, ds_path),
            os.path.join(output_path, ds_path),
            dimension_names,
        )



STORES = []
for config, path, mode in (
        (CONFIGS[0], ns.input_path, "r"),
        (CONFIGS[1], ns.output_path, "w")
    ):
    if config["bucket"]:
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
    STORES.append(store)

# Needs zarr_format=2 or we get ValueError("store mode does not support writing")
read_root = zarr.open_group(store=STORES[0], zarr_format=2)

write_store = STORES[1]
write_root = zarr.Group.create(write_store)

# image...
if read_root.attrs.get("multiscales"):
    convert_image(read_root, ns.input_path, write_root, ns.output_path)

# plate...
elif read_root.attrs.get("plate"):

    ome_attrs = {"version": "0.5-dev2"}
    for key, value in read_root.attrs.items():
        # ...replaces all other versions - remove
        if "version" in value:
            del (value["version"])
        ome_attrs[key] = value
    # dev2: everything is under 'ome' key
    write_root.attrs["ome"] = ome_attrs

    plate_attrs = read_root.attrs.get("plate")
    for well in plate_attrs.get("wells"):
        well_path = well["path"]
        well_v2 = zarr.open_group(store=read_store, path=well_path, zarr_format=2)
        well_group = write_root.create_group(well_path)
        # well_attrs = { k:v for (k,v) in well_v2.attrs.items()}
        # TODO: do we store 'version' in well?
        well_attrs = {}
        for key, value in well_v2.attrs.items():
            if "version" in value:
                del (value["version"])
            well_attrs[key] = value
        well_group.attrs["ome"] = well_attrs

        for img in well_attrs["well"]["images"]:
            img_path = well_path + "/" + img["path"]
            out_path = os.path.join(ns.output_path, img_path)
            input_path = os.path.join(ns.input_path, img_path)
            print("img_path", img_path)
            img_v2 = zarr.open_group(store=read_store, path=img_path, zarr_format=2)
            # print('img_v2', { k:v for (k,v) in img_v2.attrs.items()})
            convert_image(img_v2, input_path, out_path)
