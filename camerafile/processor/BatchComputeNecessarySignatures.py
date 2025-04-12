from camerafile.core.MediaDuplicateManager import MediaDuplicateManager
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

        # Normally it should not be required, except if for some bad reasons it was not done previously.
        # As it is not really costly, do it each time.
        self.propagate_and_synchronize()

        args_list = []
        file_list_1 = MediaDuplicateManager.get_possibly_duplicates(self.media_set)
        file_list_2 = []
        file_list_3 = []
        if self.media_set2 is not None:
            file_list_2 = MediaDuplicateManager.get_possibly_duplicates(self.media_set2)
            file_list_3 = self.media_set.get_possibly_already_exists(self.media_set2)

        # Use system_id to deduplicate media files and only process those needing signatures
        processed_system_ids = set()
        for media in file_list_1 + file_list_2 + file_list_3:
            if media.file_desc.system_id is not None and media.file_desc.system_id not in processed_system_ids and media.metadata[SIGNATURE].value is None:
                processed_system_ids.add(media.file_desc.system_id)
                args_list.append(BatchElement(
                    (media.parent_set.root_path, media.file_desc, media.metadata[SIGNATURE]), 
                    media.get_path()
                ))
        return args_list

    def post_task(self, result, progress_bar, replace=False):
        media_id, result_signature_metadata = result
        for media_set in [self.media_set, self.media_set2]:
            if media_set is not None:
                original_media = media_set.get_media(media_id)
                if original_media is not None:
                    original_media.metadata[SIGNATURE] = result_signature_metadata
                    # reindex the file, now a signature has been computed
                    original_media.parent_set.indexer.add_media_file(original_media)
        progress_bar.increment()

    def finalize(self):
        self.propagate_and_synchronize()

    def propagate_and_synchronize(self):
        # First propagate signatures within each media set
        MediaDuplicateManager.propagate_signature(self.media_set)
        if self.media_set2 is not None:
            self.media_set.synchronize_signatures(self.media_set2)
            MediaDuplicateManager.propagate_signature(self.media_set2)
            # TODO: not needed ?
            self.media_set.synchronize_signatures(self.media_set2)

        # in case new duplicates have been found because of new computed signatures
        MediaDuplicateManager.propagate_camera_model(self.media_set)
        if self.media_set2 is not None:
            MediaDuplicateManager.propagate_camera_model(self.media_set2)