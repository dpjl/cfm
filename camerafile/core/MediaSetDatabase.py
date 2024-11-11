import json
import os
import sqlite3
from datetime import datetime
from json import JSONDecodeError
from typing import Dict, Iterable
from typing import TYPE_CHECKING

import dill

from camerafile.core.Configuration import Configuration
from camerafile.core.Constants import THUMBNAIL
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.fileaccess.FileDescription import FileDescription

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet

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

    def __init__(self, output_directory, db_file=None, thb_db_file=None):
        self.cfm_file = db_file
        self.info_file = None
        self.thb_file = thb_db_file
        if self.cfm_file is None and output_directory is not None:
            self.cfm_file = output_directory.path / "cfm.db"
        if self.info_file is None and output_directory is not None:
            self.info_file = output_directory.path / "info.db"
        if self.thb_file is None and output_directory is not None:
            self.thb_file = output_directory.path / "thb.db"
        self.cache_db_connection = None
        self.info_db_connection = None
        self.thb_db_connection = None
        self.is_active = Configuration.get().use_db_for_cache or self.exists()
        self.save_info = Configuration.get().save_db

    @staticmethod
    def get(output_directory, db_file=None, thb_db_file=None):
        db_id = str(output_directory.path) if output_directory is not None else ""
        if db_file is not None:
            db_id += db_file
        if thb_db_file is not None:
            db_id += thb_db_file
        if db_id not in MediaSetDatabase.__instance:
            MediaSetDatabase.__instance[db_id] = MediaSetDatabase(output_directory, db_file, thb_db_file)
        return MediaSetDatabase.__instance[db_id]

    def initialize_cfm_connection(self):
        if self.is_active:
            if self.cache_db_connection is None:
                self.cache_db_connection = DBConnection(self.cfm_file)
                self.initialize_cache_db()
                
    def initialize_info_connection(self):
        if self.save_info:
            if self.info_db_connection is None:
                self.info_db_connection = DBConnection(self.info_file, True)
                self.initialize_info_db()

    def initialize_thb_connection(self):
        if Configuration.get().thumbnails:
            if self.thb_db_connection is None:
                self.thb_db_connection = DBConnection(self.thb_file)
                self.initialize_thb_db()

    def exists(self):
        return self.cfm_file.exists()

    def save(self, media_file_list: "Iterable[MediaFile]", log=True):

        if self.is_active:
            if self.cache_db_connection:
                if log and self.is_active:
                    LOGGER.info("Saving cache " + str(self.cache_db_connection.db_path))
                for media_file in media_file_list:
                    self.save_media_file(media_file)
                self.cache_db_connection.file_connection.commit()

        if self.save_info:
            self.initialize_info_connection()
            LOGGER.info("Saving info db " + str(self.info_db_connection.db_path))
            for media_file in media_file_list:
                self.save_info_media_file(media_file)
            self.info_db_connection.file_connection.commit()
            self.close()          

        if Configuration.get().thumbnails:
            if self.thb_db_connection:
                if log:
                    LOGGER.info("Saving thumbnails cache " + str(self.thb_db_connection.db_path))
                for media_file in media_file_list:
                    self.save_thumbnail(media_file)
                self.thb_db_connection.file_connection.commit()

        # Use to reduce size of db if rows or data have been deleted. Put this in specific option.
        # self.cache_db_connection.file_connection.execute("VACUUM")
        # self.thb_db_connection.file_connection.execute("VACUUM")

    def close(self):
        if self.cache_db_connection:
            self.cache_db_connection.file_connection.close()
            self.cache_db_connection = None
        if self.info_db_connection:
            self.info_db_connection.file_connection.close()
            self.info_db_connection = None
        if self.thb_db_connection:
            self.thb_db_connection.file_connection.close()
            self.thb_db_connection = None

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

    @staticmethod
    def new_media_file(media_set: "MediaSet", file_desc: FileDescription, file_id, json_m, binary_m):

        metadata = json.loads(json_m) if json_m is not None else "{}"
        binary_metadata = dill.loads(binary_m) if binary_m is not None else "{}"
        try:
            media_dir = media_set.create_media_dir_parent(file_desc.relative_path)

            new_media_file = MediaFile(file_desc, media_dir, media_set)
            new_media_file.metadata.load_from_dict(metadata)
            new_media_file.metadata.load_binary_from_dict(binary_metadata)
            new_media_file.db_id = file_id
            new_media_file.exists_in_db = True
            return new_media_file
        except JSONDecodeError:
            print("Invalid json in database: %s" % file_desc.relative_path)
            return None

    def load_all_files(self, media_set: "MediaSet", not_loaded_files: Dict[str, FileDescription]):

        if not self.is_active:
            return not_loaded_files

        self.initialize_cfm_connection()

        for media_file in media_set:
            media_file.exists_in_db = False

        try:
            nb_loaded = 0
            nb_total = 0
            nb_deleted = 0
            log_content = "{loaded}/{total} loaded from db " + str(self.cfm_file)

            LOGGER.start(log_content, prof=2, update_freq=1000)
            LOGGER.update(loaded=nb_loaded, total=nb_total, deleted=nb_deleted)

            cursor = self.cache_db_connection.cursor
            cursor.execute('select * from metadata')
            text_fields, other_fields = self.get_columns_ids(cursor.description)
            for result in cursor:
                if result is not None and len(result) >= 1:
                    file_path = result[text_fields["file"]]
                    nb_total += 1
                    if file_path in media_set.filename_map:
                        media_set.filename_map[file_path].exists_in_db = True

                    elif file_path in not_loaded_files:
                        file_id = result[text_fields["file_id"]]
                        json_m = result[text_fields["jm"]]
                        bin_m = result[text_fields["bm"]]
                        media_file = self.new_media_file(media_set, not_loaded_files[file_path], file_id, json_m, bin_m)
                        if media_file is not None:
                            media_set.add_file(media_file)
                            del not_loaded_files[file_path]
                            nb_loaded += 1
                    else:
                        nb_deleted += 1
                        file_id = result[text_fields["file_id"]]
                        self.delete_media_file(file_id)
                LOGGER.update(loaded=nb_loaded, total=nb_total, deleted=nb_deleted)
        except BaseException as e:
            print("can't load database: " + str(e))
            raise
        LOGGER.end(loaded=nb_loaded, total=nb_total, deleted=nb_deleted)
        return not_loaded_files

    def load_all_thumbnails(self, media_set: "MediaSet"):

        if not Configuration.get().thumbnails:
            return

        for media_file in media_set:
            media_file.thumbnail_in_db = False

        self.initialize_thb_connection()

        try:
            number_of_files = 0
            nb_deleted = 0
            LOGGER.start("{nb_file} thumbnails found in cache " + str(self.thb_file), prof=2, update_freq=1000)
            LOGGER.update(nb_file=number_of_files)

            cursor = self.thb_db_connection.cursor
            cursor.execute('select file_id, thb from thb')
            for result in cursor:
                if result is not None and len(result) >= 1:
                    file_id = result[0]
                    thb_data = result[1]
                    try:
                        if file_id in media_set.id_map:
                            media_file: MediaFile = media_set.get_media(file_id)
                            media_file.metadata[THUMBNAIL].thumbnail = thb_data
                            media_file.thumbnail_in_db = True
                            number_of_files += 1
                        else:
                            nb_deleted += 1
                            self.delete_thb(file_id)
                    except JSONDecodeError:
                        print("Invalid json in database for id: %s" % file_id)
                LOGGER.update(nb_file=number_of_files)

        except BaseException as e:
            print("can't load database: " + str(e))
            raise
        LOGGER.end(nb_file=number_of_files)

    def delete_media_file(self, file_id):
        try:
            self.cache_db_connection.cursor.execute('''delete from metadata where file_id = ?''', file_id)
        except sqlite3.IntegrityError:
            print("Integrity error when deleting media with id " + str(file_id))

    def delete_thb(self, file_id):
        try:
            self.thb_db_connection.cursor.execute('''delete from thb where file_id = ?''', file_id)
        except sqlite3.IntegrityError:
            print("Integrity error when deleting media with id " + str(file_id))

    def save_info_media_file(self, media_file: MediaFile):
        self.info_db_connection.cursor.execute(
            '''insert into
                    media_info(file, date, cm, size, width, height)
                values
                    (?, ?, ?, ?, ?, ?)''',
            (media_file.get_path(), media_file.get_str_date('%Y-%m-%dT%H:%M:%SZ'), media_file.get_camera_model(), media_file.get_file_size(), 0, 0))


    def save_media_file(self, media_file: MediaFile):
        media_file_dict = media_file.metadata.save_to_dict()
        json_data = json.dumps(media_file_dict)

        binary_media_file_dict = media_file.metadata.save_binary_to_dict()
        bin_data = dill.dumps(binary_media_file_dict)
        if media_file.exists_in_db and not self.save_info:
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
            # TODO: is file_id always the rowid ?
            media_file.db_id = self.cache_db_connection.cursor.lastrowid
        media_file.exists_in_db = True

    def save_thumbnail(self, media_file: MediaFile):
        thumbnail_data = media_file.metadata[THUMBNAIL].thumbnail
        if media_file.thumbnail_in_db:
            try:
                self.thb_db_connection.cursor.execute(
                    '''update
                            thb
                       set
                            file = ?, thb = ?
                       where
                            file_id = ? and thb is not ?''',
                    (media_file.get_path(), thumbnail_data, media_file.db_id, thumbnail_data))
            except sqlite3.IntegrityError:
                print("Integrity error when updating media " + str(media_file))
        else:
            self.thb_db_connection.cursor.execute(
                '''insert into
                        thb(file_id, file, thb)
                   values
                        (?, ?, ?)''',
                (media_file.id, media_file.get_path(), thumbnail_data))
        media_file.thumbnail_in_db = True

    def load_database_in_dict(self):
        data_dict = {}
        self.cache_db_connection.execute('select * from metadata')
        result_list = self.cache_db_connection.cursor.fetchall()
        text_fields, other_fields = self.get_columns_ids(self.cache_db_connection.cursor.description)
        for result in result_list:
            if result is not None and len(result) >= 1:
                data_dict[result[text_fields["file"]]] = json.loads(result[text_fields["jm"]])
                data_dict[result[text_fields["file"]]]["file"] = result[text_fields["file"]]
                data_dict[result[text_fields["file"]]]["cfm-cm"] = None
                # data_dict[result[text_fields["file"]]]["faces"] = None
                # data_dict[result[text_fields["file"]]]["hash"] = None
                if "internal" in data_dict[result[text_fields["file"]]]:
                    data_dict[result[text_fields["file"]]]["internal"]["width"] = None
                    data_dict[result[text_fields["file"]]]["internal"]["height"] = None
                data_dict[result[text_fields["file"]]].pop('Faces', None)
        return data_dict

    def compare(self, db2):
        import sys
        import difflib

        db1 = self.load_database_in_dict()
        db2 = db2.load_database_in_dict()

        for file_path in db1:
            if file_path not in db2:
                print(str(file_path) + " is in (1) but not in (2)")
                continue
            d1 = json.dumps(db1[file_path], indent=4, sort_keys=True)
            d2 = json.dumps(db2[file_path], indent=4, sort_keys=True)
            sys.stdout.writelines(difflib.unified_diff([d1], [d2]))
