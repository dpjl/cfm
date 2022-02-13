import os
from datetime import datetime
from pathlib import Path

from humanize import naturalsize
from pyzipper import zipfile
from typing import List, Dict, Iterable

from camerafile.core.Constants import MANAGED_TYPE, INTERNAL, SIGNATURE, CFM_CAMERA_MODEL, THUMBNAIL, ARCHIVE_TYPE
from camerafile.core.Logging import Logger
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.MediaSetDump import MediaSetDump
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.fileaccess.StandardFileAccess import StandardFileAccess
from camerafile.fileaccess.ZipFileAccess import ZipFileAccess
from camerafile.tools.FaceRecognition import FaceRecognition

LOGGER = Logger(__name__)


class MediaSet:
    CFM_TRASH = ".cfm-trash.zip"

    def __init__(self, path: str):
        self.root_path = Path(path).resolve()
        self.name = self.root_path.name
        self.output_directory = OutputDirectory(self.root_path)
        self.trash_file = (Path(self.root_path) / self.CFM_TRASH).as_posix()
        if not MediaSetDump.get_instance(self.output_directory).load(self):
            self.media_file_list = []
            self.media_dir_list = {}
            self.date_size_map = {}
            self.date_sig_map = {}
            self.id_map = {}
            self.filename_map: Dict[str, MediaFile] = {}
        self.face_rec = FaceRecognition(self, self.output_directory)
        self.initialize_file_and_dir_list()
        self.delete_not_existing_media()

    def delete_not_existing_media(self):
        deleted = []
        for media_file in self:
            if not media_file.exists:
                deleted.append(media_file.path)
                self.remove_file(media_file)
        if len(deleted) != 0:
            deleted_file = self.output_directory.save_list(deleted, "deleted-files.json")
            LOGGER.info_indent("{l1} files detected as deleted [{file}]".format(l1=len(deleted), file=deleted_file))

    @staticmethod
    def load_media_set(media_set_path):
        LOGGER.write_title_2(str(media_set_path), "Opening media directory")
        return MediaSet(media_set_path)

    def __del__(self):
        self.close_database()

    def __str__(self):
        return str(self.root_path)

    def __len__(self):
        return len(self.media_file_list)

    def __iter__(self) -> MediaFile:
        for media_file in self.media_file_list:
            yield media_file

    def get_trash_file(self):
        return self.trash_file

    def get_date_sorted_media_list(self):
        self.media_file_list.sort(key=MediaFile.get_date)
        return self.media_file_list

    def train(self):
        self.face_rec.add_training_data()
        self.face_rec.save_training_data()
        self.face_rec.train()

    def get_file_from_path(self, file_path):
        for media_file in self.media_file_list:
            if str(media_file.path).lower() == str(file_path).lower():
                return media_file

    def save_on_disk(self):
        MediaSetDatabase.get_instance(self.output_directory).save(self)
        MediaSetDump.get_instance(self.output_directory).save(self)

    def intermediate_save_database(self, media_file_list: Iterable[MediaFile]):
        MediaSetDatabase.get_instance(self.output_directory).save(media_file_list, log=False)

    def close_database(self):
        MediaSetDatabase.get_instance(self.output_directory).close()

    def add_file(self, media_file: MediaFile):
        self.media_file_list.append(media_file)
        self.id_map[media_file.file_access.id] = media_file
        self.filename_map[media_file.relative_path] = media_file
        self.add_to_date_size_name_map(media_file)
        self.add_to_date_size_sig_map(media_file)

    def remove_file(self, media_file: MediaFile):
        self.remove_from_date_size_sig_map(media_file)
        self.remove_from_date_size_name_map(media_file)
        del self.filename_map[media_file.relative_path]
        del self.id_map[media_file.file_access.id]
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

    def add_to_date_size_sig_map(self, media_file: MediaFile):
        date = media_file.get_exif_date()
        sig = media_file.get_signature()
        if date is not None and sig is not None:
            self.add_to_x_y_map(self.date_sig_map, date, sig, media_file)

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
        # vérifier si la signature devrait être calculée (possibly already exist)
        if item.get_signature() is not None:
            if self.exist_in_x_y_map(self.date_sig_map, date, item.get_signature()):
                return True
        return False

    def get_possibly_duplicates(self):
        result = []
        for date in self.date_size_map:
            if len(self.date_size_map[date]) > 1:
                for file_size in self.date_size_map[date]:
                    result.append(self.date_size_map[date][file_size][0])
        return result

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
                if len(self.date_size_map[date]) == 1:
                    file_size, _ = self.get_first_element(self.date_size_map[date])
                    if file_size not in media_set2.date_size_map[date]:
                        result.append(self.date_size_map[date][file_size][0])
                if len(media_set2.date_size_map[date]) == 1:
                    file_size, _ = self.get_first_element(media_set2.date_size_map[date])
                    if file_size not in self.date_size_map[date]:
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

    def duplicates(self):
        n_copy = {}
        for date, file_size_map in self.date_size_map.items():
            if len(file_size_map) == 1:
                _, media_list = self.get_first_element(file_size_map)
                self.add_duplicates_to_n_copy(n_copy, media_list)
            else:
                for media_list in self.date_sig_map[date].values():
                    self.add_duplicates_to_n_copy(n_copy, media_list)
        return n_copy

    @staticmethod
    def propagate_metadata_value(metadata_name, media_file_list: List[MediaFile]):
        if len(media_file_list) > 1:
            not_empty_metadata_value = None
            for media_file in media_file_list:
                current_metadata_value = media_file.metadata[metadata_name].value
                if current_metadata_value is not None:
                    not_empty_metadata_value = current_metadata_value
            if not_empty_metadata_value is not None:
                for media_file in media_file_list:
                    current_metadata_value = media_file.metadata[metadata_name].value
                    if current_metadata_value is None:
                        media_file.metadata[metadata_name].value = not_empty_metadata_value

    def propagate_sig_to_duplicates(self):
        for date in self.date_size_map:
            for file_size in self.date_size_map[date]:
                self.propagate_metadata_value(SIGNATURE, self.date_size_map[date][file_size])

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
            media_date = datetime.strptime(media_file.metadata[INTERNAL].get_last_modification_date(),
                                           '%Y/%m/%d %H:%M:%S.%f')
            if date is None or media_date < date:
                date = media_date
                media_result = media_file
        return media_result

    def get_file_list(self, ext=None, cm=None):
        result = []
        for media_file in self.media_file_list:
            if self.filter(media_file, ext, cm):
                result.append(media_file)
        return result

    @staticmethod
    def filter(media_file: MediaFile, ext_filter, cm_filter):
        if ext_filter is not None:
            if media_file.file_access.extension not in ext_filter:
                return False

        cfm_camera_model = media_file.metadata[CFM_CAMERA_MODEL]
        internal_md = media_file.metadata[INTERNAL]

        if cm_filter == "known":
            if internal_md.get_cm() is None:
                return False

        elif cm_filter == "unknown":
            if internal_md.get_cm() is not None or cfm_camera_model.value is not None:
                return False

        elif cm_filter == "recovered":
            if internal_md.get_cm() is not None or cfm_camera_model.value is None:
                return False

        return True

    def create_media_dir_parent(self, dir_or_file_path):
        parent = Path(dir_or_file_path).parent.as_posix()
        if parent not in self.media_dir_list:
            new_media_dir = MediaDirectory(parent, self.create_media_dir_parent(parent), self)
            self.media_dir_list[parent] = new_media_dir
        return self.media_dir_list[parent]

    def initialize_file_and_dir_list(self):
        not_loaded_files = self.update_from_disk()
        LOGGER.info_indent("{l1} media files loaded media set dump".format(l1=len(self.filename_map)), prof=2)
        root_dir = MediaDirectory(self.root_path.as_posix(), None, self)
        self.media_dir_list[self.root_path.as_posix()] = root_dir
        not_loaded_files = MediaSetDatabase.get_instance(self.output_directory).load_all_files(self, not_loaded_files)
        self.init_new_media_files(not_loaded_files)
        MediaSetDatabase.get_instance(self.output_directory).load_all_thumbnails(self)

    def init_new_media_files(self, found_files_map: Dict[str, FileAccess]):
        LOGGER.start("{nb_file} new files that are not already in dump or db", 1000, prof=2)
        number_of_files = 0
        LOGGER.update(nb_file=number_of_files)
        for file_path, file_access in found_files_map.items():
            media_dir = self.create_media_dir_parent(file_access.path)
            new_media_file = MediaFile(file_access, media_dir, self)
            self.add_file(new_media_file)
            number_of_files += 1
            LOGGER.update(nb_file=number_of_files)
        LOGGER.end(nb_file=number_of_files)

    def import_zip_file(self, zip_file_path, file_map: Dict[str, FileAccess], ignored_files: List[str]):
        size = 0
        nb_mfiles = 0
        with zipfile.ZipFile(zip_file_path) as zip_file:
            number_of_files = 0
            for file_info in zip_file.filelist:
                file_name = file_info.filename
                if not file_name.endswith('/'):
                    extension = os.path.splitext(file_name)[1].lower()
                    number_of_files += 1
                    if extension in MANAGED_TYPE:
                        relative_path = (Path(zip_file_path) / file_name).relative_to(self.root_path).as_posix()
                        nb_mfiles += 1
                        if relative_path not in self.filename_map:
                            file_size = file_info.file_size
                            size += file_size
                            zip_file_access = ZipFileAccess(zip_file_path, file_name, file_size)
                            file_map[zip_file_access.path] = zip_file_access
                        else:
                            size += self.filename_map[relative_path].file_access.file_size
                            self.filename_map[relative_path].exists = True
                    else:
                        ignored_files.append(str(self.root_path / zip_file_path))
        return number_of_files, nb_mfiles, size

    def update_from_disk(self):

        for media_file in self:
            media_file.exists = False

        nb_files = 0
        nb_sfiles = 0
        nb_zfiles = 0
        nb_m_files = 0
        nb_zip = 0
        total_size = 0
        LOGGER.start(
            "{nb_file} files found ({nb_sfiles} standard, {nb_zfiles} zipped in {nb_zip} archive(s)) [{size}]")
        LOGGER.update(nb_file=nb_files, nb_sfiles=nb_sfiles, nb_zfiles=nb_zfiles, nb_zip=nb_zip,
                      size=naturalsize(total_size))
        not_loaded_files: Dict[str, FileAccess] = {}
        ignored_files: List[str] = []
        for path, dir_list, file_list in os.walk(self.root_path, topdown=True):
            for file in file_list:
                file_path = Path(path) / file
                extension = os.path.splitext(file)[1].lower()
                if extension in MANAGED_TYPE:
                    relative_path = file_path.relative_to(self.root_path).as_posix()
                    if relative_path not in self.filename_map:
                        file_size = file_path.stat().st_size
                        file_access = StandardFileAccess(file_path, file_size)
                        not_loaded_files[file_access.path] = file_access
                    else:
                        self.filename_map[relative_path].exists = True
                        file_size = self.filename_map[relative_path].file_access.file_size
                    nb_files += 1
                    nb_m_files += 1
                    nb_sfiles += 1
                    total_size += file_size
                elif extension in ARCHIVE_TYPE:
                    n_files, n_mfiles, size = self.import_zip_file(file_path, not_loaded_files, ignored_files)
                    nb_zfiles += n_files
                    nb_m_files += n_mfiles
                    nb_files += n_files
                    total_size += size
                    nb_zip += 1
                else:
                    ignored_files.append(file_path)
                    nb_files += 1
                    nb_sfiles += 1
            LOGGER.update(nb_file=nb_files, nb_sfiles=nb_sfiles, nb_zfiles=nb_zfiles, nb_zip=nb_zip,
                          size=naturalsize(total_size))

        LOGGER.end(nb_file=nb_files, nb_sfiles=nb_sfiles, nb_zfiles=nb_zfiles, nb_zip=nb_zip,
                   size=naturalsize(total_size))

        saved_file = self.output_directory.save_list(ignored_files, "ignored-files.json")
        LOGGER.info_indent("{l1} files ignored [{saved}]".format(l1=len(ignored_files), saved=saved_file))
        LOGGER.info_indent("{l1} detected as media files".format(l1=nb_m_files))

        return not_loaded_files


def get_files_with_thumbnail_errors(self):
    error_files = []
    for media_file in self:
        if media_file.metadata[THUMBNAIL].error:
            error_files.append(media_file.file_access.path)
    return error_files
