import logging
from camerafile.mdtools.MdConstants import MetadataNames

LOGGER = logging.getLogger(__name__)


class Metadata:

    def __init__(self):
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

    def get_md_value(self, md_name):
        if self.value is not None:
            if md_name.value in self.value:
                return self.value[md_name.value]
        return None

    def get_date(self):
        return self.get_md_value(MetadataNames.CREATION_DATE)

    def get_last_modification_date(self):
        return self.get_md_value(MetadataNames.MODIFICATION_DATE)
