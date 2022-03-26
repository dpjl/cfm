import logging

from typing import Dict, TYPE_CHECKING

from camerafile.core.Constants import INTERNAL, SIGNATURE, FACES, ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, \
    ORIGINAL_MOVE_PATH, DESTINATION_MOVE_PATH, CFM_CAMERA_MODEL, THUMBNAIL, ORIGINAL_PATH
from camerafile.metadata.Metadata import Metadata
from camerafile.metadata.MetadataCameraModel import MetadataCameraModel
from camerafile.metadata.MetadataFaces import MetadataFaces
from camerafile.metadata.MetadataInternal import MetadataInternal
from camerafile.metadata.MetadataSignature import MetadataSignature
from camerafile.metadata.MetadataThumbnail import MetadataThumbnail

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from camerafile.core.MediaFile import MediaFile


class MetadataList:
    metadata_list: Dict[str, Metadata]
    COMPUTE_PREFIX = "Computed "

    def __init__(self, media_file: "MediaFile"):
        self.media_file = media_file

        self.metadata_list = {CFM_CAMERA_MODEL: MetadataCameraModel(media_file),
                              INTERNAL: MetadataInternal(media_file.file_access),
                              THUMBNAIL: MetadataThumbnail(media_file.file_access),
                              ORIGINAL_COPY_PATH: Metadata(media_file),
                              DESTINATION_COPY_PATH: Metadata(media_file),
                              ORIGINAL_PATH: Metadata(media_file),
                              ORIGINAL_MOVE_PATH: Metadata(media_file),
                              DESTINATION_MOVE_PATH: Metadata(media_file),
                              SIGNATURE: MetadataSignature(media_file.file_access),
                              FACES: MetadataFaces(media_file.file_access, media_file.parent_set.face_rec.knn_clf)}

    def update_file_access(self, file_access):
        self.metadata_list[INTERNAL].file_access = file_access
        self.metadata_list[THUMBNAIL].file_access = file_access
        self.metadata_list[SIGNATURE].file_access = file_access
        self.metadata_list[FACES].file_access = file_access

    def __getitem__(self, key):
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
