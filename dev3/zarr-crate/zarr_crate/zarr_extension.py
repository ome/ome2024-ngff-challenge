from rocrate.rocrate import ROCrate


class ZarrCrate(ROCrate):
    def __init__(self, source=None, gen_preview=False, init=False, exclude=None):
        super().__init__(source, gen_preview, init, exclude)
        self.metadata.extra_terms = {
            "organism_classification": "https://schema.org/taxonomicRange",
            "BioChemEntity": "https://schema.org/BioChemEntity",
            "channel": "https://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2016-06/ome_xsd.html#Channel",
            "obo": "http://purl.obolibrary.org/obo/",
            "FBcv": "http://ontobee.org/ontology/FBcv/",
            "acquisiton_method": {
                "@reverse": "https://schema.org/result",
                "@type": "@id",
            },
            "biological_entity": "https://schema.org/about",
            "biosample": "http://purl.obolibrary.org/obo/OBI_0002648",
            "preparation_method": "https://www.wikidata.org/wiki/Property:P1537",
            "specimen": "http://purl.obolibrary.org/obo/HSO_0000308",
        }
