# ome2024-ngff-challenge
Project planning and material repository for the 2024 challenge to generate 1 PB of OME-Zarr data

## Upgrading your data

* Convert v2 arrays to v3, optionally sharding the data
* Migrate all .zattrs metadata to `zarr.json["attributes"]["ome"]`

## Related work

The following additional PRs are required to work with the data
created by the scripts in this repository:

 * https://github.com/ome/ome-ngff-validator/pull/36
 * https://github.com/ome/ome-zarr-py/pull/383
 * https://github.com/hms-dbmi/vizarr/pull/172

 Slightly less related but important at the moment:

 * https://github.com/google/neuroglancer/issues/606
 * https://github.com/ome/napari-ome-zarr/pull/112
 * https://github.com/zarr-developers/zarr-python/issues/2029 etc.
