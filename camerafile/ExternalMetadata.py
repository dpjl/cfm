import json
import os
from json import JSONDecodeError
from pathlib import Path
from dateutil import parser

from camerafile.ExifTool import ExifTool


class ExternalMetadata:
    METADATA_EXTENSION = ".metadata"
    CAMERA_MODEL = "Camera Model"
    CREATION_DATE = "Creation Date"
    RECOVERED_CAMERA_MODEL = "Recovered Camera Model"
    ORIGINAL_LOCATION = "Original Path"
    DESTINATION_LOCATION = "Destination Path"
    HASH = "Hash"

    def __init__(self, media_file_path):
        self.media_file_path = media_file_path
        self.file_path = media_file_path + ExternalMetadata.METADATA_EXTENSION
        self.file_name = Path(self.file_path).name
        self.metadata = {}
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                try:
                    self.metadata = json.load(f)
                except JSONDecodeError:
                    self.metadata = {}
        self.original_metadata = self.metadata.copy()

    def load_from_media(self):
        model, date = ExifTool.get_model_and_date(self.media_file_path)
        self.update_model(model)
        self.update_date(date.strftime("%Y/%m/%d %H:%M:%S"))
        self.save()

    def save(self):
        if self.metadata != self.original_metadata:
            with open(self.file_path, 'w') as f:
                json.dump(self.metadata, f, indent=4)
            self.original_metadata = self.metadata.copy()

    def get(self, tag):
        if tag in self.metadata:
            return True, self.metadata[tag]
        return False, None

    def update(self, tag, value):
        self.metadata[tag] = value

    def delete(self, tag):
        try:
            del self.metadata[tag]
        except KeyError:
            return

    def get_model(self):
        return self.get(ExternalMetadata.CAMERA_MODEL)

    def get_date(self):
        is_found, date = self.get(ExternalMetadata.CREATION_DATE)
        if is_found and date is not None:
            return is_found, parser.parse(date)
        return is_found, date

    def update_model(self, new_model):
        self.update(ExternalMetadata.CAMERA_MODEL, new_model)

    def update_date(self, new_date):
        self.update(ExternalMetadata.CREATION_DATE, new_date)

    def delete_model(self):
        self.delete(ExternalMetadata.CAMERA_MODEL)

    def get_recovered_model(self):
        return self.get(ExternalMetadata.RECOVERED_CAMERA_MODEL)

    def update_recovered_model(self, new_model):
        self.update(ExternalMetadata.RECOVERED_CAMERA_MODEL, new_model)

    def update_original_path(self, path):
        self.update(ExternalMetadata.ORIGINAL_LOCATION, path)

    def update_destination_path(self, path):
        self.update(ExternalMetadata.DESTINATION_LOCATION, path)

    def delete_recovered_model(self):
        self.delete(ExternalMetadata.RECOVERED_CAMERA_MODEL)

    def delete_file(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
            return True
        return False
