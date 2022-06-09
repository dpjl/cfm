import logging
from typing import Dict

from camerafile.core.Constants import INTERNAL, SIGNATURE, FACES, ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, \
    ORIGINAL_MOVE_PATH, DESTINATION_MOVE_PATH, CFM_CAMERA_MODEL, THUMBNAIL, ORIGINAL_PATH
from camerafile.metadata.Metadata import Metadata

LOGGER = logging.getLogger(__name__)


class MetadataList:
    metadata_list: Dict[str, Metadata]

    def __init__(self):
        self.metadata_list = {CFM_CAMERA_MODEL: Metadata(),
                              INTERNAL: Metadata(),
                              THUMBNAIL: Metadata(),
                              ORIGINAL_COPY_PATH: Metadata(),
                              DESTINATION_COPY_PATH: Metadata(),
                              ORIGINAL_PATH: Metadata(),
                              ORIGINAL_MOVE_PATH: Metadata(),
                              DESTINATION_MOVE_PATH: Metadata(),
                              SIGNATURE: Metadata(),
                              FACES: Metadata()}

    def __getitem__(self, key) -> Metadata:
        return self.metadata_list[key]

    def __setitem__(self, key, value):
        self.metadata_list[key] = value

    def set_value(self, name, value):
        self[name].value = value

    def get_value(self, name):
        return self[name].get()

    def save_to_dict(self):
        result = {}
        for metadata_name, metadata in self.metadata_list.items():
            if metadata.value is not None:
                result[metadata_name] = metadata.value
        return result

    def save_binary_to_dict(self):
        result = {}
        for metadata_name, metadata in self.metadata_list.items():
            if metadata.binary_value is not None:
                result[metadata_name] = metadata.binary_value
        return result

    def load_binary_from_dict(self, media_file_dict):
        for md_name, md in self.metadata_list.items():
            if md_name in media_file_dict:
                md.set_binary_value(media_file_dict[md_name])

    def load_from_dict(self, media_file_dict):
        for md_name, md in self.metadata_list.items():
            if md_name in media_file_dict:
                md.set_value(media_file_dict[md_name])
