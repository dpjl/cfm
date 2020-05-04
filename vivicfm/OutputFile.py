import os
import json
import logging

from vivicfm.OutputDirectory import OutputDirectory

LOGGER = logging.getLogger(__name__)


class OutputFile:

    @staticmethod
    def load_dict(file_name):
        file_path = OutputDirectory.path / file_name
        if os.path.exists(str(file_path.resolve())):
            with open(file_path, 'r') as f:
                result = json.load(f)
            LOGGER.info("File loaded: " + str(file_path.resolve()))
            return result
        return None

    @staticmethod
    def save_dict(dict_object, file_name):
        if len(dict_object) != 0:
            file_path = OutputDirectory.path / file_name
            with open(file_path, 'w') as f:
                json.dump(dict_object, f, indent=4)
            LOGGER.info("File saved (%s elements): %s" % (str(len(dict_object)), str(file_path.resolve())))

    @staticmethod
    def save_list(list_of_elements, file_name):
        if len(list_of_elements) != 0:
            file_path = OutputDirectory.path / file_name
            with open(file_path, 'w') as f:
                for element in list_of_elements:
                    f.write(str(element) + "\n")
            LOGGER.info("File saved (%s elements): %s" % (str(len(list_of_elements)), str(file_path.resolve())))
