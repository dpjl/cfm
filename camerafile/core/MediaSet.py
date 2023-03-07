import os
from pathlib import Path
from typing import List, Dict, Iterable

import dhash
from pyzipper import zipfile

from camerafile.console.FilesSummary import FilesSummary
from camerafile.core.Constants import MANAGED_TYPE, INTERNAL, SIGNATURE, CFM_CAMERA_MODEL, ARCHIVE_TYPE
from camerafile.core.Logging import Logger
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.MediaSetDump import MediaSetDump
from camerafile.core.MediaSetState import MediaSetState
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.fileaccess.ZipFileDescription import ZipFileDescription
from camerafile.mdtools.MdConstants import MetadataNames

LOGGER = Logger(__name__)


class MediaSet:
    CFM_TRASH = ".cfm-trash.zip"

    def __init__(self, path: str, org_format: str = None, db_file=None):
        root_path = Path(path).resolve()
        self.root_path = root_path.as_posix()
        self.name = root_path.name
        self.media_file_list = []
        self.media_dir_list = {}
        self.date_size_map = {}
        self.date_sig_map = {}
        self.id_map = {}
        self.filename_map: Dict[str, MediaFile] = {}

        self.db_file = db_file
        self.state: MediaSetState = MediaSetState(self.root_path)
        self.initialize_file_and_dir_list()
        self.delete_not_existing_media()
        self.state.load_format(org_format)
        self.state.load_metadata_to_read()

        LOGGER.debug("New MediaSet object created: " + str(id(self)))

    @staticmethod
    def load_media_set(path: str, org_format: str = None, db_file=None) -> "MediaSet":
        LOGGER.write_title_2(str(path), "Opening media directory")
        loaded = MediaSetDump.get(OutputDirectory.get(path)).load()
        if loaded:
            # root object is duplicated and then differs from mediaFiles' parent references. Replace it.
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

    def __iter__(self) -> MediaFile:
        for media_file in self.media_file_list:
            yield media_file

    def __getitem__(self, file_id) -> MediaFile:
        return self.id_map[file_id]

    def get_trash_file(self):
        return self.root_path + os.sep + self.CFM_TRASH

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

    def get_date_sorted_media_list(self):
        self.media_file_list.sort(key=MediaFile.get_date)
        return self.media_file_list

    def get_file_from_path(self, file_path):
        for media_file in self.media_file_list:
            if str(media_file.path).lower() == str(file_path).lower():
                return media_file

    def save_on_disk(self):
        MediaSetDatabase.get(OutputDirectory.get(self.root_path), self.db_file).save(self)
        MediaSetDump.get(OutputDirectory.get(self.root_path)).save(self)

    def intermediate_save_database(self, media_file_list: Iterable[MediaFile]):
        MediaSetDatabase.get(OutputDirectory.get(self.root_path), self.db_file).save(media_file_list, log=False)

    def close_database(self):
        MediaSetDatabase.get(OutputDirectory.get(self.root_path), self.db_file).close()

    def add_file(self, media_file: MediaFile):
        self.media_file_list.append(media_file)
        self.id_map[media_file.file_desc.id] = media_file
        self.filename_map[media_file.get_path()] = media_file
        self.add_to_date_size_name_map(media_file)
        self.add_to_date_sig_map(media_file)

    def remove_file(self, media_file: MediaFile):
        self.remove_from_date_size_sig_map(media_file)
        self.remove_from_date_size_name_map(media_file)
        del self.filename_map[media_file.get_path()]
        del self.id_map[media_file.file_desc.id]
        self.media_file_list.remove(media_file)

    def get_media(self, media_id):
        if media_id in self.id_map:
            return self.id_map[media_id]
        return None

    def remove_from_date_size_name_map(self, media_file: MediaFile):
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date is not None:
            self.remove_from_x_y_map(self.date_size_map, date, size, media_file)

    def remove_from_date_size_sig_map(self, media_file: MediaFile):
        date = media_file.get_exif_date()
        sig = media_file.get_signature()
        if date is not None and sig is not None:
            self.remove_from_x_y_map(self.date_sig_map, date, sig, media_file)

    @staticmethod
    def remove_from_x_y_map(map_to_update, x, y, media_file):
        map_to_update[x][y].remove(media_file)
        if len(map_to_update[x][y]) == 0:
            del map_to_update[x][y]
        if len(map_to_update[x]) == 0:
            del map_to_update[x]

    def add_to_date_size_name_map(self, media_file: MediaFile):
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date is not None:
            self.add_to_x_y_map(self.date_size_map, date, size, media_file)

    def add_to_date_sig_map(self, media_file: MediaFile):
        date = media_file.get_exif_date()
        sig = media_file.get_signature()
        if date is not None and sig is not None:
            # self.add_to_x_y_map(self.date_sig_map, date, sig, media_file)
            if date not in self.date_sig_map:
                self.date_sig_map[date] = {}
            for existing_sig in self.date_sig_map[date].keys():
                if dhash.get_num_bits_different(sig, existing_sig) < 4:
                    if media_file not in self.date_sig_map[date][existing_sig]:
                        self.date_sig_map[date][existing_sig].append(media_file)
                    return
            self.date_sig_map[date][sig] = [media_file]

    @staticmethod
    def add_to_x_y_map(map_to_update, x, y, media_file):
        if x not in map_to_update:
            map_to_update[x] = {}
        if y not in map_to_update[x]:
            map_to_update[x][y] = []
        if media_file not in map_to_update[x][y]:
            map_to_update[x][y].append(media_file)

    @staticmethod
    def exist_in_x_y_map(map_to_inspect, x, y):
        if x is not None and x in map_to_inspect:
            if y is not None and y in map_to_inspect[x]:
                return True
        return False

    def contains(self, item: MediaFile):
        date = item.get_exif_date()
        file_size = item.get_file_size()
        if self.exist_in_x_y_map(self.date_size_map, date, file_size):
            return True

        # Question:
        # Si même date exactement à la milliseconde près, et hauteur et largeur identiques
        # (mais tailles des fichiers différentes ?), on pourrait considérer que ce sont les mêmes images ?
        # Cela évituerait de calculer la signature
        # Cas des photos de l'iphone exportées par deux outils différents
        # ---

        # vérifier si la signature devrait être calculée (possibly already exist) ?
        if item.get_signature() is not None:
            # if self.exist_in_x_y_map(self.date_sig_map, date, item.get_signature()):
            #    return True
            if date is not None and date in self.date_sig_map:
                for sig in self.date_sig_map[date]:
                    if dhash.get_num_bits_different(sig, item.get_signature()) < 4:
                        return True
            return False

        return False

    def get_possibly_duplicates(self):
        result = []
        for date in self.date_size_map:
            if len(self.date_size_map[date]) > 1:
                for file_size in self.date_size_map[date]:
                    result.append(self.date_size_map[date][file_size][0])
        return result

    def duplicates(self):
        n_copy = {}
        for date, size_map in self.date_size_map.items():
            if len(size_map) == 1:
                _, media_list = self.get_first_element(size_map)
                self.add_duplicates_to_n_copy(n_copy, media_list)
            else:
                # if date not in self.date_size_map:
                #    raise Exception()
                for media_list in self.date_sig_map[date].values():
                    self.add_duplicates_to_n_copy(n_copy, media_list)
        return n_copy

    @staticmethod
    def add_to_duplicates_map(dup_map, media_list: List[MediaFile]):
        nb_copy = len(media_list)
        media_list.sort(key=lambda x: x.file_desc.name)
        group_id = media_list[0].file_desc.name
        dup_id = 1
        for media_file in media_list:
            dup_map[media_file] = (nb_copy, group_id, dup_id)
            dup_id += 1

    def duplicates_map(self):
        dup_map = {}
        for date, size_map in self.date_size_map.items():
            if len(size_map) == 1:
                _, media_list = self.get_first_element(size_map)
                self.add_to_duplicates_map(dup_map, media_list)
            else:
                for media_list in self.date_sig_map[date].values():
                    self.add_to_duplicates_map(dup_map, media_list)
        return dup_map

    def get_duplicates_report(self, duplicates):
        str_list = ["All media files: " + str(len(self.media_file_list)),
                    "Distinct elements: {distinct}".format(distinct=str(sum(map(len, duplicates.values()))))]
        for n_copy, media_list_list in sorted(duplicates.items()):
            str_list.append("%s elem. found %s times" % (len(media_list_list), n_copy))
        return str_list

    @staticmethod
    def get_first_element(dictionary):
        for key, value in dictionary.items():
            return key, value

    def get_possibly_already_exists(self, media_set2):
        result = []
        for date in self.date_size_map:
            if date in media_set2.date_size_map:
                if len(self.date_size_map[date]) > 1 or len(media_set2.date_size_map[date]) > 1:
                    for file_size in self.date_size_map[date]:
                        result.append(self.date_size_map[date][file_size][0])
                    for file_size in media_set2.date_size_map[date]:
                        result.append(media_set2.date_size_map[date][file_size][0])
        return result

    def get_copied_files(self):
        result = []
        for media_file in self.media_file_list:
            if media_file.is_copied_file():
                result.append(media_file)
        return result

    def cmp(self, other_media_set: "MediaSet"):
        in_both = []
        only_in_self = []
        for date in self.date_size_map:
            if len(self.date_size_map[date]) == 1:
                _, unique_media_list = self.get_first_element(self.date_size_map[date])
                if other_media_set.contains(unique_media_list[0]):
                    in_both.append(unique_media_list)
                else:
                    only_in_self.append(unique_media_list)
            else:
                for sig in self.date_sig_map[date]:
                    media_list = self.date_sig_map[date][sig]
                    if other_media_set.contains(media_list[0]):
                        in_both.append(media_list)
                    else:
                        only_in_self.append(media_list)
        return in_both, only_in_self

    @staticmethod
    def propagate_metadata_value(metadata_name, media_file_list: List[MediaFile]):
        not_empty_metadata_value = None
        if len(media_file_list) > 1:
            for media_file in media_file_list:
                current_metadata_value = media_file.metadata[metadata_name].value
                if current_metadata_value is not None:
                    not_empty_metadata_value = current_metadata_value
            if not_empty_metadata_value is not None:
                for media_file in media_file_list:
                    current_metadata_value = media_file.metadata[metadata_name].value
                    if current_metadata_value is None:
                        media_file.metadata[metadata_name].value = not_empty_metadata_value
        return not_empty_metadata_value is not None

    def propagate_sig_to_duplicates(self):
        for date in self.date_size_map:
            for file_size in self.date_size_map[date]:
                if len(self.date_size_map[date][file_size]) > 1:
                    if self.propagate_metadata_value(SIGNATURE, self.date_size_map[date][file_size]):
                        for media_file in self.date_size_map[date][file_size]:
                            self.add_to_date_sig_map(media_file)

    def propagate_cm_to_duplicates(self):
        for date in self.date_size_map:
            for file_size in self.date_size_map[date]:
                self.propagate_metadata_value(CFM_CAMERA_MODEL, self.date_size_map[date][file_size])

        for date in self.date_sig_map:
            for sig in self.date_sig_map[date]:
                self.propagate_metadata_value(CFM_CAMERA_MODEL, self.date_sig_map[date][sig])

    @staticmethod
    def add_duplicates_to_n_copy(n_copy, media_list: List[MediaFile]):
        nb_copy = len(media_list)
        if nb_copy not in n_copy:
            n_copy[nb_copy] = []
        n_copy[nb_copy] += [media_list]

    @staticmethod
    def get_oldest_modified_file(media_list: List[MediaFile]):
        date = None
        media_result = None
        for media_file in media_list:
            media_date = media_file.get_last_modification_date()
            if date is None or media_date < date:
                date = media_date
                media_result = media_file
        return media_result, date

    def get_file_list(self, ext=None, cm=None):
        result = []
        for media_file in self.media_file_list:
            if self.filter(media_file, ext, cm):
                result.append(media_file)
        return result

    @staticmethod
    def filter(media_file: MediaFile, ext_filter, cm_filter):
        if ext_filter is not None:
            if media_file.file_desc.extension not in ext_filter:
                return False

        cfm_camera_model = media_file.metadata[CFM_CAMERA_MODEL]
        internal_md = media_file.metadata[INTERNAL]

        if cm_filter == "known":
            if internal_md.get_md_value(MetadataNames.MODEL) is None:
                return False

        elif cm_filter == "unknown":
            if internal_md.get_md_value(MetadataNames.MODEL) is not None or cfm_camera_model.value is not None:
                return False

        elif cm_filter == "recovered":
            if internal_md.get_md_value(MetadataNames.MODEL) is not None or cfm_camera_model.value is None:
                return False

        return True

    def create_media_dir_parent(self, dir_or_file_path):
        parent = Path(dir_or_file_path).parent.as_posix()
        if parent not in self.media_dir_list:
            new_media_dir = MediaDirectory(parent, self.create_media_dir_parent(parent), self)
            self.media_dir_list[parent] = new_media_dir
        return self.media_dir_list[parent]

    def initialize_file_and_dir_list(self, root_path=None):
        if root_path is None:
            root_path = self.root_path
        not_loaded_files = self.update_from_disk(root_path)
        dump_file = MediaSetDump.get(OutputDirectory.get(self.root_path)).dump_file
        log_content = "{l1} media files loaded from dump {df}".format(l1=len(self.filename_map),
                                                                      df=dump_file)
        LOGGER.info_indent(log_content=log_content, prof=2)
        self.media_dir_list["."] = MediaDirectory(".", None, self)
        not_loaded_files = MediaSetDatabase.get(OutputDirectory.get(self.root_path),
                                                self.db_file).load_all_files(self, not_loaded_files)
        self.init_new_media_files(not_loaded_files)
        MediaSetDatabase.get(OutputDirectory.get(self.root_path), self.db_file).load_all_thumbnails(self)

    def init_new_media_files(self, found_files_map: Dict[str, FileDescription]):
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

    def update_from_disk(self, root_path=None):

        if root_path is None:
            root_path = self.root_path

        for media_file in self:
            media_file.exists = False

        files_summary = FilesSummary()
        not_loaded_files: Dict[str, FileDescription] = {}
        ignored_files: List[str] = []

        for path, dir_list, file_list in os.walk(root_path, topdown=True):
            for file_name in file_list:
                file_path = Path(path) / file_name
                extension = os.path.splitext(file_name)[1].lower()

                if extension in MANAGED_TYPE and not self.state.should_be_ignored(file_name):
                    file_size = self.register_new_standard_file(file_path, not_loaded_files)
                    files_summary.increment(all_files=1, managed=1, standard=1, size=file_size)
                elif extension in ARCHIVE_TYPE:
                    self.load_zip_archive(file_path, not_loaded_files, ignored_files, files_summary)
                else:
                    files_summary.increment(all_files=1, standard=1)
                    ignored_files.append(file_path.as_posix())
                    relative_path = file_path.relative_to(self.root_path).as_posix()
                    if relative_path in self.filename_map:
                        self.remove_file(self.filename_map[relative_path])
            files_summary.log()
        files_summary.end_logging()

        saved_file = OutputDirectory.get(self.root_path).save_list(ignored_files, "ignored-files.json")
        LOGGER.info_indent("{l1} files ignored [{saved}]".format(l1=len(ignored_files), saved=saved_file))
        LOGGER.info_indent("{l1} detected as media files".format(l1=files_summary.managed))

        return not_loaded_files

    def load_zip_archive(self, zip_file_path, file_map: Dict[str, FileDescription], ignored_files: List[str],
                         files_summary: FilesSummary):

        files_summary.increment(archive=1)
        with zipfile.ZipFile(zip_file_path) as zip_file:
            for file_info in zip_file.filelist:
                file_name = file_info.filename
                if not file_name.endswith('/'):
                    extension = os.path.splitext(file_name)[1].lower()
                    files_summary.increment(all_files=1, zipped=1)

                    if extension in MANAGED_TYPE and not self.state.should_be_ignored(Path(file_name).name):
                        file_size = self.register_new_zipped_file(file_info, file_map, file_name, zip_file_path)
                        files_summary.increment(managed=1, size=file_size)
                    else:
                        ignored_files.append((Path(self.root_path) / zip_file_path).as_posix())

    def register_new_standard_file(self, file_path, not_loaded_files):
        relative_path = file_path.relative_to(self.root_path).as_posix()
        if relative_path not in self.filename_map:
            file_size = file_path.stat().st_size
            file_desc = StandardFileDescription(relative_path, file_size)
            not_loaded_files[file_desc.relative_path] = file_desc
        else:
            self.filename_map[relative_path].exists = True
            file_size = self.filename_map[relative_path].file_desc.file_size
        return file_size

    def register_new_zipped_file(self, file_info, file_map, file_name, zip_file_path):
        relative_path = (Path(zip_file_path) / file_name).relative_to(self.root_path).as_posix()
        zip_relative_path = Path(zip_file_path).relative_to(self.root_path).as_posix()
        if relative_path not in self.filename_map:
            file_size = file_info.file_size
            zip_file_desc = ZipFileDescription(zip_relative_path, file_name, file_size)
            file_map[zip_file_desc.get_relative_path()] = zip_file_desc
        else:
            file_size = self.filename_map[relative_path].file_desc.file_size
            self.filename_map[relative_path].exists = True
        return file_size
