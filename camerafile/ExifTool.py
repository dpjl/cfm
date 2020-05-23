import json
import locale
import logging
import subprocess
from datetime import datetime
from threading import Thread
from queue import Queue, Empty
from camerafile.Resource import Resource

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
    CREATE_DATE_METADATA = "CreateDate"
    MODIFY_DATE_METADATA = "FileModifyDate"
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
            LOGGER.info("Starting %s", cls.executable)
            cls.process = subprocess.Popen(
                [cls.executable, "-stay_open", "True", "-@", "-"],
                universal_newlines=True, bufsize=1,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cls.stdout_reader.start_read(cls.process.stdout)
            cls.stderr_reader.start_read(cls.process.stderr)

    @classmethod
    def stop(cls):
        if cls.process is not None:
            LOGGER.info("Stopping %s", cls.executable)
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
            LOGGER.error(err.strip())
        return output[:-len(cls.SENTINEL)], err

    @classmethod
    def get_model_and_date(cls, filename):
        stdout, stderr = cls.execute("-j", "-n",
                                     "-" + cls.MODEL_METADATA,
                                     "-" + cls.SOURCE_METADATA,
                                     "-" + cls.CREATE_DATE_METADATA,
                                     "-" + cls.MODIFY_DATE_METADATA,
                                     filename)
        result = json.loads(stdout)
        if len(result) == 0:
            return None, None

        model = None
        if cls.MODEL_METADATA in result[0]:
            model = result[0][cls.MODEL_METADATA]
        elif cls.SOURCE_METADATA in result[0]:
            model = result[0][cls.SOURCE_METADATA]

        date = None
        if cls.CREATE_DATE_METADATA in result[0]:
            str_date = result[0][cls.CREATE_DATE_METADATA]
            try:
                date = datetime.strptime(str_date.split("+")[0], '%Y:%m:%d %H:%M:%S')
            except ValueError:
                date = datetime.min
        elif cls.MODIFY_DATE_METADATA in result[0]:
            str_date = result[0][cls.MODIFY_DATE_METADATA]
            try:
                date = datetime.strptime(str_date.split("+")[0], '%Y:%m:%d %H:%M:%S')
            except ValueError:
                date = datetime.min
        return model, date

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
