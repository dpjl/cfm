from pathlib import Path
from typing import List, Iterator, Tuple, Dict, Any, Optional, Union
from itertools import chain
import os

from camerafile.core.Constants import CFM_CAMERA_MODEL, INTERNAL, SIGNATURE
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaIndexer import MediaIndexer
from camerafile.core.MediaSetComparator import MediaSetComparator
from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.MediaSetDump import MediaSetDump
from camerafile.core.MediaSetInitializer import MediaSetInitializer
from camerafile.core.MediaSetState import MediaSetState
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.mdtools.MdConstants import MetadataNames

LOGGER = Logger(__name__)

class MediaSet:
    def __init__(self, path: str, org_format: Optional[str] = None):
        root_path = Path(path).resolve()
        self.root_path = root_path.as_posix()
        self.name = root_path.name
        self.media_file_list: List[MediaFile] = []
        self.media_dir_list = {}
        self.id_map: Dict[str, Union[MediaFile, MediaDirectory]] = {}
        self.filename_map: Dict[str, MediaFile] = {}
        self.state: MediaSetState = MediaSetState(self.root_path)
        self.indexer = MediaIndexer()
        MediaSetInitializer.initialize(self)
        self.state.load_format(org_format)
        self.state.load_metadata_to_read()

        LOGGER.debug("New MediaSet object created: " + str(id(self)))

    @staticmethod
    def load_media_set(path: str, org_format: Optional[str] = None) -> "MediaSet":
        if path is None:
            raise ValueError("Invalid MediaSet path: None")
        LOGGER.write_title_2(str(path), "Opening media directory")
        loaded = MediaSetDump.get(OutputDirectory.get(path)).load()
        if loaded:
            if len(loaded.media_file_list) >= 1:
                loaded = loaded.media_file_list[0].parent_set
            root_path = Path(path).resolve()
            loaded.root_path = root_path.as_posix()
            loaded.state = MediaSetState(loaded.root_path)
            MediaSetInitializer.initialize(loaded)
            loaded.state.load_format(org_format)
            loaded.state.load_metadata_to_read()
            return loaded
        else:
            return MediaSet(path, org_format)

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

    def __getitem__(self, item_id) -> Union[MediaFile, MediaDirectory]:
        return self.id_map[item_id]

    def save_on_disk(self):
        MediaSetDatabase.get(OutputDirectory.get(self.root_path)).save(self)
        MediaSetDump.get(OutputDirectory.get(self.root_path)).save(self)

    def register_file(self, media_file: MediaFile) -> None:
        """Adds a media file to the internal structures and updates the indexes."""
        self.media_file_list.append(media_file)
        self.id_map[media_file.file_desc.id] = media_file
        self.filename_map[media_file.get_path()] = media_file
        self.indexer.add_media_file(media_file)
        if media_file.parent_dir is not None:
            media_file.parent_dir.add_child_file(media_file)

    def add_directory(self, media_dir: MediaDirectory) -> None:
        """Adds a media directory to the internal structures and updates the indexes."""
        self.media_dir_list[media_dir.path] = media_dir
        self.id_map[media_dir.id] = media_dir
        if media_dir.parent_dir is not None:
            media_dir.parent_dir.add_child_dir(media_dir)

    def unregister_file(self, media_file: MediaFile) -> None:
        """Removes a media file from the internal structures and updates the indexes."""
        self.indexer.remove_media_file(media_file)
        if media_file.get_path() in self.filename_map:
            del self.filename_map[media_file.get_path()]
        if media_file.file_desc.id in self.id_map:
            del self.id_map[media_file.file_desc.id]
        if media_file in self.media_file_list:
            self.media_file_list.remove(media_file)
        if media_file.parent_dir is not None:
            media_file.parent_dir.children_files.remove(media_file)

    def remove_directory(self, media_dir: MediaDirectory) -> None:
        """Removes a media directory from the internal structures and updates the indexes."""
        if media_dir.path in self.media_dir_list:
            del self.media_dir_list[media_dir.path]
        if media_dir.id in self.id_map:
            del self.id_map[media_dir.id]
        if media_dir.parent_dir is not None:
            media_dir.parent_dir.children_dirs.remove(media_dir)

    def get_media(self, media_id: str) -> Optional[MediaFile]:
        return self.id_map.get(media_id, None)

    def contains(self, item: MediaFile):
        return self.indexer.exists(item)

    def get_possibly_already_exists(self, media_set2):
        """Retourne les fichiers potentiellement déjà existants dans les deux MediaSet."""
        return MediaSetComparator.get_possibly_already_exists(self, media_set2)

    def cmp(self, other_media_set: "MediaSet") -> Tuple[List[Any], List[Any]]:
        """Compare ce MediaSet à un autre et retourne les fichiers communs et uniques."""
        return MediaSetComparator.cmp(self, other_media_set)

    def get_date_sorted_media_list(self):
        self.media_file_list.sort(key=MediaFile.get_date)
        return self.media_file_list

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

    def get_media_in_directory_recursive(self, dir_id: str) -> list:
        """
        Returns all MediaFiles whose parent is the MediaDirectory with id dir_id,
        or one of its subdirectories (recursive), sorted by descending date.
        """
        if dir_id not in self.id_map:
            return []
        target_dir = self.id_map[dir_id]
        result = []
        
        def _collect_files_recursive(directory: MediaDirectory, collected_files: list):
            # Add files from current directory
            collected_files.extend(directory.children_files)
            # Recursively add files from subdirectories
            for sub_dir in directory.children_dirs:
                _collect_files_recursive(sub_dir, collected_files)

        # Use helper method to collect all files
        _collect_files_recursive(target_dir, result)
        
        # Sort once at the end
        result.sort(key=MediaFile.get_date, reverse=True)
        return result

    def get_only_here(self, other_media_set: "MediaSet", media_list: list = None) -> list:
        """
        Retourne les MediaFile présents uniquement dans ce MediaSet (parmi media_list si précisé), triés par date décroissante.
        """
        if media_list is None:
            media_list = self.media_file_list
        _, uniques = MediaSetComparator.cmp(self, other_media_set)
        # Applatit la liste si besoin
        if uniques and isinstance(uniques[0], list):
            flat_uniques = list(chain.from_iterable(uniques))
        else:
            flat_uniques = uniques
        uniques_set = set(flat_uniques)
        filtered = [m for m in media_list if m in uniques_set]
        filtered.sort(key=MediaFile.get_date, reverse=True)
        return filtered

    def get_in_both(self, other_media_set: "MediaSet", media_list: list = None) -> list:
        """
        Retourne les MediaFile présents dans les deux MediaSet (parmi media_list si précisé), triés par date décroissante.
        """
        if media_list is None:
            media_list = self.media_file_list
        commons, _ = MediaSetComparator.cmp(self, other_media_set)
        if commons and isinstance(commons[0], list):
            flat_commons = list(chain.from_iterable(commons))
        else:
            flat_commons = commons
        commons_set = set(flat_commons)
        filtered = [m for m in media_list if m in commons_set]
        filtered.sort(key=MediaFile.get_date, reverse=True)
        return filtered

    def synchronize_signatures(self, other_media_set: "MediaSet") -> None:
        """
        Synchronize signatures between two media sets based on system_id.
        For each media file in this set that has a signature, copy it to the corresponding
        media file in other_media_set that has the same system_id.
        Then do the same in the other direction.
        """
        # First direction: this -> other
        for media_file in self.media_file_list:
            if media_file.file_desc.system_id is not None and media_file.metadata[SIGNATURE].value is not None:
                # Use the index to find files with the same system_id in other_media_set
                other_media_list = other_media_set.indexer.system_id_map.get(media_file.file_desc.system_id, [])
                for other_media in other_media_list:
                    if other_media.metadata[SIGNATURE].value is None:
                        other_media.metadata[SIGNATURE] = media_file.metadata[SIGNATURE]
                        # Reindex the file in other_media_set
                        other_media_set.indexer.add_media_file(other_media)

        # Second direction: other -> this
        for other_media in other_media_set.media_file_list:
            if other_media.file_desc.system_id is not None and other_media.metadata[SIGNATURE].value is not None:
                # Use the index to find files with the same system_id in this set
                media_file_list = self.indexer.system_id_map.get(other_media.file_desc.system_id, [])
                for media_file in media_file_list:
                    if media_file.metadata[SIGNATURE].value is None:
                        media_file.metadata[SIGNATURE] = other_media.metadata[SIGNATURE]
                        # Reindex the file in this set
                        self.indexer.add_media_file(media_file)

    def synchronize_metadata(self, other_media_set: "MediaSet") -> None:
        """
        Synchronize internal metadata between two media sets based on system_id.
        For each media file in this set that has internal metadata, copy it to the corresponding
        media file in other_media_set that has the same system_id.
        Then do the same in the other direction.
        """
        for media_file in self.media_file_list:
            if media_file.file_desc.system_id is not None and media_file.metadata[INTERNAL].value is not None:
                other_media_list = other_media_set.indexer.system_id_map.get(media_file.file_desc.system_id, [])
                for other_media in other_media_list:
                    if other_media.metadata[INTERNAL].value is None:
                        other_media.metadata[INTERNAL] = media_file.metadata[INTERNAL]
                        other_media_set.indexer.add_media_file(other_media)

        for other_media in other_media_set.media_file_list:
            if other_media.file_desc.system_id is not None and other_media.metadata[INTERNAL].value is not None:
                media_file_list = self.indexer.system_id_map.get(other_media.file_desc.system_id, [])
                for media_file in media_file_list:
                    if media_file.metadata[INTERNAL].value is None:
                        media_file.metadata[INTERNAL] = other_media.metadata[INTERNAL]
                        self.indexer.add_media_file(media_file)

    def move_to_trash(self, media_file: MediaFile) -> bool:
        """Move a file to the trash directory."""
        trash_dir_path = os.path.join(self.root_path, ".cfm-trash")
        os.makedirs(trash_dir_path, exist_ok=True)
        if ".cfm-trash" not in self.media_dir_list:
            self.media_dir_list[".cfm-trash"] = MediaDirectory(trash_dir_path, None, self)
        parent_id = media_file.parent_dir.id if media_file.parent_dir else "root"
        new_filename = f"{parent_id}-{media_file.file_desc.name}"
        new_path = os.path.join(trash_dir_path, new_filename)
        try:
            self.unregister_file(media_file)
            if not media_file.move_to(new_path):
                return False
            media_file.parent_dir = self.media_dir_list[".cfm-trash"]
            self.register_file(media_file)
            return True
        except Exception as e:
            LOGGER.info(f"Failed to move file {media_file.get_path()} to trash: {str(e)}")
            return False
