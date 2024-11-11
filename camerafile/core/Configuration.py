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
        self.use_db_for_cache = False
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
        self.watch = False
        self.sync_delay = 60
        self.copy_mode = None
        self.progress = True
        self.pp_script = None
        self.whatsapp = False
        self.whatsapp_force_date = False
        self.whatsapp_db = None

    @staticmethod
    def get():
        if Configuration.__instance is None:
            Configuration.__instance = Configuration()
        return Configuration.__instance

    def load(self, key):
        pass

    def init(self, args):
        if not self.initialized:
            from camerafile.cfm import ANALYZE_CMD
            from camerafile.cfm import ORGANIZE_CMD

            self.args: Namespace = args

            if args.debug:
                self.debug = True
                logging.getLogger("camerafile").setLevel(logging.DEBUG)

            if args.workers is not None:
                self.nb_sub_process = args.workers

            self.use_db_for_cache = args.use_db
            self.use_dump_for_cache = args.use_dump
            self.save_db = args.save_db
            self.exit_on_error = args.exit_on_error
            self.thumbnails = args.thumbnails
            self.cache_path = args.cache_path
            self.ignore_list = args.ignore
            self.whatsapp_force_date = "whatsapp+" in args and args.__getattribute__("whatsapp+")
            self.whatsapp = self.whatsapp_force_date or args.whatsapp
            self.load_whatsapp_db(args.whatsapp_db)

            default_ignore_from_env = ast.literal_eval(os.getenv("IGNORE")) if os.getenv("IGNORE") is not None else None
            if self.ignore_list is None:
                self.ignore_list = default_ignore_from_env

            if args.command == ANALYZE_CMD:
                self.generate_pdf = args.generate_pdf
                self.internal_read = not args.no_internal_read

            if args.command == ORGANIZE_CMD:
                from camerafile.task.CopyFile import CollisionPolicy
                from camerafile.fileaccess.FileAccess import CopyMode

                self.org_format = args.format
                self.collision_policy = CollisionPolicy(args.collision_policy)
                self.ignore_duplicates = args.ignore_duplicates
                self.copy_mode = CopyMode(args.mode)
                self.watch = args.watch
                
                if args.sync_delay is not None:
                    self.sync_delay = args.sync_delay
                
                self.progress = not args.no_progress
                self.pp_script = args.post_processing_script

                if os.getenv("WATCH") is not None:
                    if os.getenv("WATCH").lower() in ["1", "true"]:
                        self.watch = True
                    else:
                        self.watch = False
                        
                if os.getenv("SAVE_DB") is not None:
                    if os.getenv("SAVE_DB").lower() in ["1", "true"]:
                        self.save_db = True
                    else:
                        self.save_db = False

                if os.getenv("PROGRESS") is not None:
                    if os.getenv("PROGRESS").lower() in ["1", "true"]:
                        self.progress = True
                    else:
                        self.progress = False

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
            LOGGER.debug(f"{whatsapp_db}: {len(self.whatsapp_db)} media loaded")
