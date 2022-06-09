from camerafile.metadata.Metadata import Metadata


class RecognizeFaces:

    @staticmethod
    def execute(args):
        knn_clf, metadata_face = args
        RecognizeFaces.recognize_faces(knn_clf, metadata_face)
        return metadata_face

    @staticmethod
    def recognize_faces(knn_clf, metadata_face: Metadata):
        if knn_clf is None:
            return
        if metadata_face.binary_value is None:
            return
        if metadata_face.value is None:
            metadata_face.value = {"locations": [], "names": []}
        else:
            metadata_face.value["names"] = []
        distance_threshold = 0.6
        for face_encoding in metadata_face.binary_value:
            closest_distances = knn_clf.kneighbors([face_encoding], n_neighbors=1)
            if closest_distances[0][0][0] <= distance_threshold:
                [face_name] = knn_clf.predict([face_encoding])
            else:
                face_name = "unrecognized"
            metadata_face.value["names"].append(face_name)
