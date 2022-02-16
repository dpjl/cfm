from camerafile.metadata.MetadataThumbnail import MetadataThumbnail


class ComputeThumbnail:

    @staticmethod
    def execute(metadata_thumbnail: MetadataThumbnail):
        try:
            metadata_thumbnail.compute_thumbnail()
            return metadata_thumbnail
        except:
            metadata_thumbnail.error = True
            return metadata_thumbnail
