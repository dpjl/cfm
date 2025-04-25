from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import Logger
from camerafile.core.MediaDuplicateManager import MediaDuplicateManager
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory

LOGGER = Logger(__name__)


class SearchForDuplicates:

    @staticmethod
    def execute(media_set: MediaSet):

        duplicates = MediaDuplicateManager.duplicates_map(media_set)
        duplicates_report = MediaDuplicateManager.get_duplicates_report(media_set, duplicates)

        LOGGER.display_starting_line()
        print("█ Found duplicates:")
        tab = ConsoleTable()
        tab.print_header(str(media_set.root_path))
        tab.print_multi_line(duplicates_report)
