import numpy

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.Metadata import Metadata


class MetadataFaces(Metadata):
    face_rec = None

    def __init__(self, file_access: FileAccess, knn_clf):
        super().__init__(None)
        self.file_access = file_access
        self.knn_clf = knn_clf

    def set_value(self, value):
        self.value = value

    def compute_face_boxes(self):
        if self.value is None:
            self.value, self.binary_value = self.file_access.compute_face_boxes()

    @staticmethod
    def static_compute_face_boxes(image):

        # We do this to not have to import face_recognition if it's not necessary at the load of the program
        # (but still only one time)
        if MetadataFaces.face_rec is None:
            import face_recognition
            MetadataFaces.face_rec = face_recognition

        data = image.image_data
        original_data = data
        if not Configuration.get().face_detection_keep_image_size:
            height_resize = 480
            frame_resize_scale = float(image.image_data.height) / height_resize
            (width, height) = (data.width // frame_resize_scale, data.height // frame_resize_scale)
            data = image.image_data.resize((int(width), int(height)))

        img = numpy.array(data)

        locations = MetadataFaces.face_rec.face_locations(img)
        if not Configuration.get().face_detection_keep_image_size:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]
            img = numpy.array(original_data)

        encoding = MetadataFaces.face_rec.face_encodings(img, known_face_locations=locations)

        return {"locations": locations, "names": []}, encoding

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
