import json
import locale
import logging
import subprocess
from threading import Thread
from queue import Queue, Empty

from vivicfm.CFMResource import CFMResource

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
    SENTINEL = "{ready}\n"

    def __init__(self, executable=None, stdout_file_path=None, stderr_file_path=None):
        self.executable = executable
        if self.executable is None:
            self.executable = CFMResource.exiftool_executable
        self.process = None
        self.stdout_reader = NonBlockingStreamReader(redirected_file_path=stdout_file_path)
        self.stderr_reader = NonBlockingStreamReader(redirected_file_path=stderr_file_path)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        LOGGER.info("Starting %s", self.executable)
        self.process = subprocess.Popen(
            [self.executable, "-stay_open", "True", "-@", "-"],
            universal_newlines=True, bufsize=1,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.stdout_reader.start_read(self.process.stdout)
        self.stderr_reader.start_read(self.process.stderr)

    def stop(self):
        LOGGER.info("Stopping %s", self.executable)
        self.process.stdin.write("-stay_open\nFalse\n")
        self.process.stdin.flush()

    def execute(self, *args):
        args = ExifTool.CHARSET_OPTION + args + ("-execute\n",)
        self.process.stdin.write(str.join("\n", args))
        self.process.stdin.flush()
        output = ""
        while not output.endswith(self.SENTINEL):
            output += self.stdout_reader.get_new_line()
        err = ""
        new_line = ""
        while new_line is not None:
            new_line = self.stderr_reader.get_new_line_no_wait()
            if new_line is not None:
                err += new_line
        if err != "":
            LOGGER.error(err.strip())
        return output[:-len(self.SENTINEL)], err

    def get_model_or_source(self, filename):
        stdout, stderr = self.execute("-j", "-n", "-model", "-source", filename)
        result = json.loads(stdout)
        if len(result) == 0:
            return None
        if ExifTool.MODEL_METADATA in result[0]:
            return result[0][ExifTool.MODEL_METADATA]
        if ExifTool.SOURCE_METADATA in result[0]:
            return result[0][ExifTool.SOURCE_METADATA]
        return None

    def update_model(self, filename, new_model):
        stdout, stderr = self.execute("-overwrite_original", "-source=" + new_model, filename)
        if ExifTool.IMAGE_UPDATE not in stdout:
            return "Error when trying to update %s" % filename
        return ""

    def update_source(self, filename, new_model):
        stdout, stderr = self.execute("-overwrite_original", "-source=" + new_model, filename)
        if ExifTool.IMAGE_UPDATE not in stdout:
            return "Error when trying to update %s" % filename
        return ""
