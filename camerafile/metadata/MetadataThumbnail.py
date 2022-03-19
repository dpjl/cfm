import base64
import io

from PIL import Image

from camerafile.core.Constants import IMAGE_TYPE
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.Metadata import Metadata


class MetadataThumbnail(Metadata):
    init = False
    video_clip_lib = None

    def __init__(self, file_access: FileAccess):
        super().__init__(None)
        self.file_access = file_access
        self.error = False
        self.thumbnail = None

    def compute_thumbnail(self):
        if self.thumbnail is None:

            if MetadataThumbnail.video_clip_lib is None:
                from moviepy.video.io.VideoFileClip import VideoFileClip
                MetadataThumbnail.video_clip_class = VideoFileClip

            _, _, _, _, _, _, thumbnail = self.file_access.read_md()

            if thumbnail is not None:
                self.thumbnail = base64.b64decode(thumbnail[7:])
                with Image.open(io.BytesIO(self.thumbnail)) as thb:
                    thb.thumbnail((100, 100))
                    bytes_output = io.BytesIO()
                    thb.save(bytes_output, format='JPEG')
                    self.thumbnail = bytes_output.getvalue()

            elif self.file_access.get_extension() in IMAGE_TYPE:
                with self.file_access.open() as file:
                    with Image.open(file) as image:
                        image.thumbnail((100, 100))
                        bytes_output = io.BytesIO()
                        if image.mode in ("RGBA", "P"):
                            image = image.convert("RGB")
                        image.save(bytes_output, format='JPEG')
                        self.thumbnail = bytes_output.getvalue()

            else:
                with MetadataThumbnail.video_clip_class(self.file_access.get_path()) as clip:
                    frame_at_second = 0
                    frame = clip.get_frame(frame_at_second)
                    new_image = Image.fromarray(frame)
                    new_image.thumbnail((100, 100))
                    bytes_output = io.BytesIO()
                    new_image.save(bytes_output, format='JPEG')
                    self.thumbnail = bytes_output.getvalue()
