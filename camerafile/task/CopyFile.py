import os
from enum import Enum
from pathlib import Path
from typing import Tuple

from camerafile.core.Configuration import Configuration
from camerafile.core.Constants import ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, ORIGINAL_PATH
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.fileaccess.FileAccess import CopyMode
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.processor.BatchCopyElement import BatchCopyElement
from camerafile.processor.BatchTool import BatchElement


class CollisionPolicy(Enum):
    RENAME = 1
    RENAME_PARENT = 2
    IGNORE = 3

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return CollisionPolicy[s.upper()]
        except KeyError:
            return s


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

    @classmethod
    def add_new_copy_element(cls, copy_elements_map, copy_element, new_media_set, nb_collisions=0):
        copy_element: BatchCopyElement
        new_path = Path(new_media_set.state.org_format.get_formatted_string(copy_element.media))
        collision_policy = None
        if nb_collisions != 0:
            configured_collision_policy = Configuration.get().collision_policy
            copy_element.collision_policy = configured_collision_policy
            if configured_collision_policy == CollisionPolicy.RENAME_PARENT:
                new_path = new_path.parent.parent / (new_path.parent.name + f"~{nb_collisions + 1}") / new_path.name
            elif configured_collision_policy == CollisionPolicy.RENAME:
                new_path = new_path.parent / cls.add_suffix_to_filename(new_path.name, f"~{nb_collisions + 1}")
            elif configured_collision_policy == CollisionPolicy.IGNORE:
                return

        if new_path in copy_elements_map:
            nb_collisions += 1
            other_element: BatchCopyElement = copy_elements_map[new_path]
            if copy_element.modification_date >= other_element.modification_date:
                cls.add_new_copy_element(copy_elements_map, copy_element, new_media_set, nb_collisions)
            else:
                copy_element.collision_policy = collision_policy
                copy_element.destination = new_path
                copy_elements_map[new_path] = copy_element
                cls.add_new_copy_element(copy_elements_map, other_element, new_media_set, nb_collisions)
        else:
            copy_element.collision_policy = collision_policy
            copy_element.destination = new_path
            copy_elements_map[new_path] = copy_element

    @staticmethod
    def copy(media_file: MediaFile, new_media_set: MediaSet, new_file_desc: FileDescription):
        new_media_file = MediaFile(new_file_desc, None, new_media_set)
        new_media_file.metadata = media_file.metadata
        new_media_file.metadata.set_value(ORIGINAL_COPY_PATH, str(media_file))
        new_media_file.metadata.set_value(DESTINATION_COPY_PATH, new_file_desc.get_relative_path())
        new_media_set.register_file(new_media_file)
        return True

    @staticmethod
    def move(media_file: MediaFile, new_file_desc: FileDescription):
        new_media_file = MediaFile(new_file_desc, None, media_file.parent_set)
        new_media_file.metadata = media_file.metadata
        new_media_file.loaded_from_database = True
        new_media_file.metadata.set_value(ORIGINAL_PATH, str(media_file))
        media_file.parent_set.register_file(new_media_file)
        media_file.parent_set.unregister_file(media_file)
        return True
