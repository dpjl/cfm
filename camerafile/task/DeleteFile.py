from typing import Tuple

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.processor.BatchTool import BatchElement
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory

class DeleteFile:

    @staticmethod
    def execute(batch_element: BatchElement):
        delete_task_arg: Tuple[str, FileDescription, str] = batch_element
        root_path, file_desc = delete_task_arg.args
        file_access: FileAccess = FileAccessFactory.get(root_path, file_desc)
        try:
            result = file_access.delete_file()
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise e
            else:
                batch_element.error = "DeleteFile: [{info}] - ".format(info=batch_element.info) + str(e)
        
        batch_element.args = None
        batch_element.result = result
        return batch_element
