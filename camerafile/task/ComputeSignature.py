from camerafile.core.Configuration import Configuration
from camerafile.metadata.MetadataSignature import MetadataSignature


class ComputeSignature:

    @staticmethod
    def execute(signature_metadata: MetadataSignature):
        try:
            signature_metadata.compute_value()
            return signature_metadata
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise e
            print(print(str(e) + "/" + str(signature_metadata.file_access.get_path())))
            return signature_metadata
