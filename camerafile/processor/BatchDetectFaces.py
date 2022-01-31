from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Constants import IMAGE_TYPE, FACES
from camerafile.core.Logging import Logger
from camerafile.task.ComputeFaceBoxes import ComputeFaceBoxes

LOGGER = Logger(__name__)


class BatchDetectFaces(TaskWithProgression):

    def __init__(self, media_set):
        self.media_set = media_set
        TaskWithProgression.__init__(self, batch_title="Detect faces")

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return ComputeFaceBoxes.execute

    def arguments(self):
        face_metadata_list = []
        for media_file in self.media_set:
            if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is None:
                face_metadata_list.append(media_file.metadata[FACES])
        return face_metadata_list

    def post_task(self, result_face_metadata, progress_bar, replace=True):
        self.media_set.get_media(result_face_metadata.media_id).metadata[FACES] = result_face_metadata
        progress_bar.increment()
