import logging
from datetime import datetime

from PIL import Image
from PIL.ExifTags import TAGS

from camerafile.mdtools.MdConstants import MetadataNames

LOGGER = logging.getLogger(__name__)


class ExifPil(object):
    NAME_TO_TAG = {name: tag for tag, name in TAGS.items()}

    MODEL_METADATA = "Model"
    ORIENTATION_METADATA = "Orientation"

    SUB_SEC_CREATE_DATE = "SubsecTimeDigitized"
    SUB_SEC_DATE_TIME_ORIGINAL = "SubsecTimeOriginal"
    SUB_SEC_MODIFY_DATE = "SubsecTime"

    CREATE_DATE = "DateTimeDigitized"
    DATE_TIME_ORIGINAL = "DateTimeOriginal"
    MODIFY_DATE = "DateTime"

    THUMBNAIL_OFFSET = "JpegIFOffset"
    THUMBNAIL_BYTES_COUNT = "JpegIFByteCount"

    def __init__(self, file):
        self.file = file
        self.image_data: Image.Image = Image.open(self.file, formats=["JPEG"])
        self.exif = self.image_data.getexif()
        self.width, self.height = self.image_data.size

    def print_all_exif(self):
        for exif_tag, exif_value in self.exif.items():
            if exif_tag in TAGS:
                print(TAGS[exif_tag] + " = " + str(exif_value))
            else:
                print(str(exif_tag) + "=" + str(exif_value))

        for exif_tag, exif_value in self.exif.get_ifd(0x8769).items():
            if exif_tag in TAGS:
                print(TAGS[exif_tag] + " = " + str(exif_value))
            else:
                print(str(exif_tag) + "=" + str(exif_value))

    @staticmethod
    def get_exif_value(field_name, exif):
        tag = ExifPil.NAME_TO_TAG[field_name]
        if tag in exif:
            result = exif[tag]
        elif tag in exif.get_ifd(0x8769):
            result = exif.get_ifd(0x8769)[tag]
        else:
            result = None
        if isinstance(result, str):
            result = result.strip("\u0000").strip(" ")
        return result

    def get_value(self, field_name):
        return self.get_exif_value(field_name, self.exif)

    def get_first_of(self, field_list, default=None):
        for field in field_list:
            value = self.get_value(field)
            if value is not None:
                return value
        return default

    def read_best_date(self):
        date = self.get_first_of([self.CREATE_DATE, self.DATE_TIME_ORIGINAL, self.MODIFY_DATE])
        microseconds = self.get_first_of([self.SUB_SEC_CREATE_DATE, self.SUB_SEC_DATE_TIME_ORIGINAL,
                                          self.SUB_SEC_MODIFY_DATE], "000000")
        # TODO : read time offset
        if date is not None:
            date = date + "." + microseconds
            try:
                date = datetime.strptime(date, '%Y:%m:%d %H:%M:%S.%f')
            except ValueError:
                date = None
        return date

    def read_thumbnail(self):
        offset = self.get_value(self.THUMBNAIL_OFFSET)
        length = self.get_value(self.THUMBNAIL_BYTES_COUNT)

        if offset is not None and length is not None:
            offset = int(offset)
            length = int(length)
            with open(self.file, "rb") as file:
                file.seek(offset)
                result = file.read(length)
            return result

    def load_from_result(self, metadata_name):
        if metadata_name == MetadataNames.CREATION_DATE:
            return self.read_best_date()
        if metadata_name == MetadataNames.THUMBNAIL:
            return self.read_thumbnail()
        if metadata_name == MetadataNames.WIDTH:
            return self.width
        if metadata_name == MetadataNames.HEIGHT:
            return self.height
        if metadata_name == MetadataNames.ORIENTATION:
            return self.get_value(self.ORIENTATION_METADATA)
        if metadata_name == MetadataNames.MODEL:
            return self.get_value(self.MODEL_METADATA)
        else:
            return self.get_value(metadata_name)

    def get_metadata(self, *args):
        return {metadata_name: self.load_from_result(metadata_name) for metadata_name in args}


if __name__ == '__main__':
    r = ExifPil(r"P:\arbo\perso\cfm\tests\data\camera6-honor\IMG_20151118_123300.jpg")
