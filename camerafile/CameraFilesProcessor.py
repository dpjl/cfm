import shutil
import logging
from functools import wraps

from camerafile.ConsoleTable import ConsoleTable
from camerafile.ExifTool import ExifTool
from camerafile.Metadata import CAMERA_MODEL, SIGNATURE
from camerafile.OutputFile import OutputFile
from camerafile.MediaDirectory import MediaDirectory
from camerafile.ConsoleProgressBar import ConsoleProgressBar

LOGGER = logging.getLogger(__name__)


def with_progression(batch_title=""):
    def with_progression_outer(f):
        @wraps(f)
        def with_progression_inner(called_object, input_list, *args, progress_bar=None):

            CameraFilesProcessor.display_starting_line()
            progress_bar = ConsoleProgressBar(len(input_list), batch_title)
            LOGGER.info("Start batch <{title}>".format(title=batch_title))
            try:
                ret = f(called_object, input_list, *args, progress_bar)
            finally:
                progress_bar.stop()
                ExifTool.stop()
                LOGGER.info("End batch <{title}>".format(title=batch_title))
                CameraFilesProcessor.display_ending_line()
            return ret

        return with_progression_inner

    return with_progression_outer


class CameraFilesProcessor:

    def __init__(self, input_dir_path):
        self.input_dir_path = input_dir_path

    @with_progression(batch_title="Read camera models")
    def batch_read_cm(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.read_value(CAMERA_MODEL)
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Try to recover camera models")
    def batch_compute_cm(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.compute_value(CAMERA_MODEL)
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Reset camera models")
    def batch_delete_cm(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_computed_value(CAMERA_MODEL)
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Delete external metadata files")
    def batch_delete_external_metadata(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_metadata_file()
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Reorganize media files")
    def batch_move(self, media_file_list, output_directory, progress_bar=None):
        for media_file in media_file_list:
            media_file.move(output_directory)
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Undo reorganize media files")
    def batch_unmove(self, media_file_list, output_directory, progress_bar=None):
        for media_file in media_file_list:
            media_file.unmove(output_directory)
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Compute signatures")
    def batch_compute_signature(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.compute_value(SIGNATURE)
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Delete signatures")
    def batch_delete_signature(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_computed_value(SIGNATURE)
            if progress_bar is not None:
                progress_bar.increment()

    def cmp(self, dir2):
        media_dir = MediaDirectory(self.input_dir_path)
        media_dir2 = MediaDirectory(dir2)

        str_list1 = media_dir.analyze_duplicates()
        str_list2 = media_dir2.analyze_duplicates()

        only_in_dir1, duplicates_dir1 = media_dir > media_dir2
        only_in_dir2, duplicates_dir2 = media_dir2 > media_dir
        in_the_two_dirs = media_dir == media_dir2

        tab = ConsoleTable()
        tab.print_header(str(media_dir.path), str(media_dir2.path))
        tab.print_multi_line(str_list1, str_list2)
        tab.print_line('+ %s files (%s dup.)' % (len(only_in_dir1), duplicates_dir1), '')
        tab.print_line('', '+ %s files (%s dup.)' % (len(only_in_dir2), duplicates_dir2))
        tab.print_line('%s files' % len(in_the_two_dirs))

    def move(self, output_directory):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_dir)))

        self.batch_move(media_dir, output_directory)

    def unmove(self, output_directory):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_dir)))

        self.batch_unmove(media_dir, output_directory)

    def delete_metadata(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_dir)))
        self.batch_delete_external_metadata(media_dir)

    def delete_cm(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_dir)))

        self.batch_delete_cm(media_dir)

    def compute_signature(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_dir)))

        self.batch_compute_signature(media_dir)

    def delete_signature(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_dir)))

        self.batch_delete_signature(media_dir)

    def compute_cm(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file".format(l1=len(media_dir)))

        self.batch_read_cm(media_dir)
        self.status(media_dir)

        self.batch_compute_cm(media_dir.get_file_list(cm="unknown"))
        self.status(media_dir)

        OutputFile.save_list(media_dir.get_file_list(cm="unknown"),
                             "unknown-camera-model-of-files.json")
        OutputFile.save_list(media_dir.get_file_list(cm="recovered"),
                             "recovered-camera-model-of-files.json")

    @staticmethod
    def status(media_dir):
        LOGGER.info("{l1} files have a camera model, "
                    "{l2} have a recovered one, "
                    "{l3} do not have one".
                    format(l1=len(media_dir()),
                           l2=len(media_dir(cm="recovered")),
                           l3=len(media_dir(cm="unknown"))))

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
