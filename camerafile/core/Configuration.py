import logging
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

    def init(self, args):
        if not self.initialized:

            self.args = args

            if args.workers is not None:
                self.nb_sub_process = args.workers

            if args.use_db:
                self.use_db_for_cache = True

            if args.use_dump:
                self.use_dump_for_cache = True

            if args.exit_on_error:
                self.exit_on_error = True

            if "generate_pdf" in args and args.generate_pdf:
                self.generate_pdf = True

            if "no_internal_read" in args and args.no_internal_read:
                self.internal_read = False

            if args.thumbnails:
                self.thumbnails = True

            if "keep_size" in args and args.keep_size:
                self.face_detection_keep_image_size = True

            if args.debug:
                self.debug = True
                logging.getLogger("camerafile").setLevel(logging.DEBUG)

            if "format" in args and args.format:
                self.org_format = args.format

            if args.cache_path:
                self.cache_path = args.cache_path

            if args.ignore:
                self.ignore_list = args.ignore

            if "collision_policy" in args and args.collision_policy:
                from camerafile.task.CopyFile import CollisionPolicy
                self.collision_policy = CollisionPolicy(args.collision_policy)

            if "ignore_duplicates" in args and args.ignore_duplicates:
                self.ignore_duplicates = args.ignore_duplicates

            if "watch" in args and args.watch:
                self.watch = args.watch

            if "mode" in args and args.mode:
                from camerafile.fileaccess.FileAccess import CopyMode
                self.copy_mode = CopyMode(args.mode)

            if "no_progress" in args and args.no_progress:
                self.progress = not args.no_progress

            if "post_processing_script" in args and args.post_processing_script:
                self.pp_script = args.post_processing_script

            self.initialized = True
