import locale
import subprocess
import logging

from camerafile.Resource import Resource

LOGGER = logging.getLogger(__name__)


class AviMetaEdit(object):
    NOTHING_TO_DO = "Nothing to do"
    IS_MODIFIED = "Is modified"
    executable = None
    stdout_file = None
    stderr_file = None

    @classmethod
    def init(cls, stdout_file_path=None, stderr_file_path=None):
        if stdout_file_path is not None:
            cls.stdout_file = open(stdout_file_path, "w")
        if stderr_file_path is not None:
            cls.stderr_file = open(stderr_file_path, "w")

    @classmethod
    def close(cls):
        if cls.stdout_file is not None:
            cls.stdout_file.close()
        if cls.stderr_file is not None:
            cls.stderr_file.close()

    @staticmethod
    def write_in_file(file, content):
        if file is not None:
            file.write(content)

    @classmethod
    def execute(cls, *args):
        cls.executable = Resource.avimetaedit_executable
        result = subprocess.run([cls.executable] + list(args),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout = result.stdout.decode(locale.getpreferredencoding())
        stderr = result.stderr.decode(locale.getpreferredencoding())
        cls.write_in_file(cls.stdout_file, stdout)
        cls.write_in_file(cls.stderr_file, stderr)
        return stdout, stderr

    @classmethod
    def update_source(cls, filename, new_model):
        stdout, stderr = cls.execute("-v", "--ISRC=%s" % new_model, filename)
        if AviMetaEdit.IS_MODIFIED not in stdout and AviMetaEdit.NOTHING_TO_DO not in stdout:
            return "Error when trying to update %s" % filename
        if stderr != "":
            LOGGER.error(stderr.strip())
        return ""
