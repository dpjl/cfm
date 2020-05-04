import os
import shutil
import imagehash
from PIL import Image
from pathlib import Path
from vivicfm.MediaDate import MediaDate
from vivicfm.MediaCameraModel import MediaCameraModel
from vivicfm.ExternalMetadata import ExternalMetadata


class MediaFile:
    TYPE = [".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi", ".wav"]

    def __init__(self, path, parent_dir):
        self.path = path
        self.parent_dir = parent_dir
        self.name = Path(self.path).name
        self.extension = os.path.splitext(self.name)[1].lower()

        self.camera_model = MediaCameraModel(self)
        self.date = MediaDate(self)
        self.signature = None

        self.external_metadata = ExternalMetadata(path)

    def __str__(self):
        return self.path

    def compute_signature(self):
        signature = self.external_metadata.get_signature()
        if signature is None:
            signature = imagehash.average_hash(Image.open(self.path))
            self.external_metadata.update_signature(str(signature))
            self.external_metadata.save()

    def move(self, new_root_path):
        camera_model = self.camera_model.get().replace(" ", "-")
        date = self.date.get()
        year = date.strftime("%Y")
        month = date.strftime("%m-%B")
        new_dir_path = Path(new_root_path) / year / month / camera_model
        os.makedirs(new_dir_path, exist_ok=True)

        new_file_path = new_dir_path / self.name
        new_metadata_file_path = new_dir_path / self.external_metadata.file_name

        self.external_metadata.update_original_path(str(self.path))
        self.external_metadata.update_destination_path(str(new_file_path))
        self.external_metadata.save()

        # shutil.move(self.path, new_file_path)
        # self.path = new_file_path  # necessary ?
        # shutil.copy2(self.external_metadata.file_path, new_metadata_file_path)

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

    @classmethod
    def is_media_file(cls, file_path):
        file_name = Path(file_path).name
        file_extension = os.path.splitext(file_name)[1].lower()
        if file_extension in cls.TYPE:
            return True
        return False
