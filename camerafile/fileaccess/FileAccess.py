import os
from datetime import timedelta
from enum import IntEnum
from typing import Tuple, Union

from camerafile.core import Constants
from camerafile.fileaccess.FileDescription import FileDescription


class CopyMode(IntEnum):
    HARD_LINK = 1
    SOFT_LINK = 2
    COPY = 3

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return CopyMode[s.upper()]
        except KeyError:
            return s


class FileAccess:

    def __init__(self, root_path, file_description: FileDescription):
        self.file_desc = file_description
        self.root_path = root_path

    def get_path(self):
        return self.root_path + os.sep + self.file_desc.relative_path

    def get_id(self):
        return self.file_desc.id

    def get_extension(self):
        return self.file_desc.extension

    @staticmethod
    def even_round(date):
        microseconds = date.microsecond
        date = date.replace(microsecond=0)
        if microseconds >= 500:
            date += timedelta(seconds=1)
            if date.second % 2 != 0:
                date -= timedelta(seconds=1)
        else:
            if date.second % 2 != 0:
                date += timedelta(seconds=1)
        return date

    def is_image(self):
        return self.get_extension() in Constants.IMAGE_TYPE

    def is_video(self):
        return self.get_extension() in Constants.IMAGE_TYPE

    def is_qt_video(self):
        return self.get_extension() in Constants.QT_TYPE

    def is_avi_video(self):
        return self.get_extension() in Constants.AVI_TYPE

    def read_md(self, args):
        pass

    def open(self):
        pass

    def copy_to(self, new_root_path, new_file_path, copy_mode: CopyMode) \
            -> Tuple[bool, str, "FileAccess", Union["FileAccess", None]]:
        pass

    def delete_file(self, trash_file_path) \
            -> Tuple[bool, str, "FileAccess", Union["FileAccess", None]]:
        pass

    def get_file_size(self):
        pass

    def get_last_modification_date(self):
        pass

    def hash(self):
        pass

    def compute_face_boxes(self):
        pass

    def get_image(self):
        pass

    def get_cv2_image(self):
        pass
