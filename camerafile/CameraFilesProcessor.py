import logging
from pathlib import Path

from camerafile.BatchTool import with_progression, with_progression_multi_process
from camerafile.ConsoleTable import ConsoleTable
from camerafile.Constants import IMAGE_TYPE, INTERNAL, SIGNATURE, FACES, CFM_CAMERA_MODEL, THUMBNAIL
from camerafile.MediaFile import MediaFile
from camerafile.MediaSet import MediaSet
from camerafile.MediaSetDatabase import MediaSetDatabase
from camerafile.MetadataFaces import MetadataFaces
from camerafile.MetadataInternal import MetadataInternal
from camerafile.MetadataSignature import MetadataSignature
from camerafile.MetadataThumbnail import MetadataThumbnail
from camerafile.OutputDirectory import OutputDirectory
from camerafile.PdfFile import PdfFile

LOGGER = logging.getLogger(__name__)


class CameraFilesProcessor:

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Internal metadata and camera models
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression_multi_process(batch_title="Compute missing thumbnails")
    def batch_missing_thumbnails_multi_process(media_set):

        def task():
            return MetadataThumbnail.compute_thumbnail_task

        def arguments():
            thumbnail_metadata_list = []
            for media_file in media_set:
                if media_file.metadata[THUMBNAIL].thumbnail is None:
                    thumbnail_metadata_list.append(media_file.metadata[THUMBNAIL])
            return thumbnail_metadata_list

        def post_task(result_thumbnail_metadata, progress_bar):
            original_media = media_set.get_media(result_thumbnail_metadata.media_id)
            original_media.metadata[THUMBNAIL] = result_thumbnail_metadata
            progress_bar.increment()

        return task, arguments, post_task

    @staticmethod
    @with_progression_multi_process(batch_title="Read media internal metadata")
    def batch_read_internal_md_multi_process(media_set):

        def task():
            return MetadataInternal.load_internal_metadata_task

        def arguments():
            internal_metadata_list = []
            for media_file in media_set:
                if media_file.metadata[INTERNAL].value is None:
                    internal_metadata_list.append(media_file.metadata[INTERNAL])
            return internal_metadata_list

        def post_task(result_internal_metadata, progress_bar):
            original_media = media_set.get_media(result_internal_metadata.media_id)
            original_media.metadata[INTERNAL] = result_internal_metadata
            original_media.metadata[THUMBNAIL].thumbnail = original_media.metadata[INTERNAL].thumbnail
            original_media.metadata[INTERNAL].thumbnail = None
            original_media.metadata[CFM_CAMERA_MODEL].set_value_read(original_media.metadata[INTERNAL].get_cm())
            original_media.parent_set.update_date_size_name_map(original_media)
            progress_bar.increment()

        return task, arguments, post_task

    @staticmethod
    @with_progression(title="Read media internal metadata",
                      short_title="Read metadata")
    def batch_read_internal_md(media_set, progress_bar=None):
        for media_file in media_set:
            media_file.metadata[INTERNAL].load_internal_metadata()
            media_file.metadata[CFM_CAMERA_MODEL].set_value_read(media_file.metadata[INTERNAL].get_cm())
            media_file.parent_set.update_date_size_name_map(media_file)
            if progress_bar is not None:
                progress_bar.increment()

    @staticmethod
    @with_progression(title="Add all images to pdf file",
                      short_title="Create index-all.pdf")
    def batch_create_pdf(media_set, progress_bar=None):

        pdf_file = PdfFile(str(media_set.output_directory.path / "index-all.pdf"))

        for media in media_set.get_date_sorted_media_list():
            pdf_file.add_media_image(media)
            if progress_bar is not None:
                progress_bar.increment()

        LOGGER.info("|___ No thb : " + str(pdf_file.no_thb))
        pdf_file.save()

    @staticmethod
    @with_progression(title="Try to recover missing camera models",
                      short_title="Recover camera models")
    def batch_compute_cm(media_file_list, media_set, progress_bar=None):

        CameraFilesProcessor.status(media_set)

        for media_file in media_file_list:
            media_file.metadata[CFM_CAMERA_MODEL].compute_value()
            media_file.parent_set.update_date_model_size_map(media_file)
            if progress_bar is not None:
                progress_bar.increment()

        media_set.propagate_cm_to_duplicates()
        CameraFilesProcessor.status(media_set)

        unknown_cm = media_set.get_file_list(cm="unknown")
        recovered_cm = media_set.get_file_list(cm="recovered")
        media_set.output_directory.save_list(unknown_cm, "unknown-camera-model-of-files.json")
        media_set.output_directory.save_list(recovered_cm, "recovered-camera-model-of-files.json")

    @staticmethod
    def find_cm(dir_path):
        media_set = MediaSet(dir_path)

        # CameraFilesProcessor.batch_compute_cm(media_set.get_file_list(cm="unknown"), media_set)

        CameraFilesProcessor.batch_read_internal_md_multi_process(media_set)
        CameraFilesProcessor.batch_missing_thumbnails_multi_process(media_set)
        media_set.output_directory.save_list(media_set.get_files_with_thumbnail_errors(), "thumbnails_errors.json")
        CameraFilesProcessor.batch_create_pdf(media_set)

        media_set.save_database()
        media_set.close_database()

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

    @staticmethod
    @with_progression(title="Copy media files",
                      short_title="Copy files")
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
        print("")
        tab = ConsoleTable()
        tab.print_header("Status", "Number")
        for status in result:
            tab.print_line(status, str(result[status]))
        print("")

        old_media_set.output_directory.save_list(not_copied_files, "not-copied-files.json")

    @staticmethod
    @with_progression_multi_process(batch_title="Copy files")
    def batch_copy_multi_process(old_media_set, new_media_set):

        def task():
            return MediaFile.copy_file

        def arguments():
            return old_media_set.unique_files_not_in_destination(new_media_set)

        def post_task(result_copy, progress_bar):
            status, file_id, new_file_path = result_copy
            if status:
                original_media = old_media_set.get_media(file_id)
                original_media.copy_metadata(new_media_set, new_file_path)
            progress_bar.increment()

        return task, arguments, post_task

    @staticmethod
    @with_progression_multi_process(batch_title="Compute necessary signatures in order to detect duplicates")
    def batch_compute_necessary_signatures_multi_process(media_set, media_list):

        def task():
            return MetadataSignature.compute_signature_task

        def arguments():
            signature_metadata_list = []
            for media_file in media_list:
                if media_file.metadata[SIGNATURE].value is None:
                    signature_metadata_list.append(media_file.metadata[SIGNATURE])
            return signature_metadata_list

        def post_task(result_signature_metadata, progress_bar):
            original_media = media_set.get_media(result_signature_metadata.media_id)
            original_media.metadata[SIGNATURE] = result_signature_metadata
            original_media.parent_set.update_date_size_sig_map(original_media)
            progress_bar.increment()

        return task, arguments, post_task

    @staticmethod
    @with_progression(title="Compute necessary signatures in order to detect duplicates",
                      short_title="Compute signatures")
    def batch_compute_necessary_signatures(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            CameraFilesProcessor.compute_one_signature(media_file, progress_bar)
            media_file.parent_set.update_date_size_sig_map(media_file)

    @staticmethod
    def compute_necessary_signatures(media_set, media_set2, progress_bar=None):
        file_list_1 = media_set.get_possibly_duplicates()
        file_list_2 = media_set2.get_possibly_duplicates()
        file_list_3 = media_set.get_possibly_already_exists(media_set2)

        # Optimization: in file_list_2, inutile d'ajouter les dupliqués potentiels dont
        # le nom de fichier est déjà dans dans file_list_1 ?

        CameraFilesProcessor.batch_compute_necessary_signatures(file_list_1 + file_list_2 + file_list_3)

        media_set.propagate_sig_to_duplicates()
        media_set2.propagate_sig_to_duplicates()

        # in case new duplicates have been found because of new computed signatures
        media_set.propagate_cm_to_duplicates()
        media_set2.propagate_cm_to_duplicates()

    @staticmethod
    def copy_media(input_dir_path, output_directory):
        media_set = MediaSet(input_dir_path)
        media_set2 = MediaSet(output_directory)

        CameraFilesProcessor.compute_necessary_signatures(media_set, media_set2)
        CameraFilesProcessor.batch_copy_multi_process(media_set, media_set2)

        media_set.save_database()
        media_set.close_database()

        media_set2.save_database()
        media_set2.close_database()

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
        CameraFilesProcessor.batch_compute_necessary_signatures_multi_process(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Compute faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def detect_faces_in_one_image(media_file, progress_bar):
        media_file.metadata.compute_value(FACES)
        if progress_bar is not None:
            progress_bar.increment()

    @staticmethod
    @with_progression(title="Detect faces",
                      short_title="Detect faces")
    def batch_detect_faces(media_file_list, progress_bar=None):
        for media_file in media_file_list:
            CameraFilesProcessor.detect_faces_in_one_image(media_file, progress_bar)

    @staticmethod
    @with_progression_multi_process(batch_title="Detect faces")
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

        CameraFilesProcessor.batch_detect_faces2(media_set)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    Recognize faces
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    @with_progression_multi_process(batch_title="Recognize faces")
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

        CameraFilesProcessor.batch_reco_faces(media_set)

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

        file_list_1 = media_set.get_possibly_duplicates()
        CameraFilesProcessor.batch_compute_necessary_signatures_multi_process(media_set, file_list_1)
        media_set.propagate_sig_to_duplicates()
        media_set.propagate_cm_to_duplicates()

        duplicates = media_set.duplicates()
        duplicates_report = CameraFilesProcessor.get_duplicates_report(duplicates, media_set)

        tab = ConsoleTable()
        tab.print_header(str(media_set.root_path))
        tab.print_multi_line(duplicates_report)
        print("")

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

        media_set.save_database()
        media_set.close_database()

    @staticmethod
    def cmp(dir_1_path, dir_2_path):
        media_set1 = MediaSet(dir_1_path)
        media_set2 = MediaSet(dir_2_path)

        CameraFilesProcessor.compute_necessary_signatures(media_set1, media_set2)

        duplicates_1 = media_set1.duplicates()
        duplicates_2 = media_set2.duplicates()

        duplicates_1_report = CameraFilesProcessor.get_duplicates_report(duplicates_1, media_set1)
        duplicates_2_report = CameraFilesProcessor.get_duplicates_report(duplicates_2, media_set2)

        in_the_two_dirs_1, only_in_dir1 = media_set1.cmp(media_set2)
        in_the_two_dirs_2, only_in_dir2 = media_set2.cmp(media_set1)

        tab = ConsoleTable()
        tab.print_header(str(media_set1.root_path), str(media_set2.root_path))
        tab.print_multi_line(duplicates_1_report, duplicates_2_report)
        tab.print_line('+ %s distinct (%s files)' % (len(only_in_dir1), sum(map(len, only_in_dir1))), '')
        tab.print_line('', '+ %s distinct (%s files)' % (len(only_in_dir2), sum(map(len, only_in_dir2))))
        tab.print_line('%s distinct' % len(in_the_two_dirs_1))

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
