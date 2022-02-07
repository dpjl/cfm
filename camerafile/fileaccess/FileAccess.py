import hashlib
import os
from datetime import timedelta
from pathlib import Path


class FileAccess:
    HARD_LINKS = "HARD_LINKS"
    SYM_LINKS = "SYM_LINKS"
    FULL_COPY = "FULL_COPY"

    CFM_TRASH = ".cfm-sync.zip"

    TYPE = -1

    def __init__(self, root_path, path):
        path = Path(path)
        root_path = Path(root_path)
        self.root_path = root_path.as_posix()
        self.path = path.as_posix()
        self.relative_path = path.relative_to(root_path).as_posix()
        self.name = path.name
        self.extension = os.path.splitext(self.name)[1].lower()
        self.id: str = hashlib.md5(self.relative_path.encode()).hexdigest()
        self.loaded_from_database = False
        self.file_size = None

    def get_relative_path(self):
        return self.relative_path

    def get_path(self):
        return self.path

    def is_in_trash(self):
        return False

    def get_sync_file(self):
        return (Path(self.root_path) / self.CFM_TRASH).as_posix()

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

    def call_exif_tool(self):
        pass

    def open(self):
        pass

    def copy_to(self, new_file_path, copy_mode):
        pass

    def get_file_size(self):
        pass

    def get_last_modification_date(self):
        pass
