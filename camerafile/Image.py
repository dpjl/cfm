from datetime import datetime
from pathlib import Path

from PIL import Image as PilImage, ImageDraw


class Image:

    def __init__(self, path):
        self.path = Path(path)
        self.image_data = None
        self.model = None
        self.date = None
        self.width = None
        self.height = None
        self.orientation = None
        self.read_image()

    def read_image(self):
        self.image_data = PilImage.open(self.path)
        self.width, self.height = self.image_data.size
        self.get_metadata_with_pil()

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

        if self.orientation is not None:
            if self.orientation == 3:
                self.image_data = self.image_data.rotate(180, expand=True)
            if self.orientation == 6:
                self.image_data = self.image_data.rotate(270, expand=True)
            if self.orientation == 8:
                self.image_data = self.image_data.rotate(90, expand=True)

    def display_face(self, face):
        img_copy = self.image_data.copy()
        draw = ImageDraw.Draw(img_copy)
        top, right, bottom, left = face
        draw.rectangle(((left, top), (right, bottom)), outline=(0, 0, 255))
        del draw
        img_copy.show()
        return img_copy.crop((left + 1, top + 1, right, bottom))
