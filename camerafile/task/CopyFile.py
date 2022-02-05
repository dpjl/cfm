from typing import Tuple

from camerafile.fileaccess.FileAccess import FileAccess


class CopyFile:

    @staticmethod
    def execute(copy_task_arg: Tuple[FileAccess, str, str]):
        file_access, new_file_path, copy_mode = copy_task_arg
        try:
            return file_access.copy_to(new_file_path, copy_mode)
        except BaseException as e:
            print(e)
            return False, file_access.id, None