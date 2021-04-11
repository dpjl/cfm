
import numpy
from camerafile.Image import Image
from camerafile.Metadata import Metadata


class MetadataFaces(Metadata):

    face_rec = None

    def __init__(self, media_id, media_path, knn_clf):
        super().__init__(None)
        self.media_id = media_id
        self.media_path = media_path
        self.knn_clf = knn_clf

    def set_value(self, value):
        if type(value) is list:
            # TO REMOVE: only for compatibility with old version
            self.value = {"locations": value, "names": []}
        else:
            self.value = value

    @staticmethod
    def compute_face_boxes_task(metadata_face):
        metadata_face.compute_face_boxes()
        return metadata_face

    def compute_face_boxes(self):

        if self.face_rec is None:
            import face_recognition
            self.face_rec = face_recognition

        if self.value is None:
            image = Image(self.media_path)
            img = numpy.array(image.image_data)
            self.value = {"locations": self.face_rec.face_locations(img), "names": []}
            self.binary_value = self.face_rec.face_encodings(img, known_face_locations=self.value["locations"])

    @staticmethod
    def recognize_faces_task(metadata_face):
        metadata_face.recognize_faces()
        return metadata_face

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
