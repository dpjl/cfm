import logging
import mmap
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path

import pyzipper
from typing import Tuple, Union

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess, CopyMode
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.mdtools.AVIMdReader import AVIMdReader
from camerafile.mdtools.ExifToolReader import ExifTool, ExifToolNotFound
from camerafile.mdtools.JPEGMdReader import JPEGMdReader
from camerafile.mdtools.MdException import MdException
from camerafile.tools.CFMImage import CFMImage
from camerafile.tools.Hash import Hash

LOGGER = logging.getLogger(__name__)


class StandardFileAccess(FileAccess):

    def __init__(self, root_path, file_description: StandardFileDescription):
        super().__init__(root_path, file_description)

    def open(self):
        return open(self.get_path(), "rb")

    def get_file_size(self):
        if self.file_desc.file_size is None:
            self.file_desc.file_size = os.stat(self.get_path()).st_size
        return self.file_desc.file_size

    def delete_file(self, trash_file_path) -> Tuple[bool, str, FileAccess, Union[FileAccess, None]]:
        from camerafile.fileaccess.ZipFileAccess import ZipFileAccess
        with pyzipper.AESZipFile(trash_file_path, "w", compression=pyzipper.ZIP_LZMA) as sync_file:
            password = Configuration.get().cfm_sync_password
            if password is not None:
                sync_file.setpassword(password)
                sync_file.setencryption(pyzipper.WZ_AES, nbits=128)
            sync_file.write(self.get_path(), self.file_desc.relative_path)
        os.remove(self.get_path())
        return True, "Moved to trash", self, ZipFileAccess(trash_file_path, self.file_desc.relative_path,
                                                           self.file_desc.file_size)

    def copy_to(self, new_root_path, new_relative_file_path: str, copy_mode: CopyMode) \
            -> Tuple[bool, str, FileDescription, Union[FileDescription, None]]:
        new_file_path = new_root_path / new_relative_file_path
        if os.path.exists(new_file_path):
            return False, "File does not exist", self.file_desc, None
        os.makedirs(Path(new_file_path).parent, exist_ok=True)
        if copy_mode == CopyMode.COPY:
            shutil.copy2(self.get_path(), new_file_path)
        elif copy_mode == CopyMode.SOFT_LINK:
            os.symlink(self.get_path(), new_file_path)
        elif copy_mode == CopyMode.HARD_LINK:
            os.link(self.get_path(), new_file_path)
        else:
            return False, "Invalid copy path", self.file_desc, None

        post_proc_status = self.copy_post_processing(new_file_path)
        status = f"Copied ({str(copy_mode)}) {post_proc_status}"
        return True, status, self.file_desc, StandardFileDescription(new_relative_file_path, self.file_desc.file_size)

    def get_last_modification_date(self):
        # round to the nearest even second because of differences between ntfs en fat
        return self.even_round(datetime.fromtimestamp(Path(self.get_path()).stat().st_mtime))

    def call_exif_tool(self, call_info, args):
        try:
            return call_info, ExifTool.get_metadata(self.get_path(), *args)
        except ExifToolNotFound as e:
            raise e
        except MdException as e:
            LOGGER.info(f"{self.get_path()} : {e}")
            return call_info + " -> Failed", {}

    def read_md(self, args):
        if Configuration.get().exif_tool:
            return self.call_exif_tool("ExifTool", args)
        else:
            if self.is_image():
                try:
                    return "JPEGMdReader", JPEGMdReader(self.get_path()).get_metadata(*args)
                except Exception:
                    LOGGER.info(traceback.format_exc())
                    LOGGER.info("Failed with JPEGMdReader, try with ExifTool")
                    return self.call_exif_tool("JPEGMdReader -> ExifTool", args)
            elif self.is_avi_video():
                try:
                    return "AVIMdReader", AVIMdReader(self.get_path()).get_metadata(*args)
                except Exception:
                    LOGGER.info(traceback.format_exc())
                    return self.call_exif_tool("AVIMdReader -> ExifTool", args)
            else:
                return self.call_exif_tool("ExifTool", args)

    def hash(self):
        if self.is_image():
            with open(self.get_path(), 'rb') as f:
                with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                    with CFMImage(mmap_obj, self.file_desc.name) as image:
                        return Hash.image_hash(image)
        else:
            return self.get_file_size()

    def get_image(self):
        if self.is_image():
            with open(self.get_path(), 'rb') as f:
                with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                    return CFMImage(mmap_obj, self.file_desc.name)
