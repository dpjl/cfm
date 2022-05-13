import datetime

import humanize

from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.BatchTool import BatchElement
from camerafile.core.Constants import IMAGE_TYPE, FACES
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.ComputeFaceBoxes import ComputeFaceBoxes

LOGGER = Logger(__name__)


class BatchDetectFaces(CFMBatch):
    BATCH_TITLE = "Detect faces"

    def __init__(self, media_set: MediaSet):
        self.media_set = media_set
        self.processed_media_files = []
        CFMBatch.__init__(self, batch_title=self.BATCH_TITLE,
                          stderr_file=media_set.output_directory.batch_stderr,
                          stdout_file=media_set.output_directory.batch_stdout)
        self.number_of_faces = 0
        self.det_dur = 0
        self.enc_dur = 0

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return ComputeFaceBoxes.execute

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].value is None:
                args_list.append(BatchElement(media_file.metadata[FACES], media_file.relative_path))
            elif media_file.extension in IMAGE_TYPE:
                self.number_of_faces += len(media_file.metadata[FACES].value["locations"])
        return args_list

    def post_task(self, result, progress_bar, replace=True):
        result_face_metadata, det_dur, enc_dur = result
        if det_dur is not None:
            self.det_dur += det_dur
        if enc_dur is not None:
            self.enc_dur += enc_dur
        media_file: MediaFile = self.media_set.get_media(result_face_metadata.file_access.id)
        media_file.metadata[FACES] = result_face_metadata
        self.processed_media_files.append(media_file)
        if result_face_metadata.value is not None and "locations" in result_face_metadata.value:
            self.number_of_faces += len(result_face_metadata.value["locations"])
        progress_bar.increment()
        if len(self.processed_media_files) > 100:
            self.media_set.intermediate_save_database(self.processed_media_files)
            self.processed_media_files = []

    def finalize(self):
        print("")
        tab = ConsoleTable()
        tab.print_header("Number of faces")
        tab.print_line(str(self.number_of_faces))
        print("")

        print("")
        tab = ConsoleTable()
        tab.print_header("Faces detection duration", "Faces encoding duration")
        tab.print_line(str(self.det_dur),
                       str(self.enc_dur))
        print("")
