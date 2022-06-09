from camerafile.fileaccess.FileDescription import FileDescription


class StandardFileDescription(FileDescription):

    def __init__(self, relative_path, file_size=None):
        super().__init__(relative_path)
        self.file_size = file_size
