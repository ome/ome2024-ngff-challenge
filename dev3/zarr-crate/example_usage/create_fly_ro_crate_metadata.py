import json
from zarr_crate.zarr_extension import ZarrCrate
from zarr_crate.rembi_extension import Biosample, Specimen, ImageAcquistion


if __name__ == "__main__":
    crate = ZarrCrate()

    zarr_root = crate.add_dataset(
        "./",
        properties={
            "name": "Light microscopy photo of a fly",
            "description": "Light microscopy photo of a fruit fly.",
            "licence": "https://creativecommons.org/licenses/by/4.0/",
        },
    )
    biosample = crate.add(
        Biosample(
            crate, properties={"organism_classification": {"@id": "NCBI:txid7227"}}
        )
    )
    specimen = crate.add(Specimen(crate, biosample))
    image_acquisition = crate.add(
        ImageAcquistion(
            crate, specimen, properties={"fbbi_id": {"@id": "obo:FBbi_00000243"}}
        )
    )
    zarr_root["resultOf"] = image_acquisition

    metadata_dict = crate.metadata.generate()

    with open("ro-crate-metadata.json", "w") as f:
        f.write(json.dumps(metadata_dict, indent=2))
