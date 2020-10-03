import logging
import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class OutputDirectory:
    base_path = None
    FILE_WITH_INPUT_PATH = "input_path.txt"

    @staticmethod
    def init(base_output_path):
        OutputDirectory.base_path = Path(base_output_path) / ".cfm"
        os.makedirs(OutputDirectory.base_path, exist_ok=True)

    def __init__(self, media_set_root_path):
        self.path = Path(media_set_root_path) / ".cfm"
        os.makedirs(self.path, exist_ok=True)

    def save_list(self, list_of_elements, file_name):
        if len(list_of_elements) != 0:
            file_path = self.path / file_name
            with open(file_path, 'w') as f:
                for element in list_of_elements:
                    f.write(str(element) + "\n")
            LOGGER.info("File saved (%s elements): %s" % (str(len(list_of_elements)), str(file_path.resolve())))
