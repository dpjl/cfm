import concurrent
import shutil
import logging
from concurrent.futures.thread import ThreadPoolExecutor
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


def with_progression_thread(batch_title="", threads=1):
    def with_progression_outer(f):
        @wraps(f)
        def with_progression_inner(input_list, *args):

            CameraFilesProcessor.display_starting_line()
            progress_bar = ConsoleProgressBar(len(input_list), batch_title)
            LOGGER.info("Start batch <{title}>".format(title=batch_title))
            try:
                walk, task = f(input_list, *args)
                with ThreadPoolExecutor(max_workers=threads) as executor:
                    future_list = {executor.submit(task, item, progress_bar): item for item in walk()}
                    for future in concurrent.futures.as_completed(future_list):
                        data = future.result()
            finally:
                progress_bar.stop()
                ExifTool.stop()
                LOGGER.info("End batch <{title}>".format(title=batch_title))
                CameraFilesProcessor.display_ending_line()
            return None

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
    @with_progression(batch_title="Delete external metadata cache")
    def batch_delete_metadata_cache(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_metadata_cache()
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Organize media files")
    def batch_organize(media_file_list, progress_bar=None):
        result = {}
        for media_file in media_file_list:
            report = media_file.organize()
            status = report[0]
            if status not in result:
                result[status] = 0
            result[status] += 1
            if progress_bar is not None:
                progress_bar.increment()
        tab = ConsoleTable()
        tab.print_header("Status", "Number")
        for status in result:
            tab.print_line(status, str(result[status]))

    @staticmethod
    @with_progression(batch_title="Copy media files")
    def batch_copy(media_file_list, new_media_set, progress_bar=None):
        result = {}
        for media_file in media_file_list:
            status = media_file.copy(new_media_set)
            if status not in result:
                result[status] = 0
            result[status] += 1
            if progress_bar is not None:
                progress_bar.increment()
        tab = ConsoleTable()
        tab.print_header("Status", "Number")
        for status in result:
            tab.print_line(status, str(result[status]))

    @staticmethod
    def compute_one_signature(media_file, progress_bar):
        media_file.metadata.compute_value(SIGNATURE)
        if progress_bar is not None:
            progress_bar.increment()

    @staticmethod
    @with_progression(batch_title="Compute signatures")
    def batch_compute_signature(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            CameraFilesProcessor.compute_one_signature(media_file, progress_bar)

    @staticmethod
    @with_progression_thread(batch_title="Compute signatures", threads=2)
    def batch_compute_signature2(media_file_list):

        def walk():
            for media_file in media_file_list:
                yield media_file

        def task(media_file, progress_bar=None):
            media_file.metadata.compute_value(SIGNATURE)
            if progress_bar is not None:
                progress_bar.increment()

        return walk, task

    @staticmethod
    @with_progression(batch_title="Delete signatures")
    def batch_delete_signature(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_computed_value(SIGNATURE)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    def dup(dir_1_path):
        media_set1 = MediaSet(dir_1_path)
        str_list1 = media_set1.analyze_duplicates()
        tab = ConsoleTable()
        tab.print_header(str(media_set1.root_path))
        tab.print_multi_line(str_list1)

    @staticmethod
    def cmp(dir_1_path, dir_2_path):
        media_set1 = MediaSet(dir_1_path)
        media_set2 = MediaSet(dir_2_path)

        str_list1 = media_set1.analyze_duplicates()
        str_list2 = media_set2.analyze_duplicates()

        only_in_dir1 = media_set1.get_files_not_in(media_set2)
        only_in_dir2 = media_set2.get_files_not_in(media_set1)
        in_the_two_dirs = media_set1.get_files_in(media_set2)

        tab = ConsoleTable()
        tab.print_header(str(media_set1.root_path), str(media_set2.root_path))
        tab.print_multi_line(str_list1, str_list2)
        tab.print_line('+ %s distinct (%s files)' % (len(only_in_dir1), sum(map(len, only_in_dir1.values()))), '')
        tab.print_line('', '+ %s distinct (%s files)' % (len(only_in_dir2), sum(map(len, only_in_dir2.values()))))
        tab.print_line('%s distinct' % len(in_the_two_dirs))

    @staticmethod
    def organize_media(input_dir_path):
        media_set = MediaSet(input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_organize(media_set.get_copied_files())

    @staticmethod
    def copy_media(input_dir_path, output_directory):
        media_set = MediaSet(input_dir_path)
        media_set2 = MediaSet(output_directory)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_copy(media_set, media_set2)

    @staticmethod
    def delete_metadata(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))
        CameraFilesProcessor.batch_delete_external_metadata(media_set)

    @staticmethod
    def delete_metadata_cache(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))
        CameraFilesProcessor.batch_delete_metadata_cache(media_set)

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
        with media_set:
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
    def status(media_set):
        LOGGER.info("{l1} files have a camera model, "
                    "{l2} have a recovered one, "
                    "{l3} do not have one".
                    format(l1=len(media_set.get_file_list(cm="known")),
                           l2=len(media_set.get_file_list(cm="recovered")),
                           l3=len(media_set.get_file_list(cm="unknown"))))

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
