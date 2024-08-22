# ome2024-ngff-challenge

[![Actions Status][actions-badge]][actions-link]
[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]
[![Image.SC Zulip][zulip-badge]][zulip-link]

<!-- SPHINX-START -->

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/ome/ome2024-ngff-challenge/workflows/CI/badge.svg
[actions-link]:             https://github.com/ome/ome2024-ngff-challenge/actions
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/ome2024-ngff-challenge
[conda-link]:               https://github.com/conda-forge/ome2024-ngff-challenge-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/ome/ome2024-ngff-challenge/discussions
[pypi-link]:                https://pypi.org/project/ome2024-ngff-challenge/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/ome2024-ngff-challenge
[pypi-version]:             https://img.shields.io/pypi/v/ome2024-ngff-challenge
[rtd-badge]:                https://readthedocs.org/projects/ome2024-ngff-challenge/badge/?version=latest
[rtd-link]:                 https://ome2024-ngff-challenge.readthedocs.io/en/latest/?badge=latest
[zulip-badge]:              https://img.shields.io/badge/zulip-join_chat-brightgreen.svg
[zulip-link]:               https://imagesc.zulipchat.com/#narrow/stream/328251-NGFF

<!-- prettier-ignore-end -->

Project planning and material repository for the 2024 challenge to generate 1 PB
of OME-Zarr data

## Challenge overview

The high-level goal of the challenge is to generate OME-Zarr data according to a
development version of the specification to drive forward the implementation
work and establish a baseline for the conversion costs that members of the
community can expect to incur.

Data generated within the challenge will have:

- all v2 arrays converted to v3, optionally sharding the data
- all .zattrs metadata migrated to `zarr.json["attributes"]["ome"]`
- a top-level `ro-crate-metadata.json` file with minimal metadata (specimen and
  imaging modality)

