import logging
import os

LOGGER = logging.getLogger(__name__)


class MediaDate:
    NOT_READ = "Not-yet-read"

    def __init__(self, media):
        self.media = media
        self.value = MediaDate.NOT_READ

    def __str__(self):
        return self.get()

    def get(self):
        self.read()
        return self.value

    def read(self):
        if os.path.isdir(self.media.path):
            LOGGER.error("Metadata of directory can't be read {path}".format(path=self.media.path))
        is_found, self.value = self.media.external_metadata.get_date()
        if not is_found:
            self.media.external_metadata.load_from_media()
            model_found, self.value = self.media.external_metadata.get_date()
