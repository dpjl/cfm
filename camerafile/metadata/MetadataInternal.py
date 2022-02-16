import base64
import io
import logging
import re

import sys
from PIL import Image

from camerafile.core.Configuration import Configuration
from camerafile.core.Constants import CAMERA_MODEL, DATE, WIDTH, HEIGHT, ORIENTATION, DATE_LAST_MODIFICATION
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.Metadata import Metadata
from camerafile.tools.ExifTool import ExifTool

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
            if md_name in self.value:
                return self.value[md_name]
        return None

    def get_cm(self):
        return self.get_md_value(CAMERA_MODEL)

    def get_date(self):
        return self.get_md_value(DATE)

    def get_last_modification_date(self):
        return self.get_md_value(DATE_LAST_MODIFICATION)

    def get_width(self):
        return self.get_md_value(WIDTH)

    def get_height(self):
        return self.get_md_value(HEIGHT)

    def load_internal_metadata(self):

        # mode DO_NOT_READ_EXIF : warning car analyze moins précis / ne peux être appliqué que pour "analyze"
        # error si format qui contient un exif dans l'organize'

        # ${exif:field}
        # ${cfm:field}
        # ${file:field:}

        # ${cfm:creationDate:%Y}/${cfm:creationDate:%m[%B]}/{cfm:cameraModel:Unknown}

        # Traitament des "file" et des "cfm" à part (à peu près comme aujourd'hui).
        # Les exifs, on les charge et on les enregistre dans la map avec leur nom exiftool

        if self.value is None:

            args = (ExifTool.BEST_CAMERA_MODEL,
                    ExifTool.BEST_CREATION_DATE,
                    ExifTool.WIDTH_METADATA,
                    ExifTool.HEIGHT_METADATA,
                    ExifTool.ORIENTATION_METADATA)

            if Configuration.get().thumbnails:
                args += (ExifTool.THUMBNAIL_METADATA,)

            result = self.file_access.call_exif_tool(args)

            orientation = result[ExifTool.ORIENTATION_METADATA] if ExifTool.ORIENTATION_METADATA in result else None
            width = result[ExifTool.WIDTH_METADATA] if ExifTool.WIDTH_METADATA in result else None
            height = result[ExifTool.HEIGHT_METADATA] if ExifTool.HEIGHT_METADATA in result else None
            date = result[ExifTool.BEST_CREATION_DATE] if ExifTool.BEST_CREATION_DATE in result else None
            thumbnail = result[ExifTool.THUMBNAIL_METADATA] if ExifTool.THUMBNAIL_METADATA in result else None
            camera_model = result[ExifTool.BEST_CAMERA_MODEL] if ExifTool.BEST_CAMERA_MODEL in result else None

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

            self.value = {CAMERA_MODEL: camera_model,
                          DATE: date,
                          DATE_LAST_MODIFICATION: last_modified_date,
                          WIDTH: width,
                          HEIGHT: height,
                          ORIENTATION: orientation}

            if thumbnail is not None:
                thumbnail = base64.b64decode(thumbnail[7:])
                thb = Image.open(io.BytesIO(thumbnail))
                thb.thumbnail((100, 100))
                bytes_output = io.BytesIO()
                thb.save(bytes_output, format='JPEG')
                self.thumbnail = bytes_output.getvalue()
