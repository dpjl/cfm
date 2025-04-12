import ast
import logging
import os
from argparse import Namespace
from multiprocessing import cpu_count
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class Configuration:
    __instance = None

    def __init__(self):
        self.args = None
        self.cfm_sync_password = None
        self.nb_sub_process = cpu_count()
        self.generate_pdf = False
        self.thumbnails = False
        self.face_detection_keep_image_size = False
        self.use_dump_for_cache = False
        self.save_db = False
        self.exit_on_error = False
        self.org_format = None
        self.debug = False
        self.initialized = False
        self.exif_tool = False
        self.internal_read = True
        self.first_output_directory = None
        self.cache_path = None
        self.ignore_list = None
        self.collision_policy = None
        self.ignore_duplicates = False
        self.delete_in_target = False
        self.watch = False
        self.sync_delay = 60
        self.copy_mode = None
        self.progress = True
        self.pp_script = None
        self.whatsapp = False
        self.whatsapp_date_update = False
        self.whatsapp_db = None
        self.whatsapp_db_name = None
        self.ui = False

    @staticmethod
    def get() -> "Configuration":
        if Configuration.__instance is None:
            Configuration.__instance = Configuration()
        return Configuration.__instance

    def load(self, key):
        pass
    
    def get_command(self):
        return self.get_param("COMMAND", "command")
        
    def get_dir1(self):
        return self.get_param("DIR1", "dir1")
    
    def get_dir2(self):
        return self.get_param("DIR2", "dir2")

    def get_arg_value(self, arg_name, default_value=None):
        return getattr(self.args, arg_name, default_value)
        
    def get_param(self, env_name, arg_name, default_value=None):
        if os.getenv(env_name) is not None:
            return os.getenv(env_name)
        else:
            return self.get_arg_value(arg_name, default_value)
        
    def get_int_param(self, env_name, arg_name, default_value=None):
        if os.getenv(env_name) is not None:
            return int(os.getenv(env_name))
        else:
            return self.get_arg_value(arg_name, default_value)
        
    def get_bool_param(self, env_name, arg_name, default_value=None):
        if os.getenv(env_name) is not None:
            return os.getenv(env_name).lower() in ["1", "true"]
        else:
            return self.get_arg_value(arg_name, default_value)


    def init(self, args):
        if not self.initialized:
            from camerafile.cfm import ANALYZE_CMD
            from camerafile.cfm import ORGANIZE_CMD

            self.args: Namespace = args

            if args.debug:
                self.debug = True
                logging.getLogger("camerafile").setLevel(logging.DEBUG)

            nb_workers = self.get_int_param("NB_WORKERS", "workers")
            if nb_workers is not None:
                self.nb_sub_process = nb_workers
            
            self.cache_path = self.get_param("CACHE_PATH", "cache_path")
            self.use_dump_for_cache = args.use_dump
            self.save_db = self.get_bool_param("SAVE_DB", "save_db")
            self.exit_on_error = args.exit_on_error
            self.thumbnails = self.get_bool_param("THUMBNAILS", "thumbnails")
            self.ignore_list = args.ignore
            self.ui = self.get_bool_param("UI", "ui")
            self.whatsapp_date_update = self.get_bool_param("WHATSAPP_DATE_UPDATE", "whatsapp_date_update")
            self.whatsapp_db_name = self.get_param("WHATSAPP_DB", "whatsapp_db")
            self.whatsapp = self.get_bool_param("WHATSAPP", "whatsapp")
            if self.whatsapp_date_update or self.whatsapp_db_name:
                self.whatsapp = True
            self.load_whatsapp_db(self.whatsapp_db_name)

            default_ignore_from_env = ast.literal_eval(os.getenv("IGNORE")) if os.getenv("IGNORE") is not None else None
            if self.ignore_list is None:
                self.ignore_list = default_ignore_from_env

            self.progress = self.get_bool_param("PROGRESS", "progress", True)
            if args.no_progress:
                self.progress = False

            if self.get_command() == ANALYZE_CMD:
                self.generate_pdf = self.get_bool_param("GENERATE_PDF", "generate_pdf", False)
                self.internal_read = not self.get_bool_param("NO_INTERNAL_READ", "no_internal_read", False)

            if self.get_command() == ORGANIZE_CMD:
                from camerafile.task.CopyFile import CollisionPolicy
                from camerafile.fileaccess.FileAccess import CopyMode
                
                self.ignore_duplicates = self.get_bool_param("IGNORE_DUPLICATES", "ignore_duplicates")
                self.org_format = self.get_param("ORG_FORMAT", "format")
                self.collision_policy = CollisionPolicy(self.get_param("COLLISION_POLICY", "collision_policy", CollisionPolicy.RENAME_PARENT))
                self.delete_in_target = self.get_bool_param("DELETE_IN_TARGET", "delete_in_target")
                self.copy_mode = CopyMode(self.get_param("MODE", "mode", CopyMode.HARD_LINK))
                self.watch = self.get_bool_param("WATCH", "watch")
                self.pp_script = self.get_param("POST_PROCESSING_SCRIPT", "post_processing_script")

                self.sync_delay = self.get_param("SYNC_DELAY", "sync_delay", self.sync_delay)
                
            self.initialized = True

    def load_whatsapp_db(self, whatsapp_db):
        if whatsapp_db is not None:
            import sqlite3
            self.whatsapp_db = {}
            file_connection = sqlite3.connect(whatsapp_db)
            cursor = file_connection.cursor()
            cursor.execute("""SELECT 
                                message_media.file_path, available_message_view.received_timestamp
                            FROM
                                available_message_view INNER JOIN message_media
                            ON
                                available_message_view._id = message_media.message_row_id""")
            for (file_path, timestamp) in cursor:
                if file_path is not None:
                    self.whatsapp_db[Path(file_path).name] = timestamp
            LOGGER.debug("%s: %s media loaded", whatsapp_db, len(self.whatsapp_db))
