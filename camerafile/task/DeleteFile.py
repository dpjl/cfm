from camerafile.core import Configuration


class DeleteFile:

    @staticmethod
    def execute(file_access):
        if not Configuration.initialized:
            from camerafile.cfm import configure
            from camerafile.cfm import create_main_args_parser
            parser = create_main_args_parser()
            args = parser.parse_args()
            configure(args)
            Configuration.initialized = True
        try:
            return file_access.delete_file()
        except BaseException as e:
            print(e)
            return False, file_access.id, None
