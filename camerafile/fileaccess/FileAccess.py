import os
import re
from datetime import timedelta, datetime
from enum import IntEnum
from typing import Tuple, Union

from camerafile.core import Constants
from camerafile.core.Configuration import Configuration
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

    def copy_post_processing(self, new_file_path):
        if Configuration.get().whatsapp_force_date:
            sent_date, _ = self.parse_whatsapp_filename()
            if sent_date is not None:
                os.utime(new_file_path, (sent_date.timestamp(), sent_date.timestamp()))
                return "[time modified]"
        return ""

    def parse_whatsapp_filename(self) -> tuple[Union[datetime, None], Union[str, None]]:
        if Configuration.get().whatsapp:
            fields = re.findall(r'^(VID|IMG)-([0-9]{8})-WA[0-9]{4}\.(jpg|jpeg|mp4)$', self.file_desc.name)
            if len(fields) == 1 and len(fields[0]) == 3:
                str_date = fields[0][1]
                try:
                    return datetime.strptime(str_date, '%Y%m%d'), "WhatsApp"
                except ValueError:
                    pass
        return None, None

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
