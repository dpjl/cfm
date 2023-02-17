import logging
from datetime import datetime
from typing import TYPE_CHECKING

from camerafile.core.Constants import INTERNAL, SIGNATURE, CFM_CAMERA_MODEL
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.metadata.MetadataList import MetadataList

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet

LOGGER = logging.getLogger(__name__)


class MediaFile:

    def __init__(self, file_desc: FileDescription, parent_dir: MediaDirectory, parent_set: "MediaSet"):
        self.parent_dir = parent_dir
        self.parent_set = parent_set
        self.file_desc: FileDescription = file_desc
        self.id = self.file_desc.get_id()
        self.metadata = MetadataList()
        self.db_id = None
        self.date_identifier = None
        self.exists_in_db = False
        self.thumbnail_in_db = False
        self.exists = True

    def __str__(self):
        return self.file_desc.relative_path

    def get_path(self):
        return self.file_desc.relative_path

    def get_extension(self):
        return self.file_desc.extension

    def is_in_trash(self):
        if MediaSet.CFM_TRASH in self.get_path():
            return True
        return False

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

    def get_str_date(self):
        date = self.get_date()
        if date is not None:
            new_date_format = date.strftime("%Y/%m/%d")
            return new_date_format
        return ""
