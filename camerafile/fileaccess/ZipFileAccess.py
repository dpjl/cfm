import os
from pathlib import Path
from typing import Tuple

from pyzipper import zipfile
from datetime import datetime
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.tools.ExifTool import ExifTool


class ZipFileAccess(FileAccess):
    TYPE = 1

    def __init__(self, root_path, zip_path, file_path):
        super().__init__(root_path, Path(zip_path) / file_path)
        self.zip_path = zip_path
        self.file_path = file_path

    def get_file_size(self):
        if self.file_size is None:
            with zipfile.ZipFile(self.zip_path) as zip_file:
                self.file_size = zip_file.getinfo(self.file_path).file_size
        return self.file_size

    def is_in_trash(self):
        return self.zip_path == self.get_sync_file()

    def delete_file(self):
        print("Delete not managed inside zip: " + self.path)
        return False, self.id, None

    def open(self):
        with zipfile.ZipFile(self.zip_path) as zip_file:
            return zip_file.open(self.file_path, "r")

    def copy_to(self, new_file_path: str, copy_mode: str) -> Tuple[bool, str, str, str]:
        os.makedirs(Path(new_file_path).parent, exist_ok=True)
        with zipfile.ZipFile(self.zip_path) as origin:
            with open(new_file_path, 'wb') as destination:
                destination.write(origin.read(self.file_path))
        return True, "Extracted", self.id, new_file_path

    def get_last_modification_date(self):
        try:
            with zipfile.ZipFile(self.zip_path) as zip_file:
                result = self.even_round(datetime(*zip_file.getinfo(self.file_path).date_time))
        except KeyError as e:
            print(str(e) + "[" + self.path + "]")
            return None
        return result

    def call_exif_tool(self):
        try:
            with zipfile.ZipFile(self.zip_path) as zip_file:
                result = ExifTool.get_metadata(zip_file.read(self.file_path))
        except KeyError as e:
            print(str(e) + "[" + self.path + "]")
            return None, None, None, None, None, None, None

        return result
