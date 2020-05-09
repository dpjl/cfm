import hashlib
import imagehash
from PIL import Image
from camerafile.Metadata import Metadata


class MetadataSignature(Metadata):

    def __init__(self, media_file):
        super().__init__(media_file)

    def compute_value(self):
        if self.value_computed is None:
            if self.media_file.extension in [".jpg", ".jpeg", ".png"]:
                image_hash = imagehash.average_hash(Image.open(self.media_file.path))
                self.value_computed = str(image_hash)
                # imagehash.hex_to_hash(self.value_computed)
            else:
                self.value_computed = self.md5_hash()

    def md5_hash(self):
        with open(self.media_file.path, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()
