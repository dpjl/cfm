import difflib
import json
import os
import sqlite3
import sys
from datetime import datetime
from json import JSONDecodeError
from typing import Dict, Iterable

import dill

from camerafile.core.Constants import THUMBNAIL
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.fileaccess.FileAccess import FileAccess

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet

LOGGER = Logger(__name__)


class DBConnection:
    def __init__(self, db_path):
        self.db_path = db_path
        self.new_database = not os.path.exists(db_path)
        self.file_connection = sqlite3.connect(self.db_path)
        self.cursor = self.file_connection.cursor()
        self.cursor.execute("PRAGMA journal_mode = MEMORY")

    def execute(self, cmd):
        return self.cursor.execute(cmd)

    def commit(self):
        return self.file_connection.commit()


class MediaSetDatabase:

    def __init__(self, output_directory):
        self.cache_db_connection = DBConnection(output_directory.path / 'cfm.db')
        self.thb_db_connection = DBConnection(output_directory.path / 'thb.db')
        self.initialize_cache_db()
        self.initialize_thb_db()

    def save(self, media_file_list: "Iterable[MediaFile]", log=True):

        if log:
            LOGGER.info("Saving cache " + str(self.cache_db_connection.db_path))
        for media_file in media_file_list:
            self.save_media_file(media_file)
        self.cache_db_connection.file_connection.commit()

        if log:
            LOGGER.info("Saving thumbnails cache " + str(self.thb_db_connection.db_path))
        for media_file in media_file_list:
            self.save_thumbnail(media_file)
        self.thb_db_connection.file_connection.commit()

        # Use to reduce size of db if rows or data have been deleted. Put this in specific option.
        # self.cache_db_connection.file_connection.execute("VACUUM")
        # self.thb_db_connection.file_connection.execute("VACUUM")

    def close(self):
        self.cache_db_connection.file_connection.close()
        self.thb_db_connection.file_connection.close()

    def initialize_cache_db(self):
        if self.cache_db_connection.new_database:
            self.cache_db_connection.execute('''CREATE TABLE metadata(
                                        file_id INTEGER PRIMARY KEY,
                                        file TEXT,
                                        jm TEXT,
                                        bm BLOB,
                                        last_update_date TIMESTAMP)''')
            self.cache_db_connection.execute('''CREATE UNIQUE INDEX idx_file_path ON metadata(file)''')
            self.cache_db_connection.commit()

    def initialize_thb_db(self):
        if self.thb_db_connection.new_database:
            self.thb_db_connection.execute('''CREATE TABLE thb(
                                        file_id TEXT PRIMARY KEY,
                                        file TEXT,
                                        thb BLOB)''')
            self.thb_db_connection.execute('''CREATE UNIQUE INDEX idx_file_path ON thb(file)''')
            self.thb_db_connection.commit()

    def table_columns(self):
        sql = "select * from metadata where 1=0;"
        self.cache_db_connection.execute(sql)
        return [d[0] for d in self.cache_db_connection.cursor.description]

    @staticmethod
    def get_columns_ids(description):
        text = {}
        others = {}
        for n in range(len(description)):
            column_name = description[n][0]
            if column_name in ["file_id", "file", "jm", "bm"]:
                text[column_name] = n
            else:
                others[column_name] = n
        return text, others

    def load_all_files(self, media_set: "MediaSet", found_file_map: Dict[str, FileAccess]):
        try:
            number_of_files = 0
            log_content = "{nb_file} files are already in cache " + str(self.cache_db_connection.db_path)
            LOGGER.start_status_line(log_content, prof=2)
            LOGGER.update_status_line(nb_file=number_of_files)
            self.cache_db_connection.cursor.execute('select * from metadata')
            result_list = self.cache_db_connection.cursor.fetchall()
            text_fields, other_fields = self.get_columns_ids(self.cache_db_connection.cursor.description)
            for result in result_list:
                if result is not None and len(result) >= 1:
                    file = result[text_fields["file"]]
                    file_path = (media_set.root_path / file).as_posix()
                    if file_path in found_file_map:
                        file_id = result[text_fields["file_id"]]
                        json_content = result[text_fields["jm"]]
                        binary_content = result[text_fields["bm"]]
                        metadata = json.loads(json_content) if json_content is not None else "{}"
                        binary_metadata = dill.loads(binary_content) if binary_content is not None else "{}"
                        try:
                            media_dir = media_set.create_media_dir_parent(file_path)

                            new_media_file = MediaFile(found_file_map[file_path], media_dir, media_set)
                            new_media_file.metadata.load_from_dict(metadata)
                            new_media_file.metadata.load_binary_from_dict(binary_metadata)
                            new_media_file.db_id = file_id

                            media_set.add_file(new_media_file)
                            found_file_map[file_path].loaded_from_database = True
                            number_of_files += 1
                        except JSONDecodeError:
                            print("Invalid json in database: %s" % file_path)
                    else:
                        # TODO not found on filesystem, delete from database
                        pass
                LOGGER.update_status_line(nb_file=number_of_files)
        except:
            print("can't load database")
            raise
        LOGGER.end_status_line(nb_file=number_of_files)

    def load_all_thumbnails(self, media_set: "MediaSet"):
        try:
            number_of_files = 0
            LOGGER.start_status_line("{nb_file} thumbnails found in cache " + str(self.thb_db_connection.db_path),
                                     prof=2)
            LOGGER.update_status_line(nb_file=number_of_files)
            self.thb_db_connection.cursor.execute('select file_id, thb from thb')
            result_list = self.thb_db_connection.cursor.fetchall()
            for result in result_list:
                if result is not None and len(result) >= 1:
                    file_id = result[0]
                    thb_data = result[1]
                    try:
                        if file_id in media_set.id_map:
                            media_file = media_set.get_media(file_id)
                            media_file.metadata[THUMBNAIL].thumbnail = thb_data
                            number_of_files += 1
                    except JSONDecodeError:
                        print("Invalid json in database for id: %s" % file_id)
                LOGGER.update_status_line(nb_file=number_of_files)
        except:
            print("can't load database")
            raise
        LOGGER.end_status_line(nb_file=number_of_files)

    def save_media_file(self, media_file: MediaFile):
        media_file_dict = media_file.metadata.save_to_dict()
        json_data = json.dumps(media_file_dict)

        binary_media_file_dict = media_file.metadata.save_binary_to_dict()
        bin_data = dill.dumps(binary_media_file_dict)
        if media_file.file_access.loaded_from_database:
            if json_data == 0 or json_data == '0':
                print(media_file.get_path())
            try:
                self.cache_db_connection.cursor.execute(
                    '''update
                            metadata 
                       set 
                            file = ?, jm = ?, bm = ?, last_update_date = ?
                       where
                            file_id = ? and (jm is not ? or bm is not ?)''',
                    (media_file.get_path(), json_data, bin_data, datetime.now(), media_file.db_id, json_data, bin_data))
            except sqlite3.IntegrityError:
                print("Integrity error when updating media " + str(media_file))
        else:
            self.cache_db_connection.cursor.execute(
                '''insert into 
                        metadata(file, jm, bm, last_update_date)
                   values
                        (?, ?, ?, ?)''',
                (media_file.get_path(), json_data, bin_data, datetime.now()))

    def save_thumbnail(self, media_file: MediaFile):
        thumbnail_data = media_file.metadata[THUMBNAIL].thumbnail
        if media_file.file_access.loaded_from_database:
            try:
                self.thb_db_connection.cursor.execute(
                    '''update
                            thb 
                       set 
                            file = ?, thb = ?
                       where
                            file_id = ? and thb is not ?''',
                    (media_file.get_path(), thumbnail_data, media_file.db_id, thumbnail_data))
                # Vérifier si ligne mise à jour ? Sinon ajouter une nouvelle ligne ?
            except sqlite3.IntegrityError:
                print("Integrity error when updating media " + str(media_file))
        else:
            self.thb_db_connection.cursor.execute(
                '''insert into 
                        thb(file_id, file, thb)
                   values
                        (?, ?, ?)''',
                (media_file.id, media_file.get_path(), thumbnail_data))

    def load_database_in_dict(self):
        data_dict = {}
        self.cache_db_connection.execute('select * from metadata')
        result_list = self.cache_db_connection.cursor.fetchall()
        text_fields, other_fields = self.get_columns_ids(self.cache_db_connection.cursor.description)
        for result in result_list:
            if result is not None and len(result) >= 1:
                data_dict[result[text_fields["file"]]] = json.loads(result[text_fields["jm"]])
                data_dict[result[text_fields["file"]]].pop('Faces', None)
        return data_dict

    def compare(self, db2):
        db1 = self.load_database_in_dict()
        db2 = db2.load_database_in_dict()
        for file_path in db1:
            if file_path not in db2:
                print(str(file_path) + " is in (1) but not in (2)")
                continue
            d1 = json.dumps(db1[file_path], indent=4, sort_keys=True)
            d2 = json.dumps(db2[file_path], indent=4, sort_keys=True)
            sys.stdout.writelines(difflib.unified_diff([d1], [d2]))
