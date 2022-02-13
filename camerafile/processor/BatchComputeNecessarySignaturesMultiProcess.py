from camerafile.core.BatchTool import TaskWithProgression, BatchArgs
from camerafile.core.Constants import SIGNATURE
from camerafile.core.Logging import Logger
from camerafile.task.ComputeSignature import ComputeSignature

LOGGER = Logger(__name__)


class BatchComputeNecessarySignaturesMultiProcess(TaskWithProgression):

    def __init__(self, media_set, media_set2=None):
        self.media_set = media_set
        self.media_set2 = media_set2
        if media_set2 is None:
            TaskWithProgression.__init__(self,
                                         batch_title="Compute necessary signatures in order to detect duplicates")
        else:
            TaskWithProgression.__init__(self,
                                         batch_title="Compute necessary signatures in order to compare 2 mediasets")

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

        for media_file in file_list_1 + file_list_2 + file_list_3:
            if media_file.metadata[SIGNATURE].value is None:
                args_list.append(BatchArgs(media_file.metadata[SIGNATURE], media_file.relative_path))
        return args_list

    def post_task(self, result_signature_metadata, progress_bar, replace=False):
        original_media = self.media_set.get_media(result_signature_metadata.file_access.id)
        if original_media is None:
            original_media = self.media_set2.get_media(result_signature_metadata.file_access.id)
        original_media.metadata[SIGNATURE] = result_signature_metadata
        original_media.parent_set.add_to_date_size_sig_map(original_media)
        progress_bar.increment()

    def finalize(self):
        self.media_set.propagate_sig_to_duplicates()
        if self.media_set2 is not None:
            self.media_set2.propagate_sig_to_duplicates()

        # in case new duplicates have been found because of new computed signatures
        self.media_set.propagate_cm_to_duplicates()
        if self.media_set2 is not None:
            self.media_set2.propagate_cm_to_duplicates()
