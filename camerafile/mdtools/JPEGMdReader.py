import logging
import mmap
from datetime import datetime

import exifread
from PIL.ExifTags import TAGS

from camerafile.mdtools.MdConstants import MetadataNames

LOGGER = logging.getLogger(__name__)


class JPEGMdReader(object):
    NAME_TO_TAG = {name: tag for tag, name in TAGS.items()}

    MODEL_METADATA = "Image Model"
    ORIENTATION_METADATA = "Image Orientation"
    ORIENTATION_METADATA_2 = "Thumbnail Orientation"

    SS_CREATE_DATE = "EXIF SubSecTimeDigitized"
    SS_DATE_TIME_ORI = "EXIF SubSecTimeOriginal"
    SS_MODIFY_DATE = "EXIF SubSecTime"

    CREATE_DATE = "EXIF DateTimeDigitized"
    CREATE_DATE_2 = "Image DateTimeDigitized"

    DATE_TIME_ORI = "EXIF DateTimeOriginal"
    DATE_TIME_ORI_2 = "Image DateTimeOriginal"

    MODIFY_DATE = "EXIF DateTime"
    MODIFY_DATE_2 = "Image DateTime"

    WIDTH_METADATA = "Image ImageWidth"
    HEIGHT_METADATA = "Image ImageLength"

    THUMBNAIL = "JPEGThumbnail"

    def __init__(self, file):
        self.file = None
        self.filename = None
        if isinstance(file, str):
            self.filename = file
        else:
            self.file = file
        self.metadata = {}

    def open(self, details=False):
        if self.file is None:
            with open(self.filename, 'rb') as f:
                with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                    self.metadata = exifread.process_file(mmap_obj, details=details)
        else:
            self.metadata = exifread.process_file(self.file, details=details)

        if self.metadata == {}:
            raise Exception(f"JPEGMdReader cannot parse {self.filename}")

    def get_first_of(self, field_list, default=None):
        for field in field_list:
            if field in self.metadata:
                return self.metadata[field]
        return default

    def to_date(self, str_date, ss_str_date):
        if str_date is None:
            return None
        microseconds = ss_str_date if ss_str_date else "000000"
        str_date = str(str_date) + "." + str(microseconds)
        try:
            return datetime.strptime(str_date, '%Y:%m:%d %H:%M:%S.%f')
        except ValueError:
            return None

    def read_best_date(self):
        create_date = self.metadata[self.CREATE_DATE] if self.CREATE_DATE in self.metadata else None
        if not create_date:
            create_date = self.metadata[self.CREATE_DATE_2] if self.CREATE_DATE_2 in self.metadata else None

        date_time_original = self.metadata[self.DATE_TIME_ORI] if self.DATE_TIME_ORI in self.metadata else None
        if not date_time_original:
            date_time_original = self.metadata[self.DATE_TIME_ORI_2] if self.DATE_TIME_ORI_2 in self.metadata else None

        modify_date = self.metadata[self.MODIFY_DATE] if self.MODIFY_DATE in self.metadata else None
        if not modify_date:
            modify_date = self.metadata[self.MODIFY_DATE_2] if self.MODIFY_DATE_2 in self.metadata else None

        ss_create_date = self.metadata[self.SS_CREATE_DATE] if self.SS_CREATE_DATE in self.metadata else None
        ss_date_time_original = self.metadata[self.SS_DATE_TIME_ORI] if self.SS_DATE_TIME_ORI in self.metadata else None
        ss_modify_date = self.metadata[self.SS_MODIFY_DATE] if self.SS_MODIFY_DATE in self.metadata else None

        if create_date and ss_create_date:
            return self.to_date(create_date, ss_create_date)

        if date_time_original and ss_date_time_original:
            return self.to_date(date_time_original, ss_date_time_original)

        if modify_date and ss_modify_date:
            return self.to_date(modify_date, ss_modify_date)

        return self.to_date(date_time_original, None)

    def load_from_result(self, metadata_name):
        if metadata_name == MetadataNames.CREATION_DATE:
            result = self.read_best_date()
        elif metadata_name == MetadataNames.THUMBNAIL and self.THUMBNAIL in self.metadata:
            result = self.metadata[self.THUMBNAIL]
        elif metadata_name == MetadataNames.WIDTH and self.WIDTH_METADATA in self.metadata:
            result = self.metadata[self.WIDTH_METADATA].values[0]
        elif metadata_name == MetadataNames.HEIGHT and self.HEIGHT_METADATA in self.metadata:
            result = self.metadata[self.HEIGHT_METADATA].values[0]
        elif metadata_name == MetadataNames.ORIENTATION and self.ORIENTATION_METADATA in self.metadata:
            result = self.metadata[self.ORIENTATION_METADATA].values[0]
        elif metadata_name == MetadataNames.ORIENTATION and self.ORIENTATION_METADATA_2 in self.metadata:
            result = self.metadata[self.ORIENTATION_METADATA_2].values[0]
        elif metadata_name == MetadataNames.MODEL and self.MODEL_METADATA in self.metadata:
            result = str(self.metadata[self.MODEL_METADATA]).strip()
        else:
            result = None  # self.get_value(metadata_name)
        return result

    def get_metadata(self, *args):
        details = True if MetadataNames.THUMBNAIL in args else False
        self.open(details=details)
        return {metadata_name: self.load_from_result(metadata_name) for metadata_name in args}
