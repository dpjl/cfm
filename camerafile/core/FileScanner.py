# -*- coding: utf-8 -*-
import os
import zipfile
from pathlib import Path
import os.path
from camerafile.core.Logging import Logger
from camerafile.console.FilesSummary import FilesSummary
from camerafile.core.Constants import MANAGED_TYPE, ARCHIVE_TYPE
from camerafile.core.MediaFile import MediaFile
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.fileaccess.ZipFileDescription import ZipFileDescription
from typing import Dict, Tuple

LOGGER = Logger(__name__)

"""
FileScanner is responsible for scanning the root directory, processing
standard files and ZIP archives. It returns a dictionary of new files to load
and a list of ignored files.
"""
class FileScanner:

    @staticmethod
    def update_from_disk(root_path: str, state, filename_map: dict) -> Tuple[Dict[str, FileDescription], Dict[str, FileDescription]]:
        root = Path(root_path).resolve()
        files_summary = FilesSummary()
        new_files = {}
        new_dirs = {}
        ignored_files = []

        for path, dirs, files in os.walk(root.as_posix(), topdown=True):
            # Process directories first
            for dir_name in dirs:
                dir_path = Path(path) / dir_name
                relative_path = dir_path.relative_to(root).as_posix()
                FileScanner._register_new_dir(dir_path, root, new_dirs, filename_map)

            # Then process files
            for file_name in files:
                file_path = Path(path) / file_name
                extension = os.path.splitext(file_name)[1].lower()
                if extension in MANAGED_TYPE and not state.should_be_ignored(file_path):
                    file_size = FileScanner._register_new_standard_file(file_path, root, filename_map, new_files)
                    files_summary.increment(all_files=1, managed=1, standard=1, size=file_size)
                elif extension in ARCHIVE_TYPE:
                    FileScanner._load_zip_archive(file_path, root, state, filename_map, new_files, new_dirs, ignored_files, files_summary)
                else:
                    files_summary.increment(all_files=1, standard=1)
                    ignored_files.append(file_path.as_posix())
                    # If the file previously existed, remove it from the internal mapping
                    relative_path = file_path.relative_to(root).as_posix()
                    if relative_path in filename_map:
                        del filename_map[relative_path]
            files_summary.log()
        files_summary.end_logging()

        saved_file = OutputDirectory.get(root_path).save_list(ignored_files, "ignored-files.json")
        LOGGER.info_indent("{l1} files ignored [{saved}]".format(l1=len(ignored_files), saved=saved_file))
        LOGGER.info_indent("{l1} detected as media files".format(l1=files_summary.managed))

        return new_files, new_dirs

    @staticmethod
    def _register_new_dir(dir_path: Path, root: Path, new_dirs: dict, filename_map: dict) -> None:
        """Register a new directory in the new_dirs dictionary if it doesn't exist in filename_map."""
        relative_path = dir_path.relative_to(root).as_posix()
        if relative_path not in filename_map:
            stat = dir_path.stat()
            system_id = FileScanner._get_system_id(stat)
            dir_desc = StandardFileDescription(relative_path, 0, system_id)  # Directories have size 0
            new_dirs[dir_desc.relative_path] = dir_desc
        else:
            filename_map[relative_path].exists = True

    @staticmethod
    def _load_zip_archive(zip_file_path: Path, root: Path, state, filename_map: dict, new_files: dict, new_dirs: dict, ignored_files: list, files_summary: FilesSummary) -> None:
        files_summary.increment(archive=1)
        zip_relative_path = zip_file_path.relative_to(root).as_posix()
        
        with zipfile.ZipFile(zip_file_path) as zip_file:
            # First process all files to collect their paths
            new_zip_files = []  # List to store paths of newly created files
            dirs = set()  # Set to store all parent directories
            
            for file_info in zip_file.filelist:
                file_name = file_info.filename
                if file_name.endswith('/'):
                    continue
                    
                extension = os.path.splitext(file_name)[1].lower()
                files_summary.increment(all_files=1, zipped=1)
                
                if extension in MANAGED_TYPE and not state.should_be_ignored(file_name):
                    file_size = FileScanner._register_new_zipped_file(file_info, root, filename_map, new_files, file_name, zip_file_path)
                    files_summary.increment(managed=1, size=file_size)
                    
                    # Store the path and collect parent directories
                    file_path = f"{zip_relative_path}/{file_name}"
                    new_zip_files.append(file_path)
                    
                    # Add all parent directories
                    dir_path = os.path.dirname(file_path)
                    parts = dir_path.split('/')
                    for i in range(1, len(parts) + 1):
                        dirs.add('/'.join(parts[:i]))
                else:
                    ignored_files.append(zip_file_path.as_posix())

            # Register all directories
            for dir_path in sorted(dirs):  # Sort to ensure parents are processed before children
                if dir_path not in filename_map:
                    dir_desc = StandardFileDescription(dir_path, 0, None)  # Directories in zip have no system_id
                    new_dirs[dir_desc.relative_path] = dir_desc
                else:
                    filename_map[dir_path].exists = True

    @staticmethod
    def _register_new_standard_file(file_path: Path, root: Path, filename_map: dict, new_files: dict) -> int:
        relative_path = file_path.relative_to(root).as_posix()
        if relative_path not in filename_map:
            stat = file_path.stat()
            file_size = stat.st_size
            system_id = FileScanner._get_system_id(stat)
            file_desc = StandardFileDescription(relative_path, file_size, system_id)
            new_files[file_desc.relative_path] = file_desc
            return file_size
        else:
            file_entry: MediaFile = filename_map[relative_path]
            file_entry.exists = True
            if file_entry.file_desc.system_id is None:
                stat = file_path.stat()
                file_entry.file_desc.system_id = FileScanner._get_system_id(stat)
            return file_entry.file_desc.file_size

    @staticmethod
    def _register_new_zipped_file(file_info, root: Path, filename_map: dict, new_files: dict, file_name: str, zip_file_path: Path) -> int:
        zip_root = Path(zip_file_path)
        relative_path = (zip_root / file_name).relative_to(root).as_posix()
        zip_relative_path = zip_root.relative_to(root).as_posix()
        if relative_path not in filename_map:
            file_size = file_info.file_size
            zip_file_desc = ZipFileDescription(zip_relative_path, file_name, file_size)
            new_files[zip_file_desc.get_relative_path()] = zip_file_desc
            return file_size
        else:
            file_entry = filename_map[relative_path]
            file_entry.exists = True
            return file_entry.file_desc.file_size
        
    if os.name == "nt":
        import ctypes

        @staticmethod
        def _get_system_id(stat) -> int:
            FILE_READ_EA = 0x0008
            FILE_SHARE_READ = 1
            FILE_SHARE_WRITE = 2
            OPEN_EXISTING = 3

            class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("FileAttributes", ctypes.c_uint32),
                    ("CreationTime", ctypes.c_ulonglong),
                    ("LastAccessTime", ctypes.c_ulonglong),
                    ("LastWriteTime", ctypes.c_ulonglong),
                    ("VolumeSerialNumber", ctypes.c_uint32),
                    ("FileSizeHigh", ctypes.c_uint32),
                    ("FileSizeLow", ctypes.c_uint32),
                    ("NumberOfLinks", ctypes.c_uint32),
                    ("FileIndexHigh", ctypes.c_uint32),
                    ("FileIndexLow", ctypes.c_uint32),
                ]

            CreateFile = ctypes.windll.kernel32.CreateFileW
            GetFileInformationByHandle = ctypes.windll.kernel32.GetFileInformationByHandle
            CloseHandle = ctypes.windll.kernel32.CloseHandle

            handle = CreateFile(
                path,
                FILE_READ_EA,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None
            )

            if handle == -1 or handle is None:
                raise OSError(f"Cannot open file: {path}")

            info = BY_HANDLE_FILE_INFORMATION()
            res = GetFileInformationByHandle(handle, ctypes.byref(info))
            CloseHandle(handle)

            if not res:
                raise OSError(f"Cannot get file info for: {path}")

            file_index = (info.FileIndexHigh << 32) | info.FileIndexLow
            volume_serial = info.VolumeSerialNumber

            # Structure du system_id (96 bits) :
            # - Windows: [volume_serial (32 bits)][file_index (64 bits)]
            return (volume_serial << 64) | file_index

    else:
        @staticmethod
        def _get_system_id(stat) -> int:
            # Structure du system_id (96 bits) :
            # - Unix:    [st_dev (32 bits)][st_ino (64 bits)]
            return (stat.st_dev << 64) | stat.st_ino
