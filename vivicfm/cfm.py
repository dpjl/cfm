import sys
import logging
import logging.config
from pathlib import Path
from vivicfm.CFMOutputDirectory import CFMOutputDirectory
from vivicfm.CFMResource import CFMResource
from vivicfm.CameraModelProcessor import CameraModelProcessor

BASE_OUTPUT_PATH = Path("cfm-output")
LOGGER = logging.getLogger(__name__)


def execute_program(input_dir_path, action):

    if action == "camera-model-check":
        with CameraModelProcessor(input_dir_path, try_load_cache=True) as cmp:
            cmp.analyze()
            cmp.apply()

    if action == "revert":
        with CameraModelProcessor(input_dir_path, try_load_cache=True) as cmp:
            cmp.revert()

    # duplicationAnalysis = DuplicationAnalysis(input_dir_path, output_dir_path)
    # duplicationAnalysis.computeDuplicated(print_stats=True, save_results=True)


def load_logging():
    lc = CFMResource.logging_configuration
    info_file = lc["handlers"]["info_file_handler"]["filename"]
    error_file = lc["handlers"]["error_file_handler"]["filename"]
    lc["handlers"]["info_file_handler"]["filename"] = str(CFMOutputDirectory.path / info_file)
    lc["handlers"]["error_file_handler"]["filename"] = str(CFMOutputDirectory.path / error_file)
    logging.config.dictConfig(lc)


def main():

    if len(sys.argv) <= 1:
        LOGGER.error("No arguments. At least an input directory is required as first argument")
        sys.exit(0)

    input_dir_path = Path(sys.argv[1])

    action = "camera-model-check"
    if len(sys.argv) > 2:
        action = sys.argv[2]

    CFMOutputDirectory.init(BASE_OUTPUT_PATH, input_dir_path)
    CFMResource.init()
    load_logging()

    try:
        LOGGER.info("cfm started with options: %s" % " ".join(sys.argv))
        execute_program(input_dir_path, action)
    finally:
        LOGGER.info("cfm ended")


if __name__ == '__main__':
    main()
