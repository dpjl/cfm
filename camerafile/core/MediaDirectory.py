import hashlib
from pathlib import Path
from typing import List, TYPE_CHECKING
import os

from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.metadata.MetadataList import MetadataList

if TYPE_CHECKING:
    from camerafile.core.MediaFile import MediaFile


class MediaDirectory:

    def __init__(self, relative_path, parent_dir, parent_set):
        self.file_desc = StandardFileDescription(relative_path)
        self.parent_dir: "MediaDirectory" = parent_dir
        self.parent_set = parent_set
        self.metadata = MetadataList()
        self.children_files: List["MediaFile"] = []
        self.children_dirs: List["MediaDirectory"] = []

    def __str__(self):
        return self.file_desc.relative_path

    def add_child_file(self, media_file: "MediaFile"):
        self.children_files.append(media_file)

    def add_child_dir(self, child_dir: "MediaDirectory"):
        self.children_dirs.append(child_dir)
