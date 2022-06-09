from typing import Tuple, Union

from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.fileaccess.FileAccess import CopyMode
from camerafile.fileaccess.FileDescription import FileDescription
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
        CFMBatch.__init__(self, batch_title=self.BATCH_TITLE,
                          stderr_file=OutputDirectory.get(self.old_media_set.root_path).batch_stderr,
                          stdout_file=OutputDirectory.get(self.old_media_set.root_path).batch_stdout)

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
                media_file: MediaFile = self.old_media_set.get_oldest_modified_file(media_list)
                if not self.new_media_set.contains(media_file):
                    new_root, _, new_path = CopyFile.get_organization_path(media_file, self.new_media_set, new_path_map)
                    new_path_map[new_path] = 0
                    args_list.append(BatchElement(
                        (media_file.parent_set.root_path, media_file.file_desc, new_root, new_path, self.copy_mode),
                        media_file.get_path()))
        return args_list

    def post_task(self, result: Tuple[bool, str, FileDescription, Union[FileDescription, None]], pb, replace=False):
        success, status, old_file_spec, new_file_spec = result
        original_media: MediaFile = self.old_media_set.get_media(old_file_spec.id)
        if success:
            CopyFile.copy(original_media, self.new_media_set, new_file_spec)
        else:
            self.not_copied_files.append(original_media)

        if status:
            self.increment_stats(status)
        else:
            self.increment_stats(self.ERROR_STATUS)

        pb.increment()

    def finalize(self):
        LOGGER.info(OutputDirectory.get(self.old_media_set.root_path).save_list(self.not_copied_files,
                                                                                self.NOT_COPIED_FILES_JSON))

        print(self.EMPTY_STRING)
        tab = ConsoleTable()
        tab.print_header(self.RESULT_COLUMN__STATUS, self.RESULT_COLUMN__NUMBER)
        for status in self.result_stats:
            tab.print_line(status, str(self.result_stats[status]))
        print(self.EMPTY_STRING)
