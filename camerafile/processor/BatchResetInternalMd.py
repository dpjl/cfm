from camerafile.core.BatchTool import BatchElement
from camerafile.core.Constants import INTERNAL
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.metadata.MetadataInternal import MetadataInternal
from camerafile.processor.CFMBatch import CFMBatch

LOGGER = Logger(__name__)


class BatchResetInternalMd(CFMBatch):

    def __init__(self, media_set_dir):
        self.media_set = MediaSet.load_media_set(media_set_dir)
        CFMBatch.__init__(self, "Reset internal metadata in cache",
                          stderr_file=self.media_set.output_directory.batch_stderr,
                          stdout_file=self.media_set.output_directory.batch_stdout,
                          nb_sub_process=0)
        self.execute()

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    @staticmethod
    def reset(internal_metadata: MetadataInternal):
        internal_metadata.value = None
        internal_metadata.binary_value = None
        return internal_metadata

    def task_getter(self):
        return self.reset

    def arguments(self):
        args_list = []
        for media_file in self.media_set:
            if media_file.metadata[INTERNAL].value or media_file.metadata[INTERNAL].binary_value:
                args_list.append(BatchElement(media_file.metadata[INTERNAL], media_file.relative_path))
        return args_list

    def post_task(self, result_internal_metadata: MetadataInternal, progress_bar, replace=False):
        original_media = self.media_set.get_media(result_internal_metadata.file_access.id)
        if replace:
            original_media.metadata[INTERNAL] = result_internal_metadata
        progress_bar.increment()

    def finalize(self):
        self.media_set.save_on_disk()
