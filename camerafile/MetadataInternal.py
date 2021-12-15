import base64
import io
import logging
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.Image import NEAREST

from camerafile.Constants import CAMERA_MODEL, DATE, WIDTH, HEIGHT, ORIENTATION
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import Metadata

LOGGER = logging.getLogger(__name__)


class MetadataInternal(Metadata):

    def __init__(self, media_id, media_path, extension):
        super().__init__(None)
        self.media_id = media_id
        self.media_path = media_path
        self.extension = extension
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

    def get_width(self):
        return self.get_md_value(WIDTH)

    def get_height(self):
        return self.get_md_value(HEIGHT)

    @staticmethod
    def load_internal_metadata_task(internal_metadata):
        try:
            internal_metadata.load_internal_metadata()
            return internal_metadata
        except:
            print("Error during load_internal_metadata_task execution for " + str(internal_metadata.media_path))
            return internal_metadata

    def load_internal_metadata(self):
        if self.value is None:

            model, date, width, height, orientation, thumbnail = ExifTool.get_metadata(self.media_path)

            if date is None:
                date = datetime.fromtimestamp(Path(self.media_path).stat().st_mtime)

            if orientation is not None and (orientation == 6 or orientation == 8):
                old_width = width
                width = height
                height = old_width

            if date is not None:
                date = date.strftime("%Y/%m/%d %H:%M:%S.%f")

            self.value = {CAMERA_MODEL: model,
                          DATE: date,
                          WIDTH: width,
                          HEIGHT: height,
                          ORIENTATION: orientation}

            if thumbnail is not None:
                self.thumbnail = base64.b64decode(thumbnail[7:])
                thb = Image.open(io.BytesIO(self.thumbnail))
                thb.thumbnail((100, 100))
                bytes_output = io.BytesIO()
                thb.save(bytes_output, format='JPEG')
                self.thumbnail = bytes_output.getvalue()
