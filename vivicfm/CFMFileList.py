import os
import logging
from pathlib import Path

videoExt = [".avi", ".mov", ".mp4"]
imageExt = [".jpg", ".jpeg", ".thm"]
audioExt = [".wav", ".mp3"]
mediaExt = videoExt + imageExt + audioExt

LOGGER = logging.getLogger(__name__)


class CFMFileList:

    def __init__(self):
        self.files = {}
        self.all = []
        self.media = []

    def compute(self, input_dir_path):
        num_file = 0
        previous_display = 0
        for (dir_path, folder_names, file_names) in os.walk(input_dir_path):
            num_file += len(file_names)
            if int(num_file / 1000) > previous_display:
                previous_display = int(num_file / 1000)
                print("\r{number: >15} files".format(number=num_file), end='')
            for file_name in file_names:
                self.add(str(Path(dir_path) / file_name))
        print("\r{number: >15} files".format(number=num_file))

    def add(self, file):
        self.all.append(file)
        filename = Path(file).name
        ext = os.path.splitext(filename)[1].lower()
        if ext in mediaExt:
            self.media.append(file)
        if ext in self.files:
            self.files[ext] += 1
        else:
            self.files[ext] = 1

    def get_number_of(self, ext_list):
        result = 0
        for file_type in ext_list:
            if file_type in self.files:
                result += self.files[file_type]
        return result

    def log(self):
        LOGGER.debug("Number of files: " + str(len(self.all)))
        LOGGER.debug("Number of image files: " + str(self.get_number_of(imageExt)))
        LOGGER.debug("Number of video files: " + str(self.get_number_of(videoExt)))
        LOGGER.debug("Number of audio files: " + str(self.get_number_of(audioExt)))
        LOGGER.debug("Media files (" + str(self.get_number_of(mediaExt)) + " files):")
        for file_type in mediaExt:
            if file_type in self.files:
                LOGGER.debug(file_type + ": " + str(self.files[file_type]))

        LOGGER.debug("Other files:")
        for file_type, number in self.files.items():
            if file_type not in mediaExt:
                LOGGER.debug(file_type + ": " + str(number))
