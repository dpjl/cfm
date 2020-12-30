from camerafile.Hash import Hash
from camerafile.Metadata import Metadata


class MetadataSignature(Metadata):

    def __init__(self, media_file):
        super().__init__(media_file)
        self.thumbnail = None

    def set_value_computed(self, value):
        self.value = value
        self.media_file.parent_set.update_date_and_sig_map(self.media_file)

    def compute_value(self):
        if self.value is None:
            self.value = Hash(self.media_file.path).get()
            self.media_file.parent_set.update_date_and_sig_map(self.media_file)


