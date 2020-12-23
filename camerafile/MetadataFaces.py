from camerafile.Constants import IMAGE_TYPE
from camerafile.ImageTool import ImageTool
from camerafile.Metadata import Metadata, ORIENTATION
import numpy
import face_recognition


class MetadataFaces(Metadata):

    def __init__(self, media_file):
        super().__init__(media_file)

    @staticmethod
    def compute_face_boxes(arguments):
        identifier, path, orientation = arguments
        image = ImageTool.read_image(path, orientation)
        img = numpy.array(image)
        result = {'locations': face_recognition.face_locations(img)}
        result['encodings'] = face_recognition.face_encodings(img, known_face_locations=result['locations'])
        return identifier, result
