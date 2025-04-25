from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.Logging import Logger
from camerafile.core.MediaDuplicateManager import MediaDuplicateManager
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory

LOGGER = Logger(__name__)


class CompareMediaSets:

    @staticmethod
    def execute(media_set1: MediaSet, media_set2: MediaSet):
        duplicates_1 = MediaDuplicateManager.duplicates_map(media_set1)
        duplicates_2 = MediaDuplicateManager.duplicates_map(media_set2)

        duplicates_1_report = MediaDuplicateManager.get_duplicates_report(media_set1, duplicates_1)
        duplicates_2_report = MediaDuplicateManager.get_duplicates_report(media_set2, duplicates_2)

        in_the_two_dirs_1, only_in_dir1 = media_set1.cmp(media_set2)
        _, only_in_dir2 = media_set2.cmp(media_set1)

        LOGGER.display_starting_line()
        print("█ Comparison result ")
        tab = ConsoleTable()
        tab.print_header(str(media_set1.root_path), str(media_set2.root_path))
        tab.print_multi_line(duplicates_1_report, duplicates_2_report)
        tab.print_line('+ %s distinct (%s files)' % (len(only_in_dir1), sum(map(len, only_in_dir1))), '')
        tab.print_line('', '+ %s distinct (%s files)' % (len(only_in_dir2), sum(map(len, only_in_dir2))))
        tab.print_line('%s distinct' % len(in_the_two_dirs_1))

        LOGGER.info(OutputDirectory.get(media_set1.root_path)
                    .save_list([item for sublist in only_in_dir1 for item in sublist], "only-left.json"))
        LOGGER.info(OutputDirectory.get(media_set1.root_path)
                    .save_list([item for sublist in only_in_dir2 for item in sublist], "only-right.json"))
