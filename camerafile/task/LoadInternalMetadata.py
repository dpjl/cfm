class LoadInternalMetadata:

    @staticmethod
    def execute(internal_metadata):
        try:
            internal_metadata.load_internal_metadata()
            return internal_metadata
        except:
            print("Error during load_internal_metadata_task execution for " + str(internal_metadata.media_path))
            return internal_metadata
