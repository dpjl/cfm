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


if __name__ == '__main__':
    # m = JPEGMdReader(r"P:\arbo\perso\cfm\tests\data\camera6-honor\IMG_20151118_123300.jpg")
    # m = JPEGMdReader(r"P:\arbo\perso\cfm\tests\data\whatsapp/Media/WhatsApp Images/Sent/IMG-20210111-WA0001.jpg")
    # m = JPEGMdReader(r"P:\arbo\perso\cfm\tests\data\camera1-samsung/20171118_172416.jpg")
    # m = JPEGMdReader(r"P:\arbo\perso\cfm\tests\data\camera4/8mai 039.jpg")
    # m = JPEGMdReader(
    #    r"E:\data\photos-all\depuis-samsung-T5/photos divers/2007-07-04/repas avec Natacha et Diminga/100_0084.jpg")
    # m = JPEGMdReader(r"E:\data\photos-all\téléphone_samsung/albums/Balade Saacy/20180819_221155.jpg") # can't be parsed
    # m = JPEGMdReader(r"E:\data\photos-all\honor/DCIM-sd-av-guillaume/Camera/IMG_20160522_000548.jpg")
    m = JPEGMdReader(
        r"E:\data\photos-all\depuis-samsung-T5/sauvegarde photos surface pro (surement en double d'autres sauvegardes)/photos/Canon PowerShot G9 X Mark II/20180819_221155.jpg")

    m = m.get_metadata(MetadataNames.CREATION_DATE, MetadataNames.HEIGHT, MetadataNames.WIDTH,
                       MetadataNames.ORIENTATION, MetadataNames.MODEL)

    # from camerafile.fileaccess.ZipFileAccess import ZipFileAccess
    # access = ZipFileAccess("./tests/data/zip/wetransfer-4a1f94-escrime.zip", "DSC04403.JPG")
    # m = access.read_md((MetadataNames.CREATION_DATE, MetadataNames.HEIGHT, MetadataNames.WIDTH,
    #                    MetadataNames.ORIENTATION, MetadataNames.MODEL))

    print(str(m))
