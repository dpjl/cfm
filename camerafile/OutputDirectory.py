import json
import logging
import os
import uuid
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class OutputDirectory:
    base_path = None
    FILE_WITH_INPUT_PATH = "input_path.txt"

    @staticmethod
    def init(base_output_path):
        OutputDirectory.base_path = Path(base_output_path)
        os.makedirs(OutputDirectory.base_path, exist_ok=True)

    def __init__(self, media_set_root_path):
        self.media_root_path = media_set_root_path
        self.cache_path = None
        self.path = None

        files_and_dirs = os.listdir(OutputDirectory.base_path)
        for file_or_dir in files_and_dirs:
            if os.path.isdir(Path(OutputDirectory.base_path) / file_or_dir):
                dir_path = Path(OutputDirectory.base_path) / file_or_dir
                if self.is_output_directory(dir_path):
                    self.path = dir_path
                    break
        if self.path is None:
            self.path = self.create_new_output_path()

        self.cache_path = self.path / "cache"
        os.makedirs(self.cache_path, exist_ok=True)

    def is_output_directory(self, dir_path):
        file_with_input_path = dir_path / OutputDirectory.FILE_WITH_INPUT_PATH
        if os.path.exists(file_with_input_path):
            with open(file_with_input_path, "r") as f:
                line = f.readline().strip()
                if line == str(self.media_root_path):
                    return True
        return False

    def create_new_output_path(self):
        new_path = OutputDirectory.base_path / (self.media_root_path.name + "-" + uuid.uuid4().hex[:8])
        new_path.mkdir(parents=True, exist_ok=True)
        file_with_input_path = new_path / OutputDirectory.FILE_WITH_INPUT_PATH
        with open(file_with_input_path, "w") as f:
            f.write(str(self.media_root_path))
        return new_path

    def load_dict(self, file_name):
        file_path = self.path / file_name
        if os.path.exists(str(file_path.resolve())):
            with open(file_path, 'r') as f:
                result = json.load(f)
            LOGGER.info("File loaded: " + str(file_path.resolve()))
            return result
        return None

    def save_dict(self, dict_object, file_name):
        if len(dict_object) != 0:
            file_path = self.path / file_name
            with open(file_path, 'w') as f:
                json.dump(dict_object, f, indent=4)
            LOGGER.info("File saved (%s elements): %s" % (str(len(dict_object)), str(file_path.resolve())))

    def save_list(self, list_of_elements, file_name):
        if len(list_of_elements) != 0:
            file_path = self.path / file_name
            with open(file_path, 'w') as f:
                for element in list_of_elements:
                    f.write(str(element) + "\n")
            LOGGER.info("File saved (%s elements): %s" % (str(len(list_of_elements)), str(file_path.resolve())))
