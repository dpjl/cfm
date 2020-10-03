import logging
from camerafile.Metadata import Metadata, CAMERA_MODEL

LOGGER = logging.getLogger(__name__)


class MetadataCameraModel(Metadata):
    MULTIPLE = "Multiple-camera-models"

    def __init__(self, media_file):
        super().__init__(media_file)

    def set_value_computed(self, value):
        self.value_computed = value

    def compute_value(self):
        if (self.value_read == Metadata.UNKNOWN or self.value_read is None) and self.value_computed is None:
            if self.media_file.parent_dir is not None:
                parent_dir_cm = self.media_file.parent_dir.metadata[CAMERA_MODEL]
                if parent_dir_cm.value_read is not None:  # ne peut pas être UNKNOWN, car on ne propage pas cette valeur
                    if parent_dir_cm.value_read != MetadataCameraModel.MULTIPLE:
                        self.value_computed = parent_dir_cm.value_read
                else:
                    parent_dir_cm.compute_value()
                    self.value_computed = parent_dir_cm.value_computed

    def set_value_read(self, new_model):
        if self.value_read is None:
            self.value_read = new_model
        elif self.value_read != new_model:  # ne peut survenir que pour un répertoire
            self.value_read = MetadataCameraModel.MULTIPLE
        if self.value_read is not None and self.value_read != Metadata.UNKNOWN:
            if self.media_file.parent_dir is not None:
                parent_dir_cm = self.media_file.parent_dir.metadata[CAMERA_MODEL]
                parent_dir_cm.set_value_read(self.value_read)
