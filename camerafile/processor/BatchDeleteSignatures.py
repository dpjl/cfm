from camerafile.core.BatchTool import TaskWithProgression, BatchArgs
from camerafile.core.Constants import SIGNATURE
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile

LOGGER = Logger(__name__)


# Not compatible with multi sub-processes
class BatchDeleteSignatures(TaskWithProgression):
    BATCH_TITLE = "Delete computed signatures"

    def __init__(self, media_set):
        self.media_set = media_set
        TaskWithProgression.__init__(self, batch_title=self.BATCH_TITLE, nb_sub_process=0)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return self.task

    def task(self, media_file: MediaFile):
        media_file.metadata[SIGNATURE].value = None
        return media_file

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            args_list.append(BatchArgs(media_file, media_file.relative_path))
        return args_list

    def post_task(self, media_file, progress_bar, replace=False):
        progress_bar.increment()

    def finalize(self):
        pass
