from datetime import datetime

from PIL import Image as PilImage, ImageDraw, ImageOps


class Image:

    def __init__(self, file):
        self.file = file
        self.image_data = None
        self.model = None
        self.date = None
        self.width = None
        self.height = None
        self.orientation = None
        self.read_image()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.image_data is not None:
            self.image_data.close()

    def read_image(self):
        try:
            self.image_data = PilImage.open(self.file)
            self.get_metadata_with_pil()
            self.rotate_if_necessary()
            self.width, self.height = self.image_data.size
        except:
            self.image_data = None

    def rotate_if_necessary(self):
        self.image_data = ImageOps.exif_transpose(self.image_data)

        # if self.orientation is not None:
        #    if self.orientation == 3:
        #        self.image_data = self.image_data.rotate(180, expand=True)
        #    if self.orientation == 6:
        #        self.image_data = self.image_data.rotate(270, expand=True)
        #    if self.orientation == 8:
        #        self.image_data = self.image_data.rotate(90, expand=True)

    def get_metadata_with_pil(self):
        if self.image_data.getexif() is not None:
            exif = dict(self.image_data.getexif().items())
            if 0x0110 in exif:
                self.model = exif[0x0110].strip("\u0000").strip(" ")
            if 0x9003 in exif:
                try:
                    self.date = datetime.strptime(exif[0x9003], '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    self.date = None
                    # comment récupérer ici l'équivalent de FileModifyDate (voir ExifTool) ?
            if 0x0112 in exif:
                self.orientation = exif[0x0112]

    def display_face(self, face):
        img_copy = self.image_data.copy()
        draw = ImageDraw.Draw(img_copy)
        top, right, bottom, left = face
        draw.rectangle(((left, top), (right, bottom)), outline=(0, 0, 255))
        del draw
        img_copy.show()
        return img_copy.crop((left + 1, top + 1, right, bottom))
