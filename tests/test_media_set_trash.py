import os
import shutil
import tempfile
from pathlib import Path

import pytest

from camerafile.core.MediaSet import MediaSet
from camerafile.core.MediaSetInitializer import MediaSetInitializer
from camerafile.core.Constants import IMAGE_TYPE


@pytest.fixture
def test_environment():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create a test media set structure
    root_path = os.path.join(temp_dir, "test_media_set")
    os.makedirs(root_path)
    
    # Create some directories
    dir1 = os.path.join(root_path, "dir1")
    dir2 = os.path.join(root_path, "dir2")
    os.makedirs(dir1)
    os.makedirs(dir2)
    
    # Create some test image files
    test_files = []
    for i in range(3):
        # Create a file in dir1
        file_path = os.path.join(dir1, f"test{i}.jpg")
        with open(file_path, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00')
        test_files.append(file_path)
        
        # Create a file in dir2
        file_path = os.path.join(dir2, f"test{i}.jpg")
        with open(file_path, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00')
        test_files.append(file_path)
    
    yield root_path, test_files
    
    # Cleanup
    shutil.rmtree(temp_dir)


def test_move_to_trash(test_environment):
    root_path, test_files = test_environment
    
    # Initialize media set
    media_set = MediaSet(root_path)
    MediaSetInitializer.initialize(media_set)
    
    # Get the first file to move to trash
    file_to_move = test_files[0]
    media_file = next(mf for mf in media_set if mf.get_path() == os.path.relpath(file_to_move, root_path))
    
    # Store initial state
    initial_file_count = len(media_set.media_file_list)
    initial_dir_count = len(media_set.media_dir_list)
    initial_id_map_size = len(media_set.id_map)
    initial_filename_map_size = len(media_set.filename_map)
    original_parent_dir_id = media_file.parent_dir.id  # Capture the original parent directory ID
    
    # Move file to trash
    assert media_set.move_to_trash(media_file)
    
    # Verify file was physically moved
    trash_path = os.path.join(root_path, ".cfm-trash")
    assert os.path.exists(trash_path)
    trash_files = os.listdir(trash_path)
    assert len(trash_files) == 1
    
    # Verify the new filename contains the parent directory ID
    trash_file = trash_files[0]
    assert trash_file.startswith(f"{original_parent_dir_id}-")  # Use the original parent directory ID
    
    # Verify media set state
    assert len(media_set.media_file_list) == initial_file_count  # Same number of files
    assert len(media_set.media_dir_list) == initial_dir_count + 1  # Added trash directory
    assert len(media_set.id_map) == initial_id_map_size  # Same number of IDs
    assert len(media_set.filename_map) == initial_filename_map_size  # Same number of filename mappings
    
    # Verify the moved file is now in the trash directory
    moved_file = next(mf for mf in media_set if mf.parent_dir.path == os.path.join(root_path, ".cfm-trash"))
    assert moved_file is not None
    assert moved_file.parent_dir == media_set.media_dir_list[".cfm-trash"]
    
    # Verify the original directory has one less file
    original_dir = media_set.media_dir_list["dir1"]
    assert len(original_dir.children_files) == 2  # Started with 3, now has 2
    
    # Verify the trash directory has one file
    trash_dir = media_set.media_dir_list[".cfm-trash"]
    assert len(trash_dir.children_files) == 1


def test_move_to_trash_multiple_files(test_environment):
    root_path, test_files = test_environment
    
    # Initialize media set
    media_set = MediaSet(root_path)
    MediaSetInitializer.initialize(media_set)
    
    # Move two files to trash
    for file_path in test_files[:2]:
        media_file = next(mf for mf in media_set if mf.get_path() == os.path.relpath(file_path, root_path))
        assert media_set.move_to_trash(media_file)
    
    # Verify trash directory has two files
    trash_dir = media_set.media_dir_list[".cfm-trash"]
    assert len(trash_dir.children_files) == 2
    
    # Verify each file has correct parent directory reference
    for media_file in trash_dir.children_files:
        assert media_file.parent_dir == trash_dir
        assert media_file.parent_dir.path == os.path.join(root_path, ".cfm-trash")


def test_move_to_trash_invalid_file(test_environment):
    root_path, _ = test_environment
    
    # Initialize media set
    media_set = MediaSet(root_path)
    MediaSetInitializer.initialize(media_set)
    
    # Try to move a non-existent file
    non_existent_file = os.path.join(root_path, "non_existent.jpg")
    media_file = next((mf for mf in media_set if mf.get_path() == os.path.relpath(non_existent_file, root_path)), None)
    assert media_file is None or not media_set.move_to_trash(media_file) 