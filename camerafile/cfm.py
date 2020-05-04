import sys
import logging
import logging.config
from pathlib import Path

from camerafile.AviMetaEdit import AviMetaEdit
from camerafile.OutputDirectory import OutputDirectory
from camerafile.Resource import Resource
from camerafile.CameraFilesProcessor import CameraFilesProcessor
from camerafile.ExifTool import ExifTool

BASE_OUTPUT_PATH = Path("cfm-wip")
LOGGER = logging.getLogger(__name__)


def execute_program(input_dir_path, action, output_directory):

    cmp = CameraFilesProcessor(input_dir_path)

    if action == "camera-model-check":
        cmp.recover_camera_model()

    if action == "reset-camera-model":
        cmp.undo_recover_camera_model()

    if action == "delete-metadata":
        cmp.delete_metadata()

    if action == "reorganize":
        cmp.organize(output_directory)


def load_logging():
    lc = Resource.logging_configuration
    info_file = lc["handlers"]["info_file_handler"]["filename"]
    error_file = lc["handlers"]["error_file_handler"]["filename"]
    lc["handlers"]["info_file_handler"]["filename"] = str(OutputDirectory.path / info_file)
    lc["handlers"]["error_file_handler"]["filename"] = str(OutputDirectory.path / error_file)
    logging.config.dictConfig(lc)


def main():
    if len(sys.argv) <= 1:
        LOGGER.error("No arguments. At least an input directory is required as first argument")
        sys.exit(0)

    input_dir_path = Path(sys.argv[1])

    action = "camera-model-check"
    if len(sys.argv) > 2:
        action = sys.argv[2]

    output_directory = None
    if len(sys.argv) > 3:
        output_directory = sys.argv[3]

    OutputDirectory.init(BASE_OUTPUT_PATH, input_dir_path)
    Resource.init()
    load_logging()

    ExifTool.init(stdout_file_path=OutputDirectory.path / "exif-stdout.txt",
                  stderr_file_path=OutputDirectory.path / "exif-stderr.txt")

    AviMetaEdit.init(stdout_file_path=OutputDirectory.path / "avimetaedit-stdout.txt",
                     stderr_file_path=OutputDirectory.path / "avimetaedit-stderr.txt")

    try:
        LOGGER.info("cfm started with options: %s" % " ".join(sys.argv))
        execute_program(input_dir_path, action, output_directory)
    finally:
        LOGGER.info("cfm ended")


if __name__ == '__main__':
    main()
