from camerafile.metadata.MetadataInternal import MetadataInternal


class LoadInternalMetadata:

    @staticmethod
    def execute(internal_metadata: MetadataInternal):
        try:
            internal_metadata.load_internal_metadata()
            return internal_metadata
        except BaseException as e:
            print("LoadInternalMetadata: " + str(e) + "/" + str(internal_metadata.file_access.relative_path))
            return internal_metadata
