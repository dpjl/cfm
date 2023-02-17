import hashlib

from camerafile.core.Logging import Logger

LOGGER = Logger(__name__)


class Hash:
    image_hash_lib = None

    @staticmethod
    def image_hash(pil_image):

        if Hash.image_hash_lib is None:
            LOGGER.debug("Load imagehash module")
            import imagehash
            Hash.image_hash_lib = imagehash

        # faster than md5 hash
        # concatenates date to limitate false positives
        # can be a problem for "rafales" ?
        # img_date = datetime.strptime(self.media_file.metadata.get_value(DATE), '%Y/%m/%d %H:%M:%S')
        # date_str = img_date.strftime('-%Y-%m-%d-%H-%M-%S-%f')

        return str(Hash.image_hash_lib.phash(pil_image))

        # doesn't work (why ?)
        # and slower
        # file_hash = hashlib.md5()
        # file_hash.update(img.tobytes())
        # result = file_hash.hexdigest()

    def md5_hash(self, file):
        file_hash = hashlib.md5()
        while chunk := file.read(8192):
            file_hash.update(chunk)
        return file_hash.hexdigest()

    def md5_hash_old(self, file):
        file_hash = hashlib.md5()
        while chunk := file.read(65536):
            file_hash.update(chunk)
        return file_hash.hexdigest()
