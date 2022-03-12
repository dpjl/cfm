from camerafile.core.BatchTool import BatchArgs
from camerafile.core.Constants import INTERNAL, THUMBNAIL, CFM_CAMERA_MODEL
from camerafile.core.Logging import Logger
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.metadata.MetadataInternal import MetadataInternal
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.LoadInternalMetadata import LoadInternalMetadata

LOGGER = Logger(__name__)


class BatchReadInternalMd(CFMBatch):

    def __init__(self, media_set):
        self.media_set = media_set
        CFMBatch.__init__(self, "Read media exif metadata")

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return LoadInternalMetadata.execute

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            if media_file.metadata[INTERNAL].value is None:
                args_list.append(BatchArgs(media_file.metadata[INTERNAL], media_file.relative_path))
        return args_list

    def post_task(self, result_internal_metadata: MetadataInternal, progress_bar, replace=False):
        original_media = self.media_set.get_media(result_internal_metadata.file_access.id)
        if replace:
            original_media.metadata[INTERNAL] = result_internal_metadata
        original_media.metadata[THUMBNAIL].thumbnail = original_media.metadata[INTERNAL].thumbnail
        original_media.metadata[INTERNAL].thumbnail = None
        original_media.metadata[CFM_CAMERA_MODEL].set_value(
            original_media.metadata[INTERNAL].get_md_value(MetadataNames.MODEL))
        original_media.parent_set.add_to_date_size_name_map(original_media)
        progress_bar.increment()
