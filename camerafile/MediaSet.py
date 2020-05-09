import os
from pathlib import Path
from camerafile.MediaFile import MediaFile
from camerafile.Metadata import CAMERA_MODEL
from camerafile.MetadataList import MetadataList
from camerafile.Metadata import Metadata, SIGNATURE
from camerafile.MediaDirectory import MediaDirectory
from camerafile.OutputDirectory import OutputDirectory


class MediaSet:

    def __init__(self, path):
        self.create_json_metadata = False
        self.root_path = Path(self.parse_path(path))
        print(self.root_path)
        self.name = self.root_path.name
        self.output_directory = OutputDirectory(self.root_path)
        self.media_file_list = []
        self.media_dir_list = {}
        self.iter_ext_filter = None
        self.iter_cm_filter = None
        self.initialize_file_and_dir_list()

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
        num = 0
        for _ in self:
            num += 1
        return num

    def __eq__(self, other):
        result = []
        for media_file in self:
            if media_file in other and media_file not in result:
                result.append(media_file)
        return result

    def __gt__(self, other):
        result = []
        duplicates = 0
        for media_file in self:
            if media_file not in other:
                if media_file not in result:
                    result.append(media_file)
                else:
                    duplicates += 1
        return result, duplicates

    def __contains__(self, item):
        for media_file in self:
            if item == media_file:
                return True
        return False

    def analyze_duplicates(self):
        str_list = []
        total = 0
        sig_map = {}
        for media_file in self:
            total += 1
            media_file.metadata.compute_value(SIGNATURE)
            sig = media_file.metadata.get_value(SIGNATURE)
            if sig not in sig_map:
                sig_map[sig] = []
            sig_map[sig].append(media_file)

        str_list.append("All files: " + str(total))
        str_list.append("Distinct files: " + str(len(sig_map)))

        num_dup = {}
        for sig, list_same_file in sig_map.items():
            if len(list_same_file) not in num_dup:
                num_dup[len(list_same_file)] = 1
            else:
                num_dup[len(list_same_file)] += 1

        for xtimes, num_of_files in num_dup.items():
            str_list.append("x%s -> %s distinct" % (xtimes, num_of_files))

        return str_list

    def iter_filter(self, media_file):

        if self.iter_ext_filter is not None:
            if media_file.extension not in self.iter_ext_filter:
                return False

        camera_model = media_file.metadata[CAMERA_MODEL]

        if self.iter_cm_filter == "known":
            if camera_model.value_read == Metadata.UNKNOWN:
                return False

        elif self.iter_cm_filter == "unknown":
            if camera_model.value_read != Metadata.UNKNOWN or camera_model.value_computed is not None:
                return False

        elif self.iter_cm_filter == "recovered":
            if camera_model.value_computed is None:
                return False

        return True

    def __iter__(self):
        for media_file in self.media_file_list:
            if media_file.exists and self.iter_filter(media_file):
                yield media_file

        self.iter_ext_filter = None
        self.iter_cm_filter = None

    def __call__(self, ext=None, cm=None):
        self.iter_ext_filter = ext
        self.iter_cm_filter = cm
        return self

    def get_file_list(self, ext=None, cm=None):
        result = []
        self.iter_ext_filter = ext
        self.iter_cm_filter = cm
        for media_file in self:
            result.append(media_file)
        return result

    def initialize_file_and_dir_list(self):

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
                    self.media_file_list.append(new_media_file)

                elif media_file_extension == MetadataList.METADATA_EXTENSION:
                    media_file_path = media_file_path[:-len(MetadataList.METADATA_EXTENSION)]
                    if not os.path.exists(media_file_path):
                        new_media_file = MediaFile(media_file_path, parent_media_dir, self, exists=False)
                        self.media_file_list.append(new_media_file)

            print("\r{number: >15} files found".format(number=number_of_files), end='')
        print("")
