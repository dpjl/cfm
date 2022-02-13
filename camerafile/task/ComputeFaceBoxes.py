from camerafile.core import Configuration
from camerafile.metadata.MetadataFaces import MetadataFaces


class ComputeFaceBoxes:

    @staticmethod
    def execute(metadata_face: MetadataFaces):
        try:
            if not Configuration.initialized:
                from camerafile.cfm import configure
                from camerafile.cfm import create_main_args_parser
                parser = create_main_args_parser()
                args = parser.parse_args()
                configure(args)
                Configuration.initialized = True
            metadata_face.compute_face_boxes()
            return metadata_face
        except BaseException as e:
            print("Exc " + str(e) + "[" + metadata_face.file_access.path + "]")
            return metadata_face
