import pickle

import time

from camerafile.core.Configuration import Configuration as Conf
from camerafile.core.Constants import THUMBNAIL, INTERNAL
from camerafile.core.Logging import Logger

LOGGER = Logger(__name__)


class MediaSetDump:
    __instance = {}

    def __init__(self, output_directory):
        self.dump_file = output_directory.path / 'cfm.dump'
        self.is_active = Conf.get().use_dump_for_cache or self.exists() or not Conf.get().use_db_for_cache

    @staticmethod
    def get(output_directory):
        if output_directory not in MediaSetDump.__instance:
            MediaSetDump.__instance[output_directory] = MediaSetDump(output_directory)
        return MediaSetDump.__instance[output_directory]

    def exists(self):
        return self.dump_file.exists()

    def load(self, media_set):
        if self.is_active and self.exists():
            with open(self.dump_file, "rb") as file:
                LOGGER.info("Restoring dump...")
                loaded = pickle.load(file)
                LOGGER.debug("New MediaSet object loaded: " + str(id(self)))
                media_set.media_file_list = loaded.media_file_list
                media_set.media_dir_list = loaded.media_dir_list
                media_set.date_size_map = loaded.date_size_map
                media_set.date_sig_map = loaded.date_sig_map
                media_set.id_map = loaded.id_map
                media_set.filename_map = loaded.filename_map
                return True
        return False

    def save(self, media_set):
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
