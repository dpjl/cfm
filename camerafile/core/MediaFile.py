import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path

from typing import TYPE_CHECKING

from camerafile.core import Constants
from camerafile.core.Constants import INTERNAL, SIGNATURE, ORIGINAL_COPY_PATH, \
    DESTINATION_COPY_PATH, CFM_CAMERA_MODEL, ORIGINAL_PATH
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.MetadataList import MetadataList

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet

LOGGER = logging.getLogger(__name__)


class MediaFile:

    def __init__(self, file_access: FileAccess, parent_dir, parent_set: "MediaSet"):
        self.parent_dir = parent_dir
        self.parent_set = parent_set

        self.file_access = file_access
        self.relative_path = Path(file_access.path).relative_to(parent_set.root_path).as_posix()
        self.id: str = hashlib.md5(self.relative_path.encode()).hexdigest()
        file_access.set_id(self.id)
        file_access.set_relative_path(self.relative_path)
        self.extension = file_access.extension
        self.path = file_access.path

        self.metadata = MetadataList(self)
        self.db_id = None
        self.date_identifier = None
        self.exists_in_db = False
        self.thumbnail_in_db = False
        self.exists = True

    def get_path(self):
        return self.relative_path

    def is_in_trash(self):
        if self.parent_set.get_trash_file() in self.path:
            return True
        return False

    def __str__(self):
        return self.file_access.get_path()

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

    def get_file_size(self):
        return self.file_access.get_file_size()

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
            print("Width and/or height cannot be found for " + str(self))
            return filename
        return self.add_suffix_to_filename(filename, "[" + dimensions + "]")

    def add_date_to_filename(self, filename):
        date = self.get_date()
        if date is None:
            print("Date cannot be found for " + str(self))
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
        new_file_name = self.file_access.name
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

    def copy(self, new_media_set, new_file_access: FileAccess):
        new_media_file = MediaFile(new_file_access, None, new_media_set)
        new_media_file.metadata = self.metadata
        new_media_file.metadata.set_value(ORIGINAL_COPY_PATH, str(self))
        new_media_file.metadata.set_value(DESTINATION_COPY_PATH, new_file_access.path)
        new_media_set.add_file(new_media_file)
        return True

    def move(self, new_file_access: FileAccess):
        new_media_file = MediaFile(new_file_access, None, self.parent_set)
        new_media_file.metadata = self.metadata
        new_media_file.loaded_from_database = True
        new_media_file.metadata.set_value(ORIGINAL_PATH, str(self))
        self.parent_set.add_file(new_media_file)
        self.parent_set.remove_file(self)
        return True
