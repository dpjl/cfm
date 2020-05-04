import logging
import os
from vivicfm.ExifTool import ExifTool
from vivicfm.AviMetaEdit import AviMetaEdit

LOGGER = logging.getLogger(__name__)


class MediaCameraModel:
    NOT_READ = "Not-yet-read"
    MULTIPLE = "Multiple-camera-models"
    IMAGES_UPDATABLE_BY_EXIF_TOOL = [".jpg", ".jpeg"]
    VIDEOS_UPDATABLE_BY_EXIF_TOOL = [".mp4", ".mov"]
    VIDEOS_UPDATABLE_BY_AVI_META_EDIT = [".avi"]

    def __init__(self, media):
        self.media = media
        self.value = MediaCameraModel.NOT_READ
        self.recovered_value = None

    def __str__(self):
        return self.get()

    def get(self):
        self.read()
        if self.value is not None:
            return self.value
        elif self.recovered_value is not None:
            return self.recovered_value
        else:
            return "Unknown"

    def try_to_recover(self):
        if self.value is None and self.recovered_value is None:
            if self.media.parent_dir is not None:
                if self.media.parent_dir.camera_model.value != MediaCameraModel.NOT_READ:
                    if self.media.parent_dir.camera_model.value != MediaCameraModel.MULTIPLE:
                        self.recovered_value = self.media.parent_dir.camera_model.value
                else:
                    self.media.parent_dir.camera_model.try_to_recover()
                    self.recovered_value = self.media.parent_dir.camera_model.recovered_value
            if self.recovered_value is not None:
                self.media.external_metadata.update_recovered_model(self.recovered_value)
                self.media.external_metadata.save()

    def propagate_update(self, new_model):
        if self.value is None or self.value == MediaCameraModel.NOT_READ:
            self.value = new_model
        elif self.value != new_model:
            self.value = MediaCameraModel.MULTIPLE
        if self.value is not None:
            if self.media.parent_dir is not None:
                self.media.parent_dir.camera_model.propagate_update(self.value)

    def read(self):
        if os.path.isdir(self.media.path):
            LOGGER.error("Metadata of directory can't be read {path}".format(path=self.media.path))
        model_found, self.value = self.media.external_metadata.get_model()
        recovered_found, self.recovered_value = self.media.external_metadata.get_recovered_model()
        if not model_found:
            self.media.external_metadata.load_from_media()
            model_found, self.value = self.media.external_metadata.get_model()
        self.propagate_update(self.value)

    def reset_external_metadata(self):
        self.media.external_metadata.delete_recovered_model()
        self.media.external_metadata.save()

    def update_media_with_recovered(self):
        if self.recovered_value is not None:
            self.media.backup()
            if self.media.extension in MediaCameraModel.IMAGES_UPDATABLE_BY_EXIF_TOOL:
                ExifTool.update_model(self.media.path, self.recovered_value)

            elif self.media.extension in MediaCameraModel.VIDEOS_UPDATABLE_BY_EXIF_TOOL:
                ExifTool.update_source(self.media.path, self.recovered_value)

            elif self.media.extension in MediaCameraModel.VIDEOS_UPDATABLE_BY_AVI_META_EDIT:
                AviMetaEdit.update_source(self.media.path, self.recovered_value)
            else:
                LOGGER.error(
                    "Metadata of this file can't be updated with this version of the tool: %s" % self.media.name)
