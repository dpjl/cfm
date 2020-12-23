import logging

LOGGER = logging.getLogger(__name__)

CAMERA_MODEL = "Camera Model"
SIGNATURE = "Hash"
FACES = "Faces"
DATE = "Creation Date"
WIDTH = "Width"
HEIGHT = "Height"
ORIENTATION = "Orientation"
ORIGINAL_COPY_PATH = "Original Copy Path"
DESTINATION_COPY_PATH = "Destination Copy Path"
ORIGINAL_MOVE_PATH = "Original Move Path"
DESTINATION_MOVE_PATH = "Destination Move Path"


class Metadata:
    UNKNOWN = "Unknown"

    def __init__(self, media_file):
        self.media_file = media_file
        self.value = None
        self.binary_value = None

    def __str__(self):
        return self.get()

    def get(self):
        return self.value

    def compute_value(self):
        # Nothing by default
        pass

    def set_value(self, value):
        self.value = value

    def reset_value(self):
        return self.value

    # Deprecated: kept only for compatibility
    def get_value_read(self):
        return self.value

    # Deprecated: kept only for compatibility
    def get_value_computed(self):
        return self.value

    # Deprecated: kept only for compatibility
    def set_value_read(self, value):
        self.value = value

    # Deprecated: kept only for compatibility
    def set_value_computed(self, value):
        self.value = value
