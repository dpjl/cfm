from datetime import datetime
from PIL import Image
from camerafile.Constants import IMAGE_TYPE
from camerafile.ExifTool import ExifTool
import imagehash

class ImageTool:

    @staticmethod
    def read_image(path, orientation):
        img = Image.open(path)
        if orientation is not None:
            if orientation == 3:
                img = img.rotate(180, expand=True)
            if orientation == 6:
                img = img.rotate(270, expand=True)
            if orientation == 8:
                img = img.rotate(90, expand=True)
        return img

    @staticmethod
    def image_hash(self, path, orientation):
        try:
            img = self.read_image(path, orientation)

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

    @staticmethod
    def get_metadata_with_pil(path):
        model = None
        date = None
        orientation = None
        try:
            img = Image.open(path)
            width, height = img.size
            if img.getexif() is not None:
                exif = dict(img.getexif().items())
                if 0x0110 in exif:
                    model = exif[0x0110].strip("\u0000").strip(" ")
                if 0x9003 in exif:
                    try:
                        date = datetime.strptime(exif[0x9003], '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        date = None
                        # comment récupérer ici l'équivalent de FileModifyDate (voir ExifTool) ?
                if 0x0112 in exif:
                    orientation = exif[0x0112]

        except OSError:
            # print("%s can't be hashed as an image" % self.media_file.path)
            return None, None, None, None, None

        return model, date, width, height, orientation

    @staticmethod
    def get_metadata(path, extension):
        model = None
        date = None
        width = None
        height = None
        orientation = None

        if extension in IMAGE_TYPE:
            model, date, width, height, orientation = ImageTool.get_metadata_with_pil(path)

        if date is None:
            model, date, width, height, orientation = ExifTool.get_metadata(path)

        if orientation is not None and (orientation == 6 or orientation == 8):
            old_width = width
            width = height
            height = old_width

        if date is not None:
            date = date.strftime("%Y/%m/%d %H:%M:%S")

        return model, date, width, height, orientation
