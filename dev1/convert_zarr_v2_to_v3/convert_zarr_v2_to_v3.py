import numpy as np
import os.path
from ome_zarr.io import parse_url
from ome_zarr.reader import Reader
import shutil
import zarr
import zarrita
from zarrita.codecs import blosc_codec, bytes_codec

from dev1.convert_zarr_v2_to_v3.util import *


def convert_zarr_v2_to_v3(input_url, output_url, is_root=True):
    # Uses Zarr v2 for reading, Zarr(ita) v3 for writing
    # reader
    input_root = zarr.open_group(store=input_url)  # does not seem to support https URLs
    print(f"Processing {input_root.store.path}")

    if is_root:
        if input_root:
            if os.path.exists(output_url):
                # work-around for overwrite: delete existing output
                shutil.rmtree(output_url)
            root = zarrita.Group.create(store=output_url)
            root.update_attributes(update_omezarr_attributes(input_root.attrs.asdict()))
        else:
            raise FileNotFoundError(f"Error parsing {input_url}")

    # writer
    for label in input_root:
        content = input_root[label]
        input_path = input_url + content.name
        output_path = output_url + content.name
        if isinstance(content, zarr.Group):
            # create zarr group
            zarrita.Group.create(
                store=output_path,
                attributes=update_omezarr_attributes(content.attrs.asdict()),
            )
            convert_zarr_v2_to_v3(input_path, output_path, is_root=False)
        elif isinstance(content, zarr.Array):
            codecs = [bytes_codec(), blosc_codec(typesize=4)]
            output_array = zarrita.Array.create(
                output_path,
                shape=content.shape,
                chunk_shape=content.chunks,
                dtype=content.dtype,
                codecs=codecs,
                attributes=update_omezarr_attributes(content.attrs.asdict()),
            )
            output_array[:] = content
        else:
            print(f"Unsupported content {content}")


def convert_ome_zarr_v2_to_v3(input_url, output_url):
    # Uses Ome-Zarr v2 for reading, Zarr(ita) v3 for writing
    location = parse_url(input_url)  # supports https URLs*
    if location is None:
        # * under particular conditions the URL/zarr is not detected (internal .exists() returns False)
        # caused by OS / PyCharm / version / pytest?
        raise FileNotFoundError(f"Error parsing {input_url}")

    reader = Reader(location)
    input_root_path = os.path.normpath(reader.zarr.path)

    if os.path.exists(output_url):
        # work-around for overwrite: delete existing output
        shutil.rmtree(output_url)

    for image_node in reader():
        print(f"Processing {image_node}")
        metadata = image_node.metadata
        axes = metadata.get("axes", [])
        dimension_order = "".join([axis.get("name") for axis in axes])
        output_path = os.path.normpath(image_node.zarr.path).replace(
            input_root_path, output_url
        )
        output_store_path = zarrita.store.make_store_path(output_path)
        # create zarr group
        output_zarr = zarrita.Group.create(
            store=output_store_path,
            attributes=update_omezarr_attributes(image_node.zarr.root_attrs),
        )

        for level, data in enumerate(image_node.data):
            codecs = [bytes_codec(), blosc_codec(typesize=4)]
            # create zarr array
            output_array = output_zarr.create_array(
                str(level),
                shape=data.shape,
                chunk_shape=data.chunksize,
                dtype=data.dtype,
                codecs=codecs,
            )
            output_array[:] = np.array(
                data
            )  # set only supports ndarray; TODO: wrap inside (dask) chunking?


if __name__ == "__main__":
    # input_url = 'D:/slides/6001240.zarr'
    input_url = "https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.4/idr0062A/6001240.zarr"
    output_url = "D:/slides/test/" + os.path.basename(input_url)

    # convert_zarr_v2_to_v3(input_url, output_url)

    convert_ome_zarr_v2_to_v3(input_url, output_url)

    print("done")
