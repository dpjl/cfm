import os
from datetime import datetime
from pathlib import Path

from pyzipper import zipfile

from camerafile.core.Constants import MANAGED_TYPE, INTERNAL, SIGNATURE, CFM_CAMERA_MODEL, THUMBNAIL, ARCHIVE_TYPE
from camerafile.tools.FaceRecognition import FaceRecognition
from camerafile.core.Logging import Logger
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.OutputDirectory import OutputDirectory

LOGGER = Logger(__name__)


class MediaSet:

    def __init__(self, path):
        self.root_path = Path(path).resolve()
        self.name = self.root_path.name
        self.output_directory = OutputDirectory(self.root_path)
        self.face_rec = FaceRecognition(self, self.output_directory)
        self.media_file_list = []
        self.media_dir_list = {}
        self.date_size_name_map = {}
        self.date_size_sig_map = {}
        self.date_model_size_map = {}
        self.id_map = {}
        self.database = MediaSetDatabase(self.output_directory)
        self.initialize_file_and_dir_list()

    def __del__(self):
        self.save_database()
        self.close_database()

    def __str__(self):
        return self.root_path

    def __len__(self):
        return len(self.media_file_list)

    def __iter__(self):
        for media_file in self.media_file_list:
            yield media_file

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

    def save_database(self):
        if self.database is not None:
            self.database.save(self)

    def close_database(self):
        if self.database is not None:
            self.database.close()
            self.database = None

    def add_file(self, media_file):
        self.media_file_list.append(media_file)
        self.id_map[media_file.id] = media_file
        self.update_date_size_name_map(media_file)
        self.update_date_size_sig_map(media_file)
        self.update_date_model_size_map(media_file)

    def remove_file(self, media_file):
        self.media_file_list.remove(media_file)

    def get_media(self, media_id):
        if media_id in self.id_map:
            return self.id_map[media_id]
        return None

    @staticmethod
    def update_x_y_z_map(map_to_update, x, y, z, media_file):
        if x not in map_to_update:
            map_to_update[x] = {}
        if y not in map_to_update[x]:
            map_to_update[x][y] = {}
        if z not in map_to_update[x][y]:
            map_to_update[x][y][z] = []
        if media_file not in map_to_update[x][y][z]:
            map_to_update[x][y][z].append(media_file)

    @staticmethod
    def exist_in_x_y_z_map(map_to_inspect, x, y, z):
        if x is not None and x in map_to_inspect:
            if y in map_to_inspect[x]:
                if z in map_to_inspect[x][y]:
                    return True

    def update_date_size_name_map(self, media_file):
        date = media_file.get_exif_date()
        dim = media_file.get_dimensions()
        filename = media_file.name
        if date is not None:
            self.update_x_y_z_map(self.date_size_name_map, date, dim, filename, media_file)

    def update_date_size_sig_map(self, media_file):
        date = media_file.get_exif_date()
        dim = media_file.get_dimensions()
        sig = media_file.get_signature()
        if date is not None and sig is not None:
            self.update_x_y_z_map(self.date_size_sig_map, date, dim, sig, media_file)

    def update_date_model_size_map(self, media_file):
        date = media_file.get_exif_date()
        model = media_file.get_camera_model()
        dim = media_file.get_dimensions()
        if date is not None:
            self.update_x_y_z_map(self.date_model_size_map, date, model, dim, media_file)

    def contains(self, item):
        date = item.get_exif_date()
        dimensions = item.get_dimensions()
        if self.exist_in_x_y_z_map(self.date_size_name_map, date, dimensions, item.name):
            return True
        # vérifier si la signature devrait être calculée (possibly already exist)
        if item.get_signature() is not None:
            if self.exist_in_x_y_z_map(self.date_size_sig_map, date, dimensions, item.get_signature()):
                return True
        return False

    def get_possibly_duplicates(self):
        result = []
        for date in self.date_size_name_map:
            microseconds = 0
            if date is not None:
                microseconds = datetime.strptime(date, '%Y/%m/%d %H:%M:%S.%f').microsecond
            if microseconds == 0:
                for size in self.date_size_name_map[date]:
                    if len(self.date_size_name_map[date][size]) > 1:
                        for filename in self.date_size_name_map[date][size]:
                            result.append(self.date_size_name_map[date][size][filename][0])
        return result

    @staticmethod
    def get_first_element(dictionary):
        for key, value in dictionary.items():
            return key, value

    def get_possibly_already_exists(self, media_set2):
        result = []
        for date in self.date_size_name_map:
            for size in self.date_size_name_map[date]:
                if date in media_set2.date_size_name_map and size in media_set2.date_size_name_map[date]:
                    if len(self.date_size_name_map[date][size]) == 1:
                        filename1, _ = self.get_first_element(self.date_size_name_map[date][size])
                        if filename1 not in media_set2.date_size_name_map[date][size]:
                            result.append(self.date_size_name_map[date][size][filename1][0])
                    if len(media_set2.date_size_name_map[date][size]) == 1:
                        filename1, _ = self.get_first_element(media_set2.date_size_name_map[date][size])
                        if filename1 not in self.date_size_name_map[date][size]:
                            result.append(media_set2.date_size_name_map[date][size][filename1][0])
        return result

    def get_copied_files(self):
        result = []
        for media_file in self.media_file_list:
            if media_file.is_copied_file():
                result.append(media_file)
        return result

    def cmp(self, other_media_set):
        in_both = []
        only_in_self = []
        for date in self.date_size_name_map:
            if self.get_microseconds(date) != 0:
                for size in self.date_size_name_map[date]:
                    media_list = self.get_media_list_from_date_and_size(date, size)
                    if other_media_set.contains(media_list[0]):
                        in_both.append(media_list)
                    else:
                        only_in_self.append(media_list)
            else:
                for size in self.date_size_name_map[date]:
                    if len(self.date_size_name_map[date][size]) == 1:
                        _, unique_media_list = self.get_first_element(self.date_size_name_map[date][size])
                        if other_media_set.contains(unique_media_list[0]):
                            in_both.append(unique_media_list)
                        else:
                            only_in_self.append(unique_media_list)
                    else:
                        for sig in self.date_size_sig_map[date][size]:
                            media_list = self.date_size_sig_map[date][size][sig]
                            if other_media_set.contains(media_list[0]):
                                in_both.append(media_list)
                            else:
                                only_in_self.append(media_list)
        return in_both, only_in_self

    def duplicates(self):
        n_copy = {}
        for date in self.date_size_name_map:
            if self.get_microseconds(date) != 0:
                for size in self.date_size_name_map[date]:
                    media_list = self.get_media_list_from_date_and_size(date, size)
                    self.add_duplicates_to_n_copy(n_copy, media_list)
            else:
                for size, filename_map in self.date_size_name_map[date].items():
                    if len(filename_map) == 1:
                        _, media_list = self.get_first_element(filename_map)
                        self.add_duplicates_to_n_copy(n_copy, media_list)
                    else:
                        for media_list in self.date_size_sig_map[date][size].values():
                            self.add_duplicates_to_n_copy(n_copy, media_list)
        return n_copy

    @staticmethod
    def propagate_metadata_value(metadata_name, media_file_list):
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
        for date in self.date_size_name_map:
            for size in self.date_size_name_map[date]:
                for filename in self.date_size_name_map[date][size]:
                    self.propagate_metadata_value(SIGNATURE, self.date_size_name_map[date][size][filename])

    def propagate_cm_to_duplicates(self):
        for date in self.date_size_name_map:
            for size in self.date_size_name_map[date]:
                for filename in self.date_size_name_map[date][size]:
                    self.propagate_metadata_value(CFM_CAMERA_MODEL, self.date_size_name_map[date][size][filename])

        for date in self.date_size_sig_map:
            for size in self.date_size_sig_map[date]:
                for sig in self.date_size_sig_map[date][size]:
                    self.propagate_metadata_value(CFM_CAMERA_MODEL, self.date_size_sig_map[date][size][sig])

    @staticmethod
    def get_microseconds(date):
        if date is not None:
            return datetime.strptime(date, '%Y/%m/%d %H:%M:%S.%f').microsecond
        return 0

    def get_media_list_from_date_and_size(self, date, size):
        media_list = []
        for filename in self.date_size_name_map[date][size]:
            media_list += self.date_size_name_map[date][size][filename]
        return media_list

    @staticmethod
    def add_duplicates_to_n_copy(n_copy, media_list):
        nb_copy = len(media_list)
        if nb_copy not in n_copy:
            n_copy[nb_copy] = []
        n_copy[nb_copy] += [media_list]

    @staticmethod
    def get_oldest_modified_file(media_list):
        date = None
        media_result = None
        for media_file in media_list:
            media_date = datetime.strptime(media_file.metadata[INTERNAL].get_last_modification_date(),
                                           '%Y/%m/%d %H:%M:%S.%f')
            if date is None or media_date < date:
                date = media_date
                media_result = media_file
        return media_result

    def unique_files_not_in_destination(self, new_media_set, copy_mode):
        result = []
        n_copy_list = self.duplicates()
        new_path_map = {}
        for n_copy in n_copy_list.values():
            for media_list in n_copy:
                media_file = self.get_oldest_modified_file(media_list)
                if not new_media_set.contains(media_file):
                    # _, new_path = media_file.get_destination_path(new_media_set)
                    _, new_path = media_file.get_organization_path(new_media_set, new_path_map)
                    new_path_map[new_path] = 0
                    result.append((media_file.file_access, new_path, copy_mode))
        return result

    def all_files_not_in_other_media_set(self, new_media_set):
        result = []
        for media_file in self:
            if not new_media_set.contains(media_file):
                if not media_file.file_access.is_in_trash():
                    result.append(media_file.file_access)
        return result

    def get_file_list(self, ext=None, cm=None):
        result = []
        for media_file in self.media_file_list:
            if self.filter(media_file, ext, cm):
                result.append(media_file)
        return result

    @staticmethod
    def filter(media_file, ext_filter, cm_filter):
        if ext_filter is not None:
            if media_file.extension not in ext_filter:
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
        file_map, zipped_file_map, ignored_files = self.list_all_files()
        saved_file = self.output_directory.save_list(ignored_files, "ignored-files.json")
        LOGGER.info_indent("{l1} files ignored [{saved}]".format(l1=len(ignored_files), saved=saved_file))
        LOGGER.info_indent("{l1} files detected as media file".format(l1=len(file_map)))
        root_dir = MediaDirectory(self.root_path.as_posix(), None, self)
        self.media_dir_list[self.root_path.as_posix()] = root_dir
        self.database.load_all_files(self, file_map, zipped_file_map)
        self.database.load_all_thumbnails(self)
        self.init_new_media_files(file_map)
        self.init_new_media_files(zipped_file_map, archive=1)

    def init_new_media_files(self, found_file_map, archive=0):
        if archive == 0:
            LOGGER.start_status_line("{nb_file} files are not in cache", 1000, prof=2)
        else:
            LOGGER.start_status_line("{nb_file} zipped files are not in cache", 1, prof=2)
        number_of_files = 0
        LOGGER.update_status_line(nb_file=number_of_files)
        for file_path, loaded in found_file_map.items():
            if not loaded:
                new_media_file = MediaFile(file_path, self.create_media_dir_parent(file_path), self, archive)
                self.add_file(new_media_file)
                number_of_files += 1
                LOGGER.update_status_line(nb_file=number_of_files)
        LOGGER.end_status_line(nb_file=number_of_files)

    @staticmethod
    def import_zip_file(zip_file_path, zipped_file_map):
        with zipfile.ZipFile(zip_file_path) as zip_file:
            number_of_files = 0
            for file_name in zip_file.namelist():
                if not file_name.endswith('/'):
                    file_path = Path(zip_file_path + "<~>" + file_name).as_posix()
                    zipped_file_map[file_path] = False
                    number_of_files += 1
        return number_of_files

    def list_all_files(self):
        # Use windows commands like dir /a-D /S /B D:\data\photos-all ?
        number_of_files = 0
        number_of_zip_files = 0
        LOGGER.start_status_line(
            "{nb_file} files found in directory and subdirectories ({nb_zip_files} inside zip files)")
        LOGGER.update_status_line(nb_file=number_of_files, nb_zip_files=number_of_zip_files)
        file_map = {}
        zipped_file_map = {}
        ignored_files = []
        for path, dir_list, file_list in os.walk(self.root_path, topdown=True):
            for file in file_list:
                number_of_files += 1
                extension = os.path.splitext(file)[1].lower()
                file_path = (Path(path) / file).as_posix()
                if extension in MANAGED_TYPE:
                    file_map[file_path] = False
                elif extension in ARCHIVE_TYPE:
                    number_of_zip_files += self.import_zip_file(file_path, zipped_file_map)
                else:
                    ignored_files.append(file_path)
            LOGGER.update_status_line(nb_file=number_of_files, nb_zip_files=number_of_zip_files)
        LOGGER.end_status_line(nb_file=number_of_files, nb_zip_files=number_of_zip_files)
        return file_map, zipped_file_map, ignored_files

    def get_files_with_thumbnail_errors(self):
        error_files = []
        for media_file in self:
            if media_file.metadata[THUMBNAIL].error:
                error_files.append(media_file.path)
        return error_files
