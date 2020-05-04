from pathlib import Path

import bsdiff4
import os


class CFMPatch:

    def __init__(self, file_path):
        self.file_path = file_path
        self.first_file = None
        self.second_file = None

    def set_first_file(self, file_path):
        with open(file_path, "rb") as f:
            self.first_file = f.read()

    def set_second_file(self, file_path):
        with open(file_path, "rb") as f:
            self.second_file = f.read()

    def create(self):
        patch = bsdiff4.diff(self.second_file, self.first_file)
        patch_path = Path(str(self.file_path) + ".patch")
        with open(patch_path, "wb") as f:
            f.write(patch)

    def apply(self):
        patch_path = Path(str(self.file_path) + ".patch")
        if os.path.exists(patch_path):
            bsdiff4.file_patch_inplace(self.file_path, patch_path)
            os.remove(patch_path)

