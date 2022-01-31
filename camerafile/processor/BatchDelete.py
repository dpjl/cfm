from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Logging import Logger
from camerafile.task.DeleteFile import DeleteFile

LOGGER = Logger(__name__)


class BatchDelete(TaskWithProgression):

    def __init__(self, media_set_1, media_set_2, copy_mode):
        self.media_set_1 = media_set_1
        self.media_set_2 = media_set_2
        self.copy_mode = copy_mode
        TaskWithProgression.__init__(self, batch_title="Delete files (move to trash)")
        self.result = {"Deleted": 0, "Error": 0}
        self.not_copied_files = []

    def task_getter(self):
        return DeleteFile.execute

    def arguments(self):
        return self.media_set_2.all_files_not_in_other_media_set(self.media_set_1)

    def post_task(self, result_delete, progress_bar, replace=False):
        status, file_id, new_file_path = result_delete
        original_media = self.media_set_2.get_media(file_id)
        if status:
            original_media.move_metadata(new_file_path)
            self.result["Deleted"] += 1
        else:
            self.not_copied_files.append(original_media)
            self.result["Error"] += 1

        progress_bar.increment()

    def finalize(self):
        LOGGER.info(self.media_set_1.output_directory.save_list(self.not_copied_files, "not-deleted-files.json"))
        print("")
        tab = ConsoleTable()
        tab.print_header("Status", "Number")
        for status in self.result:
            tab.print_line(status, str(self.result[status]))
        print("")
