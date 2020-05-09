import hashlib
from pathlib import Path
from camerafile.MetadataList import MetadataList


class MediaDirectory:

    def __init__(self, path, parent_dir, parent_set):
        self.name = Path(path).name
        self.path = path
        self.parent_dir = parent_dir
        self.parent_set = parent_set
        self.id = hashlib.md5(self.path.encode()).hexdigest()
        self.metadata = MetadataList(self)

    def __str__(self):
        return self.path
