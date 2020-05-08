import os
import shutil
from datetime import datetime
from pathlib import Path
from camerafile.MetadataList import MetadataList
from camerafile.Metadata import ORIGINAL_PATH, DESTINATION_PATH, CAMERA_MODEL, DATE, SIGNATURE


class MediaFile:
    TYPE = [".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi", ".wav"]

    def __init__(self, path, parent_dir, exists=True):
        self.path = path
        self.parent_dir = parent_dir
        self.name = Path(self.path).name
        self.extension = os.path.splitext(self.name)[1].lower()
        self.metadata = MetadataList(self)
        self.exists = exists

    def __str__(self):
        return self.path

    def __eq__(self, other):
        self.metadata.compute_value(SIGNATURE)
        other.metadata.compute_value(SIGNATURE)
        if self.metadata.get_value(SIGNATURE) == other.metadata.get_value(SIGNATURE):
            return True
        return False

    def unmove(self):
        original_path = self.metadata.get_value(ORIGINAL_PATH)
        destination_path = self.metadata.get_value(DESTINATION_PATH)
        shutil.move(destination_path, original_path)
        if os.path.exists(destination_path + MetadataList.METADATA_EXTENSION):
            os.remove(destination_path + MetadataList.METADATA_EXTENSION)

    def move(self, new_root_path):
        camera_model = self.metadata.get_value(CAMERA_MODEL).replace(" ", "-")
        date = datetime.strptime(self.metadata.get_value(DATE), '%Y:%m:%d %H:%M:%S')
        year = date.strftime("%Y")
        month = date.strftime("%m-%B")
        new_dir_path = Path(new_root_path) / year / month / camera_model
        os.makedirs(new_dir_path, exist_ok=True)

        new_file_path = new_dir_path / self.name
        new_metadata_file_path = new_dir_path / Path(self.metadata.external_metadata_file_path).name

        self.metadata.set_value(ORIGINAL_PATH, str(self.path))
        self.metadata.set_value(DESTINATION_PATH, str(new_file_path))

        shutil.move(self.path, new_file_path)
        if os.path.exists(self.metadata.external_metadata_file_path):
            shutil.copy2(self.metadata.external_metadata_file_path, new_metadata_file_path)

    def backup(self):
        original_renamed = self.path + ".original"
        if not os.path.exists(original_renamed):
            os.rename(self.path, original_renamed)
            shutil.copy2(original_renamed, self.path)
            return True
        return False

    def restore(self):
        original_file = self.path + ".original"
        if os.path.exists(original_file):
            os.remove(self.path)
            os.rename(original_file, self.path)
            return True
        return False
