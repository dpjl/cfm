from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.processor.BatchComputeNecessarySignaturesMultiProcess import BatchComputeNecessarySignaturesMultiProcess
from camerafile.tools.PdfFile import PdfFile

LOGGER = Logger(__name__)


class CompareMediaSets:

    @staticmethod
    def execute(media_set1: MediaSet, media_set2: MediaSet):
        BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()

        duplicates_1 = media_set1.duplicates()
        duplicates_2 = media_set2.duplicates()

        duplicates_1_report = media_set1.get_duplicates_report(duplicates_1)
        duplicates_2_report = media_set2.get_duplicates_report(duplicates_2)

        in_the_two_dirs_1, only_in_dir1 = media_set1.cmp(media_set2)
        in_the_two_dirs_2, only_in_dir2 = media_set2.cmp(media_set1)

        LOGGER.display_starting_line()
        print("█ Comparison result ")
        tab = ConsoleTable()
        tab.print_header(str(media_set1.root_path), str(media_set2.root_path))
        tab.print_multi_line(duplicates_1_report, duplicates_2_report)
        tab.print_line('+ %s distinct (%s files)' % (len(only_in_dir1), sum(map(len, only_in_dir1))), '')
        tab.print_line('', '+ %s distinct (%s files)' % (len(only_in_dir2), sum(map(len, only_in_dir2))))
        tab.print_line('%s distinct' % len(in_the_two_dirs_1))

        pdf_file = PdfFile(str(media_set1.output_directory.path / "only_left.pdf"))

        for media_list in only_in_dir1:
            for media in media_list:
                pdf_file.add_media_image(media)
            pdf_file.new_line()

        pdf_file.save()

        # pdf_file2 = PdfFile(str(media_set1.output_directory.path / "only_right.pdf"))

        # for media_list in only_in_dir2:
        #    for media in media_list:
        #        pdf_file2.add_media_image(media)
        #    pdf_file2.new_line()

        # pdf_file2.save()

        LOGGER.info(media_set1.output_directory.save_list([item for sublist in only_in_dir1 for item in sublist],
                                                          "only-left.json"))
        LOGGER.info(media_set1.output_directory.save_list([item for sublist in only_in_dir2 for item in sublist],
                                                          "only-right.json"))
