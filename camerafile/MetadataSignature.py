from camerafile.Hash import Hash
from camerafile.Metadata import Metadata


class MetadataSignature(Metadata):

    def __init__(self, media_id, media_path, extension):
        super().__init__(None)
        self.media_id = media_id
        self.media_path = media_path
        self.extension = extension

    @staticmethod
    def compute_signature_task(signature_metadata):
        try:
            signature_metadata.compute_value()
            return signature_metadata
        except:
            print("Error during compute_signature_task execution for " + str(signature_metadata.media_path))
            return signature_metadata

    def compute_value(self):
        if self.value is None:
            self.value = Hash(self.media_path).get()
