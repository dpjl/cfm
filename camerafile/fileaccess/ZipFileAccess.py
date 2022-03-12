import os
from datetime import datetime
from pathlib import Path

from pyzipper import zipfile
from typing import Tuple, Union

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess, CopyMode
from camerafile.fileaccess.StandardFileAccess import StandardFileAccess
from camerafile.mdtools.ExifToolReader import ExifTool
from camerafile.mdtools.JPEGMdReader import JPEGMdReader


class ZipFileAccess(FileAccess):

    def __init__(self, zip_path, file_path, file_size=None):
        super().__init__(Path(zip_path) / file_path)
        self.zip_path = zip_path
        self.file_path = file_path
        self.file_size = file_size

    def get_file_size(self):
        if self.file_size is None:
            with zipfile.ZipFile(self.zip_path) as zip_file:
                self.file_size = zip_file.getinfo(self.file_path).file_size
        return self.file_size

    def open(self):
        with zipfile.ZipFile(self.zip_path) as zip_file:
            return zip_file.open(self.file_path)

    def delete_file(self, trash_file_path) -> Tuple[bool, str, FileAccess, Union[FileAccess, None]]:
        print("Delete not managed inside zip: " + self.path)
        return False, "Not managed inside zip", self, None

    def copy_to(self, new_file_path: str, copy_mode: CopyMode) -> Tuple[bool, str, FileAccess, Union[FileAccess, None]]:
        os.makedirs(Path(new_file_path).parent, exist_ok=True)
        with zipfile.ZipFile(self.zip_path) as origin:
            with open(new_file_path, 'wb') as destination:
                destination.write(origin.read(self.file_path))
        return True, "Extracted", self, StandardFileAccess(new_file_path, self.file_size)

    def get_last_modification_date(self):
        try:
            with zipfile.ZipFile(self.zip_path) as zip_file:
                result = self.even_round(datetime(*zip_file.getinfo(self.file_path).date_time))
        except KeyError as e:
            print(str(e) + "[" + self.path + "]")
            return None
        return result

    def call_exif_tool(self, args):
        try:
            with zipfile.ZipFile(self.zip_path) as zip_file:
                result = ExifTool.get_metadata(zip_file.read(self.file_path), *args)
        except KeyError as e:
            print(str(e) + "[" + self.path + "]")
            return {}
        return result

    def read_md(self, args):
        if Configuration.get().exif_tool:
            return self.call_exif_tool(args)
        else:
            if self.is_image():
                with zipfile.ZipFile(self.zip_path) as zip_file:
                    return JPEGMdReader(zip_file.open(self.file_path)).get_metadata(*args)
            else:
                return self.call_exif_tool(args)
