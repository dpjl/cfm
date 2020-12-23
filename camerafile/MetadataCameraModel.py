import logging
from camerafile.Metadata import Metadata, CAMERA_MODEL

LOGGER = logging.getLogger(__name__)

COMPUTED = "Computed"
READ = "Read"


class MetadataCameraModel(Metadata):
    MULTIPLE = "Multiple-camera-models"

    def __init__(self, media_file):
        super().__init__(media_file)
        self.value = {COMPUTED: None, READ: None}

    def get(self):
        if self.value[COMPUTED] is not None:
            return self.value[COMPUTED]
        return self.value[READ]

    def get_value_read(self):
        return self.value[READ]

    def get_value_computed(self):
        return self.value[COMPUTED]

    def set_value_computed(self, value):
        self.value[COMPUTED] = value

    def reset_value(self, value):
        self.value[COMPUTED] = value

    def compute_value(self):
        if (self.value[READ] == Metadata.UNKNOWN or self.value[READ] is None) and self.value[COMPUTED] is None:
            if self.media_file.parent_dir is not None:
                parent_dir_cm = self.media_file.parent_dir.metadata[CAMERA_MODEL]
                if parent_dir_cm.value[
                    READ] is not None:  # ne peut pas être UNKNOWN, car on ne propage pas cette valeur
                    if parent_dir_cm.value[READ] != MetadataCameraModel.MULTIPLE:
                        self.value[COMPUTED] = parent_dir_cm.value[READ]
                else:
                    parent_dir_cm.compute_value()
                    self.value[COMPUTED] = parent_dir_cm.value[COMPUTED]

    def set_value_read(self, new_model):
        if self.value[READ] is None:
            self.value[READ] = new_model
        elif self.value[READ] != new_model:  # ne peut survenir que pour un répertoire
            self.value[READ] = MetadataCameraModel.MULTIPLE
        if self.value[READ] is not None and self.value[READ] != Metadata.UNKNOWN:
            if self.media_file.parent_dir is not None:
                parent_dir_cm = self.media_file.parent_dir.metadata[CAMERA_MODEL]
                parent_dir_cm.set_value_read(self.value[READ])
