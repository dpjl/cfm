import base64
import io
import logging

from PIL import Image

from camerafile.core import Configuration
from camerafile.core.Constants import CAMERA_MODEL, DATE, WIDTH, HEIGHT, ORIENTATION, DATE_LAST_MODIFICATION, SIZE
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.Metadata import Metadata
from camerafile.tools.ExifTool import ExifTool

LOGGER = logging.getLogger(__name__)


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

        if self.value is None:

            args = (ExifTool.BEST_CAMERA_MODEL,
                    ExifTool.BEST_CREATION_DATE,
                    ExifTool.WIDTH_METADATA,
                    ExifTool.HEIGHT_METADATA,
                    ExifTool.ORIENTATION_METADATA)

            if Configuration.THUMBNAILS:
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
