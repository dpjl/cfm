import json
import sys
import os
from pathlib import Path


class Resource:

    exiftool_executable = None
    program_path = None
    logging_configuration = None
    cfm_configuration = None

    @staticmethod
    def get_main_path():
        try:
            return Path(sys._MEIPASS) / ".."
        except AttributeError:
            return Path(os.path.dirname(__file__))

    @staticmethod
    def init():
        Resource.program_path = Resource.get_main_path()
        logging_configuration_file = Resource.program_path / "conf" / "logging.json"
        cfm_configuration_file = Resource.program_path / "conf" / "cfm.json"
        with open(logging_configuration_file, 'r') as f:
            Resource.logging_configuration = json.load(f)
        with open(cfm_configuration_file, 'r') as f:
            Resource.cfm_configuration = json.load(f)

        Resource.exiftool_executable = Resource.program_path / Path(Resource.cfm_configuration["exiftool"])
