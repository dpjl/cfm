from typing import List

from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Constants import THUMBNAIL
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.ComputeThumbnail import ComputeThumbnail

LOGGER = Logger(__name__)


class BatchComputeMissingThumbnails(CFMBatch):

    def __init__(self, media_set: MediaSet):
        self.media_set = media_set
        self.thb_errors = []
        CFMBatch.__init__(self, "Generate missing thumbnails",
                          stderr_file=OutputDirectory.get(self.media_set.root_path).batch_stderr,
                          stdout_file=OutputDirectory.get(self.media_set.root_path).batch_stdout)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return ComputeThumbnail.execute

    def arguments(self) -> List[BatchElement]:
        args_list = []
        media_file: MediaFile
        for media_file in self.media_set:
            if media_file.metadata[THUMBNAIL].binary_value is None:
                args_list.append(BatchElement(media_file.metadata[THUMBNAIL], media_file.get_path()))
        return args_list

    def post_task(self, result, progress_bar, replace=False):
        media_id, success, result_thumbnail_metadata = result
        original_media: MediaFile = self.media_set.get_media(media_id)
        if not success:
            self.thb_errors.append(original_media.file_desc.relative_path)
        if replace:
            original_media.metadata[THUMBNAIL] = result_thumbnail_metadata
        progress_bar.increment()

    def finalize(self):
        LOGGER.info(OutputDirectory.get(self.media_set.root_path).save_list(self.thb_errors, "thumbnails-errors.json"))
