import hashlib
import os
from pathlib import Path

from camerafile.core import Constants
from camerafile.core.Logging import Logger

LOGGER = Logger(__name__)


class FileDescription:

    def __init__(self, relative_path):
        relative_path = Path(relative_path)
        self.relative_path = relative_path.as_posix()
        self.name = relative_path.name
        self.id = self._compute_id()
        self.extension = os.path.splitext(self.name)[1].lower()
        self.file_size = None
        self.system_id = None

    def compare_with(self, file_desc_2: "FileDescription"):
        LOGGER.diff("FileDescription", "relative_path", self.relative_path, file_desc_2.relative_path)
        LOGGER.diff("FileDescription", "name", self.name, file_desc_2.name)
        LOGGER.diff("FileDescription", "id", self.id, file_desc_2.id)
        LOGGER.diff("FileDescription", "extension", self.extension, file_desc_2.extension)
        LOGGER.diff("FileDescription", "file_size", self.file_size, file_desc_2.file_size)
        LOGGER.diff("FileDescription", "system_id", self.system_id, file_desc_2.system_id)

    def get_relative_path(self):
        return self.relative_path

    def get_id(self):
        return self.id
    
    def is_image(self):
        return self.extension in Constants.IMAGE_TYPE

    def is_video(self):
        return self.extension in Constants.VIDEO_TYPE

    def _compute_id(self) -> str:
        return hashlib.md5(self.relative_path.encode()).hexdigest()

    def update_relative_path(self, new_relative_path: str) -> None:
        self.relative_path = new_relative_path
        self.id = self._compute_id()
