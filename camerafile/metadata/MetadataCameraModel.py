import logging
from typing import TYPE_CHECKING

from camerafile.core.Constants import CFM_CAMERA_MODEL
from camerafile.metadata.Metadata import Metadata

if TYPE_CHECKING:
    from camerafile.core.MediaFile import MediaFile

LOGGER = logging.getLogger(__name__)


class MetadataCameraModel(Metadata):
    MULTIPLE = "Multiple-camera-models"

    def __init__(self, media_file: "MediaFile"):
        super().__init__(media_file)
        self.value = None

    def compute_value(self):
        if self.value is None:
            if self.media_file.parent_dir is not None:
                parent_dir_cm: MetadataCameraModel = self.media_file.parent_dir.metadata[CFM_CAMERA_MODEL]
                if parent_dir_cm.value is not None:
                    if parent_dir_cm.value != MetadataCameraModel.MULTIPLE:
                        self.value = parent_dir_cm.value
                else:
                    parent_dir_cm.compute_value()
                    self.value = parent_dir_cm.value

    def set_value(self, new_model):
        if new_model is not None:
            if self.value is None:
                self.value = new_model
            elif self.value != new_model:
                self.value = MetadataCameraModel.MULTIPLE
            if self.value is not None:
                if self.media_file.parent_dir is not None:
                    parent_dir_cm = self.media_file.parent_dir.metadata[CFM_CAMERA_MODEL]
                    parent_dir_cm.set_value(self.value)
