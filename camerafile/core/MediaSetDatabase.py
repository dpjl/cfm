import os
import os
import sqlite3
from typing import Iterable
from typing import TYPE_CHECKING

from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile

if TYPE_CHECKING:
    pass

LOGGER = Logger(__name__)


class DBConnection:
    def __init__(self, db_path, delete_existing_database = False):
        self.db_path = db_path
        if delete_existing_database and os.path.exists(db_path):
            os.remove(db_path)
        self.new_database = not os.path.exists(db_path)
        self.file_connection = sqlite3.connect(db_path)
        self.cursor = self.file_connection.cursor()
        self.cursor.execute("PRAGMA journal_mode = MEMORY")

    def execute(self, cmd):
        return self.cursor.execute(cmd)

    def commit(self):
        return self.file_connection.commit()


class MediaSetDatabase:
    __instance = {}

    def __init__(self, output_directory):
        self.info_file = None
        if self.info_file is None and output_directory is not None:
            self.info_file = output_directory.path / "info.db"
        self.info_db_connection = None
        self.save_info = Configuration.get().save_db

    @staticmethod
    def get(output_directory)-> "MediaSetDatabase":
        db_id = str(output_directory.path) if output_directory is not None else ""
        if db_id not in MediaSetDatabase.__instance:
            MediaSetDatabase.__instance[db_id] = MediaSetDatabase(output_directory)
        return MediaSetDatabase.__instance[db_id]

    def initialize_info_connection(self):
        if self.save_info:
            if self.info_db_connection is None:
                self.info_db_connection = DBConnection(self.info_file, True)
                self.initialize_info_db()

    def save(self, media_file_list: "Iterable[MediaFile]", log=True):
        if self.save_info:
            self.initialize_info_connection()
            LOGGER.info("Saving info db " + str(self.info_db_connection.db_path))
            for media_file in media_file_list:
                self.save_info_media_file(media_file)
            self.info_db_connection.file_connection.commit()
            self.close()

    def close(self):
        if self.info_db_connection:
            self.info_db_connection.file_connection.close()
            self.info_db_connection = None

    def initialize_info_db(self):
        self.info_db_connection.execute('''CREATE TABLE media_info(
                                    file_id INTEGER PRIMARY KEY,
                                    file TEXT,
                                    date TEXT,
                                    cm TEXT,
                                    size INTEGER,
                                    width INTEGER,
                                    height INTEGER)''')
        self.info_db_connection.execute('''CREATE INDEX idx_date ON media_info(date)''')
        self.info_db_connection.commit()

    def save_info_media_file(self, media_file: MediaFile):
        self.info_db_connection.cursor.execute(
            '''insert into
                    media_info(file, date, cm, size, width, height)
                values
                    (?, ?, ?, ?, ?, ?)''',
            (media_file.get_path(),
             media_file.get_str_date('%Y-%m-%dT%H:%M:%SZ'),
             media_file.get_camera_model(),
             media_file.get_file_size(),
             0,
             0))

