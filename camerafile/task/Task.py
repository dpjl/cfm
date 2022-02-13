from camerafile.core import Configuration


class Task:

    @staticmethod
    def init():
        if not Configuration.initialized:
            from camerafile.cfm import configure
            from camerafile.cfm import create_main_args_parser
            parser = create_main_args_parser()
            args = parser.parse_args()
            configure(args)
            Configuration.initialized = True
