import os
import shutil
from datetime import datetime
from pathlib import Path

import pyzipper
from typing import Tuple, Union

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess, CopyMode
from camerafile.tools.ExifTool import ExifTool


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

    def call_exif_tool(self, args):
        return ExifTool.get_metadata(self.path, *args)
