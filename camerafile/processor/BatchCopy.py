from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Logging import Logger
from camerafile.task.CopyFile import CopyFile

LOGGER = Logger(__name__)


class BatchCopy(TaskWithProgression):

    def __init__(self, old_media_set, new_media_set, copy_mode):
        self.old_media_set = old_media_set
        self.new_media_set = new_media_set
        self.copy_mode = copy_mode
        TaskWithProgression.__init__(self, batch_title="Copy files")
        self.result = {"Copied": 0, "Error": 0}
        self.not_copied_files = []

    def task_getter(self):
        return CopyFile.execute

    def arguments(self):
        return self.old_media_set.unique_files_not_in_destination(self.new_media_set, self.copy_mode)

    def post_task(self, result_copy, progress_bar, replace=False):
        status, file_id, new_file_path = result_copy
        original_media = self.old_media_set.get_media(file_id)
        if status:
            original_media.copy_metadata(self.new_media_set, new_file_path)
            self.result["Copied"] += 1
        else:
            self.not_copied_files.append(original_media)
            self.result["Error"] += 1

        progress_bar.increment()

    def finalize(self):
        LOGGER.info(self.old_media_set.output_directory.save_list(self.not_copied_files, "not-copied-files.json"))
        print("")
        tab = ConsoleTable()
        tab.print_header("Status", "Number")
        for status in self.result:
            tab.print_line(status, str(self.result[status]))
        print("")
