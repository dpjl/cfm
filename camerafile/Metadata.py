import logging

LOGGER = logging.getLogger(__name__)

CAMERA_MODEL = "Camera Model"
SIGNATURE = "Hash"
DATE = "Creation Date"
ORIGINAL_PATH = "Original Path"
DESTINATION_PATH = "Destination Path"


class Metadata:
    UNKNOWN = "Unknown"

    def __init__(self, media_file):
        self.media_file = media_file
        self.value_read = None
        self.value_computed = None

    def __str__(self):
        return self.get()

    def get(self):
        if self.value_computed is not None:
            return self.value_computed
        return self.value_read

    def set_value_read(self, value):
        self.value_read = value

    def set_value_computed(self, value):
        self.value_computed = value

    def compute_value(self):
        return self.value_computed
