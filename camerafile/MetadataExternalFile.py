import json
import os
from json import JSONDecodeError


class MetadataExternalFile:

    def __init__(self, file_path, metadata_list, create_if_not_exists):
        self.file_path = file_path
        self.file_exists = False
        self.metadata_list = metadata_list
        self.create_if_not_exists = create_if_not_exists
        self.loaded_metadata = {}
        self.load()

    def load(self):
        try:
            with open(self.file_path, 'r') as f:
                self.file_exists = True
                try:
                    self.loaded_metadata = json.load(f)
                    self.metadata_list.load_from_dict(self.loaded_metadata)
                except JSONDecodeError:
                    self.loaded_metadata = {}
        except FileNotFoundError:
            self.file_exists = False

    def save(self, new_saved_metadata):
        if self.file_exists or self.create_if_not_exists:
            if not self.file_exists or new_saved_metadata != self.loaded_metadata:
                with open(self.file_path, 'w') as f:
                    json.dump(new_saved_metadata, f, indent=4)
                self.file_exists = True

    def delete(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
            return True
        return False
