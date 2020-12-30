import hashlib
import os

import imagehash

from camerafile.Constants import IMAGE_TYPE
from camerafile.Image import Image


class Hash:

    def __init__(self, path):
        self.path = path
        self.extension = self.extension = os.path.splitext(path.name)[1].lower()

    def get(self):
        if self.extension in IMAGE_TYPE:
            hash_value = self.image_hash()
        else:
            hash_value = self.md5_hash()
        return hash_value

    def image_hash(self):
        image = Image(self.path)
        try:
            # faster than md5 hash
            # concatenates date to limitate false positives
            # can be a problem for "rafales" ?
            # img_date = datetime.strptime(self.media_file.metadata.get_value(DATE), '%Y/%m/%d %H:%M:%S')
            # date_str = img_date.strftime('-%Y-%m-%d-%H-%M-%S-%f')
            result = str(imagehash.phash(image.image_data))

            # doesn't work (why ?)
            # and slower
            # file_hash = hashlib.md5()
            # file_hash.update(img.tobytes())
            # result = file_hash.hexdigest()
        except OSError:
            result = self.md5_hash()
        return result

    def md5_hash(self):
        with open(self.path, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(65536):
                file_hash.update(chunk)
        return file_hash.hexdigest()
