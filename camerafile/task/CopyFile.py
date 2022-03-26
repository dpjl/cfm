from typing import Tuple

from camerafile.core.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess, CopyMode


class CopyFile:

    @staticmethod
    def execute(batch_element: BatchElement):
        copy_task_arg: Tuple[FileAccess, str, CopyMode] = batch_element.args
        file_access, new_file_path, copy_mode = copy_task_arg
        result = False, file_access.id, None

        try:
            result = file_access.copy_to(new_file_path, copy_mode)
        except BaseException as e:
            if Configuration.get().exit_on_error:
                pass  # TODO : put full stacktrace in batch_element.error
            else:
                batch_element.error = "CopyFile: [{info}] - ".format(info=batch_element.info) + str(e)

        batch_element.args = None
        batch_element.result = result
        return batch_element
