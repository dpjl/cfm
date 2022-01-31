class RecognizeFaces:

    @staticmethod
    def execute(metadata_face):
        metadata_face.recognize_faces()
        return metadata_face
