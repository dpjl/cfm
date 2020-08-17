import base64
import hashlib
import io

import imagehash
from PIL import Image
from camerafile.Metadata import Metadata

HASH = "Hash"
WIDTH = "Width"
HEIGHT = "Height"
FORMAT = "Format"
THUMBNAIL = "Thumbnail"


class MetadataSignature(Metadata):

    def __init__(self, media_file):
        super().__init__(media_file)
        self.thumbnail = None

    def compute_value(self):
        if self.value_computed is None:
            if self.media_file.extension in [".jpg", ".jpeg", ".png"]:
                try:
                    image = Image.open(self.media_file.path)
                    width, height = image.size
                    img_format = image.format
                    image.thumbnail((100, 100))
                    bytes_output = io.BytesIO()
                    image.save(bytes_output, format='JPEG')
                    image_hash = imagehash.phash(image)
                    # imagehash.hex_to_hash(self.value_computed)

                    self.thumbnail = bytes_output.getvalue()
                    self.value_computed = {FORMAT: img_format,
                                           WIDTH: str(width),
                                           HEIGHT: str(height),
                                           HASH: str(image_hash)}

                except OSError:
                    print("%s can't be hashed as an image" % self.media_file.path)
                    self.value_computed = {HASH: self.md5_hash()}
            else:
                self.value_computed = {HASH: self.md5_hash()}
            self.media_file.parent_set.update_sig_maps(self.media_file)

    def md5_hash(self):
        with open(self.media_file.path, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(65536):
                file_hash.update(chunk)
        return file_hash.hexdigest()
