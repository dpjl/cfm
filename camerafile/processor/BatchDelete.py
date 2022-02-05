from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.task.DeleteFile import DeleteFile

LOGGER = Logger(__name__)


class BatchDelete(TaskWithProgression):
    BATCH_TITLE = "Delete files (move to trash)"
    RESULT_COLUMN__STATUS = "Status"
    RESULT_COLUMN__NUMBER = "Number"
    EMPTY_STRING = ""
    NOT_DELETED_FILES_JSON = "not-deleted-files.json"
    ERROR_STATUS = "Error"

    def __init__(self, media_set_1: MediaSet, media_set_2: MediaSet, copy_mode):
        self.media_set_1 = media_set_1
        self.media_set_2 = media_set_2
        self.copy_mode = copy_mode
        TaskWithProgression.__init__(self, batch_title=self.BATCH_TITLE)
        self.result_stats = {}
        self.not_copied_files = []

    def task_getter(self):
        return DeleteFile.execute

    def increment_stats(self, status):
        if status not in self.result_stats:
            self.result_stats[status] = 0
        self.result_stats[status] += 1

    def arguments(self):
        return self.media_set_2.all_files_not_in_other_media_set(self.media_set_1)

    def post_task(self, result_delete, progress_bar, replace=False):
        success, status, file_id, new_file_path = result_delete
        original_media = self.media_set_2.get_media(file_id)

        if success:
            original_media.move_metadata(new_file_path)
        else:
            self.not_copied_files.append(original_media)

        if status:
            self.increment_stats(status)
        else:
            self.increment_stats(self.ERROR_STATUS)

        progress_bar.increment()

    def finalize(self):
        LOGGER.info(self.media_set_1.output_directory.save_list(self.not_copied_files, self.NOT_DELETED_FILES_JSON))

        print(self.EMPTY_STRING)
        tab = ConsoleTable()
        tab.print_header(self.RESULT_COLUMN__STATUS, self.RESULT_COLUMN__NUMBER)
        for status in self.result_stats:
            tab.print_line(status, str(self.result_stats[status]))
        print(self.EMPTY_STRING)
