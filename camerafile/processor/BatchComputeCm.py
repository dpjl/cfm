from typing import List

from camerafile.core.Configuration import Configuration
from camerafile.core.MediaDuplicateManager import MediaDuplicateManager
from camerafile.processor.BatchTool import TaskWithProgression, BatchElement
from camerafile.core.Constants import INTERNAL
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.task.ComputeCameraModel import ComputeCameraModel

LOGGER = Logger(__name__)


# Not compatible with multi sub-processes
class BatchComputeCm(TaskWithProgression):
    BATCH_TITLE = "Try to recover missing camera models"

    def __init__(self, media_set: MediaSet):
        self.media_set = media_set
        self.something_to_do = True
        TaskWithProgression.__init__(self, batch_title=self.BATCH_TITLE, nb_sub_process=0)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

        media: MediaFile
        for media in self.media_set.get_file_list(cm="known"):
            ComputeCameraModel.set_value(media, media.metadata[INTERNAL].get_md_value(MetadataNames.MODEL))

    def task_getter(self):
        return ComputeCameraModel.execute

    def arguments(self) -> List[BatchElement]:
        media_list: List[MediaFile] = self.media_set.get_file_list(cm="unknown")
        args_list = []
        for media_file in media_list:
            args_list.append(BatchElement(media_file, media_file.get_path()))
        if len(args_list) != 0:
            if not Configuration.get().watch:
                self.status(self.media_set, prefix="Before execution: ")
        else:
            self.something_to_do = False
        return args_list

    def post_task(self, current_media, progress_bar, replace=False):
        progress_bar.increment()

    def finalize(self):
        if not self.something_to_do:
            return

        MediaDuplicateManager.propagate_camera_model(self.media_set)
        if not Configuration.get().watch:
            self.status(self.media_set, prefix="After execution: ")
            unknown_cm = self.media_set.get_file_list(cm="unknown")
            recovered_cm = self.media_set.get_file_list(cm="recovered")
            if len(unknown_cm) != 0:
                LOGGER.info(OutputDirectory.get(self.media_set.root_path).save_list(unknown_cm, "unknown-cm.json"))
            if len(recovered_cm) != 0:
                LOGGER.info(OutputDirectory.get(self.media_set.root_path).save_list(recovered_cm, "recovered-cm.json"))

    @staticmethod
    def status(media_set, prefix=""):
        LOGGER.info(prefix + "{l1} files have a camera model, "
                             "{l2} have a recovered one, "
                             "{l3} do not have one".
                    format(l1=len(media_set.get_file_list(cm="known")),
                           l2=len(media_set.get_file_list(cm="recovered")),
                           l3=len(media_set.get_file_list(cm="unknown"))))
