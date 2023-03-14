import os
from datetime import datetime
from pathlib import Path
from typing import Tuple, Union

from pyzipper import zipfile

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess, CopyMode
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.fileaccess.ZipFileDescription import ZipFileDescription
from camerafile.mdtools.ExifToolReader import ExifTool, ExifToolNotFound
from camerafile.mdtools.JPEGMdReader import JPEGMdReader
from camerafile.mdtools.MdException import MdException
from camerafile.tools.CFMImage import CFMImage
from camerafile.tools.Hash import Hash


class ZipFileAccess(FileAccess):

    def __init__(self, root_path, zip_file_description: ZipFileDescription):
        super().__init__(root_path, None)
        self.file_desc = zip_file_description

    def get_zip_path(self):
        return self.root_path + os.sep + self.file_desc.relative_zip_path

    def get_file_size(self):
        if self.file_desc.file_size is None:
            with zipfile.ZipFile(self.get_zip_path()) as zip_file:
                self.file_desc.file_size = zip_file.getinfo(self.file_desc.file_path).file_size
        return self.file_desc.file_size

    def open(self):
        with zipfile.ZipFile(self.get_zip_path()) as zip_file:
            return zip_file.open(self.file_desc.file_path)

    def delete_file(self, trash_file_path) -> Tuple[bool, str, FileAccess, Union[FileAccess, None]]:
        print("Delete not managed inside zip: " + self.get_path())
        return False, "Not managed inside zip", self, None

    def copy_to(self, new_root_path, new_relative_file_path: str, copy_mode: CopyMode) -> \
            Tuple[bool, str, FileDescription, Union[FileDescription, None]]:
        new_file_path = new_root_path / new_relative_file_path
        os.makedirs(Path(new_file_path).parent, exist_ok=True)
        with zipfile.ZipFile(self.get_zip_path()) as origin:
            with open(new_file_path, 'wb') as destination:
                destination.write(origin.read(self.file_desc.file_path))
            date_time = self.get_last_modification_date().timestamp()
            os.utime(new_file_path, (date_time, date_time))
            self.copy_post_processing(new_file_path)

        post_proc_status = self.copy_post_processing(new_file_path)
        status = f"Extracted {post_proc_status}"
        return True, status, self.file_desc, StandardFileDescription(new_relative_file_path,
                                                                     self.file_desc.file_size)

    def get_last_modification_date(self):
        try:
            with zipfile.ZipFile(self.get_zip_path()) as zip_file:
                result = self.even_round(datetime(*zip_file.getinfo(self.file_desc.file_path).date_time))
        except KeyError as e:
            print(str(e) + "[" + self.get_path() + "]")
            return None
        return result

    def call_exif_tool(self, call_info, args):
        try:
            with zipfile.ZipFile(self.get_zip_path()) as zip_file:
                return call_info, ExifTool.get_metadata(zip_file.read(self.file_desc.file_path), *args)
        except ExifToolNotFound as e:
            raise e
        except MdException:
            return call_info + " -> Failed", {}

    def read_md(self, args):
        if Configuration.get().exif_tool:
            return self.call_exif_tool("ExifTool", args)
        else:
            if self.is_image():
                try:
                    with zipfile.ZipFile(self.get_zip_path()) as zip_file:
                        return "JPEGMdReader", JPEGMdReader(zip_file.open(self.file_desc.file_path)).get_metadata(*args)
                except BaseException:
                    return self.call_exif_tool("JPEGMdReader -> ExifTool", args)
            else:
                return self.call_exif_tool("ExifTool", args)

    def hash(self):
        if self.is_image():
            with self.open() as image_file:
                with CFMImage(image_file, self.file_desc.name) as image:
                    return Hash.image_hash(image)
        else:
            return self.get_file_size()

    def get_image(self):
        if self.is_image():
            with zipfile.ZipFile(self.get_zip_path()) as zip_file:
                with zip_file.open(self.file_desc.file_path) as zip_file_element:
                    return CFMImage(zip_file_element, self.file_desc.name)
