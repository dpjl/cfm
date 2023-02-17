from enum import Enum


class MetadataNames(Enum):
    MODEL = "cm"
    WIDTH = "width"
    HEIGHT = "height"
    ORIENTATION = "orient"
    CREATION_DATE = "date"
    MODIFICATION_DATE = "date-lm"
    THUMBNAIL = "thumbnail"

    # MODEL = "Model"
    # WIDTH = "Width"
    # HEIGHT = "Height"
    # ORIENTATION = "Orientation"
    # CREATION_DATE = "CreationDate"
    # MODIFICATION_DATE = "ModifyDate"
    # THUMBNAIL = "thumbnail"

    def __str__(self):
        return self.value

    @staticmethod
    def from_str(md_name):
        if md_name == "cm":
            return MetadataNames.MODEL
        elif md_name == "width":
            return MetadataNames.WIDTH
        elif md_name == "height":
            return MetadataNames.HEIGHT
        elif md_name == "orient":
            return MetadataNames.ORIENTATION
        elif md_name == "date":
            return MetadataNames.CREATION_DATE
        elif md_name == "date-lm":
            return MetadataNames.MODIFICATION_DATE
        elif md_name == "thumbnail":
            return MetadataNames.THUMBNAIL
        else:
            return md_name
