from __future__ import annotations

from rocrate.model.contextentity import ContextEntity


class Biosample(ContextEntity):
    def __init__(self, crate, identifier=None, properties=None):
        biosample_type_path = "biosample"
        if properties:
            biosample_properties = {}
            biosample_properties.update(properties)
            if "@type" in properties:
                biosample_types = biosample_properties["@type"]
                if biosample_type_path not in biosample_types:
                    try:
                        biosample_types.append(biosample_type_path)
                    except Exception:
                        biosample_types = [biosample_types]
                        biosample_types.append(biosample_type_path)
                    biosample_properties["@type"] = biosample_types
            else:
                biosample_properties.update({"@type": biosample_type_path})
        else:
            biosample_properties = {"@type": biosample_type_path}

        super().__init__(crate, identifier, biosample_properties)

    def popitem(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError


class Specimen(ContextEntity):
    def __init__(self, crate, biosample, identifier=None, properties=None):
        specimen_type_path = "specimen"
        if properties:
            specimen_properties = {}
            specimen_properties.update(properties)
            if "@type" in properties:
                specimen_type = specimen_properties["@type"]
                if specimen_type_path not in specimen_type:
                    try:
                        specimen_type.append(specimen_type_path)
                    except Exception:
                        specimen_type = [specimen_type]
                        specimen_type.append(specimen_type_path)
                    specimen_properties["@type"] = specimen_type
            else:
                specimen_properties.update({"@type": specimen_type_path})
        else:
            specimen_properties = {"@type": specimen_type_path}

        super().__init__(crate, identifier, specimen_properties)

        self["biosample"] = biosample

    def popitem(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError


class ImageAcquistion(ContextEntity):
    def __init__(self, crate, specimen, identifier=None, properties=None):
        image_acquisition_type_path = "image_acquisition"
        if properties:
            image_acquisition_properties = {}
            image_acquisition_properties.update(properties)
            if "@type" in properties:
                image_acquisition_type = image_acquisition_properties["@type"]
                if image_acquisition_type_path not in image_acquisition_type:
                    try:
                        image_acquisition_type.append(image_acquisition_type_path)
                    except Exception:
                        image_acquisition_type = [image_acquisition_type]
                        image_acquisition_type.append(image_acquisition_type_path)
                    image_acquisition_properties["@type"] = image_acquisition_type
            else:
                image_acquisition_properties.update(
                    {"@type": image_acquisition_type_path}
                )
        else:
            image_acquisition_properties = {"@type": image_acquisition_type_path}

        super().__init__(crate, identifier, image_acquisition_properties)

        self["specimen"] = specimen

    def popitem(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError
