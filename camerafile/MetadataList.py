import logging
from typing import Dict
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import Metadata, CAMERA_MODEL, DATE, SIGNATURE, ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, \
    ORIGINAL_MOVE_PATH, DESTINATION_MOVE_PATH
from camerafile.MetadataCameraModel import MetadataCameraModel
from camerafile.MetadataExternalFile import MetadataExternalFile
from camerafile.MetadataSignature import MetadataSignature

LOGGER = logging.getLogger(__name__)


class MetadataList:
    metadata_list: Dict[str, Metadata]
    METADATA_EXTENSION = ".cfm-metadata"
    COMPUTE_PREFIX = "Computed "

    def __init__(self, media_file):
        self.media_file = media_file
        self.metadata_list = {CAMERA_MODEL: MetadataCameraModel(media_file),
                              DATE: Metadata(media_file),
                              ORIGINAL_COPY_PATH: Metadata(media_file),
                              DESTINATION_COPY_PATH: Metadata(media_file),
                              ORIGINAL_MOVE_PATH: Metadata(media_file),
                              DESTINATION_MOVE_PATH: Metadata(media_file),
                              SIGNATURE: MetadataSignature(media_file)}

        ext_metadata_file_path = str(self.media_file.path) + MetadataList.METADATA_EXTENSION
        self.external_metadata = MetadataExternalFile(ext_metadata_file_path,
                                                      self,
                                                      self.media_file.parent_set.create_json_metadata)

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
        self.save_external_metadata()
        return value

    def delete_computed_value(self, name):
        if self[name].value_computed is not None:
            self[name].value_computed = None
        self.save_external_metadata()

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
            self.save_external_metadata()

    def save_to_dict(self):
        result = {}
        for metadata_name, metadata in self.metadata_list.items():
            if metadata.value_read is not None:
                result[metadata_name] = metadata.value_read
            if metadata.value_computed is not None:
                result[MetadataList.COMPUTE_PREFIX + metadata_name] = metadata.value_computed
        return result

    def load_from_dict(self, media_file_dict):
        for md_name, md_value in self.metadata_list.items():
            if md_name in media_file_dict:
                md_value.set_value_read(media_file_dict[md_name])
            if MetadataList.COMPUTE_PREFIX + md_name in media_file_dict:
                md_value.set_value_computed(media_file_dict[MetadataList.COMPUTE_PREFIX + md_name])

    def get_thumbnail(self):
        return self.metadata_list[SIGNATURE].thumbnail

    def set_thumbnail(self, thumbnail):
        self.metadata_list[SIGNATURE].thumbnail = thumbnail

    def save_external_metadata(self):
        json_metadata = self.save_to_dict()
        self.external_metadata.save(json_metadata)

    def delete_metadata_file(self):
        self.external_metadata.delete()
