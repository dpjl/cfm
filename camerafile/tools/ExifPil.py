import json
import locale
import logging
import subprocess
from datetime import datetime
from threading import Thread
from queue import Queue, Empty
from camerafile.core.Resource import Resource

LOGGER = logging.getLogger(__name__)


class ExifPil(object):
    CHARSET_OPTION = ("-charset", "filename=" + locale.getpreferredencoding())
    IMAGE_UPDATE = "image files updated"
    SOURCE_METADATA = "Source"
    MODEL_METADATA = "Model"
    WIDTH_METADATA = "ImageWidth"
    HEIGHT_METADATA = "ImageHeight"
    ORIENTATION_METADATA = "Orientation"
    FILE_SIZE_METADATA = "FileSize"
    SUB_SEC_CREATE_DATE = "SubSecCreateDate"
    SUB_SEC_DATE_TIME_ORIGINAL = "SubSecDateTimeOriginal"
    SUB_SEC_MODIFY_DATE = "SubSecModifyDate"
    DATE_TIME_ORIGINAL = "DateTimeOriginal"  # Attention to timezone ?
    CREATE_DATE_METADATA = "CreateDate"  # Use it or not ? Currently: no. If yes, attention to timezone
    MODIFY_DATE_METADATA = "FileModifyDate"  # not used anymore in ExifTool because of differences between fat and ntfs
    THUMBNAIL_METADATA = "ThumbnailImage"
    BEST_CAMERA_MODEL = 'best-camera-model'
    BEST_CREATION_DATE = "best-creation-date"
    BEST_CAMERA_MODEL_LIST = (MODEL_METADATA,
                              SOURCE_METADATA)
    BEST_CREATION_DATE_LIST = (SUB_SEC_CREATE_DATE,
                               SUB_SEC_DATE_TIME_ORIGINAL,
                               SUB_SEC_MODIFY_DATE,
                               DATE_TIME_ORIGINAL)


    @classmethod
    def execute(cls, *args):
        args = cls.CHARSET_OPTION + args + ("-execute\n",)
        cls.process.stdin.write(str.join("\n", args))
        cls.process.stdin.flush()
        output = ""
        while not output.endswith(cls.SENTINEL):
            output += cls.stdout_reader.get_new_line()
        err = ""
        new_line = ""
        while new_line is not None:
            new_line = cls.stderr_reader.get_new_line_no_wait()
            if new_line is not None:
                err += new_line
        if err != "":
            LOGGER.error(err.strip())
        return output[:-len(cls.SENTINEL)], err

    @classmethod
    def parse_date(cls, exif_tool_result, field, date_format):
        if field in exif_tool_result[0]:
            str_date = exif_tool_result[0][field]
            try:
                return datetime.strptime(str_date.split("+")[0], date_format)
            except ValueError:
                return None

    @classmethod
    def read_date(cls, exif_tool_result):
        date = cls.parse_date(exif_tool_result, cls.SUB_SEC_DATE_TIME_ORIGINAL, '%Y:%m:%d %H:%M:%S.%f')
        if date is None:
            date = cls.parse_date(exif_tool_result, cls.SUB_SEC_CREATE_DATE, '%Y:%m:%d %H:%M:%S.%f')
        if date is None:
            date = cls.parse_date(exif_tool_result, cls.SUB_SEC_MODIFY_DATE, '%Y:%m:%d %H:%M:%S.%f')
        if date is None:
            date = cls.parse_date(exif_tool_result, cls.DATE_TIME_ORIGINAL, '%Y:%m:%d %H:%M:%S')
        return date

    @classmethod
    def load_from_result(cls, result, metadata_name):

        if metadata_name == cls.BEST_CAMERA_MODEL:
            if cls.MODEL_METADATA in result[0]:
                return result[0][cls.MODEL_METADATA]
            elif cls.SOURCE_METADATA in result[0]:
                return result[0][cls.SOURCE_METADATA]

        elif metadata_name == cls.BEST_CREATION_DATE:
            return cls.read_date(result)

        elif metadata_name in result[0]:
            return result[0][metadata_name]

        return None

    @classmethod
    def expand_args(cls, *args):
        result = ()
        for arg in args:

            if str(arg) == cls.BEST_CREATION_DATE:
                result += cls.BEST_CREATION_DATE_LIST

            elif str(arg) == cls.BEST_CAMERA_MODEL:
                result += cls.BEST_CAMERA_MODEL_LIST

            else:
                result += (arg,)
        return tuple(['-' + arg for arg in result])

    @classmethod
    def get_metadata(cls, file, *args):

        for arg in args:
            get_metadata

        result = json.loads(stdout)
        if len(result) == 0:
            return {}

        return {metadata_name: cls.load_from_result(result, metadata_name) for metadata_name in args}

