import logging
import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class OutputDirectory:

    def __init__(self, media_set_root_path):
        self.path = Path(media_set_root_path) / ".cfm"
        os.makedirs(self.path, exist_ok=True)

    def save_list(self, list_of_elements, file_name):
        if len(list_of_elements) != 0:
            file_path = self.path / file_name
            with open(file_path, 'w') as f:
                for element in list_of_elements:
                    f.write(str(element) + "\n")
            return "File saved ({nb_elements} elements): {path}".format(nb_elements=str(len(list_of_elements)),
                                                                        path=str(file_path.resolve()))