You can example the contents of a sample dataset by using
[the minio client](https://github.com/minio/mc):

```
$ mc config host add uk1anon https://uk1s3.embassy.ebi.ac.uk "" ""
Added `uk1anon` successfully.
$ mc ls -r uk1anon/idr/share/ome2024-ngff-challenge/0.0.5/6001240.zarr/
[2024-08-01 14:24:35 CEST]  24MiB STANDARD 0/c/0/0/0/0
[2024-08-01 14:24:28 CEST]   598B STANDARD 0/zarr.json
[2024-08-01 14:24:32 CEST] 6.0MiB STANDARD 1/c/0/0/0/0
[2024-08-01 14:24:28 CEST]   598B STANDARD 1/zarr.json
[2024-08-01 14:24:29 CEST] 1.6MiB STANDARD 2/c/0/0/0/0
[2024-08-01 14:24:28 CEST]   592B STANDARD 2/zarr.json
[2024-08-01 14:24:28 CEST] 1.2KiB STANDARD ro-crate-metadata.json
[2024-08-01 14:24:28 CEST] 2.7KiB STANDARD zarr.json
```

The dataset (from idr0062) can be inspected using a development version of the
OME-NGFF Validator available at
<https://deploy-preview-36--ome-ngff-validator.netlify.app/?source=https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/0.0.5/6001240.zarr>

Other samples:

- [4496763.zarr](https://deploy-preview-36--ome-ngff-validator.netlify.app/?source=https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/4496763.zarr)
  Shape `4,25,2048,2048`, Size `589.81 MB`, from idr0047.
- [9822152.zarr](https://deploy-preview-36--ome-ngff-validator.netlify.app/?source=https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/0.0.5/9822152.zarr)
  Shape `1,1,1,93184,144384`, Size `21.57 GB`, from idr0083.
- [9846151.zarr](https://deploy-preview-36--ome-ngff-validator.netlify.app/?source=https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/0.0.5/9846151.zarr)
  Shape `1,3,1402,5192,2947`, Size `66.04 GB`, from idr0048.
- [Week9_090907.zarr](https://deploy-preview-36--ome-ngff-validator.netlify.app/?source=https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/0.0.5/idr0035/Week9_090907.zarr)
  plate from idr0035.
- [l4_sample/color](https://deploy-preview-36--ome-ngff-validator.netlify.app/?source=https://data-humerus.webknossos.org/data/zarr3_experimental/scalable_minds/l4_sample/color)
  from WebKnossos.

 <details><summary>Expand for more details on creation of these samples</summary>

<hr>

`4496763.json` was created with ome2024-ngff-challenge commit `0e1809bf3b`.

First the config details were generated with:

```
$ ome2024-ngff-challenge --input-bucket=idr --input-endpoint=https://uk1s3.embassy.ebi.ac.uk --input-anon zarr/v0.4/idr0047A/4496763.zarr params_4496763.json --output-write-details
```

The `params_4496763.json` file was edited to set "shards" to:
`[4, 1, sizeY, sizeX]` for each pyramid resolution to create a single shard for
each Z section.

```
# params_4496763.json
[{"shape": [4, 25, 2048, 2048], "chunks": [1, 1, 2048, 2048], "shards": [4, 1, 2048, 2048]}, {"shape": [4, 25, 1024, 1024], "chunks": [1, 1, 1024, 1024], "shards": [4, 1, 1024, 1024]}, {"shape": [4, 25, 512, 512], "chunks": [1, 1, 512, 512], "shards": [4, 1, 512, 512]}, {"shape": [4, 25, 256, 256], "chunks": [1, 1, 256, 256], "shards": [4, 1, 256, 256]}, {"shape": [4, 25, 128, 128], "chunks": [1, 1, 128, 128], "shards": [4, 1, 128, 128]}, {"shape": [4, 25, 64, 64], "chunks": [1, 1, 64, 64], "shards": [4, 1, 64, 64]}]
```

This was then used to run the conversion:

```
ome2024-ngff-challenge --input-bucket=idr --input-endpoint=https://uk1s3.embassy.ebi.ac.uk --input-anon zarr/v0.4/idr0047A/4496763.zarr 4496763.zarr --output-read-details params_4496763.json
```

<hr>

`9822152.zarr` was created with ome2024-ngff-challenge commit `f17a6de963`.

The chunks and shard shapes are specified to be the same for all resolution
levels. This is required since the smaller resolution levels of the source image
at
https://ome.github.io/ome-ngff-validator/?source=https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.4/idr0083A/9822152.zarr
have chunks that correspond to the resolution shape, e,g, `1,1,1,91,141` and
this will fail to convert using a shard shape of `1,1,1,4096,4096`.

Took 34 minutes to run conversion with this command:

```
$ ome2024-ngff-challenge --input-bucket=idr --input-endpoint=https://uk1s3.embassy.ebi.ac.uk --input-anon zarr/v0.4/idr0083A/9822152.zarr 9822152.zarr --output-shards=1,1,1,4096,4096 --output-chunks=1,1,1,1024,1024 --log debug
```

<hr>

Took 9 hours to run this conversion:

```
$ ome2024-ngff-challenge 9846151.zarr/0 will/9846151_2D_chunks_3.zarr --output-shards=1,1,1,4096,4096 --output-chunks=1,1,1,1024,1024 --log debug
```

<hr>

Plate conversion, took 19 minutes, choosing a shard size that contained a whole
image. Image shape is `1,3,1,1024,1280`.

```
$ ome2024-ngff-challenge --input-bucket=bia-integrator-data --input-endpoint=https://uk1s3.embassy.ebi.ac.uk --input-anon S-BIAD847/0762bf96-4f01-454d-9b13-5c8438ea384f/0762bf96-4f01-454d-9b13-5c8438ea384f.zarr /data/will/idr0035/Week9_090907.zarr --output-shards=1,3,1,1024,2048 --output-chunks=1,1,1,1024,1024 --log debug
```

 </details>

## CLI Commands

### `resave`: convert your data

The `ome2024-ngff-challenge` tool can be used to convert an OME-Zarr 0.4 dataset
that is based on Zarr v2. The input data will **not be modified** in any way and
a full copy of the data will be created at the chosen location.

#### Getting started

```
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr
```

is the most basic invocation of the tool. If you do not choose a license, the
application will fail with:

```
No license set. Choose one of the Creative Commons license (e.g., `--cc-by`) or skip RO-Crate creation (`--rocrate-skip`)
```

#### Licenses

There are several license options to choose from. We suggest one of:

- `--cc-by` credit must be given to the creator
- `--cc0`: Add your data to the public domain

Alternatively, you can choose your own license, e.g.,

`--rocrate-license=https://creativecommons.org/licenses/by-nc/4.0/`

to restrict commercial use of your data. Additionally, you can disable metadata
collection at all.

**Note:** you will need to add metadata later for your dataset to be considered
valid.

#### Metadata

There are four additional fields of metadata that are being collected for the
challenge:

- organism and modality: RECOMMENDED
- name and description: SUGGESTED

These can be set via the properties prefixed with `--rocrate-` since they will
be stored in the standard [RO-Crate](https://w3id.org/ro/crate/) JSON file
(`./ro-crate-metadata.json`) at the top-level of the Zarr dataset.

```
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --rocrate-organism=NCBI:txid9606      # Human
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --rocrate-modality=obo:FBbi_00000369  # SPIM
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --rocrate-name="your name here"
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --rocrate-description="and a longer description"
```

For other examples including severa other NCBI and FBbi terms, please see:

```
ome2024-ngff-challenge resave --help
```

#### Re-running the script

If you would like to re-run the script with different parameters, you can
additionally set `--output-overwrite` to ignore a previous conversion:

```
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --output-overwrite
```

#### Writing in parallel

By default, 16 chunks of data will be processed simultaneously in order to bound
memory usage. You can increase this number based on your local resources:

```
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --output-threads=128
```

#### Reading/writing remotely

If you would like to avoid downloading and/or upload the Zarr datasets, you can
set S3 parameters on the command-line which will then treat the input and/or
output datasets as a prefix within an S3 bucket:

```
ome2024-ngff-challenge resave --cc-by \
        --input-bucket=BUCKET \
        --input-endpoint=HOST \
        --input-anon \
        input.zarr \
        output.zarr
```

A small example you can try yourself:

```
ome2024-ngff-challenge resave --cc-by \
        --input-bucket=idr \
        --input-endpoint=https://uk1s3.embassy.ebi.ac.uk \
        --input-anon \
        zarr/v0.4/idr0062A/6001240.zarr \
        /tmp/6001240.zarr
```

#### Reading/writing via a script

Another R/W option is to have `resave.py` generate a script which you can
execute later. If you pass `--output-script`, then rather than generate the
arrays immediately, a file named `convert.sh` will be created which can be
executed later.

For example, running:

```
ome2024-ngff-challenge resave --cc-by dev2/input.zarr /tmp/scripts.zarr --output-script
```

produces a dataset with one `zarr.json` file and 3 `convert.sh` scripts:

```
/tmp/scripts.zarr/0/convert.sh
/tmp/scripts.zarr/1/convert.sh
/tmp/scripts.zarr/2/convert.sh
```

Each of the scripts contains a statement of the form:

```
zarrs_reencode --chunk-shape 1,1,275,271 --shard-shape 2,236,275,271 --dimension-names c,z,y,x --validate dev2/input.zarr /tmp/scripts.zarr
```

Running this script will require having installed `zarrs_tools` with:

```
cargo install zarrs_tools
export PATH=$PATH:$HOME/.cargo/bin
```

#### Optimizing chunks and shards

Finally, there is not yet a single heuristic for determining the chunk and shard
sizes that will work for all data. Pass the `--output-chunks` and
`--output-shards` flags in order to set the size of chunks and shards for all
resolutions:

```
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --output-chunks=1,1,1,256,256 --output-shards=1,1,1,2048,2048
```

Alternatively, you can use a JSON file to review and manually optimize the
chunking and sharding parameters on a per-resolution basis:

```
ome2024-ngff-challenge resave --cc-by input.zarr parameters.json --output-write-details
```

This will write a JSON file of the form:

```
[{"shape": [...], "chunks": [...], "shards": [...]}, ...
```

where the order of the dictionaries matches the order of the "datasets" field in
the "multiscales". Edits to this file can be read back in using the
`output-read-details` flag:

```
ome2024-ngff-challenge resave --cc-by input.zarr output.zarr --output-read-details=parameters.json
```

Note: Changes to the shape are ignored.

#### More information

See `ome2024-ngff-challenge resave -h` for more arguments and examples.

### `lookup`: finding ontology terms (WIP)

The `ome2024-ngff-challenge` tool can also be used to look up terms from the EBI
OLS for setting metadata fields like `--rocrate-modality` and
`--rocrate-organism`:

```
ome2024-ngff-challenge lookup "homo sapiens"
ONTOLOGY  	TERM                	LABEL                         	DESCRIPTION
ncbitaxon 	NCBITaxon_9606      	Homo sapiens
vto       	VTO_0011993         	Homo sapiens
snomed    	SNOMED_337915000    	Homo sapiens
...
```

## Related work

The following additional PRs are required to work with the data created by the
scripts in this repository:

- https://github.com/ome/ome-ngff-validator/pull/36
- https://github.com/ome/ome-zarr-py/pull/383
- https://github.com/hms-dbmi/vizarr/pull/172
- https://github.com/LDeakin/zarrs_tools/issues/8

Slightly less related but important at the moment:

- https://github.com/google/neuroglancer/issues/606
- https://github.com/ome/napari-ome-zarr/pull/112
- https://github.com/zarr-developers/zarr-python/issues/2029
