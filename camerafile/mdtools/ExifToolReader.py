import base64
import io
import json
import locale
import logging
import os
import subprocess
from datetime import datetime

from PIL import Image

from camerafile.core.Resource import Resource
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.mdtools.MdException import MdException

LOGGER = logging.getLogger(__name__)


class ExifToolNotFound(Exception):
    pass


class ExifTool(object):
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
    CREATE_DATE_METADATA = "CreateDate"  # Use it or not ? Currently: YES. Attention to timezone ?
    MODIFY_DATE_METADATA = "FileModifyDate"  # not used anymore in ExifTool because of differences between fat and ntfs
    THUMBNAIL_METADATA = "ThumbnailImage"
    ROTATION_METADATA = "Rotation"

    BEST_CAMERA_MODEL_LIST = (MODEL_METADATA,
                              SOURCE_METADATA)
    BEST_CREATION_DATE_LIST = (SUB_SEC_CREATE_DATE,
                               SUB_SEC_DATE_TIME_ORIGINAL,
                               SUB_SEC_MODIFY_DATE,
                               DATE_TIME_ORIGINAL,
                               CREATE_DATE_METADATA)
    SENTINEL = "{ready}\n"

    executable = None
    process = None

    @classmethod
    def init(cls, stdout_file_path=None, stderr_file_path=None):
        pass

    @classmethod
    def start(cls):
        if cls.process is None:
            cls.executable = Resource.exiftool_executable
            try:
                cls.process = subprocess.Popen(
                    [cls.executable, "-stay_open", "True", "-@", "-"],
                    universal_newlines=True, bufsize=1,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                os.set_blocking(cls.process.stderr.fileno(), False)
            except Exception as e:
                LOGGER.info("Exception during ExifTool start: " + str(e))
                raise ExifToolNotFound(cls.executable)
            LOGGER.debug("%s started", cls.executable)

    @classmethod
    def stop(cls):
        if cls.process is not None:
            cls.process.stdin.write("-stay_open\nFalse\n")
            cls.process.stdin.flush()
            cls.process.wait()
            cls.process = None
            LOGGER.debug("%s stopped", cls.executable)

    @classmethod
    def execute_once(cls, *args):
        result = cls.execute(args)
        cls.stop()
        return result

    @classmethod
    def __read_stdout(cls):
        output = ""
        new_line = cls.process.stdout.readline()
        while new_line != cls.SENTINEL:
            output += new_line
            new_line = cls.process.stdout.readline()
        return output

    @classmethod
    def __read_stderr(cls):
        err = ""
        new_line = cls.process.stderr.readline()
        while new_line != "":
            err += new_line
            new_line = cls.process.stderr.readline()
        return err

    @classmethod
    def execute(cls, *args):
        if cls.process is None:
            cls.start()
        args = cls.CHARSET_OPTION + args + ("-execute\n",)
        cls.process.stdin.write(str.join("\n", args))
        cls.process.stdin.flush()
        out = cls.__read_stdout()
        err = cls.__read_stderr()
        if err != "":
            raise MdException(err.strip())
        return out, err

    @classmethod
    def execute_with_bytes(cls, input_bytes, *args):
        result = subprocess.run([Resource.exiftool_executable, *args], input=input_bytes,
                                capture_output=True)
        return result.stdout

    @classmethod
    def parse_date(cls, exif_tool_result, field, date_format):
        if field in exif_tool_result[0]:
            str_date = exif_tool_result[0][field]
            try:
                return datetime.strptime(str_date.split("+")[0], date_format)
            except ValueError:
                return None

    @classmethod
    def __get_date_metadata(cls, exif_tool_result):
        date = cls.parse_date(exif_tool_result, cls.SUB_SEC_DATE_TIME_ORIGINAL, '%Y:%m:%d %H:%M:%S.%f')
        if date is None:
            date = cls.parse_date(exif_tool_result, cls.SUB_SEC_CREATE_DATE, '%Y:%m:%d %H:%M:%S.%f')
        if date is None:
            date = cls.parse_date(exif_tool_result, cls.SUB_SEC_MODIFY_DATE, '%Y:%m:%d %H:%M:%S.%f')
        if date is None:
            date = cls.parse_date(exif_tool_result, cls.DATE_TIME_ORIGINAL, '%Y:%m:%d %H:%M:%S')
        if date is None:
            date = cls.parse_date(exif_tool_result, cls.CREATE_DATE_METADATA, '%Y:%m:%d %H:%M:%S')
        return date

    @classmethod
    def __get_model_metadata(cls, metadata):
        if cls.MODEL_METADATA in metadata:
            return metadata[cls.MODEL_METADATA]
        elif cls.SOURCE_METADATA in metadata:
            return metadata[cls.SOURCE_METADATA]
        return None

    @classmethod
    def __get_thumbnail_metadata(cls, metadata):
        if cls.THUMBNAIL_METADATA in metadata:
            thumbnail = metadata[cls.THUMBNAIL_METADATA]
            if thumbnail is not None:
                thumbnail = base64.b64decode(thumbnail[7:])
                thb = Image.open(io.BytesIO(thumbnail))
                thb.thumbnail((100, 100))
                bytes_output = io.BytesIO()
                thb.save(bytes_output, format='JPEG')
                return bytes_output.getvalue()
        return None

    @classmethod
    def load_from_result(cls, result, metadata_name):

        if len(result) == 0:
            return

        metadata = result[0]

        if metadata_name == MetadataNames.MODEL:
            return cls.__get_model_metadata(metadata)

        elif metadata_name == MetadataNames.CREATION_DATE:
            return cls.__get_date_metadata(result)

        elif metadata_name == MetadataNames.THUMBNAIL or metadata_name == cls.THUMBNAIL_METADATA:
            return cls.__get_thumbnail_metadata(metadata)

        elif metadata_name == MetadataNames.WIDTH and cls.WIDTH_METADATA in metadata:
            return metadata[cls.WIDTH_METADATA]

        elif metadata_name == MetadataNames.HEIGHT and cls.HEIGHT_METADATA in metadata:
            return metadata[cls.HEIGHT_METADATA]

        elif metadata_name == MetadataNames.ORIENTATION:
            # Priorité à l'orientation exif native
            if cls.ORIENTATION_METADATA in metadata:
                return metadata[cls.ORIENTATION_METADATA]
            # Sinon, tenter de convertir la rotation (en degrés) vers orientation exif
            elif cls.ROTATION_METADATA in metadata:
                try:
                    deg = int(metadata[cls.ROTATION_METADATA])
                except Exception:
                    deg = None
                if deg is not None:
                    deg_to_orientation = {
                        0: 1,
                        90: 6,
                        180: 3,
                        270: 8
                    }
                    return deg_to_orientation.get(deg, None)
                else:
                    return None

        elif metadata_name in metadata:
            return metadata[metadata_name]

        return None

    @classmethod
    def expand_args(cls, *args):
        result = ()
        for arg in args:

            if arg == MetadataNames.CREATION_DATE:
                result += cls.BEST_CREATION_DATE_LIST

            elif arg == MetadataNames.MODEL:
                result += cls.BEST_CAMERA_MODEL_LIST

            elif arg == MetadataNames.WIDTH:
                result += (cls.WIDTH_METADATA,)

            elif arg == MetadataNames.HEIGHT:
                result += (cls.HEIGHT_METADATA,)

            elif arg == MetadataNames.ORIENTATION:
                result += (cls.ORIENTATION_METADATA, cls.ROTATION_METADATA)

            elif isinstance(arg, MetadataNames):
                result += (arg.value,)

            elif isinstance(arg, str):
                result += (arg,)
        return tuple(['-' + str(arg) for arg in result])

    @classmethod
    def get_metadata(cls, file, *args):
        try:
            real_args = cls.expand_args(*args)
            if isinstance(file, str):
                stdout, stderr = cls.execute("-fast2", "-b", "-j", "-n", *real_args, file)
            else:
                stdout = cls.execute_with_bytes(file, "-fast2", "-b", "-j", "-n", *real_args, "-")

            result = json.loads(stdout)
            if len(result) == 0:
                return {}
            return {metadata_name: cls.load_from_result(result, metadata_name) for metadata_name in args}
        except Exception as e:
            # traceback.print_exc()
            raise MdException(e)

    @classmethod
    def update_model(cls, filename, new_model):
        stdout, stderr = cls.execute("-overwrite_original", "-source=" + new_model, filename)
        if cls.IMAGE_UPDATE not in stdout:
            return "Error when trying to update %s" % filename
        return ""

    @classmethod
    def update_source(cls, filename, new_model):
        stdout, stderr = cls.execute("-overwrite_original", "-source=" + new_model, filename)
        if cls.IMAGE_UPDATE not in stdout:
            return "Error when trying to update %s" % filename
        return ""
