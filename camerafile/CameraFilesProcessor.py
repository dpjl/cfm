import logging
from pathlib import Path

from camerafile.BatchTool import with_progression, with_progression_thread
from camerafile.ConsoleTable import ConsoleTable
from camerafile.Constants import IMAGE_TYPE
from camerafile.MediaSet import MediaSet
from camerafile.MediaSetDatabase import MediaSetDatabase
from camerafile.Metadata import CAMERA_MODEL, SIGNATURE, FACES, ORIENTATION
from camerafile.MetadataFaces import MetadataFaces
from camerafile.OutputDirectory import OutputDirectory

LOGGER = logging.getLogger(__name__)


class CameraFilesProcessor:

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Find camera models
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
    def find_cm(dir_path):
        media_set = MediaSet(dir_path)
        with media_set:
            LOGGER.info("{l1} files detected as media file".format(l1=len(media_set)))

            CameraFilesProcessor.batch_read_cm(media_set)
            CameraFilesProcessor.status(media_set)

            CameraFilesProcessor.batch_compute_cm(media_set.get_file_list(cm="unknown"))
            media_set.propagate_cm_to_duplicates()
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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Organize files
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
    def organize_media(input_dir_path):
        media_set = MediaSet(input_dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_organize(media_set.get_copied_files())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Copy files
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(batch_title="Copy media files")
    def batch_copy(old_media_set, new_media_set, progress_bar=None):
        result = {}
        not_copied_files = []
        for media_file in old_media_set:
            if progress_bar is not None:
                progress_bar.set_item_text(str(media_file.relative_path))
            status = media_file.copy(new_media_set)
            if status not in result:
                result[status] = 0
            result[status] += 1
            if status != "Copied":
                not_copied_files.append(media_file)
            if progress_bar is not None:
                progress_bar.increment()
        tab = ConsoleTable()
        tab.print_header("Status", "Number")
        for status in result:
            tab.print_line(status, str(result[status]))
        old_media_set.output_directory.save_list(not_copied_files, "not-copied-files.json")

    @staticmethod
    def copy_media(input_dir_path, output_directory):
        media_set = MediaSet(input_dir_path)
        media_set2 = MediaSet(output_directory)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        file_list_1 = media_set.get_possibly_duplicates()
        file_list_2 = media_set2.get_possibly_duplicates()
        file_list_3 = media_set.get_possibly_already_exists(media_set2)

        for file in file_list_3:
            if file not in file_list_1 and file not in file_list_2:
                print(file)

        CameraFilesProcessor.batch_compute_signature(file_list_1)
        CameraFilesProcessor.batch_compute_signature(file_list_2)
        CameraFilesProcessor.batch_compute_signature(file_list_3)

        media_set.propagate_sig_to_duplicates()
        media_set2.propagate_sig_to_duplicates()

        # in case new duplicates have been found because of new computed signatures
        media_set.propagate_cm_to_duplicates()
        media_set2.propagate_cm_to_duplicates()

        CameraFilesProcessor.batch_copy(media_set, media_set2)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Compute signature
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
    def compute_signature(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_compute_signature(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Compute faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(batch_title="Detect faces")
    def batch_detect_faces(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            CameraFilesProcessor.detect_faces_in_one_image(media_file, progress_bar)

    @staticmethod
    @with_progression_thread(batch_title="Detect faces", threads=7)
    def batch_detect_faces2(media_set):

        def task():
            return MetadataFaces.compute_face_boxes_task

        def arguments():
            face_metadata_list = []
            for media_file in media_set:
                if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is None:
                    face_metadata_list.append(media_file.metadata[FACES])
            return face_metadata_list

        def post_task(result_face_metadata, progress_bar):
            media_set.get_media(result_face_metadata.media_id).metadata[FACES] = result_face_metadata
            progress_bar.increment()

        return task, arguments, post_task

    @staticmethod
    def detect_faces(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_detect_faces2(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Recognize faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression_thread(batch_title="Recognize faces", threads=7)
    def batch_reco_faces(media_set):

        def task():
            return MetadataFaces.recognize_faces_task

        def arguments():
            face_metadata_list = []
            for media_file in media_set:
                if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is not None:
                    face_metadata_list.append(media_file.metadata[FACES])
            return face_metadata_list

        def post_task(result_face_metadata, progress_bar):
            media_set.get_media(result_face_metadata.media_id).metadata[FACES] = result_face_metadata
            progress_bar.increment()

        return task, arguments, post_task

    @staticmethod
    def reco_faces(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_reco_faces(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Train faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(batch_title="Detect faces")
    def batch_train_faces(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            CameraFilesProcessor.train_faces(media_file, progress_bar)

    @staticmethod
    def train_faces(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        media_set.train()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Reset faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(batch_title="Delete faces")
    def batch_delete_faces(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata[FACES].value = None
            media_file.metadata[FACES].binary_value = None
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    def reset_faces(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_delete_faces(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Analyze (duplicates / comparison)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
    @with_progression(batch_title="Reset camera models")
    def batch_delete_cm(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            media_file.metadata.delete_computed_value(CAMERA_MODEL)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    def reset_cm(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_delete_cm(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Reset signatures
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def detect_faces_in_one_image(media_file, progress_bar):
        media_file.metadata.compute_value(FACES)
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
    def reset_signature(dir_path):
        media_set = MediaSet(dir_path)
        LOGGER.info("{l1} files detected as media file"
                    .format(l1=len(media_set)))

        CameraFilesProcessor.batch_delete_signature(media_set)
