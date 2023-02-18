import io

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Frame, Paragraph

from camerafile.core.Constants import THUMBNAIL
from camerafile.core.MediaFile import MediaFile


class PdfFile:
    def __init__(self, file_path):
        self.page_width, self.page_height = A4
        self.thb_width, self.thb_height = 40, 40
        self.y = self.page_height - self.thb_height
        self.x = 10
        self.no_thb = 0
        self.canvas = Canvas(file_path)

    def new_line(self):
        self.y -= self.thb_height
        self.x = 10
        if self.y < 0:
            self.canvas.showPage()
            # Ajouter un entete / un pied de page, avec date et le nombre dans la page sur le nombre total
            self.y = self.page_height - self.thb_height

    def next_position(self):
        self.x += self.thb_width
        if self.x > 540:
            self.new_line()

    def add_image(self, image_binary):
        self.canvas.drawImage(ImageReader(image_binary), self.x, self.y, width=self.thb_width, height=self.thb_height,
                              preserveAspectRatio=True)

    def add_text(self, text):
        items = [Paragraph(text, ParagraphStyle(name='Normal', fontSize=3, leading=0))]
        f = Frame(self.x, self.y - 6, 50, 10, leftPadding=1, bottomPadding=0, rightPadding=0, topPadding=0)
        f.addFromList(items, self.canvas)

    def add_media_image(self, media: MediaFile):

        if media.metadata[THUMBNAIL].thumbnail is not None and media.metadata[THUMBNAIL].thumbnail != b'':
            bytes_image = io.BytesIO(media.metadata[THUMBNAIL].thumbnail)
            self.add_image(bytes_image)

        else:
            self.canvas.drawBoundary(Color(4, 4, 4, 0), self.x, self.y, self.thb_width, self.thb_height)
            self.no_thb += 1

        self.canvas.linkURL("../" + str(media.get_path()),
                            (self.x, self.y + self.thb_height, self.x + self.thb_width, self.y))

        self.add_text(str(media.db_id) + " | " + media.get_extension()[1:] + " | " + media.get_str_date())
        self.next_position()

    def save(self):
        self.canvas.showPage()
        self.canvas.save()
