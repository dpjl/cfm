import os
from pathlib import Path
from typing import Tuple

from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration
from camerafile.core.Constants import ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, ORIGINAL_PATH
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.fileaccess.FileAccess import CopyMode
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.fileaccess.FileDescription import FileDescription


class CopyFile:

    @staticmethod
    def execute(batch_element: BatchElement):
        copy_task_arg: Tuple[str, FileDescription, str, str, CopyMode] = batch_element.args
        old_root, file_desc, new_root_path, new_file_path, copy_mode = copy_task_arg
        result = False, "Default status", file_desc, None
        file_access = FileAccessFactory.get(old_root, file_desc)

        try:
            result = file_access.copy_to(new_root_path, new_file_path, copy_mode)
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise
            else:
                batch_element.error = "CopyFile: [{info}] - ".format(info=batch_element.info) + str(e)

        batch_element.args = None
        batch_element.result = result
        return batch_element

    @staticmethod
    def add_suffix_to_filename(filename, suffix):
        splitext = os.path.splitext(filename)
        name_without_extension = splitext[0]
        extension = splitext[1] if len(splitext) > 1 else ""
        return name_without_extension + suffix + extension

    @staticmethod
    def get_organization_path(media_file: MediaFile, new_media_set: MediaSet, new_path_map):
        new_root_path = Path(new_media_set.root_path)
        new_dir_path = new_media_set.org_format.get_formatted_string(media_file)
        new_file_path = Path(new_dir_path)
        original_file_name = media_file.file_desc.name
        i = 2
        while new_file_path in new_path_map:
            new_file_name = CopyFile.add_suffix_to_filename(original_file_name, "~" + str(i))
            new_file_path = Path(new_dir_path) / new_file_name
            i += 1

        if new_file_path in new_path_map:
            print("Something is wrong: destination still exists " + new_file_path)

        return new_root_path, new_dir_path, new_file_path

    @staticmethod
    def copy(media_file: MediaFile, new_media_set: MediaSet, new_file_desc: FileDescription):
        new_media_file = MediaFile(new_file_desc, None, new_media_set)
        new_media_file.metadata = media_file.metadata
        new_media_file.metadata.set_value(ORIGINAL_COPY_PATH, str(media_file))
        new_media_file.metadata.set_value(DESTINATION_COPY_PATH, new_file_desc.get_relative_path())
        new_media_set.add_file(new_media_file)
        return True

    @staticmethod
    def move(media_file: MediaFile, new_file_desc: FileDescription):
        new_media_file = MediaFile(new_file_desc, None, media_file.parent_set)
        new_media_file.metadata = media_file.metadata
        new_media_file.loaded_from_database = True
        new_media_file.metadata.set_value(ORIGINAL_PATH, str(media_file))
        media_file.parent_set.add_file(new_media_file)
        media_file.parent_set.remove_file(media_file)
        return True
