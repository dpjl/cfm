from camerafile.core import Configuration
from camerafile.core.Resource import Resource
from camerafile.metadata.MetadataThumbnail import MetadataThumbnail


class ComputeThumbnail:

    @staticmethod
    def execute(metadata_thumbnail: MetadataThumbnail):
        try:
            if not Configuration.initialized:
                Resource.init()
                Configuration.initialized = True
            metadata_thumbnail.compute_thumbnail()
            return metadata_thumbnail
        except:
            metadata_thumbnail.error = True
            return metadata_thumbnail
