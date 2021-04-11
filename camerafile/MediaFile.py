import hashlib
import logging
import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from camerafile import Constants
from camerafile.Constants import INTERNAL, SIGNATURE, ORIGINAL_COPY_PATH, \
    DESTINATION_COPY_PATH, ORIGINAL_MOVE_PATH, DESTINATION_MOVE_PATH, CFM_CAMERA_MODEL
from camerafile.MetadataList import MetadataList

CFM_COPY = ".tmp-cfm-copy"

LOGGER = logging.getLogger(__name__)

lock = threading.Lock()


class MediaFile:

    def __init__(self, path, parent_dir, parent_set):
        self.path = path
        self.relative_path = Path(self.path).relative_to(parent_set.root_path)
        self.parent_dir = parent_dir
        self.parent_set = parent_set
        self.name = Path(self.path).name.lower()
        self.original_filename = self.get_original_filename()
        self.extension = os.path.splitext(self.name)[1].lower()
        self.id = hashlib.md5(self.path.encode()).hexdigest()
        self.metadata = MetadataList(self)
        self.loaded_from_database = False
        self.db_id = None
        self.date_identifier = None

    def reinit(self):
        self.relative_path = Path(self.path).relative_to(self.parent_set.root_path)
        self.name = Path(self.path).name.lower()
        self.original_filename = self.get_original_filename()
        self.id = hashlib.md5(self.path.encode()).hexdigest()

    def __str__(self):
        return self.path

    def is_same(self, other):
        # self.metadata.compute_value(SIGNATURE)
        # other.metadata.compute_value(SIGNATURE)
        sig1 = self.get_signature()
        sig2 = other.get_signature()
        if sig1 == sig2:
            return True
        return False

    def get_signature(self):
        # self.metadata.compute_value(SIGNATURE)
        return self.metadata.get_value(SIGNATURE)

    def get_original_filename(self):
        m = re.search(".*~{(.*)}~.*", self.name)
        if m is not None:
            return m.group(1)
        return self.name

    def get_date(self):
        date = self.metadata[INTERNAL].get_date()
        if date is not None:
            return datetime.strptime(date, '%Y/%m/%d %H:%M:%S.%f')
        return None

    def get_str_date(self):
        date = self.metadata[INTERNAL].get_date()
        if date is not None:
            date = datetime.strptime(date, '%Y/%m/%d %H:%M:%S.%f')
            new_date_format = date.strftime("%Y/%m/%d")
            return new_date_format
        return ""

    def get_cfm_filename(self):
        m = re.search(".*~{(.*)}~.*", self.name)
        if m is None:
            date = self.metadata[INTERNAL].get_date()
            width = self.metadata[INTERNAL].get_width()
            height = self.metadata[INTERNAL].get_height()
            if date is not None:
                date = datetime.strptime(date, '%Y/%m/%d %H:%M:%S.%f')
                new_date_format = date.strftime("%Y-%m-%d_%Hh%Mm%S.%f")
                cfm_filename = new_date_format + "~{" + self.name + "}~"
                if width is not None and height is not None:
                    cfm_filename += str(width) + "x" + str(height)
                cfm_filename += self.extension
                return cfm_filename
            else:
                return None
        else:
            return self.name

    def get_exif_date(self):
        return self.metadata[INTERNAL].get_date()

    def get_camera_model(self):
        return self.metadata[CFM_CAMERA_MODEL].value

    def get_dimensions(self):
        width = self.metadata[INTERNAL].get_width()
        height = self.metadata[INTERNAL].get_height()
        if width is not None and height is not None:
            return str(width) + "x" + str(height)
        return None

    def update_date_identifier(self):
        if self.date_identifier is None:
            date = self.metadata[INTERNAL].get_date()
            width = self.metadata[INTERNAL].get_width()
            height = self.metadata[INTERNAL].get_height()
            if date is not None and width is not None and height is not None:
                self.date_identifier = date + "-" + str(width) + "x" + str(height)
            elif date is not None:
                self.date_identifier = date

    def is_copied_file(self):
        copied_path = Path(self.parent_set.root_path) / CFM_COPY
        if copied_path in Path(self.path).parents:
            return True
        return False

    def get_destination_path(self, new_media_set):
        relative_path = self.relative_path.parent
        new_dir_path = Path(new_media_set.root_path) / CFM_COPY / relative_path
        new_file_path = new_dir_path / self.get_cfm_filename()
        return new_file_path

    @staticmethod
    def copy_file(copy_task_arg):
        file_id, old_file_path, new_file_path = copy_task_arg
        try:
            if os.path.exists(new_file_path):
                return False, file_id, None
            os.makedirs(Path(new_file_path).parent, exist_ok=True)
            #shutil.copy2(old_file_path, new_file_path)
            os.symlink(old_file_path, new_file_path)
            return True, file_id, new_file_path
        except:
            return False, file_id, None

    def copy_metadata(self, new_media_set, new_file_path):
        new_media_file = MediaFile(str(new_file_path), None, new_media_set)
        new_media_file.metadata = self.metadata
        new_media_file.metadata.set_value(ORIGINAL_COPY_PATH, str(self.path))
        new_media_file.metadata.set_value(DESTINATION_COPY_PATH, str(new_file_path))
        new_media_set.add_file(new_media_file)
        return True

    def add_suffix_to_filename(self, suffix):
        splitext = os.path.splitext(self.name)
        name_without_extension = splitext[0]
        extension = splitext[1] if len(splitext) > 1 else ""
        new_file_name = name_without_extension + suffix + extension
        new_file_path = Path(self.path).parent / new_file_name
        shutil.move(self.path, new_file_path)
        self.metadata.set_value(DESTINATION_MOVE_PATH, str(new_file_path))
        self.path = str(new_file_path)
        self.reinit()

    def relative_path_to_filename(self):
        result = ""
        for parent in self.relative_path.parents:
            if parent.name != "" and parent.name != CFM_COPY:
                result = "[" + parent.name + "]" + result
        return "[.]" + result

    def organize(self):
        camera_model = self.metadata[CFM_CAMERA_MODEL].value
        if camera_model is not None:
            camera_model = camera_model.replace(" ", "-")
        if camera_model is None:
            camera_model = Constants.UNKNOWN  # + "~{" + self.relative_path_to_filename() + "}~"
        date = datetime.strptime(self.metadata[INTERNAL].get_date(), '%Y/%m/%d %H:%M:%S.%f')
        year = date.strftime("%Y")
        month = date.strftime("%m[%B]")
        new_dir_path = self.parent_set.root_path / year / month / camera_model
        new_file_path = new_dir_path / self.name

        if new_file_path == self.path:
            return "Already organized", self.path, new_file_path

        os.makedirs(new_dir_path, exist_ok=True)

        if os.path.exists(new_file_path):
            self.parent_set.add_size_to_filename(str(new_file_path))
            self.parent_set.add_size_to_filename(str(self.path))
            new_file_path = new_dir_path / self.name

        if os.path.exists(new_file_path):
            self.parent_set.add_date_to_filename(str(new_file_path))
            self.parent_set.add_date_to_filename(str(self.path))
            new_file_path = new_dir_path / self.name

        if os.path.exists(new_file_path):
            print("Something is wrong: destination still exists " + new_file_path)

        result = ("Moved", self.path, new_file_path)
        shutil.move(self.path, new_file_path)

        self.metadata.set_value(ORIGINAL_MOVE_PATH, str(self.path))
        self.metadata.set_value(DESTINATION_MOVE_PATH, str(new_file_path))
        self.path = str(new_file_path)
        self.reinit()

        return result
