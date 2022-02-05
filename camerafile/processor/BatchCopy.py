from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.task.CopyFile import CopyFile

LOGGER = Logger(__name__)


class BatchCopy(TaskWithProgression):
    BATCH_TITLE = "Copy files"
    RESULT_COLUMN__STATUS = "Status"
    RESULT_COLUMN__NUMBER = "Number"
    EMPTY_STRING = ""
    NOT_COPIED_FILES_JSON = "not-copied-files.json"
    ERROR_STATUS = "Error"

    def __init__(self, old_media_set: MediaSet, new_media_set: MediaSet, copy_mode):
        self.old_media_set = old_media_set
        self.new_media_set = new_media_set
        self.copy_mode = copy_mode
        TaskWithProgression.__init__(self, batch_title=self.BATCH_TITLE)
        self.result_stats = {}
        self.not_copied_files = []

    def task_getter(self):
        return CopyFile.execute

    def increment_stats(self, status):
        if status not in self.result_stats:
            self.result_stats[status] = 0
        self.result_stats[status] += 1

    def arguments(self):
        return self.old_media_set.unique_files_not_in_destination(self.new_media_set, self.copy_mode)

    def post_task(self, result_copy, progress_bar, replace=False):
        success, status, file_id, new_file_path = result_copy
        original_media = self.old_media_set.get_media(file_id)
        if success:
            original_media.copy_metadata(self.new_media_set, new_file_path)
        else:
            self.not_copied_files.append(original_media)

        if status:
            self.increment_stats(status)
        else:
            self.increment_stats(self.ERROR_STATUS)

        progress_bar.increment()

    def finalize(self):
        LOGGER.info(self.old_media_set.output_directory.save_list(self.not_copied_files, self.NOT_COPIED_FILES_JSON))

        print(self.EMPTY_STRING)
        tab = ConsoleTable()
        tab.print_header(self.RESULT_COLUMN__STATUS, self.RESULT_COLUMN__NUMBER)
        for status in self.result_stats:
            tab.print_line(status, str(self.result_stats[status]))
        print(self.EMPTY_STRING)
