import hashlib
import os

import imagehash
from PIL import ImageOps

from camerafile.core.Constants import IMAGE_TYPE
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.tools.CFMImage import CFMImage


class Hash:

    def __init__(self, file_access: FileAccess):
        self.file_access = file_access
        self.extension = file_access.get_extension()

    def get(self):
        if self.extension in IMAGE_TYPE:
            hash_value = self.image_hash()
        else:
            hash_value = self.file_size_in_bytes()
            # hash_value = self.md5_hash()
        return hash_value

    def image_hash(self):

        with self.file_access.open() as image_file:
            image = CFMImage(image_file)
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
            except BaseException as e:
                print("image_hash: " + str(e) + " / " + self.file_access.relative_path)
                result = self.file_size_in_bytes()
                # result = self.md5_hash()
        return result

    def file_size_in_bytes(self):
        return str(self.file_access.get_file_size())

    def md5_hash(self):
        with self.file_access.open() as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()

    def md5_hash_old(self):
        with self.file_access.open() as f:
            file_hash = hashlib.md5()
            while chunk := f.read(65536):
                file_hash.update(chunk)
        return file_hash.hexdigest()
