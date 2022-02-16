from camerafile.metadata.MetadataFaces import MetadataFaces


class ComputeFaceBoxes:

    @staticmethod
    def execute(metadata_face: MetadataFaces):
        try:
            metadata_face.compute_face_boxes()
            return metadata_face
        except BaseException as e:
            print("-----------------")
            print("Error for " + metadata_face.file_access.path + ":")
            print(str(e))
            print("-----------------")
            return metadata_face
