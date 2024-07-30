Example zattrs file and how that data would look in ro-crate-metadata.json.

Context has been left to the imagination, as it would require a lot of effort to find suitable linked data terms to use.

zattr_as_rocrate.json shows an approximation of what the structure might look like. Fields such as "omero" and "multiscales" have dissapeared, as they would probably be equivalent to different named graphs in linked data terminology, rather than actual different objects. 

zattr_as_rocrate_extended_linked_data.json builds on zattr_as_rocrate.json to show what the data could look like were external vocabularies used to reference the units & types of axes used. This could possbily also be used for the 'family' field in channels, but stopped with units & axes because those seemed most likely to have existing external vocabularies.