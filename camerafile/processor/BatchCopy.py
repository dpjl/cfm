from datetime import datetime
from pathlib import Path
from typing import Tuple, Union

from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.Configuration import Configuration
from camerafile.core.MediaDuplicateManager import MediaDuplicateManager
from camerafile.processor.BatchCopyElement import BatchCopyElement
from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.fileaccess.FileAccess import CopyMode
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.CopyFile import CopyFile, CollisionPolicy

LOGGER = Logger(__name__)


class BatchCopy(CFMBatch):
    BATCH_TITLE = "Copy files"
    RESULT_COLUMN__STATUS = "Status"
    RESULT_COLUMN__NUMBER = "Number"
    EMPTY_STRING = ""
    NOT_COPIED_FILES_JSON = "not-copied-files.json"
    ERROR_STATUS = "Error"

    def __init__(self, old_media_set: MediaSet, new_media_set: MediaSet, copy_mode: CopyMode):
        self.old_media_set = old_media_set
        self.new_media_set = new_media_set
        self.copy_mode = copy_mode
        CFMBatch.__init__(self, batch_title=self.BATCH_TITLE,
                          stderr_file=OutputDirectory.get(self.old_media_set.root_path).batch_stderr,
                          stdout_file=OutputDirectory.get(self.old_media_set.root_path).batch_stdout)

        self.result_stats = {}
        self.not_copied_files = []
        self.target_modified_paths = []

    def initialize(self):
        LOGGER.write_title(self.new_media_set, self.update_title())
        self.new_media_set.state.org_format.init_duplicates(self.old_media_set)

    def task_getter(self):
        return CopyFile.execute

    def increment_stats(self, status):
        if status not in self.result_stats:
            self.result_stats[status] = 0
        self.result_stats[status] += 1

    def arguments(self):
        args_list = []
        copy_elements_map = {}
        ignore = 0
        if not Configuration.get().watch:
            LOGGER.info("Create copy list...")
        if Configuration.get().ignore_duplicates:
            ignore = self.__create_copy_list_without_duplicates(copy_elements_map, ignore)
        else:
            ignore = self.__create_copy_list(copy_elements_map, ignore)

        if ignore != 0:
            LOGGER.info(f"{ignore} collisions ignored")
        stats = {col: 0 for col in CollisionPolicy}
        cp_element: BatchCopyElement
        for cp_element in copy_elements_map.values():
            if cp_element.collision_policy is not None:
                stats[cp_element.collision_policy] += 1
            media = cp_element.media
            cp_args = (media.parent_set.root_path,
                       media.file_desc,
                       self.new_media_set.root_path,
                       cp_element.destination,
                       self.copy_mode)
            batch_element = BatchElement(cp_args, media.get_path())
            args_list.append(batch_element)
        for collision_policy, nb in stats.items():
            if nb != 0:
                LOGGER.info(f"{nb} files will be copied with collision policy '{collision_policy}'")

        return args_list

    def __create_copy_list(self, copy_elements_map, ignore):
        for media in self.old_media_set:
            date: datetime = media.get_last_modification_date()
            cp_element = BatchCopyElement(media, date)
            CopyFile.add_new_copy_element(copy_elements_map, cp_element, self.new_media_set)
            if cp_element.collision_policy == CollisionPolicy.IGNORE:
                ignore += 1
        return ignore

    def __create_copy_list_without_duplicates(self, copy_elements_map, ignore):
        n_copy_list = MediaDuplicateManager.duplicates_map(self.old_media_set)
        for n_copy in n_copy_list.values():
            for media_list in n_copy:
                media: MediaFile
                date: datetime
                media, date = self.old_media_set.get_oldest_modified_file(media_list)
                if not self.new_media_set.contains(media):
                    cp_element = BatchCopyElement(media, date)
                    CopyFile.add_new_copy_element(copy_elements_map, cp_element, self.new_media_set)
                    if cp_element.collision_policy == CollisionPolicy.IGNORE:
                        ignore += 1
        return ignore

    def add_target_modified_path(self, new_path: str):
        found = False
        for i, path in enumerate(self.target_modified_paths):
            if new_path == path:
                found = True
            elif new_path in path:
                self.target_modified_paths[i] = new_path
                found = True
            elif path in new_path:
                found = True
        if not found:
            self.target_modified_paths.append(new_path)

    def post_task(self, result: Tuple[bool, str, FileDescription, Union[FileDescription, None]], pb, replace=False):
        success, status, old_file_spec, new_file_spec = result
        original_media: MediaFile = self.old_media_set.get_media(old_file_spec.id)
        if success:
            self.add_target_modified_path(Path(new_file_spec.relative_path).parent.as_posix())
            CopyFile.copy(original_media, self.new_media_set, new_file_spec)
        else:
            self.not_copied_files.append(original_media)

        if status:
            self.increment_stats(status)
        else:
            self.increment_stats(self.ERROR_STATUS)

        pb.increment()

    def finalize(self):
        self.new_media_set.state["loaded_metadata"] = self.old_media_set.state["loaded_metadata"]
        self.new_media_set.state.save()

        if len(self.not_copied_files) != 0:
            LOGGER.info(OutputDirectory.get(self.old_media_set.root_path).save_list(self.not_copied_files,
                                                                                    self.NOT_COPIED_FILES_JSON))

        if len(self.result_stats) != 0:
            print(self.EMPTY_STRING)
            tab = ConsoleTable()
            tab.print_header(self.RESULT_COLUMN__STATUS, self.RESULT_COLUMN__NUMBER)
            for status in self.result_stats:
                tab.print_line(status, str(self.result_stats[status]))
            print(self.EMPTY_STRING)

    def get_copy_elements_without_duplicates(self):
        """
        Returns a list of BatchCopyElement corresponding to the copy logic without duplicates.
        """
        copy_elements_map = {}
        ignore = 0
        self.__create_copy_list_without_duplicates(copy_elements_map, ignore)
        return list(copy_elements_map.values())
