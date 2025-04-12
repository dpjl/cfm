from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.core.MediaSetDump import MediaSetDump
from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.Logging import Logger
from camerafile.core.FileScanner import FileScanner

LOGGER = Logger(__name__)

class MediaSetInitializer:
    """
    Orchestrator for MediaSet initialization.
    This includes:
      - Scanning the directory via FileScanner
      - Loading from the database
      - Initializing media directories
      - Loading thumbnails
    """
    def __init__(self, media_set):
        self.media_set = media_set

    def initialize(self, root_path: str) -> None:
        # 1. Scan the disk to obtain new files and ignored files
        not_loaded_files, ignored_files = FileScanner.update_from_disk(self.media_set.root_path, self.media_set.state, self.media_set.filename_map)
        dump_file = MediaSetDump.get(OutputDirectory.get(self.media_set.root_path)).dump_file
        LOGGER.info_indent(f"{len(self.media_set.filename_map)} media files loaded from dump {dump_file}", prof=2)

        # 2. Initialize the root directory
        self.media_set.media_dir_list["."] = MediaDirectory(".", None, self)

        # 3. Load from the database (update existing files, add new ones)
        db = MediaSetDatabase.get(OutputDirectory.get(self.media_set.root_path), self.media_set.db_file)
        not_loaded_files = db.load_all_files(self.media_set, not_loaded_files)

        # 4. Initialize new media files
        self.media_set.init_new_media_files(not_loaded_files)
