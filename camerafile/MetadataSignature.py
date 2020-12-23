import hashlib

from camerafile.Constants import IMAGE_TYPE
from camerafile.ImageTool import ImageTool
from camerafile.Metadata import Metadata, ORIENTATION


class MetadataSignature(Metadata):

    def __init__(self, media_file):
        super().__init__(media_file)
        self.thumbnail = None

    def set_value_computed(self, value):
        self.value = value
        self.media_file.parent_set.update_date_and_sig_map(self.media_file)

    def compute_value(self):
        if self.value is None:
            if self.media_file.extension in IMAGE_TYPE:
                hash_value = ImageTool.image_hash(self.media_file.path,
                                                  self.media_file.metadata.get_value(ORIENTATION))
            else:
                hash_value = self.md5_hash(self.media_file.path)
            self.value = hash_value
            self.media_file.parent_set.update_date_and_sig_map(self.media_file)

    @staticmethod
    def md5_hash(path):
        with open(path, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(65536):
                file_hash.update(chunk)
        return file_hash.hexdigest()
