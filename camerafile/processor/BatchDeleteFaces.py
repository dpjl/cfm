from camerafile.core.BatchTool import BatchElement
from camerafile.core.Constants import FACES
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.processor.CFMBatch import CFMBatch

LOGGER = Logger(__name__)


# Not compatible with multi sub-processes
class BatchDeleteFaces(CFMBatch):
    BATCH_TITLE = "Delete computed faces"

    def __init__(self, media_set: MediaSet):
        self.media_set = media_set
        CFMBatch.__init__(self, batch_title=self.BATCH_TITLE, nb_sub_process=0,
                          stderr_file=media_set.output_directory.batch_stderr,
                          stdout_file=media_set.output_directory.batch_stdout)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return self.task

    def task(self, media_file: MediaFile):
        media_file.metadata[FACES].value = None
        media_file.metadata[FACES].binary_value = None
        return media_file

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            args_list.append(BatchElement(media_file, media_file.relative_path))
        return args_list

    def post_task(self, media_file, progress_bar, replace=False):
        progress_bar.increment()

    def finalize(self):
        pass
