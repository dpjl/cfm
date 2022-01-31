class ComputeFaceBoxes:

    @staticmethod
    def execute(metadata_face):
        try:
            metadata_face.compute_face_boxes()
            return metadata_face
        except:
            print("Error " + metadata_face.media_path)
            return metadata_face
