import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path

from camerafile.core import Constants
from camerafile.core.Constants import INTERNAL, SIGNATURE, ORIGINAL_COPY_PATH, \
    DESTINATION_COPY_PATH, CFM_CAMERA_MODEL, ORIGINAL_PATH
from camerafile.fileaccess.StandardFileAccess import StandardFileAccess
from camerafile.fileaccess.ZipFileAccess import ZipFileAccess
from camerafile.metadata.MetadataList import MetadataList

LOGGER = logging.getLogger(__name__)


class MediaFile:

    def __init__(self, path, parent_dir, parent_set, archive=0):
        self.path = path
        self.parent_dir = parent_dir
        self.parent_set = parent_set
        self.archive = archive

        self.relative_path = Path(self.path).relative_to(parent_set.root_path)
        self.name = Path(self.path).name
        self.extension = os.path.splitext(self.name)[1].lower()
        self.id = hashlib.md5(str(self.relative_path).encode()).hexdigest()

        if archive == 0:
            self.file_access = StandardFileAccess(parent_set.root_path, path, self.id)
        else:
            self.file_access = ZipFileAccess(parent_set.root_path, path, self.id)

        self.metadata = MetadataList(self)
        self.loaded_from_database = False
        self.db_id = None
        self.date_identifier = None

    def __str__(self):
        return self.path

    def is_same(self, other):
        # self.metadata.compute_value(SIGNATURE)
        # other.metadata.compute_value(SIGNATURE)
        sig1 = self.get_signature()
        sig2 = other.get_signature()
        if sig1 == sig2:
            return True
        return False

    def get_signature(self):
        # self.metadata.compute_value(SIGNATURE)
        return self.metadata.get_value(SIGNATURE)

    def get_camera_model(self):
        return self.metadata[CFM_CAMERA_MODEL].value

    def get_dimensions(self):
        width = self.metadata[INTERNAL].get_width()
        height = self.metadata[INTERNAL].get_height()
        if width is not None and height is not None:
            return str(width) + "x" + str(height)
        return None

    def get_exif_date(self):
        return self.metadata[INTERNAL].get_date()

    def get_exif_last_modification_date(self):
        return self.metadata[INTERNAL].get_last_modification_date()

    def get_date(self):
        date = self.get_exif_date()
        if date is not None:
            return datetime.strptime(date, '%Y/%m/%d %H:%M:%S.%f')
        return None

    def get_last_modification_date(self):
        date = self.get_exif_last_modification_date()
        if date is not None:
            return datetime.strptime(date, '%Y/%m/%d %H:%M:%S.%f')
        return None

    def get_str_date(self):
        date = self.get_date()
        if date is not None:
            new_date_format = date.strftime("%Y/%m/%d")
            return new_date_format
        return ""

    def update_date_identifier(self):
        if self.date_identifier is None:
            date = self.get_exif_date()
            dimensions = self.get_dimensions()
            if date is not None and dimensions is not None:
                self.date_identifier = date + "-" + dimensions
            elif date is not None:
                self.date_identifier = date

    @staticmethod
    def add_suffix_to_filename(filename, suffix):
        splitext = os.path.splitext(filename)
        name_without_extension = splitext[0]
        extension = splitext[1] if len(splitext) > 1 else ""
        return name_without_extension + suffix + extension

    def add_size_to_filename(self, filename):
        dimensions = self.get_dimensions()
        if dimensions is None:
            print("Width and/or height cannot be found for " + self.path)
            return filename
        return self.add_suffix_to_filename(filename, "[" + dimensions + "]")

    def add_date_to_filename(self, filename):
        date = self.get_date()
        if date is None:
            print("Date cannot be found for " + self.path)
            return filename
        new_date_format = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
        return self.add_suffix_to_filename(filename, "[" + new_date_format + "]")

    def is_modified(self):
        date = self.get_date()
        last_modification_date = self.get_last_modification_date()
        seconds_diff = abs((last_modification_date - date).total_seconds())
        # second test is because of possible timezone diff
        if seconds_diff > 60 and int(seconds_diff) % 3600 > 20:
            return True

    def get_organization_path(self, new_media_set, new_path_map):
        camera_model = self.get_camera_model()
        if camera_model is not None:
            camera_model = camera_model.replace(" ", "-")
        if camera_model is None:
            camera_model = Constants.UNKNOWN

        date = self.get_date()

        year = date.strftime("%Y")
        month = date.strftime("%m[%B]")
        new_dir_path = new_media_set.root_path / year / month / camera_model
        new_file_name = self.name
        new_file_path = new_dir_path / new_file_name

        # Here, concatenate only [~2], [~3], ...

        if new_file_path in new_path_map:
            new_file_name = self.add_size_to_filename(new_file_name)
            new_file_path = new_dir_path / new_file_name

        if new_file_path in new_path_map:
            new_file_name = self.add_date_to_filename(new_file_name)
            new_file_path = new_dir_path / new_file_name

        if new_file_path in new_path_map:
            print("Something is wrong: destination still exists " + new_file_path)

        return new_dir_path, new_file_path

    def copy_metadata(self, new_media_set, new_file_path):
        new_media_file = MediaFile(str(new_file_path), None, new_media_set)
        new_media_file.metadata = self.metadata
        new_media_file.metadata.set_value(ORIGINAL_COPY_PATH, str(self.path))
        new_media_file.metadata.set_value(DESTINATION_COPY_PATH, str(new_file_path))
        new_media_set.add_file(new_media_file)
        return True

    def move_metadata(self, new_file_path):
        new_media_file = MediaFile(str(new_file_path), None, self.parent_set)
        new_media_file.metadata = self.metadata
        new_media_file.loaded_from_database = True
        new_media_file.metadata.set_value(ORIGINAL_PATH, str(self.path))
        self.parent_set.add_file(new_media_file)
        self.parent_set.remove_file(self)
        return True
