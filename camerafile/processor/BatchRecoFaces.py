from camerafile.core.BatchTool import BatchElement
from camerafile.core.Constants import IMAGE_TYPE, FACES
from camerafile.core.Logging import Logger
from camerafile.metadata.MetadataFaces import MetadataFaces
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.RecognizeFaces import RecognizeFaces

LOGGER = Logger(__name__)


class BatchRecoFaces(CFMBatch):

    def __init__(self, media_set):
        self.media_set = media_set
        CFMBatch.__init__(self, batch_title="Recognize faces",
                          stderr_file=media_set.output_directory.batch_stderr,
                          stdout_file=media_set.output_directory.batch_stdout)

    def task_getter(self):
        return RecognizeFaces.execute

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is not None:
                args_list.append(BatchElement(media_file.metadata[FACES], media_file.relative_path))
        return args_list

    def post_task(self, result_face_metadata: MetadataFaces, progress_bar, replace=False):
        self.media_set.get_media(result_face_metadata.file_access.id).metadata[FACES] = result_face_metadata
        progress_bar.increment()
