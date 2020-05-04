import locale
import subprocess
import logging

from vivicfm.CFMResource import CFMResource

LOGGER = logging.getLogger(__name__)


class AviMetaEdit(object):
    NOTHING_TO_DO = "Nothing to do"
    IS_MODIFIED = "Is modified"

    def __init__(self, executable=None, stdout_file_path=None, stderr_file_path=None):
        self.executable = executable
        if self.executable is None:
            self.executable = CFMResource.avimetaedit_executable
        self.stdout_file = None
        self.stderr_file = None
        if stdout_file_path is not None:
            self.stdout_file = open(stdout_file_path, "w")
        if stderr_file_path is not None:
            self.stderr_file = open(stderr_file_path, "w")

    def __del__(self):
        if self.stdout_file is not None:
            self.stdout_file.close()
        if self.stderr_file is not None:
            self.stderr_file.close()

    @staticmethod
    def write_in_file(file, content):
        if file is not None:
            file.write(content)

    def execute(self, *args):
        result = subprocess.run([self.executable] + list(args),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout = result.stdout.decode(locale.getpreferredencoding())
        stderr = result.stderr.decode(locale.getpreferredencoding())
        self.write_in_file(self.stdout_file, stdout)
        self.write_in_file(self.stderr_file, stderr)
        return stdout, stderr

    def update_source(self, filename, new_model):
        stdout, stderr = self.execute("-v", "--ISRC=%s" % new_model, filename)
        if AviMetaEdit.IS_MODIFIED not in stdout and AviMetaEdit.NOTHING_TO_DO not in stdout:
            return "Error when trying to update %s" % filename
        if stderr != "":
            LOGGER.error(stderr.strip())
        return ""
