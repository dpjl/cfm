import logging
from camerafile.AviMetaEdit import AviMetaEdit
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import Metadata, CAMERA_MODEL

LOGGER = logging.getLogger(__name__)


class MetadataCameraModel(Metadata):
    MULTIPLE = "Multiple-camera-models"
    IMAGES_UPDATABLE_BY_EXIF_TOOL = [".jpg", ".jpeg"]
    VIDEOS_UPDATABLE_BY_EXIF_TOOL = [".mp4", ".mov"]
    VIDEOS_UPDATABLE_BY_AVI_META_EDIT = [".avi"]

    def __init__(self, media_file):
        super().__init__(media_file)

    def compute_value(self):
        if self.value_read == Metadata.UNKNOWN and self.value_computed is None:
            if self.media_file.parent_dir is not None:
                parent_dir_cm = self.media_file.parent_dir.metadata[CAMERA_MODEL]
                if parent_dir_cm.value_read is not None:
                    if parent_dir_cm.value_read != MetadataCameraModel.MULTIPLE:
                        self.value_computed = parent_dir_cm.value_read
                else:
                    parent_dir_cm.compute_value()
                    self.value_computed = parent_dir_cm.value_computed

    def set_value_read(self, new_model):
        if self.value_read is None:
            self.value_read = new_model
        elif self.value_read != new_model:
            self.value_read = MetadataCameraModel.MULTIPLE
        if self.value_read is not None and self.value_read != Metadata.UNKNOWN:
            if self.media_file.parent_dir is not None:
                parent_dir_cm = self.media_file.parent_dir.metadata[CAMERA_MODEL]
                parent_dir_cm.set_value_read(self.value_read)

    def update_media_with_recovered(self):
        if self.value_computed is not None:
            self.media_file.backup()
            if self.media_file.extension in MetadataCameraModel.IMAGES_UPDATABLE_BY_EXIF_TOOL:
                ExifTool.update_model(self.media_file.path, self.value_computed)

            elif self.media_file.extension in MetadataCameraModel.VIDEOS_UPDATABLE_BY_EXIF_TOOL:
                ExifTool.update_source(self.media_file.path, self.value_computed)

            elif self.media_file.extension in MetadataCameraModel.VIDEOS_UPDATABLE_BY_AVI_META_EDIT:
                AviMetaEdit.update_source(self.media_file.path, self.value_computed)
            else:
                LOGGER.error("Metadata of this file can't be updated "
                             "with this version of the tool: {file_name}"
                             .format(file_name=self.media_file.name))
