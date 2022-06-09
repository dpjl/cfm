import hashlib
from pathlib import Path

from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.metadata.MetadataList import MetadataList


class MediaDirectory:

    def __init__(self, path, parent_dir, parent_set):
        self.name = Path(path).name
        self.path = path
        self.parent_dir = parent_dir
        self.parent_set = parent_set
        self.id = hashlib.md5(self.path.encode()).hexdigest()
        self.extension = None
        self.file_desc = StandardFileDescription(path),
        self.metadata = MetadataList()

    def __str__(self):
        return self.path
