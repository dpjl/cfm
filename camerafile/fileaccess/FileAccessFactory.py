from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.fileaccess.StandardFileAccess import StandardFileAccess
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.fileaccess.ZipFileAccess import ZipFileAccess
from camerafile.fileaccess.ZipFileDescription import ZipFileDescription


class FileAccessFactory:

    @staticmethod
    def get(root_dir: str, file_desc: FileDescription):
        if isinstance(file_desc, StandardFileDescription):
            return StandardFileAccess(root_dir, file_desc)
        if isinstance(file_desc, ZipFileDescription):
            return ZipFileAccess(root_dir, file_desc)
