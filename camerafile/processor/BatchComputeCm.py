from typing import List

from camerafile.core.BatchTool import TaskWithProgression, BatchArgs
from camerafile.core.Constants import CFM_CAMERA_MODEL
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile

LOGGER = Logger(__name__)


# Not compatible with multi sub-processes
class BatchComputeCm(TaskWithProgression):
    BATCH_TITLE = "Try to recover missing camera models"

    def __init__(self, media_set):
        self.media_set = media_set
        TaskWithProgression.__init__(self, batch_title=self.BATCH_TITLE, nb_sub_process=0)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return self.task

    def task(self, current_media):
        current_media.metadata[CFM_CAMERA_MODEL].compute_value()
        return current_media

    def arguments(self) -> List[BatchArgs]:
        self.status(self.media_set)
        media_list: List[MediaFile] = self.media_set.get_file_list(cm="unknown")
        args_list = []
        for media_file in media_list:
            args_list.append(BatchArgs(media_file, media_file.relative_path))
        return args_list

    def post_task(self, current_media, progress_bar, replace=False):
        progress_bar.increment()

    def finalize(self):
        self.media_set.propagate_cm_to_duplicates()
        self.status(self.media_set)

        unknown_cm = self.media_set.get_file_list(cm="unknown")
        recovered_cm = self.media_set.get_file_list(cm="recovered")
        LOGGER.info(self.media_set.output_directory.save_list(unknown_cm, "unknown-camera-model.json"))
        LOGGER.info(self.media_set.output_directory.save_list(recovered_cm, "recovered-camera-model.json"))

    @staticmethod
    def status(media_set):
        LOGGER.info("{l1} files have a camera model, "
                    "{l2} have a recovered one, "
                    "{l3} do not have one".
                    format(l1=len(media_set.get_file_list(cm="known")),
                           l2=len(media_set.get_file_list(cm="recovered")),
                           l3=len(media_set.get_file_list(cm="unknown"))))
