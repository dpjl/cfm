import hashlib
import os
from pathlib import Path


class FileDescription:

    def __init__(self, relative_path):
        relative_path = Path(relative_path)
        self.relative_path = relative_path.as_posix()
        self.name = relative_path.name
        self.id: str = hashlib.md5(self.relative_path.encode()).hexdigest()
        self.extension = os.path.splitext(self.name)[1].lower()
        self.file_size = None

    def get_relative_path(self):
        return self.relative_path

    def get_id(self):
        return self.id
