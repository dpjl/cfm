import base64
import io
from typing import Tuple

from PIL import Image
from cv2.cv2 import VideoCapture

from camerafile.core.Constants import IMAGE_TYPE
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.metadata.Metadata import Metadata


class ComputeThumbnail:

    @staticmethod
    def execute(args: Tuple[str, FileDescription, Metadata]):
        root_path, file_desc, metadata_thumbnail = args
        try:
            ComputeThumbnail.compute_thumbnail(root_path, file_desc, metadata_thumbnail)
            return file_desc.id, True, metadata_thumbnail
        except Exception:
            return file_desc.id, False, metadata_thumbnail

    @staticmethod
    def compute_thumbnail(root_path: str, file_desc: FileDescription, metadata_thumbnail: Metadata):
        file_access = FileAccessFactory.get(root_path, file_desc)
        if metadata_thumbnail.binary_value is None:

            _, _, _, _, _, _, thumbnail = file_access.read_md()

            if thumbnail is not None:
                metadata_thumbnail.thumbnail = base64.b64decode(thumbnail[7:])
                with Image.open(io.BytesIO(metadata_thumbnail.thumbnail)) as thb:
                    thb.thumbnail((100, 100))
                    bytes_output = io.BytesIO()
                    thb.save(bytes_output, format='JPEG')
                    metadata_thumbnail.thumbnail = bytes_output.getvalue()

            elif file_desc.extension in IMAGE_TYPE:
                with file_access.open() as file:
                    with Image.open(file) as image:
                        image.thumbnail((100, 100))
                        bytes_output = io.BytesIO()
                        if image.mode in ("RGBA", "P"):
                            image = image.convert("RGB")
                        image.save(bytes_output, format='JPEG')
                        metadata_thumbnail.thumbnail = bytes_output.getvalue()

            else:
                videoCapture = VideoCapture(file_access.get_path())
                success, image = videoCapture.read()

                # TODO
                # cv2.resize(image, max_size, interpolation=cv2.INTER_AREA)

                # frame = clip.get_frame(frame_at_second)
                # new_image = Image.fromarray(frame)
                # new_image.thumbnail((100, 100))
                # bytes_output = io.BytesIO()
                # new_image.save(bytes_output, format='JPEG')
                # self.thumbnail = bytes_output.getvalue()
