from typing import Tuple, Union

from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.DeleteFile import DeleteFile

LOGGER = Logger(__name__)


class BatchDelete(CFMBatch):
    BATCH_TITLE = "Delete files"
    RESULT_COLUMN__STATUS = "Status"
    RESULT_COLUMN__NUMBER = "Number"
    EMPTY_STRING = ""
    NOT_DELETED_FILES_JSON = "not-deleted-files.json"
    ERROR_STATUS = "Error"

    def __init__(self, media_set_1: MediaSet, media_set_2: MediaSet):
        self.media_set_1 = media_set_1
        self.media_set_2 = media_set_2
        CFMBatch.__init__(self, batch_title=self.BATCH_TITLE,
                          stderr_file=OutputDirectory.get(self.media_set_1.root_path).batch_stderr,
                          stdout_file=OutputDirectory.get(self.media_set_1.root_path).batch_stdout)

        self.result_stats = {}
        self.not_copied_files = []

    def initialize(self):
        LOGGER.write_title(self.media_set_2, self.update_title())

    def task_getter(self):
        return DeleteFile.execute

    def increment_stats(self, status):
        if status not in self.result_stats:
            self.result_stats[status] = 0
        self.result_stats[status] += 1

    def arguments(self):
        args_list = []
        for media_file in self.media_set_2:
            if not self.media_set_1.contains(media_file):
                args_list.append(
                    BatchElement((self.media_set_2.root_path, media_file.file_desc),
                                    media_file.file_desc.relative_path))
        return args_list

    def post_task(self, result_delete: Tuple[bool, str, FileAccess, Union[FileAccess, None]], pb, replace=False):
        success, status, old_file_access, new_file_access = result_delete

        if not success:
            original_media = self.media_set_2.get_media(old_file_access.id)
            self.not_copied_files.append(original_media)

        if status:
            self.increment_stats(status)
        else:
            self.increment_stats(self.ERROR_STATUS)

        pb.increment()

    def finalize(self):
        
        #LOGGER.info(self.media_set_1.output_directory.save_list(self.not_copied_files, self.NOT_DELETED_FILES_JSON))
        self.media_set_2.delete_not_existing_media()

        print(self.EMPTY_STRING)
        tab = ConsoleTable()
        tab.print_header(self.RESULT_COLUMN__STATUS, self.RESULT_COLUMN__NUMBER)
        for status in self.result_stats:
            tab.print_line(status, str(self.result_stats[status]))
        print(self.EMPTY_STRING)
