import re

from camerafile.mdtools.MdConstants import MetadataNames


class OrgFormat:

    def __init__(self, format_description: str):
        self.format_description = format_description
        self.fields = re.findall(r'\${((.*?):(.*?))}', format_description)
        self.default = {}
        self.format = {}
        self.md_list = []
        for field in self.fields:
            self.md_list.append(MetadataNames.from_str(field[0]))
            if len(field > 1):
                self.default[field[0]] = field[1]
            if len(field > 2):
                self.format[field[0]] = field[2]
        self.arg_md_list = self.get_required_metadata_list()

    def get_metadata_list(self):
        return self.md_list

    def get_default_value(self, metadata_name):
        if metadata_name in self.default:
            return self.default[metadata_name]
        return None

    def get_format(self, metadata_name):
        if metadata_name in self.format:
            return self.format[metadata_name]
        return None

    def get_formated_string(self):
        result = self.format_description
        for field in self.fields:
            result = result.replace(field[0], self.get_value(field[0]))
