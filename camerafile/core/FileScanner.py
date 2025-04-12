# -*- coding: utf-8 -*-
"""
FileScanner is responsible for scanning the root directory, processing
standard files and ZIP archives. It returns a dictionary of new files to load
and a list of ignored files.
"""
import os
import zipfile
from pathlib import Path
import os.path

# It is necessary to import the constants and classes used
from camerafile.core.Constants import MANAGED_TYPE, ARCHIVE_TYPE
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.fileaccess.ZipFileDescription import ZipFileDescription

class FileScanner:
    # Note: This class has been converted into a utility with static methods.
    # No instance attributes are maintained; all necessary parameters are passed as arguments.

    @staticmethod
    def update_from_disk(root_path: str, state, filename_map: dict) -> tuple[dict, list]:
        """
        Traverses the root directory and returns:
          - not_loaded_files: dict mapping relative paths to FileDescription objects.
          - ignored_files: list of ignored file paths.
        """
        root = Path(root_path).resolve()
        # Reset the "exists" flag for all previously registered files
        for key in filename_map:
            filename_map[key].exists = False

        not_loaded_files = {}
        ignored_files = []

        for path, _, files in os.walk(root.as_posix(), topdown=True):
            for file_name in files:
                file_path = Path(path) / file_name
                extension = os.path.splitext(file_name)[1].lower()
                if extension in MANAGED_TYPE and not state.should_be_ignored(file_path):
                    FileScanner._register_new_standard_file(file_path, root, filename_map, not_loaded_files)
                elif extension in ARCHIVE_TYPE:
                    FileScanner._load_zip_archive(file_path, root, state, filename_map, not_loaded_files, ignored_files)
                else:
                    ignored_files.append(file_path.as_posix())
                    # If the file previously existed, remove it from the internal mapping
                    relative_path = file_path.relative_to(root).as_posix()
                    if relative_path in filename_map:
                        del filename_map[relative_path]
        return not_loaded_files, ignored_files

    @staticmethod
    def _register_new_standard_file(file_path: Path, root: Path, filename_map: dict, not_loaded_files: dict) -> int:
        relative_path = file_path.relative_to(root).as_posix()
        if relative_path not in filename_map:
            file_size = file_path.stat().st_size
            file_desc = StandardFileDescription(relative_path, file_size)
            not_loaded_files[file_desc.relative_path] = file_desc
            return file_size
        else:
            file_entry = filename_map[relative_path]
            file_entry.exists = True
            return file_entry.file_desc.file_size

    @staticmethod
    def _load_zip_archive(zip_file_path: str, root: Path, state, filename_map: dict, not_loaded_files: dict, ignored_files: list) -> None:
        with zipfile.ZipFile(zip_file_path) as zip_file:
            for file_info in zip_file.filelist:
                file_name = file_info.filename
                if file_name.endswith('/'):
                    continue
                extension = os.path.splitext(file_name)[1].lower()
                if extension in MANAGED_TYPE and not state.should_be_ignored(file_name):
                    FileScanner._register_new_zipped_file(file_info, root, filename_map, not_loaded_files, file_name, zip_file_path)
                else:
                    ignored_files.append((root / zip_file_path).as_posix())

    @staticmethod
    def _register_new_zipped_file(file_info, root: Path, filename_map: dict, not_loaded_files: dict, file_name: str, zip_file_path: str) -> int:
        zip_root = Path(zip_file_path)
        relative_path = (zip_root / file_name).relative_to(root).as_posix()
        zip_relative_path = zip_root.relative_to(root).as_posix()
        if relative_path not in filename_map:
            file_size = file_info.file_size
            zip_file_desc = ZipFileDescription(zip_relative_path, file_name, file_size)
            not_loaded_files[zip_file_desc.get_relative_path()] = zip_file_desc
            return file_size
        else:
            file_entry = filename_map[relative_path]
            file_entry.exists = True
            return file_entry.file_desc.file_size
