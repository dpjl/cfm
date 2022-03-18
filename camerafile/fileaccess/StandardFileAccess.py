import mmap
import os
import shutil
from datetime import datetime
from pathlib import Path

import pyzipper
from typing import Tuple, Union

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess, CopyMode
from camerafile.mdtools.AVIMdReader import AVIMdReader
from camerafile.mdtools.ExifToolReader import ExifTool
from camerafile.mdtools.JPEGMdReader import JPEGMdReader
from camerafile.metadata.MetadataFaces import MetadataFaces
from camerafile.tools.CFMImage import CFMImage
from camerafile.tools.Hash import Hash


class StandardFileAccess(FileAccess):

    def __init__(self, path, file_size=None):
        super().__init__(path)
        self.file_size = file_size

    def open(self):
        return open(self.path, "rb")

    def get_file_size(self):
        if self.file_size is None:
            self.file_size = os.stat(self.path).st_size
        return self.file_size

    def delete_file(self, trash_file_path) -> Tuple[bool, str, FileAccess, Union[FileAccess, None]]:
        from camerafile.fileaccess.ZipFileAccess import ZipFileAccess
        with pyzipper.AESZipFile(trash_file_path, "w", compression=pyzipper.ZIP_LZMA) as sync_file:
            password = Configuration.get().cfm_sync_password
            if password is not None:
                sync_file.setpassword(password)
                sync_file.setencryption(pyzipper.WZ_AES, nbits=128)
            sync_file.write(self.path, self.relative_path)
        os.remove(self.path)
        return True, "Moved to trash", self, ZipFileAccess(trash_file_path, self.relative_path, self.file_size)

    def copy_to(self, new_file_path: str, copy_mode: CopyMode) -> Tuple[bool, str, FileAccess, Union[FileAccess, None]]:
        if os.path.exists(new_file_path):
            return False, "File does not exist", self, None
        os.makedirs(Path(new_file_path).parent, exist_ok=True)
        if copy_mode == CopyMode.COPY:
            shutil.copy2(self.path, new_file_path)
        elif copy_mode == CopyMode.SOFT_LINK:
            os.symlink(self.path, new_file_path)
        elif copy_mode == CopyMode.HARD_LINK:
            os.link(self.path, new_file_path)
        else:
            return False, "Invalid copy path", self, None
        return True, "Copied", self, StandardFileAccess(new_file_path, self.file_size)

    def get_last_modification_date(self):
        # round to the nearest even second because of differences between ntfs en fat
        return self.even_round(datetime.fromtimestamp(Path(self.path).stat().st_mtime))

    def call_exif_tool(self, call_info, args):
        try:
            return call_info, ExifTool.get_metadata(self.path, *args)
        except:
            return call_info + " -> Failed", {}

    def read_md(self, args):
        if Configuration.get().exif_tool:
            return "ExifTool", ExifTool.get_metadata(self.path, *args)
        else:
            if self.is_image():
                try:
                    return "JPEGMdReader", JPEGMdReader(self.path).get_metadata(*args)
                except:
                    return self.call_exif_tool("JPEGMdReader -> ExifTool", args)

            # This code is not ready (QTMdReader is much less compatible with different brands than ExifTool)
            # elif self.is_qt_video():
            #    return QTMdReader(self.path).get_metadata(*args)
            elif self.is_avi_video():
                try:
                    return "AVIMdReader", AVIMdReader(self.path).get_metadata(*args)
                except:
                    return self.call_exif_tool("AVIMdReader -> ExifTool", args)
            else:
                return self.call_exif_tool("ExifTool", args)

    def hash(self):
        if self.is_image():
            with open(self.path, 'rb') as f:
                with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                    with CFMImage(mmap_obj) as image:
                        try:
                            return Hash.image_hash(image.image_data)
                        except BaseException as e:
                            print("image_hash: " + str(e) + " / " + self.relative_path)
                            return str(self.get_file_size())
        else:
            return str(self.get_file_size())

    def compute_face_boxes(self):
        if self.is_image():
            with open(self.path, 'rb') as f:
                with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                    with CFMImage(mmap_obj) as image:
                        return MetadataFaces.static_compute_face_boxes(image)
