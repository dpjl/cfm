from humanize import naturalsize

from camerafile.core.Logging import Logger

LOGGER = Logger(__name__)


class FilesSummary:
    def __init__(self):
        self.all = 0
        self.standard = 0
        self.zipped = 0
        self.managed = 0
        self.archive = 0
        self.size = 0
        LOGGER.start("{all} files found ({standard} standard, {zipped} zipped in {archive} archive(s)) [{size}]")

    def increment(self, all_files=None, standard=None, zipped=None, managed=None, archive=None, size=None):
        if all_files is not None:
            self.all += all_files
        if standard is not None:
            self.standard += standard
        if zipped is not None:
            self.zipped += zipped
        if managed is not None:
            self.managed += managed
        if archive is not None:
            self.archive += archive
        if size is not None:
            self.size += size

    def log(self):
        LOGGER.update(all=self.all,
                      standard=self.standard,
                      zipped=self.zipped,
                      archive=self.archive,
                      size=naturalsize(self.size))

    def end_logging(self):
        LOGGER.end(all=self.all,
                   standard=self.standard,
                   zipped=self.zipped,
                   archive=self.archive,
                   size=naturalsize(self.size))
