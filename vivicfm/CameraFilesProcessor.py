import logging
import shutil
from functools import wraps
from vivicfm.ExifTool import ExifTool
from vivicfm.OutputFile import OutputFile
from vivicfm.MediaDirectory import MediaDirectory
from vivicfm.ConsoleProgressBar import ConsoleProgressBar

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
    def batch_read(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.camera_model.read()
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Try to recover camera models")
    def batch_try_to_recover(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.camera_model.try_to_recover()
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Reset camera models")
    def batch_reset_cm(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.camera_model.reset_external_metadata()
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Delete external metadata files")
    def batch_delete_external_metadata(self, media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.external_metadata.delete_file()
            if progress_bar is not None:
                progress_bar.increment()

    @with_progression(batch_title="Reorganize media files")
    def batch_reorganize(self, media_file_list, output_directory, progress_bar=None):
        for media_file in media_file_list:
            media_file.move(output_directory)
            if progress_bar is not None:
                progress_bar.increment()

    def organize(self, output_directory):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file".format(l1=len(media_dir.get_all_media_files())))

        self.batch_reorganize(media_dir.get_all_media_files(), output_directory)

    def undo_recover_camera_model(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file".format(l1=len(media_dir.get_all_media_files())))

        self.batch_reset_cm(media_dir.get_all_media_files())

    def delete_metadata(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file".format(l1=len(media_dir.get_all_media_files())))
        self.batch_delete_external_metadata(media_dir.get_all_media_files())

    def recover_camera_model(self):
        media_dir = MediaDirectory(self.input_dir_path)
        LOGGER.info("{l1} files detected as media file".format(l1=len(media_dir.get_all_media_files())))

        self.batch_read(media_dir.get_all_media_files())
        self.status(media_dir)

        self.batch_try_to_recover(media_dir.get_files_with_unknown_camera_model())
        self.status(media_dir)

        OutputFile.save_list(media_dir.get_files_with_unknown_camera_model(), "unknown-camera-model-of-files.json")
        OutputFile.save_list(media_dir.get_files_with_recovered_camera_model(), "recovered-camera-model-of-files.json")

    @staticmethod
    def status(media_dir):
        LOGGER.info("{l1} files have a camera model, "
                    "{l2} have a recovered one, "
                    "{l3} do not have one".
                    format(l1=len(media_dir.get_files_with_camera_model()),
                           l2=len(media_dir.get_files_with_recovered_camera_model()),
                           l3=len(media_dir.get_files_with_unknown_camera_model())))

    @staticmethod
    def display_starting_line():
        console_width = shutil.get_terminal_size((80, 20)).columns - 1
        line = '\n{text:{fill}{align}{width}}'.format(
            text='',
            fill='-',
            align='<',
            width=console_width,
        )
        print(line)

    @staticmethod
    def display_ending_line():
        console_width = shutil.get_terminal_size((80, 20)).columns - 1
        line = '{text:{fill}{align}{width}}\n'.format(
            text='',
            fill='-',
            align='<',
            width=console_width,
        )
        print(line)
