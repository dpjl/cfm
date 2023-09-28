import pickle

import time
from pathlib import Path
from typing import TYPE_CHECKING

from camerafile.core.Configuration import Configuration as Conf
from camerafile.core.Constants import THUMBNAIL, INTERNAL
from camerafile.core.Logging import Logger

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet

LOGGER = Logger(__name__)


class MediaSetDump:
    __instance = {}

    def __init__(self, output_directory_path):
        self.dump_file = Path(output_directory_path) / 'cfm.dump'
        self.is_active = Conf.get().use_dump_for_cache or self.exists() or not Conf.get().use_db_for_cache

    @staticmethod
    def get(output_directory) -> "MediaSetDump":
        if output_directory not in MediaSetDump.__instance:
            MediaSetDump.__instance[output_directory] = MediaSetDump(output_directory.path)
        return MediaSetDump.__instance[output_directory]

    def exists(self):
        return self.dump_file.exists()

    def load(self) -> "MediaSet":
        try:
            if self.is_active and self.exists():
                with open(self.dump_file, "rb") as file:
                    LOGGER.info("Restoring cache...")
                    loaded = pickle.load(file)
                    LOGGER.debug("New MediaSet object loaded: " + str(id(self)))
                    return loaded
        except EOFError:
            LOGGER.info("Cache file was found, but is invalid. Ignore it.")
        return None

    def save(self, media_set: "MediaSet"):
        if self.is_active:
            for media_file in media_set:
                media_file.metadata[INTERNAL].thumbnail = None
                media_file.metadata[THUMBNAIL].thumbnail = None
            with open(self.dump_file, "wb") as file:
                LOGGER.start("Writing " + str(self.dump_file) + "... {result}")
                LOGGER.update(result="")
                start_time = time.time()
                pickle.dump(media_set, file, protocol=pickle.HIGHEST_PROTOCOL)
                processing_time = str(int(time.time() - start_time)) + " seconds."
                LOGGER.end(result=processing_time)
