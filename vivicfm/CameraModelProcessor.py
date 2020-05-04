import logging
from pathlib import Path
from vivicfm.CFMOutputFile import CFMFileRW
from vivicfm.FoldersMetadata import FoldersMetadata
from vivicfm.CFMFileList import CFMFileList
from vivicfm.MetadataManager import MetadataManager

LOGGER = logging.getLogger(__name__)


class CameraModelProcessor:
    MODIFIED_FILES_CACHE = "cache-modified_files.txt"
    UNKNOWN_MODEL_VALUE = "UnknownCameraModel"

    def __init__(self, input_dir_path, try_load_cache=True):
        self.input_dir_path = input_dir_path
        self.files_with_cm = {}
        self.files_with_recovered_cm = {}
        self.files_with_unknown_cm = {}
        self.cm_of_folders = FoldersMetadata("Camera models per folder")
        self.mm = MetadataManager(try_load_cache)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def analyze(self):
        file_list = self.get_list_of_all_files()
        cm_of_files = self.mm.batch_get_cm(file_list.media, "Reading camera models")
        self.analyze_cm(cm_of_files)
        if len(self.files_with_unknown_cm) != 0:
            self.try_to_recover(self.cm_of_folders)

    def apply(self):

        if len(self.files_with_recovered_cm) == 0 and len(self.files_with_unknown_cm) == 0:
            LOGGER.info("No transformation needed, all files have a camera model")
            return

        print("")
        print("Please verify carefully the saved lists.")
        print("Do you want to update media files with detected camera models ?")
        typed_text = input("Type 'yes' and press 'Enter' key: ")
        print("")

        if typed_text == "yes":
            files_to_modify = {}
            files_to_modify.update(self.files_with_recovered_cm)
            files_to_modify.update(self.files_with_unknown_cm)
            self.mm.batch_update_cm(files_to_modify, "Updating files metadata")
            self.reload_and_verify_updated_files(files_to_modify)
            CFMFileRW.save_dict(files_to_modify, CameraModelProcessor.MODIFIED_FILES_CACHE)
        else:
            LOGGER.info("Transformation NOT performed.")

    def revert(self):
        files_stats = self.get_list_of_all_files()
        reverted_files = self.mm.batch_revert(files_stats.media)
        LOGGER.info("%s files have been reverted" % len(reverted_files))
        if len(reverted_files) != 0:
            self.mm.batch_get_cm(reverted_files,
                                 "Reload camera models of reverted files",
                                 force_reload=True)

    def reload_and_verify_updated_files(self, modified_files):
        cm_of_files = self.mm.batch_get_cm(modified_files,
                                           "Reload camera models of updated files",
                                           force_reload=True)
        self.analyze_cm(cm_of_files)
        for filePath in self.files_with_recovered_cm:
            LOGGER.warning("This file has not been correctly updated: %s" % filePath)
        for filePath in self.files_with_unknown_cm:
            LOGGER.warning("This file has not been correctly updated: %s" % filePath)

    def analyze_cm(self, cm_of_files):
        self.files_with_recovered_cm = {}
        self.files_with_unknown_cm = {}
        for filename, model in cm_of_files.items():
            if model is None:
                self.files_with_unknown_cm[filename] = CameraModelProcessor.UNKNOWN_MODEL_VALUE
            else:
                self.files_with_cm[filename] = model
                self.cm_of_folders.add_model_from_file(filename, model)

        LOGGER.info("%i files have a camera model, %i do not have one",
                    len(self.files_with_cm),
                    len(self.files_with_unknown_cm))

    def try_to_recover(self, camera_model_of_folders):
        for file_path in self.files_with_unknown_cm:
            directory_path = Path(file_path).parent
            model = camera_model_of_folders.get_model(directory_path)
            if model is not None:
                self.files_with_recovered_cm[file_path] = model

        for recovered_file in self.files_with_recovered_cm:
            try:
                del self.files_with_unknown_cm[recovered_file]
            except KeyError:
                LOGGER.warning("%s could not be deleted from self.files_with_unknown_camera_model" % recovered_file)
        LOGGER.info("Try recover unknown camera models: %i files recovered, %i remain unknown",
                    len(self.files_with_recovered_cm),
                    len(self.files_with_unknown_cm))

    def save(self):
        self.save_unknown()
        self.save_recovered()

    def save_unknown(self):
        CFMFileRW.save_dict(self.files_with_unknown_cm, "unknown-camera-model-of-files.json")

    def save_recovered(self):
        CFMFileRW.save_dict(self.files_with_recovered_cm, "recovered-camera-model-of-files.json")

    def get_list_of_all_files(self):
        LOGGER.info("Getting the list of all files...")
        file_list = CFMFileList()
        file_list.compute(self.input_dir_path)
        LOGGER.info("List files of input directory: %i files found, "
                    "%i of them detected as media files",
                    len(file_list.all), len(file_list.media))
        return file_list
