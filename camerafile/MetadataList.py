import os
import json
import logging
from typing import Dict
from json import JSONDecodeError
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import Metadata, CAMERA_MODEL, DATE, ORIGINAL_PATH, DESTINATION_PATH, SIGNATURE
from camerafile.MetadataSignature import MetadataSignature
from camerafile.MetadataCameraModel import MetadataCameraModel
from camerafile.OutputDirectory import OutputDirectory

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
        self.saved_metadata = {}
        self.external_metadata_file_path = str(self.media_file.path) + MetadataList.METADATA_EXTENSION
        self.create_json_metadata = self.media_file.parent_set.create_json_metadata
        cache_path = self.media_file.parent_set.output_directory.cache_path
        self.cache_metadata_file_path = cache_path / (self.media_file.id + ".json")
        self.load()

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
        self[name].compute_value()
        value = self[name].value_computed
        self.save()
        return value

    def delete_computed_value(self, name):
        if self[name].value_computed is not None:
            self[name].value_computed = None
        self.save()

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
            self.save()

    def load(self):
        self.saved_metadata = {}
        self.load_from_file(self.cache_metadata_file_path)
        self.load_from_file(self.external_metadata_file_path)

    def save(self):
        new_saved_metadata = self.create_new_saved_metadata()
        self.save_to_file(self.external_metadata_file_path, new_saved_metadata, self.create_json_metadata)
        self.save_to_file(self.cache_metadata_file_path, new_saved_metadata, True)
        self.saved_metadata = new_saved_metadata

    def create_new_saved_metadata(self):
        new_saved_metadata = {}
        for metadata_name, metadata in self.metadata_list.items():
            if metadata.value_read is not None:
                new_saved_metadata[metadata_name] = metadata.value_read
            if metadata.value_computed is not None:
                new_saved_metadata[MetadataList.COMPUTE_PREFIX + metadata_name] = metadata.value_computed
        return new_saved_metadata

    def load_from_file(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                try:
                    self.saved_metadata = json.load(f)
                    for metadata_name, metadata in self.metadata_list.items():
                        if metadata_name in self.saved_metadata:
                            metadata.set_value_read(self.saved_metadata[metadata_name])
                        if MetadataList.COMPUTE_PREFIX + metadata_name in self.saved_metadata:
                            metadata.set_value_computed(
                                self.saved_metadata[MetadataList.COMPUTE_PREFIX + metadata_name])
                except JSONDecodeError:
                    self.saved_metadata = {}

    def save_to_file(self, file_path, new_saved_metadata, create_if_not_exist):
        if not os.path.exists(file_path) or new_saved_metadata != self.saved_metadata:
            if os.path.exists(file_path) or create_if_not_exist:
                with open(file_path, 'w') as f:
                    json.dump(new_saved_metadata, f, indent=4)

    def delete_metadata_file(self):
        if os.path.exists(self.external_metadata_file_path):
            os.remove(self.external_metadata_file_path)
            return True
        return False
