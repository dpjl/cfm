import logging

from typing import Dict

from camerafile.Metadata import Metadata, CAMERA_MODEL, DATE, SIGNATURE, ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, \
    ORIGINAL_MOVE_PATH, DESTINATION_MOVE_PATH, WIDTH, HEIGHT, ORIENTATION, FACES
from camerafile.MetadataCameraModel import MetadataCameraModel
from camerafile.MetadataFaces import MetadataFaces
from camerafile.MetadataSignature import MetadataSignature

LOGGER = logging.getLogger(__name__)


class MetadataList:
    metadata_list: Dict[str, Metadata]
    COMPUTE_PREFIX = "Computed "

    def __init__(self, media_file):
        self.media_file = media_file
        self.metadata_list = {CAMERA_MODEL: MetadataCameraModel(media_file),
                              DATE: Metadata(media_file),
                              WIDTH: Metadata(media_file),
                              HEIGHT: Metadata(media_file),
                              ORIENTATION: Metadata(media_file),
                              ORIGINAL_COPY_PATH: Metadata(media_file),
                              DESTINATION_COPY_PATH: Metadata(media_file),
                              ORIGINAL_MOVE_PATH: Metadata(media_file),
                              DESTINATION_MOVE_PATH: Metadata(media_file),
                              SIGNATURE: MetadataSignature(media_file),
                              FACES: MetadataFaces(media_file.id, media_file.path,
                                                   media_file.parent_set.face_rec.knn_clf)}

    def __getitem__(self, key):
        return self.metadata_list[key]

    def __setitem__(self, key, value):
        self.metadata_list[key] = value

    def set_value(self, name, value):
        self[name].value = value
        # Why that ?? I don't remember. TODO !
        self.load_from_media(name)

    def get_value(self, name):
        # Here only because we wan't to load every exif data only one time
        # TO CHANGE
        self.read_value(name)
        return self[name].get()

    def read_value(self, name):
        if self[name].get_value_read() is None:
            self.load_from_media(name)
        return self[name].get_value_read()

    def compute_value(self, name):
        self[name].compute_value()
        value = self[name].get_value_computed()
        return value

    def delete_computed_value(self, name):
        if self[name].get_value_computed() is not None:
            self[name].reset_value()

    def load_from_media(self, name):
        if name in [DATE, CAMERA_MODEL, WIDTH, HEIGHT, ORIENTATION]:
            model, date, width, height, orientation = self.media_file.get_metadata()
            self.set_metadata_read_value(DATE, date)
            self.set_metadata_read_value(CAMERA_MODEL, model)
            self.set_metadata_read_value(WIDTH, width)
            self.set_metadata_read_value(HEIGHT, height)
            self.set_metadata_read_value(ORIENTATION, orientation)

            self.media_file.parent_set.update_date_and_name_map(self.media_file)

    def set_metadata_read_value(self, metadata_name, value):
        if value is not None:
            self[metadata_name].set_value_read(value)
        else:
            self[metadata_name].set_value_read(Metadata.UNKNOWN)

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

            # For compatibility with old versions
            old_set = False
            if isinstance(md, MetadataCameraModel):
                if md_name in media_file_dict and isinstance(media_file_dict[md_name], str):
                    md.set_value_read(media_file_dict[md_name])
                    old_set = True

            if MetadataList.COMPUTE_PREFIX + md_name in media_file_dict:
                md.set_value_computed(media_file_dict[MetadataList.COMPUTE_PREFIX + md_name])

            if not old_set and md_name in media_file_dict:
                md.set_value(media_file_dict[md_name])
