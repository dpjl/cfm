from pathlib import Path

from camerafile.BatchTool import with_progression, TaskWithProgression
from camerafile.ConsoleTable import ConsoleTable
from camerafile.Constants import IMAGE_TYPE, INTERNAL, SIGNATURE, FACES, CFM_CAMERA_MODEL, THUMBNAIL
from camerafile.Logging import Logger
from camerafile.MediaFile import MediaFile
from camerafile.MediaSet import MediaSet
from camerafile.MediaSetDatabase import MediaSetDatabase
from camerafile.MetadataFaces import MetadataFaces
from camerafile.MetadataInternal import MetadataInternal
from camerafile.MetadataSignature import MetadataSignature
from camerafile.MetadataThumbnail import MetadataThumbnail
from camerafile.OutputDirectory import OutputDirectory
from camerafile.PdfFile import PdfFile

LOGGER = Logger(__name__)


class CameraFilesProcessor:

    @staticmethod
    def load_media_set(media_set_path):
        LOGGER.write_title_2(str(media_set_path), "Opening media directory")
        return MediaSet(media_set_path)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Internal metadata and camera models
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class BatchComputeMissingThumbnails(TaskWithProgression):

        def __init__(self, media_set):
            self.media_set = media_set
            TaskWithProgression.__init__(self, "Generate missing thumbnails")

        def initialize(self):
            LOGGER.write_title(self.media_set, self.update_title())

        def task_getter(self):
            return MetadataThumbnail.compute_thumbnail_task

        def arguments(self):
            thumbnail_metadata_list = []
            for media_file in self.media_set:
                if media_file.metadata[THUMBNAIL].thumbnail is None:
                    thumbnail_metadata_list.append(media_file.metadata[THUMBNAIL])
            return thumbnail_metadata_list

        def post_task(self, result_thumbnail_metadata, progress_bar, replace=False):
            if replace:
                original_media = self.media_set.get_media(result_thumbnail_metadata.media_id)
                original_media.metadata[THUMBNAIL] = result_thumbnail_metadata
            progress_bar.increment()

        def finalize(self):
            thb_errors = self.media_set.get_files_with_thumbnail_errors()
            LOGGER.info(self.media_set.output_directory.save_list(thb_errors, "thumbnails_errors.json"))

    class BatchReadInternalMd(TaskWithProgression):

        def __init__(self, media_set):
            self.media_set = media_set
            TaskWithProgression.__init__(self, "Read media exif metadata")

        def initialize(self):
            LOGGER.write_title(self.media_set, self.update_title())

        def task_getter(self):
            return MetadataInternal.load_internal_metadata_task

        def arguments(self):
            internal_metadata_list = []
            for media_file in self.media_set:
                if media_file.metadata[INTERNAL].value is None:
                    internal_metadata_list.append(media_file.metadata[INTERNAL])
            return internal_metadata_list

        def post_task(self, result_internal_metadata, progress_bar, replace=False):
            original_media = self.media_set.get_media(result_internal_metadata.media_id)
            if replace:
                original_media.metadata[INTERNAL] = result_internal_metadata
            original_media.metadata[THUMBNAIL].thumbnail = original_media.metadata[INTERNAL].thumbnail
            original_media.metadata[INTERNAL].thumbnail = None
            original_media.metadata[CFM_CAMERA_MODEL].set_value(original_media.metadata[INTERNAL].get_cm())
            original_media.parent_set.update_date_size_name_map(original_media)
            progress_bar.increment()

    # Not compatible with multi sub-processes
    class BatchCreatePdf(TaskWithProgression):

        def __init__(self, media_set):
            self.media_set = media_set
            self.pdf_file = PdfFile(str(media_set.output_directory.path / "index-all.pdf"))
            TaskWithProgression.__init__(self, batch_title="Generate a pdf file with all thumbnails", nb_sub_process=0)

        def initialize(self):
            LOGGER.write_title(self.media_set, self.update_title())

        def task_getter(self):
            return self.task

        def task(self, current_media):
            self.pdf_file.add_media_image(current_media)

        def arguments(self):
            return self.media_set.get_date_sorted_media_list()

        def post_task(self, result, progress_bar, replace=False):
            progress_bar.increment()

        def finalize(self):
            LOGGER.info("No thumbnail found for " + str(self.pdf_file.no_thb) + " files")
            self.pdf_file.save()

    # Not compatible with multi sub-processes
    class BatchComputeCm(TaskWithProgression):

        def __init__(self, media_set):
            self.media_set = media_set
            TaskWithProgression.__init__(self, batch_title="Try to recover missing camera models", nb_sub_process=0)

        def initialize(self):
            LOGGER.write_title(self.media_set, self.update_title())

        def task_getter(self):
            return self.task

        def task(self, current_media):
            current_media.metadata[CFM_CAMERA_MODEL].compute_value()
            return current_media

        def arguments(self):
            self.status(self.media_set)
            return self.media_set.get_file_list(cm="unknown")

        def post_task(self, current_media, progress_bar, replace=False):
            current_media.parent_set.update_date_model_size_map(current_media)
            progress_bar.increment()

        def finalize(self):
            self.media_set.propagate_cm_to_duplicates()
            self.status(self.media_set)

            unknown_cm = self.media_set.get_file_list(cm="unknown")
            recovered_cm = self.media_set.get_file_list(cm="recovered")
            LOGGER.info(self.media_set.output_directory.save_list(unknown_cm, "unknown-camera-model.json"))
            LOGGER.info(self.media_set.output_directory.save_list(recovered_cm, "recovered-camera-model.json"))

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
    @with_progression(title="Organize media files",
                      short_title="Move files")
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
        print("")
        tab = ConsoleTable()
        tab.print_header("Status", "Number")
        for status in result:
            tab.print_line(status, str(result[status]))
        print("")

    @staticmethod
    def organize_media(input_dir_path):
        media_set = MediaSet(input_dir_path)

        CameraFilesProcessor.batch_organize(media_set.get_copied_files())
        media_set.save_database()
        media_set.close_database()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Copy files
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class BatchCopy(TaskWithProgression):

        def __init__(self, old_media_set, new_media_set, copy_mode):
            self.old_media_set = old_media_set
            self.new_media_set = new_media_set
            self.copy_mode = copy_mode
            TaskWithProgression.__init__(self, batch_title="Copy files")
            self.result = {"Copied": 0, "Error": 0}
            self.not_copied_files = []

        def task_getter(self):
            return MediaFile.copy_file

        def arguments(self):
            return self.old_media_set.unique_files_not_in_destination(self.new_media_set, self.copy_mode)

        def post_task(self, result_copy, progress_bar, replace=False):
            status, file_id, new_file_path = result_copy
            original_media = self.old_media_set.get_media(file_id)
            if status:
                original_media.copy_metadata(self.new_media_set, new_file_path)
                self.result["Copied"] += 1
            else:
                self.not_copied_files.append(original_media)
                self.result["Error"] += 1

            progress_bar.increment()

        def finalize(self):
            LOGGER.info(self.old_media_set.output_directory.save_list(self.not_copied_files, "not-copied-files.json"))
            print("")
            tab = ConsoleTable()
            tab.print_header("Status", "Number")
            for status in self.result:
                tab.print_line(status, str(self.result[status]))
            print("")

    class BatchComputeNecessarySignaturesMultiProcess(TaskWithProgression):

        def __init__(self, media_set, media_set2=None):
            self.media_set = media_set
            self.media_set2 = media_set2
            if media_set2 is None:
                TaskWithProgression.__init__(self,
                                             batch_title="Compute necessary signatures in order to detect duplicates")
            else:
                TaskWithProgression.__init__(self,
                                             batch_title="Compute necessary signatures in order to compare 2 mediasets")

        def initialize(self):
            LOGGER.write_title(self.media_set, self.update_title())

        def task_getter(self):
            return MetadataSignature.compute_signature_task

        def arguments(self):
            signature_metadata_list = []
            file_list_1 = self.media_set.get_possibly_duplicates()
            file_list_2 = []
            file_list_3 = []
            if self.media_set2 is not None:
                file_list_2 = self.media_set2.get_possibly_duplicates()
                file_list_3 = self.media_set.get_possibly_already_exists(self.media_set2)

            # Optimization: in file_list_2, inutile d'ajouter les dupliqués potentiels dont
            # le nom de fichier est déjà dans dans file_list_1 ?

            for media_file in file_list_1 + file_list_2 + file_list_3:
                if media_file.metadata[SIGNATURE].value is None:
                    signature_metadata_list.append(media_file.metadata[SIGNATURE])
            return signature_metadata_list

        def post_task(self, result_signature_metadata, progress_bar, replace=False):
            original_media = self.media_set.get_media(result_signature_metadata.media_id)
            if original_media is None:
                original_media = self.media_set2.get_media(result_signature_metadata.media_id)
            original_media.metadata[SIGNATURE] = result_signature_metadata
            original_media.parent_set.update_date_size_sig_map(original_media)
            progress_bar.increment()

        def finalize(self):
            self.media_set.propagate_sig_to_duplicates()
            if self.media_set2 is not None:
                self.media_set2.propagate_sig_to_duplicates()

            # in case new duplicates have been found because of new computed signatures
            self.media_set.propagate_cm_to_duplicates()
            if self.media_set2 is not None:
                self.media_set2.propagate_cm_to_duplicates()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Compute signature
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def compute_one_signature(media_file, progress_bar):
        media_file.metadata[SIGNATURE].compute_value()
        if progress_bar is not None:
            progress_bar.increment()

    @staticmethod
    @with_progression(title="Compute signatures",
                      short_title="Compute signatures")
    def batch_compute_signature(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            CameraFilesProcessor.compute_one_signature(media_file, progress_bar)

    @staticmethod
    def compute_signature(dir_path):
        media_set = MediaSet(dir_path)
        CameraFilesProcessor.BatchComputeNecessarySignaturesMultiProcess(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Compute faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class BatchDetectFaces(TaskWithProgression):

        def __init__(self, media_set):
            self.media_set = media_set
            TaskWithProgression.__init__(self, batch_title="Detect faces")

        def initialize(self):
            LOGGER.write_title(self.media_set, self.update_title())

        def task_getter(self):
            return MetadataFaces.compute_face_boxes_task

        def arguments(self):
            face_metadata_list = []
            for media_file in self.media_set:
                if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is None:
                    face_metadata_list.append(media_file.metadata[FACES])
            return face_metadata_list

        def post_task(self, result_face_metadata, progress_bar, replace=True):
            self.media_set.get_media(result_face_metadata.media_id).metadata[FACES] = result_face_metadata
            progress_bar.increment()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Recognize faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class BatchRecoFaces(TaskWithProgression):

        def __init__(self, media_set):
            self.media_set = media_set
            TaskWithProgression.__init__(batch_title="Recognize faces")

        def task(self):
            return MetadataFaces.recognize_faces_task

        def arguments(self):
            face_metadata_list = []
            for media_file in self.media_set:
                if media_file.extension in IMAGE_TYPE and media_file.metadata[FACES].binary_value is not None:
                    face_metadata_list.append(media_file.metadata[FACES])
            return face_metadata_list

        def post_task(self, result_face_metadata, progress_bar):
            self.media_set.get_media(result_face_metadata.media_id).metadata[FACES] = result_face_metadata
            progress_bar.increment()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Train faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression(title="Detect faces",
                      short_title="Detect faces")
    def batch_train_faces(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            CameraFilesProcessor.train_faces(media_file, progress_bar)

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

        CameraFilesProcessor.BatchComputeNecessarySignaturesMultiProcess(media_set).execute()

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
        CameraFilesProcessor.BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()

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
