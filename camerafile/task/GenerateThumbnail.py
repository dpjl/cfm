from PIL import Image
#from cv2.cv2 import VideoCapture
import cv2
import os

from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration

class GenerateThumbnail:

    IMAGE_EXTENSIONS = {f"{ext.lower()}" for ext in Image.registered_extensions()}

    @staticmethod
    def execute(batch_element: BatchElement):
        root_dir, file_description, thb_path = batch_element.args
        try:
            GenerateThumbnail.generate_thumbnail(root_dir, file_description, thb_path)
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise
            else:
                batch_element.error = "GenerateThumbnail: [{info}] - ".format(info=batch_element.info) + str(e)
        batch_element.args = None
        batch_element.result = (file_description.get_id(), thb_path)
        return batch_element



    @staticmethod
    def generate_thumbnail(root_dir: str, file_description: FileDescription, thb_path, orientation=None):
        file_access = FileAccessFactory.get(root_dir, file_description)
        if file_description.extension in GenerateThumbnail.IMAGE_EXTENSIONS:
            with file_access.open() as file:
                with Image.open(file) as image:
                    image.thumbnail((512, 512))
                    if image.mode in ("RGBA", "P"):
                        image = image.convert("RGB")
                    if orientation == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation == 8:
                        image = image.rotate(90, expand=True)
                    image.save(thb_path, format='JPEG')
        else:
            videoCapture = cv2.VideoCapture(file_access.get_path())
            result, image = videoCapture.read()
            if result:
                # Appliquer l'orientation si précisée
                if orientation == 3:
                    image = cv2.rotate(image, cv2.ROTATE_180)
                elif orientation == 6:
                    image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                elif orientation == 8:
                    image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                GenerateThumbnail.save_as_jpg(thb_path, image)

            # TODO
            # cv2.resize(image, max_size, interpolation=cv2.INTER_AREA)

            # frame = clip.get_frame(frame_at_second)
            # new_image = Image.fromarray(frame)
            # new_image.thumbnail((100, 100))
            # bytes_output = io.BytesIO()
            # new_image.save(bytes_output, format='JPEG')
            # self.thumbnail = bytes_output.getvalue()

    @staticmethod
    def save_as_jpg(thb_path, image, qualite=90):
        tmp_filename = os.path.splitext(thb_path)[0] + ".jpg"
        cv2.imwrite(tmp_filename, image, [cv2.IMWRITE_JPEG_QUALITY, qualite])
        os.rename(tmp_filename, thb_path)
