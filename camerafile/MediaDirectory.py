import os
from pathlib import Path
from camerafile.MediaFile import MediaFile
from camerafile.MediaCameraModel import MediaCameraModel


class VisualFileCounter:
    count = 0

    @classmethod
    def add_and_display(cls, number):
        cls.count += number
        print("\r{number: >15} files found".format(number=cls.count), end='')

    @classmethod
    def end(cls):
        print("")


class MediaDirectory:

    def __init__(self, path, parent_dir=None):
        self.path = path
        self.camera_model = MediaCameraModel(self)
        self.parent_dir = parent_dir
        self.media_file_list = []
        self.media_dir_list = []

        if parent_dir is None:
            VisualFileCounter.count = 0

        (dir_path, folder_names, file_names) = next(os.walk(self.path))
        VisualFileCounter.add_and_display(len(file_names))
        for name in file_names:
            file_path = str(Path(dir_path) / name)
            if MediaFile.is_media_file(file_path):
                self.media_file_list.append(MediaFile(file_path, self))
        for name in folder_names:
            self.media_dir_list.append(MediaDirectory(str(Path(dir_path) / name), self))

        if parent_dir is None:
            VisualFileCounter.end()

    def __str__(self):
        return self.path

    def get_all_media_files(self):
        result = []
        result.extend(self.media_file_list)
        for media_dir in self.media_dir_list:
            result.extend(media_dir.get_all_media_files())
        return result

    def get_files_with_camera_model(self):
        result = []
        for media_file in self.media_file_list:
            if media_file.camera_model.value is not None:
                result.append(media_file)
        for media_dir in self.media_dir_list:
            result.extend(media_dir.get_files_with_camera_model())
        return result

    def get_files_with_unknown_camera_model(self):
        result = []
        for media_file in self.media_file_list:
            if media_file.camera_model.value is None and media_file.camera_model.recovered_value is None:
                result.append(media_file)
        for media_dir in self.media_dir_list:
            result.extend(media_dir.get_files_with_unknown_camera_model())
        return result

    def get_files_with_recovered_camera_model(self):
        result = []
        for media_file in self.media_file_list:
            if media_file.camera_model.recovered_value is not None:
                result.append(media_file)
        for media_dir in self.media_dir_list:
            result.extend(media_dir.get_files_with_recovered_camera_model())
        return result