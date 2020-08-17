import hashlib
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from camerafile.MetadataList import MetadataList
from camerafile.Metadata import CAMERA_MODEL, DATE, SIGNATURE, ORIGINAL_COPY_PATH, DESTINATION_COPY_PATH, \
    ORIGINAL_MOVE_PATH, DESTINATION_MOVE_PATH
from camerafile.MetadataSignature import HASH, WIDTH, HEIGHT, FORMAT

CFM_COPY = "cfm-copy"

LOGGER = logging.getLogger(__name__)


class MediaFile:
    TYPE = [".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi", ".wav"]

    def __init__(self, path, parent_dir, parent_set):
        self.path = path
        self.relative_path = Path(self.path).relative_to(parent_set.root_path)
        self.parent_dir = parent_dir
        self.parent_set = parent_set
        self.name = Path(self.path).name
        self.extension = os.path.splitext(self.name)[1].lower()
        # TODO: still useful ??
        self.id = hashlib.md5(self.path.encode()).hexdigest()
        self.metadata = MetadataList(self)
        self.loaded_from_database = False
        self.db_id = None

    def __str__(self):
        return self.path

    def get_exact_signature(self):
        # self.metadata.compute_value(SIGNATURE)
        value = self.metadata.get_value(SIGNATURE)
        if value is not None:
            if FORMAT in value and WIDTH in value and HEIGHT in value:
                return value[FORMAT] + "-" + value[WIDTH] + "x" + value[HEIGHT] + ":" + value[HASH]
            else:
                return value[HASH]
        return None

    def is_same(self, other):
        # self.metadata.compute_value(SIGNATURE)
        # other.metadata.compute_value(SIGNATURE)
        sig1 = self.get_exact_signature()
        sig2 = other.get_exact_signature()
        if sig1 == sig2:
            return True
        return False

    def get_average_signature(self):
        # self.metadata.compute_value(SIGNATURE)
        value = self.metadata.get_value(SIGNATURE)
        if value is not None:
            return value[HASH]
        else:
            return None

    def looks_like(self, other):
        sig1 = self.get_average_signature()
        sig2 = other.get_average_signature()
        if sig1 == sig2:
            return True
        return False

    def is_copied_file(self):
        copied_path = Path(self.parent_set.root_path) / CFM_COPY
        if copied_path in Path(self.path).parents:
            return True
        return False

    def copy(self, new_media_set):

        if new_media_set.contains_exact(self):
            return "Image already exists"

        relative_path = self.relative_path.parent
        new_dir_path = Path(new_media_set.root_path) / CFM_COPY / relative_path
        os.makedirs(new_dir_path, exist_ok=True)
        new_file_path = new_dir_path / self.name
        new_metadata_file_path = new_dir_path / Path(self.metadata.external_metadata.file_path).name

        if os.path.exists(new_file_path):
            return "Filename already exists"

        shutil.copy2(self.path, new_file_path)
        if os.path.exists(self.metadata.external_metadata.file_path):
            shutil.copy2(self.metadata.external_metadata.file_path, new_metadata_file_path)

        new_media_file = MediaFile(str(new_file_path), None, new_media_set)
        new_media_file.metadata = self.metadata
        new_media_file.metadata.set_value(ORIGINAL_COPY_PATH, str(self.path))
        new_media_file.metadata.set_value(DESTINATION_COPY_PATH, str(new_file_path))
        new_media_file.metadata.save_external_metadata()
        new_media_set.add_file(new_media_file)

        return "Copied"

    def organize(self):
        camera_model = self.metadata.get_value(CAMERA_MODEL).replace(" ", "-")
        date = datetime.strptime(self.metadata.get_value(DATE), '%Y/%m/%d %H:%M:%S')
        year = date.strftime("%Y")
        month = date.strftime("%m-%B")

        new_dir_path = self.parent_set.root_path / year / month / camera_model
        os.makedirs(new_dir_path, exist_ok=True)

        new_file_path = new_dir_path / self.name
        new_metadata_file_path = new_dir_path / Path(self.metadata.external_metadata.file_path).name

        result = ("Moved", self.path, new_file_path)

        if os.path.exists(new_file_path):
            destination_size = new_file_path.stat().st_size
            origin_size = Path(self.path).stat().st_size
            if destination_size >= origin_size:
                return ("Ignored", "%s[%s]" % (self.path, origin_size),
                        "%s[%s]" % (new_file_path, destination_size))
            else:
                result = ("Replace smaller", "%s[%s]" % (self.path, origin_size),
                          "%s[%s]" % (new_file_path, destination_size))
                self.parent_set.delete_file(new_file_path)

        shutil.move(self.path, new_file_path)
        if os.path.exists(self.metadata.external_metadata.file_path):
            shutil.move(self.metadata.external_metadata.file_path, new_metadata_file_path)

        self.metadata.set_value(ORIGINAL_MOVE_PATH, str(self.path))
        self.metadata.set_value(DESTINATION_MOVE_PATH, str(new_file_path))
        self.metadata.save_external_metadata()
        self.path = str(new_file_path)

        return result

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
