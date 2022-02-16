from camerafile.core.BatchTool import BatchArgs
from camerafile.core.Constants import IMAGE_TYPE, FACES
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.metadata.MetadataFaces import MetadataFaces
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.ComputeFaceBoxes import ComputeFaceBoxes

LOGGER = Logger(__name__)


class BatchDetectFaces(CFMBatch):
    BATCH_TITLE = "Detect faces"

    def __init__(self, media_set: MediaSet):
        self.media_set = media_set
        self.processed_media_files = []
        CFMBatch.__init__(self, batch_title=self.BATCH_TITLE)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return ComputeFaceBoxes.execute

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is None:
                args_list.append(BatchArgs(media_file.metadata[FACES], media_file.relative_path))
        return args_list

    def post_task(self, result_face_metadata: MetadataFaces, progress_bar, replace=True):
        media_file: MediaFile = self.media_set.get_media(result_face_metadata.file_access.id)
        media_file.metadata[FACES] = result_face_metadata
        self.processed_media_files.append(media_file)
        progress_bar.increment()
        if len(self.processed_media_files) > 100:
            self.media_set.intermediate_save_database(self.processed_media_files)
            self.processed_media_files = []
