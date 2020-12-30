import face_recognition
import numpy
from camerafile.Image import Image
from camerafile.Metadata import Metadata


class MetadataFaces(Metadata):

    def __init__(self, media_file):
        super().__init__(media_file)

    @staticmethod
    def compute_face_boxes(arguments):
        identifier, path, orientation = arguments
        try:
            image = Image(path)
            img = numpy.array(image.image_data)
            result = {'locations': face_recognition.face_locations(img)}
            result['encodings'] = face_recognition.face_encodings(img, known_face_locations=result['locations'])
            return identifier, result
        except:
            print("-Error when processing: " + path)
            return identifier, {'locations': [], 'encodings': []}
