import base64
import io
import logging

from PIL import Image

from camerafile.core.Constants import CAMERA_MODEL, DATE, WIDTH, HEIGHT, ORIENTATION, DATE_LAST_MODIFICATION, SIZE
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.Metadata import Metadata

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

    def get_file_size(self):
        return self.get_md_value(SIZE)

    def load_internal_metadata(self):

        if self.value is None:

            model, date, width, height, orientation, file_size, thumbnail = self.file_access.call_exif_tool()
            # with open(self.file_access.path, "rb") as file_stream:
            #    model, date, width, height, orientation, thumbnail = ExifTool.get_metadata(file_stream)

            last_modified_date = self.file_access.get_last_modification_date()
            if date is None:
                date = last_modified_date

            if file_size is None:
                file_size = self.file_access.get_file_size()

            if orientation is not None and (orientation == 6 or orientation == 8):
                old_width = width
                width = height
                height = old_width

            if date is not None:
                date = date.strftime("%Y/%m/%d %H:%M:%S.%f")

            if last_modified_date is not None:
                last_modified_date = last_modified_date.strftime("%Y/%m/%d %H:%M:%S.%f")

            self.value = {CAMERA_MODEL: model,
                          DATE: date,
                          DATE_LAST_MODIFICATION: last_modified_date,
                          WIDTH: width,
                          HEIGHT: height,
                          ORIENTATION: orientation,
                          SIZE: file_size}

            if thumbnail is not None:
                self.thumbnail = base64.b64decode(thumbnail[7:])
                thb = Image.open(io.BytesIO(self.thumbnail))
                thb.thumbnail((100, 100))
                bytes_output = io.BytesIO()
                thb.save(bytes_output, format='JPEG')
                self.thumbnail = bytes_output.getvalue()
