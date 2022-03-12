import logging
import re

import sys

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.mdtools.ExifToolReader import ExifTool
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.metadata.Metadata import Metadata

LOGGER = logging.getLogger(__name__)


class OrgFormat:

    def __init__(self, format_description: str):
        self.format_description = format_description
        self.fields = re.findall(r'\${((.*?):(.*?):(.*?))}', format_description)

    def get_exif_names(self):
        for field in self.fields:
            if field[1] == "exif":
                return field[2]

    def get_cfm_names(self):
        for field in self.fields:
            if field[1] == "cfm":
                if field[2] == "createDate":
                    return ExifTool.BEST_CREATION_DATE
                elif field[2] == "cameraModel":
                    return ExifTool.BEST_CAMERA_MODEL
                else:
                    print("Format error: invalid cfm field " + field[2])
                    print("Possible values: createDate, cameraModel")
                    sys.exit(1)

    def get_value(self, field):
        pass

    def get_formated_string(self):
        result = self.format_description
        for field in self.fields:
            result = result.replace(field[0], self.get_value(field[0]))


class MetadataInternal(Metadata):

    def __init__(self, file_access: FileAccess):
        super().__init__(None)
        self.file_access = file_access
        self.thumbnail = None

    def get_md_value(self, md_name):
        if self.value is not None:
            if md_name.value in self.value:
                return self.value[md_name.value]
        return None

    def get_date(self):
        return self.get_md_value(MetadataNames.CREATION_DATE)

    def get_last_modification_date(self):
        return self.get_md_value(MetadataNames.MODIFICATION_DATE)

    def load_internal_metadata(self):

        # mode DO_NOT_READ_EXIF : warning car analyze moins précis / ne peux être appliqué que pour "analyze"
        # error si format qui contient un exif dans l'organize'

        # ${exif:field}
        # ${cfm:field}
        # ${file:field:}

        # ${cfm:creationDate:%Y}/${cfm:creationDate:%m[%B]}/{cfm:cameraModel:Unknown}

        # Traitament des "file" et des "cfm" à part (à peu près comme aujourd'hui).
        # Les exifs, on les charge et on les enregistre dans la map avec leur nom exiftool

        args = (MetadataNames.MODEL,
                MetadataNames.CREATION_DATE,
                MetadataNames.WIDTH,
                MetadataNames.HEIGHT,
                MetadataNames.ORIENTATION)

        if Configuration.get().thumbnails:
            args += (MetadataNames.THUMBNAIL,)

        result = self.file_access.read_md(args)

        orientation = result[MetadataNames.ORIENTATION] if MetadataNames.ORIENTATION in result else None
        width = result[MetadataNames.WIDTH] if MetadataNames.WIDTH in result else self.file_access.get_file_size()
        height = result[MetadataNames.HEIGHT] if MetadataNames.HEIGHT in result else None
        date = result[MetadataNames.CREATION_DATE] if MetadataNames.CREATION_DATE in result else None
        thumbnail = result[MetadataNames.THUMBNAIL] if MetadataNames.THUMBNAIL in result else None
        camera_model = result[MetadataNames.MODEL] if MetadataNames.MODEL in result else None

        if orientation is not None and (orientation == 6 or orientation == 8):
            old_width = width
            width = height
            height = old_width

        last_modified_date = self.file_access.get_last_modification_date()

        if date is None:
            date = last_modified_date

        if date is not None:
            date = date.strftime("%Y/%m/%d %H:%M:%S.%f")

        if last_modified_date is not None:
            last_modified_date = last_modified_date.strftime("%Y/%m/%d %H:%M:%S.%f")

        #if camera_model is not None and camera_model != "" and self.file_access.extension in Constants.VIDEO_TYPE:
        #    print(str(self.file_access.relative_path) + ":" + camera_model)

        self.thumbnail = thumbnail
        self.value = {MetadataNames.MODEL.value: camera_model,
                      MetadataNames.CREATION_DATE.value: date,
                      MetadataNames.MODIFICATION_DATE.value: last_modified_date,
                      MetadataNames.WIDTH.value: width,
                      MetadataNames.HEIGHT.value: height,
                      MetadataNames.ORIENTATION.value: orientation}
