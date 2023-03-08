import logging
from argparse import Namespace
from multiprocessing import cpu_count


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
        self.copy_mode = None
        self.progress = True
        self.pp_script = None

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
            self.exit_on_error = args.exit_on_error
            self.thumbnails = args.thumbnails
            self.cache_path = args.cache_path
            self.ignore_list = args.ignore

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
                self.progress = not args.no_progress
                self.pp_script = args.post_processing_script

            self.initialized = True
