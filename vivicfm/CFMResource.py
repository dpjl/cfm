import json
import sys
import os
from pathlib import Path


class CFMResource:

    avimetaedit_executable = None
    exiftool_executable = None
    program_path = None
    logging_configuration = None
    cfm_configuration = None

    @staticmethod
    def init():
        try:
            CFMResource.program_path = Path(sys._MEIPASS)
        except AttributeError:
            CFMResource.program_path = Path(os.getcwd())
        logging_configuration_file = CFMResource.program_path / "conf" / "logging.json"
        cfm_configuration_file = CFMResource.program_path / "conf" / "cfm.json"
        with open(logging_configuration_file, 'r') as f:
            CFMResource.logging_configuration = json.load(f)
        with open(cfm_configuration_file, 'r') as f:
            CFMResource.cfm_configuration = json.load(f)

        CFMResource.exiftool_executable = CFMResource.program_path / Path(CFMResource.cfm_configuration["exiftool"])
        CFMResource.avimetaedit_executable = CFMResource.program_path / Path(CFMResource.cfm_configuration["avimetaedit"])
