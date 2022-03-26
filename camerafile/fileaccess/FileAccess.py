import os
from datetime import timedelta
from enum import IntEnum
from pathlib import Path

from typing import Tuple, Union

from camerafile.core import Constants


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

    def __init__(self, path):
        path = Path(path)
        self.path = path.as_posix()
        self.name = path.name
        self.extension = os.path.splitext(self.name)[1].lower()
        self.file_size = None
        self.id = None
        self.relative_path = None

    def set_id(self, identifier):
        self.id = identifier

    def set_relative_path(self, relative_path):
        self.relative_path = relative_path

    def get_path(self):
        return self.path

    def get_extension(self):
        return self.extension

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
        return self.extension in Constants.IMAGE_TYPE

    def is_video(self):
        return self.extension in Constants.IMAGE_TYPE

    def is_qt_video(self):
        return self.extension in Constants.QT_TYPE

    def is_avi_video(self):
        return self.extension in Constants.AVI_TYPE

    def read_md(self, args):
        pass

    def open(self):
        pass

    def copy_to(self, new_file_path, copy_mode: CopyMode) \
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
