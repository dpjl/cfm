import os
from datetime import timedelta
from pathlib import Path


class FileAccess:
    HARD_LINKS = "HARD_LINKS"
    SYM_LINKS = "SYM_LINKS"
    FULL_COPY = "FULL_COPY"

    CFM_TRASH = ".cfm-sync.zip"

    def __init__(self, root_path, path, file_id):
        self.root_path = root_path
        self.path = path
        self.id = file_id

    def is_in_trash(self):
        return False

    def get_sync_file(self):
        return (Path(self.root_path) / self.CFM_TRASH).as_posix()

    def get_extension(self):
        return os.path.splitext(Path(self.path).name)[1].lower()

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
