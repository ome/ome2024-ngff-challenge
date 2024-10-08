from __future__ import annotations

import argparse
import csv
from pathlib import Path

import requests

# Usage: python load_zarr_stats.py <csv_file>

# E.g. $ for idr in 10 11 12 15 26 33 35 36 54; do python load_zarr_stats.py idr00$(echo $idr)_samples.csv; done


def format_bytes_human_readable(num_bytes):
    unit = None
    for u in ["B", "KB", "MB", "GB", "TB"]:
        unit = u
        if num_bytes < 1024.0:
            break
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} {unit}"


def get_array_values(zarr_url, multiscales):
    # we want chunks, shards, shape from first resolution level...
    # but we want total 'written' bytes for all resolutions...
    dict_data = None
    for ds in multiscales[0]["datasets"]:
        array_url = zarr_url + "/" + ds["path"]
        array_json = requests.get(array_url + "/zarr.json").json()
        if dict_data is None:
            dict_data = get_chunk_and_shard_shapes(array_json)
            dict_data["written"] = 0
        stats = array_json.get("attributes", {}).get(
            "_ome2024_ngff_challenge_stats", {}
        )
        dict_data["written"] = dict_data["written"] + stats.get("written", 0)
    return dict_data


def get_chunk_and_shard_shapes(zarray):
    """Returns dict with 'shape', 'chunks' and 'shards' keys (if shards are present)"""
    if "chunks" in zarray:
        # For zarr v2 we just have chunks:
        return {"chunks": zarray["chunks"], "shape": zarray["shape"]}
    # For zarr v3 we check for sharding
    # Based on https://github.com/zarr-developers/zarr-specs/blob/main/docs/v3/codecs/sharding-indexed/v1.0.rst#configuration-parameters
    chunk_shape = (
        zarray.get("chunk_grid", {}).get("configuration", {}).get("chunk_shape")
    )
    sharding_codecs = [
        codec
        for codec in zarray.get("codecs", [])
        if codec.get("name") == "sharding_indexed"
    ]
    if len(sharding_codecs) > 0:
        sub_chunks = (
            sharding_codecs[0].get("configuration", {}).get("chunk_shape")
            if sharding_codecs
            else None
        )
        # if we have sharding, a 'chunk' is the sub-chunk of a shard
        if sub_chunks:
            return {
                "chunks": sub_chunks,
                "shards": chunk_shape,
                "shape": zarray["shape"],
            }
    return {"chunks": chunk_shape, "shape": zarray["shape"]}


# ...so we resort to using plain requests for now...
# load zarr.json for each row...
def load_zarr(zarr_url):
    response = requests.get(zarr_url + "/zarr.json").json()
    ome_json = response.get("attributes", {}).get("ome", {})
    multiscales = ome_json.get("multiscales")
    plate = ome_json.get("plate")
    bf2raw = ome_json.get("bioformats2raw.layout")
    if multiscales is not None:
        return get_array_values(zarr_url, multiscales)
    if plate is not None:
        # let's try to get average 'written' for first 5 wells...
        written_values = []
        for well in plate["wells"][:5]:
            field_path = f"{well['path']}/0"
            plate_img_json = requests.get(
                zarr_url + "/" + field_path + "/zarr.json"
            ).json()
            plate_ome_json = plate_img_json.get("attributes", {}).get("ome", {})
            plate_img = plate_ome_json.get("multiscales")
            stats = get_array_values(zarr_url + "/" + field_path, plate_img)
            if stats.get("written", 0) > 0:
                written_values.append(stats.get("written"))
        avg_written = (
            sum(written_values) / len(written_values) if len(written_values) > 0 else 0
        )
        image_count = len(plate["wells"] * plate.get("field_count", 1))
        # we want to return the total written bytes for all images...
        stats["written"] = avg_written * image_count
        return stats
    if bf2raw:
        # let's just get the first image...
        bf_img_json = requests.get(zarr_url + "/0/zarr.json").json()
        bf_img_ms = bf_img_json.get("attributes", {}).get("ome", {}).get("multiscales")
        return get_array_values(zarr_url + "/0", bf_img_ms)
    return {}


parser = argparse.ArgumentParser(description="Process zarr urls in csv files")
parser.add_argument("csv_name", help="csv file to process")
args = parser.parse_args()

csv_name = args.csv_name
output_csv = csv_name.replace(".csv", "_output.csv")

column_names = []
column_data = []
# open a local csv file and iterate through rows...
with Path(csv_name).open(newline="") as csvfile:
    csvreader = csv.reader(csvfile, delimiter=",")
    url_col = None
    for row in csvreader:
        if len(row) == 0:
            continue
        if url_col is None:
            # search for url column and skip row if found
            if "url" in row:
                column_names = row
                url_col = row.index("url")
                continue
            else:
                column_names = ["url"]
                url_col = 0

        zarr_url = row[url_col]
        if zarr_url.endswith(".csv"):
            continue
        stats = load_zarr(zarr_url)
        row.append(stats.get("written", 0))
        row.append(format_bytes_human_readable(stats.get("written", 0)))
        column_data.append(row)

        # in case script fails mid-way, we write as we go...
        with Path(output_csv).open("a", newline="") as outfile:
            csvwriter = csv.writer(outfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
            csvwriter.writerow(row)

# Update the csv file with the new column
column_names = [*column_names, "written", "written_human_readable"]

with Path(output_csv).open("w", newline="") as csvfile:
    csvwriter = csv.writer(csvfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow(column_names)
    for row in column_data:
        csvwriter.writerow(row)
