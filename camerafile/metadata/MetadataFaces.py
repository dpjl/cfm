import os

import time
from PIL.Image import Image

from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import Logger
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.Metadata import Metadata
from camerafile.tools.CFMImage import CFMImage

LOGGER = Logger(__name__)


class MetadataFaces(Metadata):
    face_rec_lib = None
    numpy_lib = None

    def __init__(self, file_access: FileAccess, knn_clf):
        super().__init__(None)
        self.file_access = file_access
        self.knn_clf = knn_clf

    def set_value(self, value):
        self.value = value

    def compute_face_boxes(self):
        if self.value is None:
            self.value, self.binary_value, det_dur, enc_dur = self.file_access.compute_face_boxes()
            return enc_dur, det_dur

    @staticmethod
    def static_compute_face_boxes(image: CFMImage):

        # We do this to not have to import face_recognition if it's not necessary at the load of the program
        # (but still only one time)
        if MetadataFaces.face_rec_lib is None and MetadataFaces.numpy_lib is None:
            LOGGER.debug("Load face_recognition and numpy modules")
            import face_recognition
            import numpy
            MetadataFaces.face_rec_lib = face_recognition
            MetadataFaces.numpy_lib = numpy

        start_time = time.time()
        data = image.image_data
        # data = ImageOps.grayscale(data1)
        original_data = data
        if not Configuration.get().face_detection_keep_image_size:
            height_resize = 1500
            frame_resize_scale = float(image.image_data.height) / height_resize
            (width, height) = (data.width // frame_resize_scale, data.height // frame_resize_scale)
            data: Image = image.image_data.resize((int(width), int(height)))
            # data = ImageOps.grayscale(data)
        img = MetadataFaces.numpy_lib.array(data)
        locations = MetadataFaces.face_rec_lib.face_locations(img)
        end_face_locations_time = time.time()

        if not Configuration.get().face_detection_keep_image_size:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]

        img = MetadataFaces.numpy_lib.array(original_data)

        if Configuration.get().debug:
            face_debug_path = Configuration.get().first_output_directory.path / "face-debug"
            os.makedirs(face_debug_path, exist_ok=True)
            with open(face_debug_path / image.filename, "wb") as file:
                image.get_image_with_faces(locations).save(file)

        # image.get_image_with_faces(locations).show()
        encoding = MetadataFaces.face_rec_lib.face_encodings(img, known_face_locations=locations)
        end_encoding_time = time.time()

        det_duration = end_face_locations_time - start_time
        enc_duration = end_encoding_time - end_face_locations_time
        return {"locations": locations, "names": []}, encoding, det_duration, enc_duration

    def recognize_faces(self):
        if self.knn_clf is None:
            return
        if self.binary_value is None:
            return
        if self.value is None:
            self.value = {"locations": [], "names": []}
        else:
            self.value["names"] = []
        distance_threshold = 0.6
        for face_encoding in self.binary_value:
            closest_distances = self.knn_clf.kneighbors([face_encoding], n_neighbors=1)
            if closest_distances[0][0][0] <= distance_threshold:
                [face_name] = self.knn_clf.predict([face_encoding])
            else:
                face_name = "unrecognized"
            self.value["names"].append(face_name)
