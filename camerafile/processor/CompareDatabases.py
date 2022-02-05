from pathlib import Path

from camerafile.core.MediaSetDatabase import MediaSetDatabase
from camerafile.core.OutputDirectory import OutputDirectory


class CompareDatabases:

    @staticmethod
    def execute(dir_1_path, dir_2_path):
        db1 = MediaSetDatabase(OutputDirectory(Path(dir_1_path).resolve()))
        db2 = MediaSetDatabase(OutputDirectory(Path(dir_2_path).resolve()))
        db1.compare(db2)
