import dhash
from pathlib import Path
from typing import List, Iterator, Tuple, Dict, Any, Optional

from camerafile.core.Constants import CFM_CAMERA_MODEL, INTERNAL
from camerafile.core.FileScanner import FileScanner
from camerafile.core.Logging import Logger
from camerafile.core.MediaDuplicateManager import MediaDuplicateManager
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaIndexManager import MediaIndexManager
from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.MediaSetDump import MediaSetDump
from camerafile.core.MediaSetState import MediaSetState
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.mdtools.MdConstants import MetadataNames

LOGGER = Logger(__name__)

class MediaSet:
    def __init__(self, path: str, org_format: Optional[str] = None, db_file=None):
        root_path = Path(path).resolve()
        self.root_path = root_path.as_posix()
        self.name = root_path.name
        self.media_file_list: List[MediaFile] = []
        self.media_dir_list = {}
        self.id_map: Dict[str, MediaFile] = {}
        self.filename_map: Dict[str, MediaFile] = {}
        self.db_file = db_file
        self.state: MediaSetState = MediaSetState(self.root_path)

        # Instantiate the delegated managers
        self.index_manager = MediaIndexManager()

        self.initialize_file_and_dir_list()
        self.delete_not_existing_media()
        self.state.load_format(org_format)
        self.state.load_metadata_to_read()

        LOGGER.debug("New MediaSet object created: " + str(id(self)))

    @staticmethod
    def load_media_set(path: str, org_format: Optional[str] = None, db_file=None) -> "MediaSet":
        if path is None:
            raise ValueError("Invalid MediaSet path: None")
        LOGGER.write_title_2(str(path), "Opening media directory")
        loaded = MediaSetDump.get(OutputDirectory.get(path)).load()
        if loaded:
            if len(loaded.media_file_list) >= 1:
                loaded = loaded.media_file_list[0].parent_set
            root_path = Path(path).resolve()
            loaded.root_path = root_path.as_posix()
            loaded.db_file = db_file
            loaded.state = MediaSetState(loaded.root_path)
            loaded.initialize_file_and_dir_list()
            loaded.delete_not_existing_media()
            loaded.state.load_format(org_format)
            loaded.state.load_metadata_to_read()
            return loaded
        else:
            return MediaSet(path, org_format, db_file)

    def __str__(self):
        return str(self.root_path)

    def __repr__(self):
        result = "-------------\nRoot path: " + str(self.root_path) + "\nFiles:\n"
        for media in self.media_file_list:
            result += repr(media) + "\n"
        return result

    def __len__(self):
        return len(self.media_file_list)

    def __iter__(self) -> Iterator[MediaFile]:
        return iter(self.media_file_list)

    def __getitem__(self, file_id) -> MediaFile:
        return self.id_map[file_id]

    def delete_not_existing_media(self):
        deleted = []
        to_be_deleted = []
        for media_file in self:
            if not media_file.exists:
                to_be_deleted.append(media_file)
        for media_file in to_be_deleted:
            deleted.append(media_file.get_path())
            self.remove_file(media_file)
        if len(deleted) != 0:
            deleted_file = OutputDirectory.get(self.root_path).save_list(deleted, "deleted-files.json")
            LOGGER.info_indent("{l1} files detected as deleted [{file}]".format(l1=len(deleted), file=deleted_file))

    def save_on_disk(self):
        MediaSetDatabase.get(OutputDirectory.get(self.root_path), self.db_file).save(self)
        MediaSetDump.get(OutputDirectory.get(self.root_path)).save(self)

    def close_database(self):
        MediaSetDatabase.get(OutputDirectory.get(self.root_path), self.db_file).close()

    def add_file(self, media_file: MediaFile) -> None:
        """Adds a media file to the internal structures and updates the indexes."""
        self.media_file_list.append(media_file)
        self.id_map[media_file.file_desc.id] = media_file
        self.filename_map[media_file.get_path()] = media_file
        self.index_manager.add_media_file_by_size(media_file)
        self.index_manager.add_media_file_by_signature(media_file)

    def remove_file(self, media_file: MediaFile) -> None:
        """Removes a media file from the internal structures and updates the indexes."""
        self.index_manager.remove_media_file_by_size(media_file)
        self.index_manager.remove_media_file_by_signature(media_file)
        if media_file.get_path() in self.filename_map:
            del self.filename_map[media_file.get_path()]
        if media_file.file_desc.id in self.id_map:
            del self.id_map[media_file.file_desc.id]
        self.media_file_list.remove(media_file)

    def get_media(self, media_id: str) -> Optional[MediaFile]:
        return self.id_map.get(media_id, None)

    def contains(self, item: MediaFile):
        date = item.get_exif_date()
        file_size = item.get_file_size()
        if self.index_manager.exist_in_x_y_map(self.index_manager.date_size_map, date, file_size):
            return True

        # Question:
        # If the date is exactly the same down to the millisecond, and the height and width are identical
        # (even if the file sizes are different?), might we consider these as the same images?
        # This would avoid having to compute the signature.
        # Case of iPhone photos exported by two different tools.
        if item.get_signature() is not None:
            if date is not None and date in self.index_manager.date_sig_map:
                for sig in self.index_manager.date_sig_map[date]:
                    if dhash.get_num_bits_different(sig, item.get_signature()) < 4:
                        return True
            return False
        return False

    def get_possibly_duplicates(self) -> List[MediaFile]:
        return MediaDuplicateManager.get_possibly_duplicates(self.index_manager)

    def duplicates_map(self) -> Dict[int, List[List[MediaFile]]]:
        return MediaDuplicateManager.duplicates_map(self.index_manager)

    def duplicates_info(self) -> Dict[MediaFile, tuple]:
        return MediaDuplicateManager.duplicates_info(self.index_manager)

    def propagate_sig_to_duplicates(self) -> None:
        MediaDuplicateManager.propagate_signature(self.index_manager)

    def propagate_cm_to_duplicates(self) -> None:
        MediaDuplicateManager.propagate_camera_model(self.index_manager)

    def get_duplicates_report(self, duplicates):
        str_list = ["All media files: " + str(len(self.media_file_list)),
                    "Distinct elements: {distinct}".format(distinct=str(sum(map(len, duplicates.values()))))]
        for n_copy, media_list_list in sorted(duplicates.items()):
            str_list.append("%s elem. found %s times" % (len(media_list_list), n_copy))
        return str_list

    def get_possibly_already_exists(self, media_set2):
        result = []
        for date in self.index_manager.date_size_map:
            if date in media_set2.index_manager.date_size_map:
                if len(self.index_manager.date_size_map[date]) > 1 or len(media_set2.index_manager.date_size_map[date]) > 1:
                    for file_size in self.index_manager.date_size_map[date]:
                        result.append(self.index_manager.date_size_map[date][file_size][0])
                    for file_size in media_set2.index_manager.date_size_map[date]:
                        result.append(media_set2.index_manager.date_size_map[date][file_size][0])
        return result

    def cmp(self, other_media_set: "MediaSet") -> Tuple[List[Any], List[Any]]:
        in_both, only_in_self = [], []
        for date in self.index_manager.date_size_map:
            size_map = self.index_manager.date_size_map[date]
            if len(size_map) == 1:
                _, unique_media_list = next(iter(size_map.items()))
                if other_media_set.contains(unique_media_list[0]):
                    in_both.append(unique_media_list)
                else:
                    only_in_self.append(unique_media_list)
            else:
                for media_list in self.index_manager.date_sig_map.get(date, {}).values():
                    if other_media_set.contains(media_list[0]):
                        in_both.append(media_list)
                    else:
                        only_in_self.append(media_list)
        return in_both, only_in_self

    @staticmethod
    def add_duplicates_to_n_copy(n_copy, media_list: List[MediaFile]):
        nb_copy = len(media_list)
        if nb_copy not in n_copy:
            n_copy[nb_copy] = []
        n_copy[nb_copy] += [media_list]

    def get_oldest_modified_file(self, media_list: List["MediaFile"]) -> Tuple[Any, Any]:
        oldest_date = None
        oldest_media = None
        for media_file in media_list:
            media_date = media_file.get_last_modification_date()
            if oldest_date is None or media_date < oldest_date:
                oldest_date = media_date
                oldest_media = media_file
        return oldest_media, oldest_date

    def get_file_list(self, ext=None, cm=None) -> List["MediaFile"]:
        return [media_file for media_file in self.media_file_list if MediaSet.filter(media_file, ext, cm)]

    @staticmethod
    def filter(media_file: MediaFile, ext_filter: Optional[List[str]], cm_filter: str) -> bool:
        if ext_filter is not None and media_file.file_desc.extension not in ext_filter:
            return False
        cfm_camera_model = media_file.metadata[CFM_CAMERA_MODEL]
        internal_md = media_file.metadata[INTERNAL]
        model_value = internal_md.get_md_value(MetadataNames.MODEL)
        if cm_filter == "known":
            if model_value is None:
                return False
        elif cm_filter == "unknown":
            if model_value is not None or cfm_camera_model.value is not None:
                return False
        elif cm_filter == "recovered":
            if model_value is not None or cfm_camera_model.value is None:
                return False
        return True

    def create_media_dir_parent(self, dir_or_file_path: str):
        parent = Path(dir_or_file_path).parent.as_posix()
        if parent not in self.media_dir_list:
            from camerafile.core.MediaDirectory import MediaDirectory
            new_media_dir = MediaDirectory(parent, self.create_media_dir_parent(parent), self)
            self.media_dir_list[parent] = new_media_dir
        return self.media_dir_list[parent]

    def initialize_file_and_dir_list(self, root_path: Optional[str] = None) -> None:
        if root_path is None:
            root_path = self.root_path
        from camerafile.core.MediaSetInitializer import MediaSetInitializer
        initializer = MediaSetInitializer(self)
        initializer.initialize(root_path)

    def init_new_media_files(self, found_files_map: Dict[str, FileDescription]) -> None:
        from camerafile.core.MediaFile import MediaFile
        LOGGER.start("{nb_file} new files that are not already in dump or db", 1000, prof=2)
        number_of_files = 0
        LOGGER.update(nb_file=number_of_files)
        for file_path, file_description in found_files_map.items():
            media_dir = self.create_media_dir_parent(file_description.relative_path)
            new_media_file = MediaFile(file_description, media_dir, self)
            self.add_file(new_media_file)
            number_of_files += 1
            LOGGER.update(nb_file=number_of_files)
        LOGGER.end(nb_file=number_of_files)
