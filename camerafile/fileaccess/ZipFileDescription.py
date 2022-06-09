from pathlib import Path

from camerafile.fileaccess.FileDescription import FileDescription


class ZipFileDescription(FileDescription):

    def __init__(self, relative_zip_path, file_path, file_size=None):
        super().__init__(Path(relative_zip_path) / file_path)
        self.relative_zip_path = relative_zip_path
        self.file_path = file_path
        self.file_size = file_size
