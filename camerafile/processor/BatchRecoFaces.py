from camerafile.core.BatchTool import TaskWithProgression, BatchArgs
from camerafile.core.Constants import IMAGE_TYPE, FACES
from camerafile.core.Logging import Logger
from camerafile.metadata.MetadataFaces import MetadataFaces
from camerafile.task.RecognizeFaces import RecognizeFaces

LOGGER = Logger(__name__)


class BatchRecoFaces(TaskWithProgression):

    def __init__(self, media_set):
        self.media_set = media_set
        TaskWithProgression.__init__(self, batch_title="Recognize faces")

    def task_getter(self):
        return RecognizeFaces.execute

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is not None:
                args_list.append(BatchArgs(media_file.metadata[FACES], media_file.relative_path))
        return args_list

    def post_task(self, result_face_metadata: MetadataFaces, progress_bar, replace=False):
        self.media_set.get_media(result_face_metadata.file_access.id).metadata[FACES] = result_face_metadata
        progress_bar.increment()
