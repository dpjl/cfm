from camerafile.core import Configuration
from camerafile.metadata.MetadataSignature import MetadataSignature
from camerafile.task.Task import Task


class ComputeSignature:

    @staticmethod
    def execute(signature_metadata: MetadataSignature):
        try:
            signature_metadata.compute_value()
            return signature_metadata
        except BaseException as e:
            if Configuration.EXIT_ON_ERROR:
                raise e
            print(print(str(e) + "/" + str(signature_metadata.file_access.get_path())))
            return signature_metadata
