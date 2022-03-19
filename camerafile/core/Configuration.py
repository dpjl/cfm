import logging
from multiprocessing import cpu_count

from camerafile.mdtools.MdConstants import MetadataNames


class Configuration:
    __instance = None

    def __init__(self):
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
        self.exif_tool = True
        self.internal_read = True

    @staticmethod
    def get():
        if Configuration.__instance is None:
            Configuration.__instance = Configuration()
        return Configuration.__instance

    def init(self, args):
        if not self.initialized:
            if args.workers is not None:
                self.nb_sub_process = args.workers

            if args.use_db:
                self.use_db_for_cache = True

            if args.use_dump:
                self.use_dump_for_cache = True

            if args.password:
                self.cfm_sync_password = args.password.encode()

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

            self.initialized = True


