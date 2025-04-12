from camerafile.fileaccess.FileDescription import FileDescription


class StandardFileDescription(FileDescription):

    def __init__(self, relative_path, file_size=None, system_id=None):
        super().__init__(relative_path)
        self.file_size = file_size
        self.system_id = system_id
