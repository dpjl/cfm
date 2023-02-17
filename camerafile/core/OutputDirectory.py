import logging
import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class OutputDirectory:
    __instance = {}

    def __init__(self, media_set_root_path):
        self.path = Path(media_set_root_path) / ".cfm"
        os.makedirs(self.path, exist_ok=True)
        self.state_file = self.path / "state.yaml"
        self.batch_stderr = self.path / "batch_stderr.txt"
        self.batch_stdout = self.path / "batch_stdout.txt"
        if self.batch_stderr.exists():
            os.remove(self.batch_stderr)
        if self.batch_stdout.exists():
            os.remove(self.batch_stdout)

    @staticmethod
    def get(root_directory) -> "OutputDirectory":
        if root_directory not in OutputDirectory.__instance:
            OutputDirectory.__instance[root_directory] = OutputDirectory(root_directory)
        return OutputDirectory.__instance[root_directory]

    def save_list(self, list_of_elements, file_name):
        if len(list_of_elements) != 0:
            file_path = self.path / file_name
            with open(file_path, 'w') as f:
                for element in list_of_elements:
                    f.write(str(element) + "\n")
            return "List ({nb_elements} elements) saved in {path}".format(nb_elements=str(len(list_of_elements)),
                                                                          path=str(file_path.resolve()))
