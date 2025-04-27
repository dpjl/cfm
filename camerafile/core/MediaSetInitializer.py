from pathlib import Path

from camerafile.core.FileScanner import FileScanner
from camerafile.core.Logging import Logger
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSetDump import MediaSetDump
from camerafile.core.OutputDirectory import OutputDirectory

LOGGER = Logger(__name__)

class MediaSetInitializer:

    @staticmethod
    def initialize(media_set) -> None:

        # 1. Reset the "exists" flag for all previously registered files
        for key in media_set.filename_map:
            media_set.filename_map[key].exists = False

        # 2. Scan the disk to obtain new files
        new_files = FileScanner.update_from_disk(media_set.root_path, media_set.state, media_set.filename_map)
        dump_file = MediaSetDump.get(OutputDirectory.get(media_set.root_path)).dump_file
        LOGGER.info_indent(f"{len(media_set.filename_map)} media files loaded from dump {dump_file}", prof=2)

        # 3. Initialize the root directory
        if "." not in media_set.media_dir_list:
            root_media_dir = MediaDirectory(".", None, media_set)
            media_set.media_dir_list["."] = root_media_dir
            media_set.add_directory(root_media_dir)

        # 4. Initialize new media files
        MediaSetInitializer.init_new_media_files(media_set, new_files)

        # 5. Delete files that are still marked as not existing after full scan
        MediaSetInitializer.delete_not_existing_media(media_set)
        
    @staticmethod
    def init_new_media_files(media_set, found_files_map) -> None:
        LOGGER.start("{nb_file} new files that are not already in dump", 1000, prof=2)
        number_of_files = 0
        LOGGER.update(nb_file=number_of_files)
        for file_path, file_description in found_files_map.items():
            media_dir = MediaSetInitializer.create_media_dir_parent(media_set, file_description.relative_path)
            new_media_file = MediaFile(file_description, media_dir, media_set)
            media_set.register_file(new_media_file)
            number_of_files += 1
            LOGGER.update(nb_file=number_of_files)
        LOGGER.end(nb_file=number_of_files)

    @staticmethod
    def create_media_dir_parent(media_set, dir_or_file_path: str):
        parent = Path(dir_or_file_path).parent.as_posix()
        if parent not in media_set.media_dir_list:
            new_media_dir = MediaDirectory(parent, MediaSetInitializer.create_media_dir_parent(media_set, parent), media_set)
            media_set.add_directory(new_media_dir)
        return media_set.media_dir_list[parent]

    @staticmethod
    def delete_not_existing_media(media_set):
        deleted = []
        to_be_deleted = []
        for media_file in media_set:
            if not media_file.exists:
                to_be_deleted.append(media_file)
        for media_file in to_be_deleted:
            deleted.append(media_file.get_path())
            media_set.unregister_file(media_file)
        if len(deleted) != 0:
            deleted_file = OutputDirectory.get(media_set.root_path).save_list(deleted, "deleted-files.json")
            LOGGER.info_indent("{l1} files detected as deleted [{file}]".format(l1=len(deleted), file=deleted_file))

