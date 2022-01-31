from camerafile.tools.Hash import Hash
from camerafile.metadata.Metadata import Metadata


class MetadataSignature(Metadata):

    def __init__(self, file_access, extension):
        super().__init__(None)
        self.file_access = file_access
        self.extension = extension

    def compute_value(self):
        if self.value is None:
            self.value = Hash(self.file_access).get()
