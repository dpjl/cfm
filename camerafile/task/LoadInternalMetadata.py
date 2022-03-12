from camerafile.core.Configuration import Configuration
from camerafile.metadata.MetadataInternal import MetadataInternal


class LoadInternalMetadata:

    @staticmethod
    def execute(internal_metadata: MetadataInternal):
        try:
            internal_metadata.load_internal_metadata()
            return internal_metadata
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise e
            if internal_metadata is not None:
                print("LoadInternalMetadata: " + str(e) + "/" + str(internal_metadata.file_access.relative_path))
            else:
                print("LoadInternalMetadata: " + str(e))
            return internal_metadata
