import json
import sys
import os
from pathlib import Path


class Resource:

    avimetaedit_executable = None
    exiftool_executable = None
    program_path = None
    logging_configuration = None
    cfm_configuration = None

    @staticmethod
    def init():
        try:
            Resource.program_path = Path(sys._MEIPASS)
        except AttributeError:
            Resource.program_path = Path(os.getcwd())
        logging_configuration_file = Resource.program_path / "conf" / "logging.json"
        cfm_configuration_file = Resource.program_path / "conf" / "cfm.json"
        with open(logging_configuration_file, 'r') as f:
            Resource.logging_configuration = json.load(f)
        with open(cfm_configuration_file, 'r') as f:
            Resource.cfm_configuration = json.load(f)

        Resource.exiftool_executable = Resource.program_path / Path(Resource.cfm_configuration["exiftool"])
        Resource.avimetaedit_executable = Resource.program_path / Path(Resource.cfm_configuration["avimetaedit"])
