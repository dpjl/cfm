from typing import Tuple

from camerafile.core import Configuration
from camerafile.fileaccess.FileAccess import FileAccess


class DeleteFile:

    @staticmethod
    def execute(delete_task_arg: Tuple[FileAccess, str]):
        file_access, trash_file = delete_task_arg
        try:
            return file_access.delete_file(trash_file)
        except BaseException as e:
            if Configuration.EXIT_ON_ERROR:
                raise e
            print(e)
            return False, "Exception", file_access, None
