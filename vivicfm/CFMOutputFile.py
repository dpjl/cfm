import os
import json
import logging

from vivicfm.CFMOutputDirectory import CFMOutputDirectory

LOGGER = logging.getLogger(__name__)


class CFMFileRW:

    @staticmethod
    def load_dict(filename):
        file_path = CFMOutputDirectory.path / filename
        if os.path.exists(str(file_path.resolve())):
            with open(file_path, 'r') as f:
                result = json.load(f)
            LOGGER.info("File loaded: " + str(file_path.resolve()))
            return result
        return None

    @staticmethod
    def save_dict(dict_object, filename):
        if len(dict_object) != 0:
            file_path = CFMOutputDirectory.path / filename
            with open(file_path, 'w') as f:
                json.dump(dict_object, f, indent=4)
            LOGGER.info("File saved (%s elements): %s" % (str(len(dict_object)), str(file_path.resolve())))
