from rocrate.rocrate import ROCrate
from pathlib import Path

if __name__ == "__main__":
    folder = Path(__file__).parent.joinpath("./example_ro_crate").absolute()
    crate = ROCrate(folder)  # or ROCrate('exp_crate.zip')

    root = crate.root_dataset
    
    image_acquisition = root["resultOf"]
    specimen = image_acquisition["specimen"]
    biosample = specimen["biosample"]
    taxon = biosample["organism_classification"]

    print(f"Imaging type: {image_acquisition["fbbi_id"]}")
    print(f"Organism Taxon id: {taxon}")