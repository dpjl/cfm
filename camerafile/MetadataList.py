import os
import json
import logging
from typing import Dict
from json import JSONDecodeError
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import Metadata, CAMERA_MODEL, DATE, ORIGINAL_PATH, DESTINATION_PATH, SIGNATURE
from camerafile.MetadataSignature import MetadataSignature
from camerafile.MetadataCameraModel import MetadataCameraModel

LOGGER = logging.getLogger(__name__)


class MetadataList:
    metadata_list: Dict[str, Metadata]
    COMPUTE_PREFIX = "Computed "
    METADATA_EXTENSION = ".cfm-metadata"

    def __init__(self, media_file):
        self.media_file = media_file
        self.metadata_list = {CAMERA_MODEL: MetadataCameraModel(media_file),
                              DATE: Metadata(media_file),
                              ORIGINAL_PATH: Metadata(media_file),
                              DESTINATION_PATH: Metadata(media_file),
                              SIGNATURE: MetadataSignature(media_file)}
        self.external_metadata = {}
        self.external_metadata_file_path = str(self.media_file.path) + MetadataList.METADATA_EXTENSION
        self.load_from_external_metadata()

    def __getitem__(self, item):
        return self.metadata_list[item]

    def set_value(self, name, value):
        self[name].value_read = value
        self.load_from_media(name)

    def get_value(self, name):
        self.read_value(name)
        return self[name].get()

    def read_value(self, name):
        if self[name].value_read is None:
            self.load_from_media(name)
        return self[name].value_read

    def compute_value(self, name):
        initial_value = self[name].value_computed
        self[name].compute_value()
        value = self[name].value_computed
        if initial_value != value:
            self.save_to_external_metadata()
        return value

    def delete_computed_value(self, name):
        if self[name].value_computed is not None:
            self[name].value_computed = None
            self.save_to_external_metadata()

    def load_from_media(self, name):
        if name in [DATE, CAMERA_MODEL]:
            model, date = ExifTool.get_model_and_date(self.media_file.path)
            if model is not None:
                self[CAMERA_MODEL].set_value_read(model)
            else:
                self[CAMERA_MODEL].set_value_read(Metadata.UNKNOWN)
            if date is not None:
                self[DATE].set_value_read(date.strftime("%Y/%m/%d %H:%M:%S"))
            else:
                self[DATE].set_value_read(Metadata.UNKNOWN)
            self.save_to_external_metadata()

    def load_from_external_metadata(self):
        self.external_metadata = {}
        if os.path.exists(self.external_metadata_file_path):
            with open(self.external_metadata_file_path, 'r') as f:
                try:
                    self.external_metadata = json.load(f)
                    for metadata_name, metadata in self.metadata_list.items():
                        if metadata_name in self.external_metadata:
                            metadata.set_value_read(self.external_metadata[metadata_name])
                        if MetadataList.COMPUTE_PREFIX + metadata_name in self.external_metadata:
                            metadata.set_value_computed(
                                self.external_metadata[MetadataList.COMPUTE_PREFIX + metadata_name])
                except JSONDecodeError:
                    self.external_metadata = {}

    def save_to_external_metadata(self):
        new_external_metadata = {}
        for metadata_name, metadata in self.metadata_list.items():
            if metadata.value_read is not None:
                new_external_metadata[metadata_name] = metadata.value_read
            if metadata.value_computed is not None:
                new_external_metadata[MetadataList.COMPUTE_PREFIX + metadata_name] = metadata.value_computed

        if new_external_metadata != self.external_metadata:
            with open(self.external_metadata_file_path, 'w') as f:
                json.dump(new_external_metadata, f, indent=4)
            self.external_metadata = new_external_metadata

    def delete_metadata_file(self):
        if os.path.exists(self.external_metadata_file_path):
            os.remove(self.external_metadata_file_path)
            return True
        return False
