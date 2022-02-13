from typing import List

from camerafile.core.BatchTool import TaskWithProgression, BatchArgs
from camerafile.core.Constants import THUMBNAIL
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.task.ComputeThumbnail import ComputeThumbnail

LOGGER = Logger(__name__)


class BatchComputeMissingThumbnails(TaskWithProgression):

    def __init__(self, media_set: MediaSet):
        self.media_set = media_set
        TaskWithProgression.__init__(self, "Generate missing thumbnails")

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return ComputeThumbnail.execute

    def arguments(self) -> List[BatchArgs]:
        args_list = []
        for media_file in self.media_set:
            if media_file.metadata[THUMBNAIL].thumbnail is None:
                args_list.append(BatchArgs(media_file.metadata[THUMBNAIL], media_file.relative_path))
        return args_list

    def post_task(self, result_thumbnail_metadata, progress_bar, replace=False):
        if replace:
            original_media = self.media_set.get_media(result_thumbnail_metadata.media_id)
            original_media.metadata[THUMBNAIL] = result_thumbnail_metadata
        progress_bar.increment()

    def finalize(self):
        thb_errors = self.media_set.get_files_with_thumbnail_errors()
        LOGGER.info(self.media_set.output_directory.save_list(thb_errors, "thumbnails_errors.json"))
