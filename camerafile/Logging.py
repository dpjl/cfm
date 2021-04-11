import logging

from camerafile.ExifTool import ExifTool
from camerafile.OutputDirectory import OutputDirectory
from camerafile.Resource import Resource


def init_logging(base_path):
    output_directory = OutputDirectory(base_path)
    logging_handlers = Resource.logging_configuration["handlers"]
    info_file = logging_handlers["info_file_handler"]["filename"]
    error_file = logging_handlers["error_file_handler"]["filename"]
    logging_handlers["info_file_handler"]["filename"] = str(output_directory.path / info_file)
    logging_handlers["error_file_handler"]["filename"] = str(output_directory.path / error_file)
    logging.config.dictConfig(Resource.logging_configuration)

    ExifTool.init(stdout_file_path=output_directory.path / "exif-stdout.txt",
                  stderr_file_path=output_directory.path / "exif-stderr.txt")


def init_only_console_logging():
    Resource.logging_configuration["root"]["handlers"] = ["console"]
    logging.config.dictConfig(Resource.logging_configuration)