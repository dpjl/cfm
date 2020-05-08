import sys
import logging
import logging.config
from pathlib import Path
from camerafile.ExifTool import ExifTool
from camerafile.Resource import Resource
from camerafile.AviMetaEdit import AviMetaEdit
from camerafile.OutputDirectory import OutputDirectory
from camerafile.CameraFilesProcessor import CameraFilesProcessor

BASE_OUTPUT_PATH = Path("cfm-wip")
LOGGER = logging.getLogger(__name__)


def execute_program(action, input_dir_path, output_dir_path):
    cmp = CameraFilesProcessor(input_dir_path)

    if action == "test":
        cmp.test()

    if action == "cmp":
        cmp.cmp(output_dir_path)

    if action == "cm":
        cmp.compute_cm()

    if action == "delete-cm":
        cmp.delete_cm()

    if action == "sig":
        cmp.compute_signature()

    if action == "delete-sig":
        cmp.delete_signature()

    if action == "delete-metadata":
        cmp.delete_metadata()

    if action == "move":
        cmp.move(output_dir_path)

    if action == "unmove":
        cmp.unmove(output_dir_path)


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

    action = sys.argv[1]
    input_dir_path = Path(sys.argv[2])

    output_dir_path = None
    if len(sys.argv) > 3:
        output_dir_path = sys.argv[3]

    OutputDirectory.init(BASE_OUTPUT_PATH, input_dir_path)
    Resource.init()
    load_logging()

    ExifTool.init(stdout_file_path=OutputDirectory.path / "exif-stdout.txt",
                  stderr_file_path=OutputDirectory.path / "exif-stderr.txt")

    AviMetaEdit.init(stdout_file_path=OutputDirectory.path / "avimetaedit-stdout.txt",
                     stderr_file_path=OutputDirectory.path / "avimetaedit-stderr.txt")

    try:
        LOGGER.info("cfm started with options: %s" % " ".join(sys.argv))
        execute_program(action, input_dir_path, output_dir_path)
    finally:
        LOGGER.info("cfm ended")


if __name__ == '__main__':
    main()
