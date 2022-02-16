from typing import Tuple

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess, CopyMode


class CopyFile:

    @staticmethod
    def execute(copy_task_arg: Tuple[FileAccess, str, CopyMode]):
        file_access, new_file_path, copy_mode = copy_task_arg
        try:
            return file_access.copy_to(new_file_path, copy_mode)
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise e
            print(e)
            return False, file_access.id, None
