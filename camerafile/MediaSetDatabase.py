import json
import os
from datetime import datetime
from json import JSONDecodeError
import sqlite3
from pathlib import Path

from camerafile.MediaFile import MediaFile


class MediaSetDatabase:

    def __init__(self, root_path):
        self.db_path = Path(root_path) / 'cfm.db'
        database_exists = os.path.exists(self.db_path)
        self.file_connection = sqlite3.connect(self.db_path)
        self.cursor = self.file_connection.cursor()
        if not database_exists:
            self.initialize_database()

    def initialize_database(self):
        self.cursor.execute('''CREATE TABLE metadata(
                                    file_id INTEGER PRIMARY KEY,
                                    file TEXT,
                                    thumbnail BLOB,
                                    jm TEXT,
                                    last_update_date TIMESTAMP)''')
        self.cursor.execute('''CREATE UNIQUE INDEX idx_file_path ON metadata(file)''')
        self.file_connection.commit()

    def load_all_media_files(self, media_set, progress_signal=None):
        try:
            self.cursor.execute('select file_id, file, thumbnail, jm from metadata')
            result_list = self.cursor.fetchall()
            number_of_files = 0
            for result in result_list:
                if result is not None and len(result) >= 1:
                    file_id = result[0]
                    file_path = str(Path(media_set.root_path / result[1]))
                    thumbnail = result[2]
                    json_content = result[3]
                    try:
                        new_media_file = MediaFile(file_path, media_set.create_media_dir_parent(file_path), media_set)
                        new_media_file.metadata.set_thumbnail(thumbnail)
                        new_media_file.metadata.load_from_dict(json.loads(json_content))
                        new_media_file.loaded_from_database = True
                        new_media_file.db_id = file_id
                        media_set.add_file(new_media_file)

                        number_of_files += 1
                        if progress_signal is not None and number_of_files % 1000 == 0:
                            progress_signal.emit(number_of_files)

                    except JSONDecodeError:
                        print("Invalid json in database: %s" % file_path)
        except:
            print("can't load database")
            raise

    def load_media_file(self, media_file):
        try:
            self.cursor.execute('select file_id, thumbnail, jm from metadata where file="%s"' % media_file.path)
            result = self.cursor.fetchone()
            if result is not None and len(result) >= 1:
                file_id = result[0]
                thumbnail = result[1]
                json_content = result[2]
                try:
                    media_file.metadata.set_thumbnail(thumbnail)
                    media_file.metadata.load_from_dict(json.loads(json_content))
                    media_file.loaded_from_database = True
                    media_file.db_id = file_id
                except JSONDecodeError:
                    print("Invalid json in database: %s" % media_file.path)
        except:
            print("can't load %s" % media_file.path)
            raise

    def save_media_file(self, media_file):
        media_file_dict = media_file.metadata.save_to_dict()
        thumbnail = media_file.metadata.get_thumbnail()
        json_content = json.dumps(media_file_dict)
        if media_file.loaded_from_database:
            if json_content == 0 or json_content == '0':
                print(media_file.path)
            self.cursor.execute(
                '''update
                        metadata set file = ?, thumbnail = ?, jm = ?, last_update_date = ?
                   where
                        file_id = ? and jm is not ?''',
                (media_file.path, thumbnail, json_content,
                 datetime.now(), media_file.db_id, json_content))
        else:
            self.cursor.execute("insert into metadata(file, thumbnail, jm, last_update_date) values(?, ?, ?, ?)",
                                (media_file.path, thumbnail, json_content, datetime.now()))
