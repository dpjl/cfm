from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.tools.Hash import Hash
from camerafile.metadata.Metadata import Metadata


class MetadataSignature(Metadata):

    def __init__(self, file_access: FileAccess):
        super().__init__(None)
        self.file_access = file_access

    def compute_value(self):
        if self.value is None:
            self.value = Hash(self.file_access).get()
