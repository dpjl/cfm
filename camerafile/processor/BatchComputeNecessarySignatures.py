from camerafile.core.MediaFile import MediaFile
from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Constants import SIGNATURE
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.ComputeSignature import ComputeSignature

LOGGER = Logger(__name__)


class BatchComputeNecessarySignaturesMultiProcess(CFMBatch):

    def __init__(self, media_set: MediaSet, media_set2: MediaSet = None):
        self.media_set = media_set
        self.media_set2 = media_set2
        if media_set2 is None:
            CFMBatch.__init__(self, batch_title="Compute necessary signatures in order to detect duplicates",
                              stderr_file=OutputDirectory.get(self.media_set.root_path).batch_stderr,
                              stdout_file=OutputDirectory.get(self.media_set.root_path).batch_stdout)

        else:
            CFMBatch.__init__(self, batch_title="Compute necessary signatures in order to compare 2 mediasets",
                              stderr_file=OutputDirectory.get(self.media_set.root_path).batch_stderr,
                              stdout_file=OutputDirectory.get(self.media_set.root_path).batch_stdout)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return ComputeSignature.execute

    def arguments(self):
        args_list = []
        file_list_1 = self.media_set.get_possibly_duplicates()
        file_list_2 = []
        file_list_3 = []
        if self.media_set2 is not None:
            file_list_2 = self.media_set2.get_possibly_duplicates()
            file_list_3 = self.media_set.get_possibly_already_exists(self.media_set2)

        # Optimization: in file_list_2, inutile d'ajouter les dupliqués potentiels dont
        # le nom de fichier est déjà dans dans file_list_1 ?
        media: MediaFile
        for media in file_list_1 + file_list_2 + file_list_3:
            if media.metadata[SIGNATURE].value is None:
                args = (media.parent_set.root_path, media.file_desc, media.metadata[SIGNATURE])
                args_list.append(BatchElement(args, media.get_path()))
        return args_list

    def post_task(self, result, progress_bar, replace=False):
        media_id, result_signature_metadata = result
        for media_set in [self.media_set, self.media_set2]:
            original_media = media_set.get_media(media_id)
            if original_media is not None:
                original_media.metadata[SIGNATURE] = result_signature_metadata
                original_media.parent_set.add_to_date_sig_map(original_media)
        progress_bar.increment()

    def finalize(self):
        self.media_set.propagate_sig_to_duplicates()
        if self.media_set2 is not None:
            self.media_set2.propagate_sig_to_duplicates()

        # in case new duplicates have been found because of new computed signatures
        self.media_set.propagate_cm_to_duplicates()
        if self.media_set2 is not None:
            self.media_set2.propagate_cm_to_duplicates()
