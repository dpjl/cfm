import base64
import io

from PIL import Image
from PIL.Image import NEAREST
from moviepy.video.io.VideoFileClip import VideoFileClip

from camerafile.Constants import IMAGE_TYPE
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import Metadata
from camerafile.Resource import Resource


class MetadataThumbnail(Metadata):
    init = False

    def __init__(self, media_id, media_path, extension):
        super().__init__(None)
        self.media_id = media_id
        self.media_path = media_path
        self.extension = extension
        self.error = False
        self.thumbnail = None

    @staticmethod
    def compute_thumbnail_task(metadata_thumbnail):
        try:
            if not MetadataThumbnail.init:
                Resource.init()
                MetadataThumbnail.init = True
            metadata_thumbnail.compute_thumbnail()
            return metadata_thumbnail
        except:
            metadata_thumbnail.error = True
            return metadata_thumbnail

    def compute_thumbnail(self):
        if self.thumbnail is None:
            _, _, _, _, _, thumbnail = ExifTool.get_metadata(self.media_path)
            if thumbnail is not None:
                self.thumbnail = base64.b64decode(thumbnail[7:])
                thb = Image.open(io.BytesIO(self.thumbnail))
                thb.thumbnail((100, 100))
                bytes_output = io.BytesIO()
                thb.save(bytes_output, format='JPEG')
                self.thumbnail = bytes_output.getvalue()
            elif self.extension in IMAGE_TYPE:
                image = Image.open(self.media_path)
                image.thumbnail((100, 100))
                bytes_output = io.BytesIO()
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                image.save(bytes_output, format='JPEG')
                self.thumbnail = bytes_output.getvalue()
            else:
                clip = None
                try:
                    clip = VideoFileClip(self.media_path)
                    frame_at_second = 0
                    frame = clip.get_frame(frame_at_second)
                    new_image = Image.fromarray(frame)
                    new_image.thumbnail((100, 100))
                    bytes_output = io.BytesIO()
                    new_image.save(bytes_output, format='JPEG')
                    self.thumbnail = bytes_output.getvalue()
                finally:
                    if clip is not None:
                        clip.close()
