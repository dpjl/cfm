import base64
import io
import json
import locale
import logging
import subprocess
from datetime import datetime
from queue import Queue, Empty
from threading import Thread

from PIL.Image import Image

from camerafile.core.Resource import Resource
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.mdtools.MdException import MdException

LOGGER = logging.getLogger(__name__)


class NonBlockingStreamReader:

    def __init__(self, redirected_file_path):
        self.queue = Queue()
        self.stream = None
        self.redirected_file = None
        if redirected_file_path is not None:
            self.redirected_file = open(redirected_file_path, "w")

    def __del__(self):
        if self.redirected_file is not None:
            self.redirected_file.close()

    def start_read(self, stream):
        if self.redirected_file is not None:
            self.redirected_file.write("--\nExifTool started\n--\n")
            self.redirected_file.flush()
        self.stream = stream
        thread = Thread(target=self.enqueue_output)
        thread.daemon = True
        thread.start()

    def enqueue_output(self):
        for line in iter(self.stream.readline, b''):
            self.queue.put(line)
            if self.redirected_file is not None:
                self.redirected_file.write(line)
        if self.redirected_file is not None:
            self.redirected_file.write("--\nExifTool stopped\n--\n")
            self.redirected_file.flush()

    def get_new_line_no_wait(self):
        try:
            line = self.queue.get_nowait()
        except Empty:
            return None
        else:
            return line

    def get_new_line(self):
        try:
            line = self.queue.get(timeout=120)
        except Empty:
            return None
        else:
            return line


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
    CREATE_DATE_METADATA = "CreateDate"  # Use it or not ? Currently: no. If yes, attention to timezone
    MODIFY_DATE_METADATA = "FileModifyDate"  # not used anymore in ExifTool because of differences between fat and ntfs
    THUMBNAIL_METADATA = "ThumbnailImage"

    BEST_CAMERA_MODEL_LIST = (MODEL_METADATA,
                              SOURCE_METADATA)
    BEST_CREATION_DATE_LIST = (SUB_SEC_CREATE_DATE,
                               SUB_SEC_DATE_TIME_ORIGINAL,
                               SUB_SEC_MODIFY_DATE,
                               DATE_TIME_ORIGINAL)
    SENTINEL = "{ready}\n"

    executable = None
    process = None
    stdout_reader = NonBlockingStreamReader(redirected_file_path=None)
    stderr_reader = NonBlockingStreamReader(redirected_file_path=None)

    @classmethod
    def init(cls, stdout_file_path=None, stderr_file_path=None):
        cls.stdout_reader = NonBlockingStreamReader(redirected_file_path=stdout_file_path)
        cls.stderr_reader = NonBlockingStreamReader(redirected_file_path=stderr_file_path)

    @classmethod
    def start(cls):
        if cls.process is None:
            cls.executable = Resource.exiftool_executable
            LOGGER.debug("Starting %s", cls.executable)
            cls.process = subprocess.Popen(
                [cls.executable, "-stay_open", "True", "-@", "-"],
                universal_newlines=True, bufsize=1,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cls.stdout_reader.start_read(cls.process.stdout)
            cls.stderr_reader.start_read(cls.process.stderr)

    @classmethod
    def stop(cls):
        if cls.process is not None:
            LOGGER.debug("Stopping %s", cls.executable)
            cls.process.stdin.write("-stay_open\nFalse\n")
            cls.process.stdin.flush()
            cls.process = None

    @classmethod
    def execute_once(cls, *args):
        result = cls.execute(args)
        cls.stop()
        return result

    @classmethod
    def execute(cls, *args):
        if cls.process is None:
            cls.start()
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
            raise MdException(err.strip())
        return output[:-len(cls.SENTINEL)], err

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

        if len(result) == 0:
            return

        metadata = result[0]

        if metadata_name == MetadataNames.MODEL:
            if cls.MODEL_METADATA in metadata:
                return metadata[cls.MODEL_METADATA]
            elif cls.SOURCE_METADATA in metadata:
                return metadata[cls.SOURCE_METADATA]

        elif metadata_name == MetadataNames.CREATION_DATE:
            return cls.read_date(result)

        elif metadata_name == MetadataNames.THUMBNAIL or metadata_name == cls.THUMBNAIL_METADATA:
            if cls.THUMBNAIL_METADATA in metadata:
                thumbnail = metadata[cls.THUMBNAIL_METADATA]
                if thumbnail is not None:
                    thumbnail = base64.b64decode(thumbnail[7:])
                    thb = Image.open(io.BytesIO(thumbnail))
                    thb.thumbnail((100, 100))
                    bytes_output = io.BytesIO()
                    thb.save(bytes_output, format='JPEG')
                    return bytes_output.getvalue()

        if metadata_name == MetadataNames.WIDTH and cls.WIDTH_METADATA in metadata:
            return metadata[cls.WIDTH_METADATA]

        if metadata_name == MetadataNames.HEIGHT and cls.HEIGHT_METADATA in metadata:
            return metadata[cls.HEIGHT_METADATA]

        if metadata_name == MetadataNames.ORIENTATION and cls.ORIENTATION_METADATA in metadata:
            return metadata[cls.ORIENTATION_METADATA]

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

            if arg == MetadataNames.WIDTH:
                result += (cls.WIDTH_METADATA,)

            elif arg == MetadataNames.HEIGHT:
                result += (cls.HEIGHT_METADATA,)

            elif arg == MetadataNames.ORIENTATION:
                result += (cls.ORIENTATION_METADATA,)

            elif isinstance(arg, MetadataNames):
                result += (arg.value,)

            elif isinstance(arg, str):
                result += (arg,)
        return tuple(['-' + str(arg) for arg in result])

    @classmethod
    def get_metadata(cls, file, *args):
        real_args = cls.expand_args(*args)
        if isinstance(file, str):
            stdout, stderr = cls.execute("-fast2", "-b", "-j", "-n", *real_args, file)
        else:
            stdout = cls.execute_with_bytes(file, "-fast2", "-b", "-j", "-n", *real_args, "-")

        result = json.loads(stdout)
        if len(result) == 0:
            return {}
        return {metadata_name: cls.load_from_result(result, metadata_name) for metadata_name in args}

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
