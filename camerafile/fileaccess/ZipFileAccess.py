import os
from datetime import datetime
from pathlib import Path

from pyzipper import zipfile

from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.tools.ExifTool import ExifTool


class ZipFileAccess(FileAccess):

    def __init__(self, root_path, path, file_id):
        super().__init__(root_path, path, file_id)
        temp_split = path.rsplit("<~>", 1)
        if len(temp_split) != 2:
            print("An error occurs with file: " + path)
            return
        self.zip_path = temp_split[0]
        self.file_path = temp_split[1]

    def is_in_trash(self):
        return self.zip_path == self.get_sync_file()

    def delete_file(self):
        print("Delete not managed inside zip: " + self.path)
        return False, self.id, None

    def open(self):
        with zipfile.ZipFile(self.zip_path) as zip_file:
            return zip_file.open(self.file_path, "r")

    @staticmethod
    def split_path(path):
        return path.rsplit("<~>", 1)

    @staticmethod
    def concat_path(path, file):
        return path + "<~>" + file

    def copy_to(self, new_file_path, copy_mode):
        os.makedirs(Path(new_file_path).parent, exist_ok=True)
        with zipfile.ZipFile(self.zip_path) as origin:
            with open(new_file_path, 'wb') as destination:
                destination.write(origin.read(self.file_path))
        return True, self.id, new_file_path

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
            return None, None, None, None, None, None

        return result
