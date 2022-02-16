import logging
from multiprocessing import cpu_count

import sys

from camerafile.core.OutputDirectory import OutputDirectory


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
        self.org_format = ""
        self.debug = False
        self.initialized = False

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

            if args.thumbnails:
                self.thumbnails = True

            if "keep_size" in args and args.keep_size:
                self.face_detection_keep_image_size = True

            if args.debug:
                self.debug = True
                logging.getLogger().setLevel(logging.DEBUG)

            if "format" in args and args.format:
                if "dir2" in args and args.dir2:
                    self.load_format(args.format, args.dir2)

            self.initialized = True

    def load_format(self, format_arg: str, dir_2: str):
        format_file = OutputDirectory(dir_2).path / ".format"
        if format_file.exists():
            save_format = format_file.read_text()
            if format_arg is not None and format_arg != "" and format_arg != save_format:
                print("Error: format in argument differs from format save in " + str(format_file))
                print("If you really want to force changing the destination format, please remove this file "
                      "and launch again cfm.")
                sys.exit(1)
            else:
                self.org_format = save_format
        else:
            format_file.write_text(format_arg)
            self.org_format = format_arg
