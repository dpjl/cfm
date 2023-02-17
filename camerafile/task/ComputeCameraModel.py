from typing import Union

from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Constants import CFM_CAMERA_MODEL
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaFile import MediaFile
from camerafile.metadata.Metadata import Metadata


class ComputeCameraModel:
    MULTIPLE = "Multiple-camera-models"

    @staticmethod
    def execute(batch_element: BatchElement):
        current_media = batch_element.args
        ComputeCameraModel.compute_value(current_media)
        batch_element.result = current_media
        return batch_element

    @staticmethod
    def compute_value(media_or_dir: Union[MediaFile, MediaDirectory]):
        if media_or_dir.metadata[CFM_CAMERA_MODEL].value is None:
            if media_or_dir.parent_dir is not None:
                parent_dir_cm: Metadata = media_or_dir.parent_dir.metadata[CFM_CAMERA_MODEL]
                if parent_dir_cm.value is not None:
                    if parent_dir_cm.value != ComputeCameraModel.MULTIPLE:
                        media_or_dir.metadata[CFM_CAMERA_MODEL].value = parent_dir_cm.value
                else:
                    ComputeCameraModel.compute_value(media_or_dir.parent_dir)
                    media_or_dir.metadata[CFM_CAMERA_MODEL].value = parent_dir_cm.value

    @staticmethod
    def set_value(media_or_dir: Union[MediaFile, MediaDirectory], new_model: str):
        metadata_cm: Metadata = media_or_dir.metadata[CFM_CAMERA_MODEL]
        if new_model is not None:
            if metadata_cm.value is None:
                metadata_cm.value = new_model
            elif metadata_cm.value != new_model:
                metadata_cm.value = ComputeCameraModel.MULTIPLE
            if metadata_cm.value is not None:
                if media_or_dir.parent_dir is not None:
                    parent_dir_cm = media_or_dir.parent_dir.metadata[CFM_CAMERA_MODEL]
                    parent_dir_cm.set_value(metadata_cm.value)
