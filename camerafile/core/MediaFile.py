from datetime import datetime
from typing import TYPE_CHECKING
import os

from camerafile.core.Constants import INTERNAL, SIGNATURE, CFM_CAMERA_MODEL
from camerafile.core.Logging import Logger
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.metadata.MetadataList import MetadataList

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet
    from camerafile.core.MediaDirectory import MediaDirectory

LOGGER = Logger(__name__)


class MediaFile:

    def __init__(self, file_desc: FileDescription, parent_dir: "MediaDirectory", parent_set: "MediaSet"):
        self.parent_dir = parent_dir
        self.parent_set = parent_set
        self.file_desc: FileDescription = file_desc
        self.metadata = MetadataList()
        self.exists = True

    def __str__(self):
        return self.file_desc.relative_path

    def __repr__(self):
        result = self.file_desc.relative_path + "\n"
        for metadata_name, metadata in self.metadata.metadata_list.items():
            result += metadata_name + "=" + repr(metadata) + "\n"
        return result

    def get_path(self):
        return self.file_desc.relative_path

    def get_extension(self):
        return self.file_desc.extension

    def get_signature(self):
        return self.metadata.get_value(SIGNATURE)

    def get_camera_model(self):
        return self.metadata[CFM_CAMERA_MODEL].value

    def get_file_size(self):
        return self.file_desc.file_size

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

    def get_str_date(self, format="%Y/%m/%d"):
        date = self.get_date()
        if date is not None:
            new_date_format = date.strftime(format)
            return new_date_format
        return ""

    def compare_with(self, media_file_2: "MediaFile"):
        LOGGER.diff("MediaFile", "id", self.file_desc.id, media_file_2.file_desc.id)
        self.file_desc.compare_with(media_file_2.file_desc)
        self.metadata.compare_with(str(self), media_file_2.metadata)

    def move_to(self, new_path: str) -> bool:
        from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
        file_access = FileAccessFactory.get(self.parent_set.root_path, self.file_desc)
        if not file_access.move_to(new_path):
            return False
        self.file_desc.update_relative_path(os.path.relpath(new_path, self.parent_set.root_path))
        return True
