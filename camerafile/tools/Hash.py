import hashlib

import imagehash


class Hash:

    @staticmethod
    def image_hash(pil_image):
        # faster than md5 hash
        # concatenates date to limitate false positives
        # can be a problem for "rafales" ?
        # img_date = datetime.strptime(self.media_file.metadata.get_value(DATE), '%Y/%m/%d %H:%M:%S')
        # date_str = img_date.strftime('-%Y-%m-%d-%H-%M-%S-%f')

        return str(imagehash.phash(pil_image))

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
