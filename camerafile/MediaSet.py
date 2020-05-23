import os
from pathlib import Path

from camerafile.MediaDirectory import MediaDirectory
from camerafile.MediaFile import MediaFile
from camerafile.MediaSetDatabase import MediaSetDatabase
from camerafile.Metadata import CAMERA_MODEL
from camerafile.Metadata import Metadata
from camerafile.OutputDirectory import OutputDirectory


class MediaSet:

    def __init__(self, path):
        self.create_json_metadata = False
        self.root_path = Path(self.parse_path(path)).resolve()
        self.name = self.root_path.name
        self.output_directory = OutputDirectory(self.root_path)
        self.media_file_list = []
        self.media_dir_list = {}
        self.sig_map = {}
        self.av_sig_map = {}
        self.database = MediaSetDatabase(self.root_path)
        self.initialize_file_and_dir_list()

    def __del__(self):
        self.save_database()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.save_database()
        # pourquoi est-ce plus lent en utilisant un enter/exit plutôt qu'un init/del ??
        pass

    def delete_file(self, file_path):
        self.media_file_list.remove(file_path)

    def save_database(self):
        print("Saving database...")
        for media_file in self.media_file_list:
            self.database.save_media_file(media_file)
        self.database.file_connection.commit()
        self.database.file_connection.close()
        print("End saving database.")

    def parse_path(self, path):
        root_path = path
        split_path = path.split(">")
        if len(split_path) == 2:
            root_path = split_path[0]
            if split_path[1] == "create-json-metadata":
                self.create_json_metadata = True
        return root_path

    def __str__(self):
        return self.root_path

    def __len__(self):
        return len(self.media_file_list)

    def __iter__(self):
        for media_file in self.media_file_list:
            yield media_file

    def update_sig_maps(self, media_file):
        self.add_to_sig_map(media_file)
        self.add_to_av_sig_map(media_file)

    def add_file(self, media_file):
        self.media_file_list.append(media_file)
        self.update_sig_maps(media_file)

    def add_to_sig_map(self, media_file):
        sig = media_file.get_exact_signature()
        if sig is not None:
            if sig not in self.sig_map:
                self.sig_map[sig] = []
            self.sig_map[sig].append(media_file)

    def add_to_av_sig_map(self, media_file):
        sig = media_file.get_average_signature()
        if sig is not None:
            if sig not in self.av_sig_map:
                self.av_sig_map[sig] = []
            self.av_sig_map[sig].append(media_file)

    def contains_exact(self, item):
        sig = item.get_exact_signature()
        return sig is not None and sig in self.sig_map

    def contains_similar(self, item):
        sig = item.get_average_signature()
        return sig is not None and sig in self.av_sig_map

    def get_copied_files(self):
        result = []
        for media_file in self.media_file_list:
            if media_file.is_copied_file():
                result.append(media_file)
        return result

    def get_files_in(self, other):
        result = {}
        sig_map_1 = self.av_sig_map
        sig_map_2 = other.av_sig_map
        for sig in sig_map_1:
            if sig in sig_map_2:
                result[sig] = sig_map_1[sig]
        return result

    def get_files_not_in(self, other):
        result = {}
        sig_map_1 = self.av_sig_map
        sig_map_2 = other.av_sig_map
        for sig in sig_map_1:
            if sig not in sig_map_2:
                result[sig] = sig_map_1[sig]
        return result

    def analyze_duplicates(self):
        str_list = []

        total = 0

        str_list.append("All media files: " + str(len(self.media_file_list)))
        str_list.append("Distinct elements: {distinct}".format(distinct=str(len(self.av_sig_map))))

        number_of_n_copied = {}
        for n_copied in map(len, self.av_sig_map.values()):
            if n_copied != 1:
                if n_copied not in number_of_n_copied:
                    number_of_n_copied[n_copied] = 0
                number_of_n_copied[n_copied] += 1

        for n_copied, number_of_n_copied in sorted(number_of_n_copied.items()):
            str_list.append("%s elem. found %s-times" % (number_of_n_copied, n_copied))

        return str_list

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
            if camera_model.value_read == Metadata.UNKNOWN:
                return False

        elif cm_filter == "unknown":
            if camera_model.value_read != Metadata.UNKNOWN or camera_model.value_computed is not None:
                return False

        elif cm_filter == "recovered":
            if camera_model.value_computed is None:
                return False

        return True

    def initialize_file_and_dir_list(self):
        print(self.root_path)
        number_of_files = 0
        root_dir = MediaDirectory(str(self.root_path), None, self)
        self.media_dir_list[str(self.root_path)] = root_dir

        for (parent_media_dir_path, folder_names, file_names) in os.walk(self.root_path, topdown=True):

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

                if media_file_extension in MediaFile.TYPE:
                    new_media_file = MediaFile(media_file_path, parent_media_dir, self)
                    self.database.load_media_file(new_media_file)
                    self.add_file(new_media_file)

            print("\r{number: >15} files found".format(number=number_of_files), end='')
        print("")
