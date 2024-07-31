# ome2024-ngff-challenge

Project planning and material repository for the 2024 challenge to generate 1 PB of OME-Zarr data

## Challenge overview

The high-level goal of the challenge is to generate OME-Zarr data according to a development
version of the specification to drive forward the implementation work and establish a baseline
for the conversion costs that members of the community can expect to incur.

Data generated within the challenge will have:

* all v2 arrays converted to v3, optionally sharding the data
* all .zattrs metadata migrated to `zarr.json["attributes"]["ome"]`
* a top-level `ro-crate-metadata.json` file with minimal metadata (specimen and imaging modality)

## Converting your data

### Getting started

The `dev2/resave.py` script can be used to convert an OME-Zarr 0.4 dataset
that is based on Zarr v2:

```
dev2/resave.py input.zarr output.zarr
```

If you would like to re-run the script with different parameters, you can additionally
set `--output-overwrite` to ignore a previous conversion:

```
dev2/resave.py input.zarr output.zarr --output-overwrite
```

### Writing metadata

The RO-Crate metadata writing code is not currently enabled by default. To generate the
metadata, use:

```
PYTHONPATH=dev3/zarr-crate dev2/resave.py input.zarr ouput.zarr --output-rocrate
```

### Reading/writing remotely

If you would like to avoid downloading and/or upload the Zarr datasets, you can set S3
parameters on the command-line which will then treat the input and/or output datasets
as a prefix within an S3 bucket:

```
dev2/resave.py \
        --input-bucket=BUCKET \
        --input-endpoint=HOST \
        --input-anon \
        input.zarr \
        output.zarr
```

A small example you can try yourself:

```
dev2/resave.py \
        --input-bucket=idr \
        --input-endpoint=https://uk1s3.embassy.ebi.ac.uk \
        --input-anon \
        zarr/v0.4/idr0062A/6001240.zarr \
        /tmp/6001240.zarr
```

### Optimizing chunks and shards

Finally, there is not yet a single heuristic for determining the chunk and shard sizes
that will work for all data. Instead, you can use a JSON file to review and manually
optimize the chunking and sharding parameters:

```
dev2/resave.py input.zarr parameters.json --output-write-details
```

This will write a JSON file of the form:

```
[{"shape": [...], "chunks": [...], "shards": [...]}, ...
```

Edits to this file can be read back in using the `output-read-details` flag:

```
dev2/resave.py input.zarr output.zarr --output-read-details=parameters.json
```

Note: Changes to the shape are ignored.


## Related work

The following additional PRs are required to work with the data
created by the scripts in this repository:

 * https://github.com/ome/ome-ngff-validator/pull/36
 * https://github.com/ome/ome-zarr-py/pull/383
 * https://github.com/hms-dbmi/vizarr/pull/172
 * https://github.com/LDeakin/zarrs_tools/issues/8

 Slightly less related but important at the moment:

 * https://github.com/google/neuroglancer/issues/606
 * https://github.com/ome/napari-ome-zarr/pull/112
 * https://github.com/zarr-developers/zarr-python/issues/2029
