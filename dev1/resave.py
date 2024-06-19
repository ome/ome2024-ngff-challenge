import numpy as np
import zarr
import os

path = "/Users/wmoore/Desktop/ZARR/data/6001240.zarr"
# remote fails - see below
# path = "https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.4/idr0062A/6001240.zarr"

rootpath = "6001240_V0.5-dev1.zarr"
if os.path.exists(rootpath):
    import shutil
    shutil.rmtree(rootpath)

store_class = zarr.store.LocalStore
if path.startswith("http"):
    # TypeError: Can't instantiate abstract class RemoteStore with abstract methods get_partial_values, list, list_dir, list_prefix, set_partial_values
    store_class = zarr.store.RemoteStore
read_store = store_class(path, mode="r")
# Needs zarr_format=2 or we get ValueError("store mode does not support writing")
read_root = zarr.open_group(store=read_store, zarr_format=2)

# Create new Image...
write_store = zarr.store.LocalStore(rootpath, mode="w")
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
    a = root.create_array(str(ds_path), shape=data.shape, chunk_shape=[64] * data.ndim, dtype=data.dtype)
    # These 2 lines are equivalent to e.g. a[:,:] = data (for any number of dimensions)
    s = [np.s_[:]] * len
