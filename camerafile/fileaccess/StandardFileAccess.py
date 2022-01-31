import os
import shutil
from datetime import datetime
from pathlib import Path

import pyzipper
from pyzipper import zipfile

from camerafile.core import Configuration
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.fileaccess.ZipFileAccess import ZipFileAccess
from camerafile.tools.ExifTool import ExifTool


class StandardFileAccess(FileAccess):

    def __init__(self, root_path, path, file_id):
        super().__init__(root_path, path, file_id)

    def open(self):
        return open(self.path, "rb")

    def delete_file(self):
        relative_path = "trash/" + Path(self.path).relative_to(self.root_path).as_posix()
        with pyzipper.AESZipFile(self.get_sync_file(), "w", compression=pyzipper.ZIP_LZMA) as sync_file:
            if Configuration.CFM_SYNC_PASSWORD is not None:
                sync_file.setpassword(Configuration.CFM_SYNC_PASSWORD)
                sync_file.setencryption(pyzipper.WZ_AES, nbits=128)
            sync_file.write(self.path, relative_path)
        os.remove(self.path)
        return True, self.id, ZipFileAccess.concat_path(self.get_sync_file(), relative_path)

    def copy_to(self, new_file_path, copy_mode):
        if os.path.exists(new_file_path):
            return False, self.id, None
        os.makedirs(Path(new_file_path).parent, exist_ok=True)
        if copy_mode == self.FULL_COPY:
            shutil.copy2(self.path, new_file_path)
        elif copy_mode == self.SYM_LINKS:
            os.symlink(self.path, new_file_path)
        elif copy_mode == self.HARD_LINKS:
            os.link(self.path, new_file_path)
        else:
            print("Invalid copy mode : " + copy_mode)
        return True, self.id, new_file_path

    def get_last_modification_date(self):
        # round to the nearest even second because of differences between ntfs en fat
        return self.even_round(datetime.fromtimestamp(Path(self.path).stat().st_mtime))

    def call_exif_tool(self):
        return ExifTool.get_metadata(self.path)
