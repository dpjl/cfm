from pathlib import Path

from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.BatchTool import with_progression
from camerafile.core.Constants import SIGNATURE, FACES, CFM_CAMERA_MODEL
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.processor.BatchComputeNecessarySignaturesMultiProcess import BatchComputeNecessarySignaturesMultiProcess
from camerafile.tools.PdfFile import PdfFile

LOGGER = Logger(__name__)


class CameraFilesProcessor:

    @staticmethod
    def load_media_set(media_set_path):
        LOGGER.write_title_2(str(media_set_path), "Opening media directory")
        return MediaSet(media_set_path)

    @staticmethod
    def train_faces(dir_path):
        media_set = MediaSet(dir_path)
        media_set.train()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Reset faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(title="Delete faces",
                      short_title="Delete faces")
    def batch_delete_faces(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata[FACES].value = None
            media_file.metadata[FACES].binary_value = None
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    def reset_faces(dir_path):
        media_set = MediaSet(dir_path)

        CameraFilesProcessor.batch_delete_faces(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Analyze (duplicates / comparison)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def get_duplicates_report(duplicates, media_set):
        str_list = ["All media files: " + str(len(media_set.media_file_list)),
                    "Distinct elements: {distinct}".format(distinct=str(sum(map(len, duplicates.values()))))]
        for n_copy, media_list_list in sorted(duplicates.items()):
            str_list.append("%s elem. found %s times" % (len(media_list_list), n_copy))
        return str_list

    @staticmethod
    def dup(dir_1_path):
        media_set = MediaSet(dir_1_path)
        CameraFilesProcessor.analyse_duplicates(media_set)
        media_set.save_database()
        media_set.close_database()

    @staticmethod
    def analyse_duplicates(media_set):

        BatchComputeNecessarySignaturesMultiProcess(media_set).execute()

        duplicates = media_set.duplicates()
        duplicates_report = CameraFilesProcessor.get_duplicates_report(duplicates, media_set)

        LOGGER.display_starting_line()
        print("█ Found duplicates:")
        tab = ConsoleTable()
        tab.print_header(str(media_set.root_path))
        tab.print_multi_line(duplicates_report)

        if True:
            pdf_file = PdfFile(str(media_set.output_directory.path / "duplicates.pdf"))

            for n_copy, media_list_list in sorted(duplicates.items()):
                if n_copy != 1:
                    for media_list in media_list_list:
                        for media in media_list:
                            pdf_file.add_media_image(media)
                        pdf_file.new_line()

            pdf_file.save()

        pdf_file = PdfFile(str(media_set.output_directory.path / "edited.pdf"))

        for date in media_set.date_model_size_map:
            for model in media_set.date_model_size_map[date]:
                if model is not None and model != "" and len(media_set.date_model_size_map[date][model]) > 1:
                    for dim in media_set.date_model_size_map[date][model]:
                        for media in media_set.date_model_size_map[date][model][dim]:
                            pdf_file.add_media_image(media)
                            break
                    pdf_file.new_line()

        pdf_file.save()

    @staticmethod
    def cmp(media_set1, media_set2):
        BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()

        duplicates_1 = media_set1.duplicates()
        duplicates_2 = media_set2.duplicates()

        duplicates_1_report = CameraFilesProcessor.get_duplicates_report(duplicates_1, media_set1)
        duplicates_2_report = CameraFilesProcessor.get_duplicates_report(duplicates_2, media_set2)

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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    DB
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def db_cmp(dir_1_path, dir_2_path):
        db1 = MediaSetDatabase(OutputDirectory(Path(dir_1_path).resolve()))
        db2 = MediaSetDatabase(OutputDirectory(Path(dir_2_path).resolve()))
        db1.compare(db2)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Reset camera models
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(title="Delete cfm camera models",
                      short_title="Delete")
    def batch_delete_cm(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata[CFM_CAMERA_MODEL] = None
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    def reset_cm(dir_path):
        media_set = MediaSet(dir_path)

        CameraFilesProcessor.batch_delete_cm(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Reset signatures
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(title="Delete signatures",
                      short_title="Delete")
    def batch_delete_signature(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata[SIGNATURE].value = None
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    def reset_signature(dir_path):
        media_set = MediaSet(dir_path)

        CameraFilesProcessor.batch_delete_signature(media_set)
