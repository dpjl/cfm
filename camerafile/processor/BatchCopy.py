from typing import Tuple, Union

from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.BatchTool import BatchArgs
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.fileaccess.FileAccess import CopyMode, FileAccess
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.CopyFile import CopyFile

LOGGER = Logger(__name__)


class BatchCopy(CFMBatch):
    BATCH_TITLE = "Copy files"
    RESULT_COLUMN__STATUS = "Status"
    RESULT_COLUMN__NUMBER = "Number"
    EMPTY_STRING = ""
    NOT_COPIED_FILES_JSON = "not-copied-files.json"
    ERROR_STATUS = "Error"

    def __init__(self, old_media_set: MediaSet, new_media_set: MediaSet, copy_mode: CopyMode):
        self.old_media_set = old_media_set
        self.new_media_set = new_media_set
        self.copy_mode = copy_mode
        CFMBatch.__init__(self, batch_title=self.BATCH_TITLE)
        self.result_stats = {}
        self.not_copied_files = []

    def initialize(self):
        LOGGER.write_title(self.new_media_set, self.update_title())

    def task_getter(self):
        return CopyFile.execute

    def increment_stats(self, status):
        if status not in self.result_stats:
            self.result_stats[status] = 0
        self.result_stats[status] += 1

    def arguments(self):
        args_list = []
        n_copy_list = self.old_media_set.duplicates()
        new_path_map = {}
        for n_copy in n_copy_list.values():
            for media_list in n_copy:
                media_file = self.old_media_set.get_oldest_modified_file(media_list)
                if not self.new_media_set.contains(media_file):
                    # _, new_path = media_file.get_destination_path(new_media_set)
                    _, new_path = media_file.get_organization_path(self.new_media_set, new_path_map)
                    new_path_map[new_path] = 0
                    args_list.append(BatchArgs((media_file.file_access, new_path, self.copy_mode),
                                               media_file.relative_path))
        return args_list

    def post_task(self, result_copy: Tuple[bool, str, FileAccess, Union[FileAccess, None]], pb, replace=False):
        success, status, old_file_access, new_file_access = result_copy
        original_media = self.old_media_set.get_media(old_file_access.id)
        if success:
            original_media.copy(self.new_media_set, new_file_access)
        else:
            self.not_copied_files.append(original_media)

        if status:
            self.increment_stats(status)
        else:
            self.increment_stats(self.ERROR_STATUS)

        pb.increment()

    def finalize(self):
        LOGGER.info(self.old_media_set.output_directory.save_list(self.not_copied_files, self.NOT_COPIED_FILES_JSON))

        print(self.EMPTY_STRING)
        tab = ConsoleTable()
        tab.print_header(self.RESULT_COLUMN__STATUS, self.RESULT_COLUMN__NUMBER)
        for status in self.result_stats:
            tab.print_line(status, str(self.result_stats[status]))
        print(self.EMPTY_STRING)
