import re
import sys
from typing import Union

import yaml
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import Logger
from camerafile.core.OrgFormat import OrgFormat
from camerafile.mdtools.MdConstants import MetadataNames

LOGGER = Logger(__name__)


class MediaSetState:

    def __init__(self, root_path: str):
        self.state_file = OutputDirectory.get(root_path).state_file
        self.state: dict[str, Union[str, list]] = {}
        self.read_md_needed = False
        self.md_needed = ()
        self.org_format: OrgFormat

    def load(self):
        if self.state_file.exists():
            with open(self.state_file) as file:
                self.state = yaml.safe_load(file)
        if Configuration.get().ignore_list is not None:
            ignore_list = Configuration.get().ignore_list
            for ignore_pattern in ignore_list:
                if "ignore" not in self.state:
                    self.state["ignore"] = []
                if ignore_pattern not in self.state["ignore"]:
                    self.state["ignore"].append(ignore_pattern)
        if "ignore" in self.state:
            LOGGER.info(f'Filename patterns to ignore: {str(self.state["ignore"])}')

    def save(self):
        with open(self.state_file, "w") as file:
            return yaml.safe_dump(self.state, file)

    def load_format(self, param_format):
        self.org_format = None
        if "format" in self.state:
            existing_format = self.state["format"]
            if existing_format is not None and param_format and param_format != "" and param_format != existing_format:
                state_file = self.state_file.as_posix()
                print(
                    f"Error: format in argument '{param_format} ' differs from "
                    f"format saved in {state_file}: '{existing_format}'")
                print("If you really want to force changing the destination format, please remove this file "
                      "and launch again cfm.")
                sys.exit(1)
            elif existing_format is not None:
                self.org_format = existing_format
            else:
                self.org_format = param_format

        else:
            self.org_format = param_format

        if self.org_format is not None and self.org_format != "":
            self.state["format"] = self.org_format
            self.save()

    def load_metadata_to_read(self):
        previously_loaded_metadata = ()
        if "loaded_metadata" in self.state:
            previously_loaded_metadata = tuple([MetadataNames.from_str(arg) for arg in self.state["loaded_metadata"]])
        args = ()
        if Configuration.get().internal_read:
            args += (MetadataNames.CREATION_DATE, MetadataNames.MODEL, MetadataNames.ORIENTATION)
        else:
            print("Warning: only system metadata will be used. It is faster but dates could be different from the"
                  "date of the original date the photos were taken")

        if Configuration.get().thumbnails:
            args += (MetadataNames.THUMBNAIL,)

        for arg in args:
            if arg not in previously_loaded_metadata:
                self.read_md_needed = True
                LOGGER.debug("This metadata was not already loaded, internal read will be performed: " + str(arg))

        self.md_needed = args

    def get_metadata_needed_by_format(self):
        args = ()
        if self.org_format is not None:
            md_list = self.org_format.get_metadata_list()
            if not Configuration.get().internal_read:
                md_list.remove(MetadataNames.CREATION_DATE)
                if len(md_list) != 0:
                    raise Exception("Error, some fields of target format cannot be loaded without "
                                    "internal metadata loading: " + ", ".join(md_list))
            for md in md_list:
                if md not in args:
                    args += (md,)
        return args

    def update_loaded_metadata(self):
        self.state["loaded_metadata"] = [str(md) for md in self.md_needed]
        self.save()

    def should_be_ignored(self, file_name):
        if "ignore" in self.state:
            for regexp in self.state["ignore"]:
                if re.match(regexp, file_name):
                    return True
        return False
