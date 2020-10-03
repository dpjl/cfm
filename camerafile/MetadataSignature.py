import hashlib
import imagehash
from PIL import Image

from camerafile.Constants import IMAGE_TYPE
from camerafile.Metadata import Metadata, ORIENTATION


class MetadataSignature(Metadata):

    def __init__(self, media_file):
        super().__init__(media_file)
        self.thumbnail = None

    def set_value_computed(self, value):
        self.value_computed = value
        self.media_file.parent_set.update_date_and_sig_map(self.media_file)

    def compute_value(self):
        if self.value_computed is None:
            if self.media_file.extension in IMAGE_TYPE:
                hash_value = self.image_hash()
            else:
                hash_value = self.md5_hash()
            self.value_computed = hash_value
            self.media_file.parent_set.update_date_and_sig_map(self.media_file)

    def image_hash(self):
        try:
            img = Image.open(self.media_file.path)
            orientation = self.media_file.metadata.get_value(ORIENTATION)
            if orientation is not None:
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                if orientation == 6:
                    img = img.rotate(270, expand=True)
                if orientation == 8:
                    img = img.rotate(90, expand=True)

            # faster than md5 hash
            # concatenates date to limitate false positives
            # can be a problem for "rafales" ?
            # img_date = datetime.strptime(self.media_file.metadata.get_value(DATE), '%Y/%m/%d %H:%M:%S')
            # date_str = img_date.strftime('-%Y-%m-%d-%H-%M-%S-%f')
            result = str(imagehash.phash(img))

            # doesn't work (why ?)
            # and slower
            # file_hash = hashlib.md5()
            # file_hash.update(img.tobytes())
            # result = file_hash.hexdigest()
        except OSError:
            result = self.md5_hash()
        return result

    def md5_hash(self):
        with open(self.media_file.path, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(65536):
                file_hash.update(chunk)
        return file_hash.hexdigest()
