from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Constants import IMAGE_TYPE, FACES
from camerafile.core.Logging import Logger
from camerafile.task.RecognizeFaces import RecognizeFaces

LOGGER = Logger(__name__)


class BatchRecoFaces(TaskWithProgression):

    def __init__(self, media_set):
        self.media_set = media_set
        TaskWithProgression.__init__(batch_title="Recognize faces")

    def task(self):
        return RecognizeFaces.execute

    def arguments(self):
        face_metadata_list = []
        for media_file in self.media_set:
            if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is not None:
                face_metadata_list.append(media_file.metadata[FACES])
        return face_metadata_list

    def post_task(self, result_face_metadata, progress_bar):
        self.media_set.get_media(result_face_metadata.media_id).metadata[FACES] = result_face_metadata
        progress_bar.increment()
