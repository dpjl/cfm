import logging

LOGGER = logging.getLogger(__name__)


class Metadata:

    def __init__(self, media_file):
        self.media_file = media_file
        self.value = None
        self.binary_value = None

    def __str__(self):
        return self.get()

    def get(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def set_binary_value(self, value):
        self.binary_value = value

    def reset_value(self):
        self.value = None

