import json
import logging
import subprocess
from datetime import datetime

from camerafile.core.Resource import Resource

LOGGER = logging.getLogger(__name__)


class ExifTool(object):
    SOURCE_METADATA = "Source"
    MODEL_METADATA = "Model"
    WIDTH_METADATA = "ImageWidth"
    HEIGHT_METADATA = "ImageHeight"
    ORIENTATION_METADATA = "Orientation"
    SUB_SEC_CREATE_DATE = "SubSecCreateDate"
    SUB_SEC_DATE_TIME_ORIGINAL = "SubSecDateTimeOriginal"
    SUB_SEC_MODIFY_DATE = "SubSecModifyDate"
    DATE_TIME_ORIGINAL = "DateTimeOriginal"  # Attention to timezone ?
    CREATE_DATE_METADATA = "CreateDate"  # Use it or not ? Currently: no. If yes, attention to timezone
    MODIFY_DATE_METADATA = "FileModifyDate"  # not used anymore in ExifTool because of differences between fat and ntfs
    THUMBNAIL_METADATA = "ThumbnailImage"


    @classmethod
    def get_metadata(cls, file_stream):
        stdout = cls.execute(file_stream, "-b", "-j", "-n",
                             "-" + cls.MODEL_METADATA,
                             "-" + cls.SOURCE_METADATA,
                             "-" + cls.WIDTH_METADATA,
                             "-" + cls.HEIGHT_METADATA,
                             "-" + cls.ORIENTATION_METADATA,
                             "-" + cls.THUMBNAIL_METADATA,
                             "-" + cls.SUB_SEC_CREATE_DATE,
                             "-" + cls.SUB_SEC_DATE_TIME_ORIGINAL,
                             "-" + cls.SUB_SEC_MODIFY_DATE,
                             "-" + cls.DATE_TIME_ORIGINAL,
                             "-")

        result = json.loads(stdout)
        if len(result) == 0:
            return None, None

        thumbnail = None
        if cls.THUMBNAIL_METADATA in result[0]:
            thumbnail = result[0][cls.THUMBNAIL_METADATA]

        model = None
        if cls.MODEL_METADATA in result[0]:
            model = result[0][cls.MODEL_METADATA]
        elif cls.SOURCE_METADATA in result[0]:
            model = result[0][cls.SOURCE_METADATA]

        date = cls.read_date(result)

        width = None
        if cls.WIDTH_METADATA in result[0]:
            width = result[0][cls.WIDTH_METADATA]

        height = None
        if cls.HEIGHT_METADATA in result[0]:
            height = result[0][cls.HEIGHT_METADATA]

        orientation = None
        if cls.ORIENTATION_METADATA in result[0]:
            orientation = result[0][cls.ORIENTATION_METADATA]

        return model, date, width, height, orientation, thumbnail
