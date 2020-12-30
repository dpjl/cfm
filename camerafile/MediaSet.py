import os
from datetime import datetime
from pathlib import Path

from camerafile.Constants import TYPE
from camerafile.FaceRecognition import FaceRecognition
from camerafile.MediaDirectory import MediaDirectory
from camerafile.MediaFile import MediaFile
from camerafile.MediaSetDatabase import MediaSetDatabase
from camerafile.Metadata import CAMERA_MODEL, WIDTH, HEIGHT, DATE, SIGNATURE
from camerafile.Metadata import Metadata
from camerafile.OutputDirectory import OutputDirectory


class MediaSet:

    def __init__(self, path, progress_signal=None):
        self.root_path = Path(path).resolve()
        self.name = self.root_path.name
        self.output_directory = OutputDirectory(self.root_path)
        self.media_file_list = []
        self.media_dir_list = {}
        self.date_and_sig_map = {}
        self.date_and_name_map = {}
        self.database = MediaSetDatabase(self.output_directory)
        self.initialize_file_and_dir_list(progress_signal)
        self.face_rec = FaceRecognition(self)

    def __del__(self):
        self.save_database()
        self.close_database()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.save_database()
        # pourquoi est-ce plus lent en utilisant un enter/exit plutôt qu'un init/del ??
        pass

    def train(self):
        self.face_rec.add_training_data()
        self.face_rec.save_training_data()
        self.face_rec.train()

    def get_file_from_path(self, file_path):
        for media_file in self.media_file_list:
            if str(media_file.path).lower() == str(file_path).lower():
                return media_file

    def add_size_to_filename(self, file_path):
        media_file = self.get_file_from_path(file_path)
        width = media_file.metadata.get_value(WIDTH)
        height = media_file.metadata.get_value(HEIGHT)
        media_file.add_suffix_to_filename("[" + str(width) + "x" + str(height) + "]")

    def add_date_to_filename(self, file_path):
        media_file = self.get_file_from_path(file_path)
        date = datetime.strptime(media_file.metadata.get_value(DATE), '%Y/%m/%d %H:%M:%S')
        new_date_format = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
        media_file.add_suffix_to_filename("[" + new_date_format + "]")

    def save_database(self):
        print("Saving database...")
        for media_file in self.media_file_list:
            self.database.save_media_file(media_file)
        self.database.file_connection.commit()
        print("End saving database.")

    def close_database(self):
        self.database.file_connection.close()

    def __str__(self):
        return self.root_path

    def __len__(self):
        return len(self.media_file_list)

    def __iter__(self):
        for media_file in self.media_file_list:
            yield media_file

    def add_file(self, media_file):
        self.media_file_list.append(media_file)
        self.update_date_and_sig_map(media_file)
        self.update_date_and_name_map(media_file)

    def update_date_and_name_map(self, media_file):
        date_id = media_file.get_date_identifier()
        if date_id is not None:
            if date_id not in self.date_and_name_map:
                self.date_and_name_map[date_id] = {}
            if media_file.original_filename not in self.date_and_name_map[date_id]:
                self.date_and_name_map[date_id][media_file.original_filename] = []
            if media_file not in self.date_and_name_map[date_id][media_file.original_filename]:
                self.date_and_name_map[date_id][media_file.original_filename].append(media_file)

    def update_date_and_sig_map(self, media_file):
        date_id = media_file.get_date_identifier()
        sig = media_file.get_signature()
        if date_id is not None and sig is not None:
            if date_id not in self.date_and_sig_map:
                self.date_and_sig_map[date_id] = {}
            if sig not in self.date_and_sig_map[date_id]:
                self.date_and_sig_map[date_id][sig] = []
            if media_file not in self.date_and_sig_map[date_id][sig]:
                self.date_and_sig_map[date_id][sig].append(media_file)

    def contains(self, item):
        date_id = item.get_date_identifier()
        if date_id is not None:
            if date_id in self.date_and_name_map:
                if item.original_filename in self.date_and_name_map[date_id]:
                    return True
                if item.get_signature() is None:
                    print("Warning: signature is not already computed. Should never happened.")
                    item.metadata.compute_value(SIGNATURE)
                if date_id in self.date_and_sig_map:
                    if item.get_signature() in self.date_and_sig_map[date_id]:
                        return True
        return False

    def get_possibly_duplicates(self):
        result = []
        for date_id in self.date_and_name_map:
            if len(self.date_and_name_map[date_id]) > 1:
                for filename in self.date_and_name_map[date_id]:
                    result.append(self.date_and_name_map[date_id][filename][0])
        return result

    @staticmethod
    def get_one_key(dictionary):
        for key in dictionary:
            return key

    def get_possibly_already_exists(self, media_set2):
        result = []
        for date_id in self.date_and_name_map:
            if date_id in media_set2.date_and_name_map:
                if len(self.date_and_name_map[date_id]) == 1:
                    filename1 = self.get_one_key(self.date_and_name_map[date_id])
                    if filename1 not in media_set2.date_and_name_map[date_id]:
                        result.append(self.date_and_name_map[date_id][filename1][0])
                if len(media_set2.date_and_name_map[date_id]) == 1:
                    filename1 = self.get_one_key(media_set2.date_and_name_map[date_id])
                    if filename1 not in self.date_and_name_map[date_id]:
                        result.append(media_set2.date_and_name_map[date_id][filename1][0])
        return result

    def get_copied_files(self):
        result = []
        for media_file in self.media_file_list:
            if media_file.is_copied_file():
                result.append(media_file)
        return result

    ## TO CHANGE
    def get_files_in(self, other):
        result = {}
        sig_map_1 = self.date_and_sig_map
        sig_map_2 = other.date_and_sig_map
        for sig in sig_map_1:
            if sig in sig_map_2:
                result[sig] = sig_map_1[sig]
        return result

    ## TO CHANGE
    def get_files_not_in(self, other):
        result = {}
        sig_map_1 = self.date_and_sig_map
        sig_map_2 = other.date_and_sig_map
        for sig in sig_map_1:
            if sig not in sig_map_2:
                result[sig] = sig_map_1[sig]
        return result

    @staticmethod
    def propagate_metadata_computed_value(metadata_name, media_file_list):
        if len(media_file_list) > 1:
            not_empty_metadata_value = Metadata.UNKNOWN
            for media_file in media_file_list:
                current_metadata_value = media_file.metadata.get_value(metadata_name)
                if current_metadata_value is not None and current_metadata_value != Metadata.UNKNOWN:
                    not_empty_metadata_value = current_metadata_value
            if not_empty_metadata_value != Metadata.UNKNOWN:
                for media_file in media_file_list:
                    current_metadata_value = media_file.metadata.get_value(metadata_name)
                    if current_metadata_value is None or current_metadata_value == Metadata.UNKNOWN:
                        media_file.metadata[metadata_name].set_value_computed(not_empty_metadata_value)

    def propagate_sig_to_duplicates(self):
        for date_id in self.date_and_name_map:
            for filename in self.date_and_name_map[date_id]:
                self.propagate_metadata_computed_value(SIGNATURE,
                                                       self.date_and_name_map[date_id][filename])

    def propagate_cm_to_duplicates(self):
        for date_id in self.date_and_name_map:
            for filename in self.date_and_name_map[date_id]:
                self.propagate_metadata_computed_value(CAMERA_MODEL,
                                                       self.date_and_name_map[date_id][filename])
        for date_id in self.date_and_sig_map:
            for sig in self.date_and_sig_map[date_id]:
                self.propagate_metadata_computed_value(CAMERA_MODEL,
                                                       self.date_and_sig_map[date_id][sig])

    def analyze_duplicates(self):
        str_list = ["All media files: " + str(len(self.media_file_list)),
                    "Distinct elements: {distinct}".format(distinct=str(len(self.date_and_sig_map)))]

        number_of_n_copied = {}
        for n_copied in map(len, self.date_and_sig_map.values()):
            if n_copied != 1:
                if n_copied not in number_of_n_copied:
                    number_of_n_copied[n_copied] = 0
                number_of_n_copied[n_copied] += 1

        for n_copied, number_of_n_copied in sorted(number_of_n_copied.items()):
            str_list.append("%s elem. found %s-times" % (number_of_n_copied, n_copied))

        return str_list

    def analyze_duplicates_2(self):
        number_of_n_copied = {}
        for signature in self.date_and_sig_map:
            n_copied = len(self.date_and_sig_map[signature])
            if n_copied not in number_of_n_copied:
                number_of_n_copied[n_copied] = {}
            number_of_n_copied[n_copied][signature] = self.date_and_sig_map[signature]

        return number_of_n_copied

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

        camera_model = media_file.metadata[CAMERA_MODEL]

        if cm_filter == "known":
            if camera_model.get_value_read() == Metadata.UNKNOWN:
                return False

        elif cm_filter == "unknown":
            if camera_model.get_value_read() != Metadata.UNKNOWN or camera_model.get_value_computed() is not None:
                return False

        elif cm_filter == "recovered":
            if camera_model.get_value_computed() is None:
                return False

        return True

    def create_media_dir_parent(self, dir_or_file_path):
        parent = str(Path(dir_or_file_path).parent)
        if parent not in self.media_dir_list:
            new_media_dir = MediaDirectory(parent, self.create_media_dir_parent(parent), self)
            self.media_dir_list[parent] = new_media_dir
        return self.media_dir_list[parent]

    def initialize_file_and_dir_list2(self, progress_signal=None):
        print(self.root_path)
        number_of_files = 0
        root_dir = MediaDirectory(str(self.root_path), None, self)
        self.media_dir_list[str(self.root_path)] = root_dir
        self.database.load_all_media_files(self, progress_signal)

    def initialize_file_and_dir_list(self, progress_signal=None):
        print(self.root_path)
        number_of_files = 0
        ignored_files = []
        root_dir = MediaDirectory(str(self.root_path), None, self)
        self.media_dir_list[str(self.root_path)] = root_dir

        for (parent_media_dir_path, folder_names, file_names) in os.walk(self.root_path, topdown=True):

            if ".cfm" in parent_media_dir_path:
                continue

            parent_media_dir_path = Path(parent_media_dir_path)
            parent_media_dir = self.media_dir_list[str(parent_media_dir_path)]

            for name in folder_names:
                media_dir_path = str(parent_media_dir_path / name)
                new_media_dir = MediaDirectory(media_dir_path, parent_media_dir, self)
                self.media_dir_list[media_dir_path] = new_media_dir

            for name in file_names:
                number_of_files += 1
                media_file_path = str(parent_media_dir_path / name)
                media_file_extension = os.path.splitext(name)[1].lower()

                if media_file_extension in TYPE:
                    new_media_file = MediaFile(media_file_path, parent_media_dir, self)
                    self.database.load_media_file(new_media_file)
                    self.add_file(new_media_file)
                else:
                    ignored_files.append(media_file_path)

            if progress_signal is not None:
                progress_signal.emit(number_of_files)
            print("\r{number: >15} files found".format(number=number_of_files), end='')
        print("")
        self.output_directory.save_list(ignored_files, "ignored-files.json")
