from camerafile.core.Logging import Logger
from camerafile.metadata.MetadataFaces import MetadataFaces


class ComputeFaceBoxes:

    @staticmethod
    def execute(metadata_face: MetadataFaces):
        try:
            metadata_face.compute_face_boxes()
            return metadata_face
        except BaseException as e:
            print("Exc " + str(e) + "[" + metadata_face.file_access.path + "]")
            return metadata_face
