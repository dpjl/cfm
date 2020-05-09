import shutil
import logging
from functools import wraps

from camerafile.ConsoleTable import ConsoleTable
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import CAMERA_MODEL, SIGNATURE
from camerafile.MediaSet import MediaSet
from camerafile.ConsoleProgressBar import ConsoleProgressBar

LOGGER = logging.getLogger(__name__)


def with_progression(batch_title=""):
    def with_progression_outer(f):
        @wraps(f)
        def with_progression_inner(input_list, *args, progress_bar=None):

            CameraFilesProcessor.display_starting_line()
            progress_bar = ConsoleProgressBar(len(input_list), batch_title)
            LOGGER.info("Start batch <{title}>".format(title=batch_title))
            try:
                ret = f(input_list, *args, progress_bar)
            finally:
                progress_bar.stop()
                ExifTool.stop()
                LOGGER.info("End batch <{title}>".format(title=batch_title))
                CameraFilesProcessor.display_ending_line()
            return ret

        return with_progression_inner

    return with_progression_outer


class CameraFilesProcessor:

    @staticmethod
    @with_progression(batch_title="Read camera models")
    def batch_read_cm(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.read_value(CAMERA_MODEL)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Try to recover camera models")
    def batch_compute_cm(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.compute_value(CAMERA_MODEL)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Reset camera models")
    def batch_delete_cm(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_computed_value(CAMERA_MODEL)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Delete external metadata files")
    def batch_delete_external_metadata(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_metadata_file()
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Reorganize media files")
    def batch_move(media_file_list, output_directory, progress_bar=None):
        for media_file in media_file_list:
            media_file.move(output_directory)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Undo reorganize media files")
    def batch_unmove(media_file_list, output_directory, progress_bar=None):
        for media_file in media_file_list:
            media_file.unmove(output_directory)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Compute signatures")
    def batch_compute_signature(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.compute_value(SIGNATURE)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Delete signatures")
    def batch_delete_signature(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_computed_value(SIGNATURE)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    def cmp(dir_1_path, dir_2_path):
        media_set1 = MediaSet(dir_1_path)
        media_set2 = MediaSet(dir_2_path)

        str_list1 = media_set1.analyze_duplicates()
        str_list2 = media_set2.analyze_duplicates()

        only_in_dir1, duplicates_dir1 = media_set1 > media_set2
        only_in_dir2, duplicates_dir2 = media_set2 > media_set1
        in_the_two_dirs = media_set1 == media_set2

        tab = ConsoleTable()
        tab.print_header(str(media_set1.root_path), str(media_set2.root_path))
        tab.print_multi_line(str_list1, str_list2)
        tab.print_line('+ %s files (%s dup.)' % (len(only_in_dir1), duplicates_dir1), '')
        tab.print_line('', '+ %s files (%s dup.)' % (len(only_in_dir2), duplicates_dir2))
        tab.print_line('%s files' % len(in_the_two_dirs))

    @staticmethod
    def move(input_dir_path, output_directory):
        media_set = MediaSet(input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_move(media_set, output_directory)

    @staticmethod
    def unmove(dir_1_path, dir_2_path):
        media_set = MediaSet(dir_1_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_unmove(media_set, dir_2_path)

    @staticmethod
    def delete_metadata(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))
        CameraFilesProcessor.batch_delete_external_metadata(media_set)

    @staticmethod
    def reset_cm(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_delete_cm(media_set)

    @staticmethod
    def compute_signature(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_compute_signature(media_set)

    @staticmethod
    def reset_signature(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_delete_signature(media_set)

    @staticmethod
    def find_cm(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file".format(l1=len(media_set)))

        CameraFilesProcessor.batch_read_cm(media_set)
        CameraFilesProcessor.status(media_set)

        CameraFilesProcessor.batch_compute_cm(media_set.get_file_list(cm="unknown"))
        CameraFilesProcessor.status(media_set)

        media_set.output_directory.save_list(media_set.get_file_list(cm="unknown"),
                                             "unknown-camera-model-of-files.json")
        media_set.output_directory.save_list(media_set.get_file_list(cm="recovered"),
                                             "recovered-camera-model-of-files.json")

    @staticmethod
    def remove_cache():
        print("Remove cache")

    @staticmethod
    def copy_media():
        print("Copy media")

    @staticmethod
    def move_media():
        print("Move media")

    @staticmethod
    def status(media_set):
        LOGGER.info("{l1} files have a camera model, "
                    "{l2} have a recovered one, "
                    "{l3} do not have one".
                    format(l1=len(media_set()),
                           l2=len(media_set(cm="recovered")),
                           l3=len(media_set(cm="unknown"))))

    @staticmethod
    def display_starting_line():
        console_width = shutil.get_terminal_size((80, 20)).columns - 1
        line = '\n{text:{fill}{align}{width}}'.format(
            text='', fill='-', align='<', width=console_width,
        )
        print(line)

    @staticmethod
    def display_ending_line():
        console_width = shutil.get_terminal_size((80, 20)).columns - 1
        line = '{text:{fill}{align}{width}}\n'.format(
            text='', fill='-', align='<', width=console_width,
        )
        print(line)
