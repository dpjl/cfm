import logging
from datetime import datetime
from typing import Dict

from PIL import Image

from camerafile.Constants import IMAGE_TYPE
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import Metadata, CAMERA_MODEL, DATE, SIGNATURE, ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, \
    ORIGINAL_MOVE_PATH, DESTINATION_MOVE_PATH, WIDTH, HEIGHT, ORIENTATION
from camerafile.MetadataCameraModel import MetadataCameraModel
from camerafile.MetadataSignature import MetadataSignature

LOGGER = logging.getLogger(__name__)


class MetadataList:
    metadata_list: Dict[str, Metadata]
    COMPUTE_PREFIX = "Computed "

    def __init__(self, media_file):
        self.media_file = media_file
        self.metadata_list = {CAMERA_MODEL: MetadataCameraModel(media_file),
                              DATE: Metadata(media_file),
                              WIDTH: Metadata(media_file),
                              HEIGHT: Metadata(media_file),
                              ORIENTATION: Metadata(media_file),
                              ORIGINAL_COPY_PATH: Metadata(media_file),
                              DESTINATION_COPY_PATH: Metadata(media_file),
                              ORIGINAL_MOVE_PATH: Metadata(media_file),
                              DESTINATION_MOVE_PATH: Metadata(media_file),
                              SIGNATURE: MetadataSignature(media_file)}

    def __getitem__(self, item):
        return self.metadata_list[item]

    def set_value(self, name, value):
        self[name].value_read = value
        self.load_from_media(name)

    def get_value(self, name):
        self.read_value(name)
        return self[name].get()

    def read_value(self, name):
        if self[name].value_read is None:
            self.load_from_media(name)
        return self[name].value_read

    def compute_value(self, name):
        self[name].compute_value()
        value = self[name].value_computed
        return value

    def delete_computed_value(self, name):
        if self[name].value_computed is not None:
            self[name].value_computed = None

    def get_metadata_with_pil(self):
        model = None
        date = None
        orientation = None
        try:
            img = Image.open(self.media_file.path)
            width, height = img.size
            if img.getexif() is not None:
                exif = dict(img.getexif().items())
                if 0x0110 in exif:
                    model = exif[0x0110].strip("\u0000").strip(" ")
                if 0x9003 in exif:
                    try:
                        date = datetime.strptime(exif[0x9003], '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        date = None
                        # comment récupérer ici l'équivalent de FileModifyDate (voir ExifTool) ?
                if 0x0112 in exif:
                    orientation = exif[0x0112]

        except OSError:
            # print("%s can't be hashed as an image" % self.media_file.path)
            return None, None, None, None, None

        return model, date, width, height, orientation

    def load_from_media(self, name):
        if name in [DATE, CAMERA_MODEL, WIDTH, HEIGHT, ORIENTATION]:

            model = None
            date = None
            width = None
            height = None
            orientation = None

            if self.media_file.extension in IMAGE_TYPE:
                model, date, width, height, orientation = self.get_metadata_with_pil()

            if date is None:
                model, date, width, height, orientation = ExifTool.get_metadata(self.media_file.path)

            if orientation is not None and (orientation == 6 or orientation == 8):
                old_width = width
                width = height
                height = old_width

            if date is not None:
                date = date.strftime("%Y/%m/%d %H:%M:%S")

            self.set_metadata_read_value(DATE, date)
            self.set_metadata_read_value(CAMERA_MODEL, model)
            self.set_metadata_read_value(WIDTH, width)
            self.set_metadata_read_value(HEIGHT, height)
            self.set_metadata_read_value(ORIENTATION, orientation)

            self.media_file.parent_set.update_date_and_name_map(self.media_file)

    def set_metadata_read_value(self, metadata_name, value):
        if value is not None:
            self[metadata_name].set_value_read(value)
        else:
            self[metadata_name].set_value_read(Metadata.UNKNOWN)

    def save_to_dict(self):
        result = {}
        for metadata_name, metadata in self.metadata_list.items():
            if metadata.value_read is not None:
                result[metadata_name] = metadata.value_read
            if metadata.value_computed is not None:
                result[MetadataList.COMPUTE_PREFIX + metadata_name] = metadata.value_computed
        return result

    def load_from_dict(self, media_file_dict):
        for md_name, md_value in self.metadata_list.items():
            if md_name in media_file_dict:
                md_value.set_value_read(media_file_dict[md_name])
            if MetadataList.COMPUTE_PREFIX + md_name in media_file_dict:
                md_value.set_value_computed(media_file_dict[MetadataList.COMPUTE_PREFIX + md_name])
