#!/usr/bin/env python3
"""
Test script to verify the WhatsApp date update functionality.
This script creates a test environment and validates the new feature.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from camerafile.core.MediaSet import MediaSet
from camerafile.processor.BatchUpdateWhatsAppDates import BatchUpdateWhatsAppDates
from camerafile.core.Configuration import Configuration


def create_test_whatsapp_file(directory, filename, date_str):
    """Create a fake WhatsApp file with a specific name."""
    file_path = directory / filename
    with open(file_path, 'w') as f:
        f.write("Test WhatsApp file content")
    
    # Set a different modification time initially
    wrong_time = datetime(2020, 1, 1, 12, 0, 0).timestamp()
    os.utime(file_path, (wrong_time, wrong_time))
    
    return file_path


def test_batch_update_whatsapp_dates():
    """Test the BatchUpdateWhatsAppDates processor."""
    print("=" * 60)
    print("Testing BatchUpdateWhatsAppDates")
    print("=" * 60)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_media_set"
        test_dir.mkdir()
        
        print(f"\n✓ Created test directory: {test_dir}")
        
        # Create test files
        files = [
            ("IMG-20231225-WA0001.jpg", "2023-12-25"),
            ("VID-20240101-WA0002.mp4", "2024-01-01"),
            ("not_a_whatsapp_file.jpg", None),
            ("IMG-20231220-WA0003.jpg", "2023-12-20"),
        ]
        
        created_files = []
        for filename, date_str in files:
            file_path = create_test_whatsapp_file(test_dir, filename, date_str)
            created_files.append((file_path, date_str))
            print(f"✓ Created test file: {filename}")
        
        # Initialize configuration
        print("\n" + "=" * 60)
        print("Initializing configuration...")
        print("=" * 60)
        
        # Create a mock args object
        class MockArgs:
            def __init__(self):
                self.debug = False
                self.use_dump = False
                self.save_db = False
                self.exit_on_error = False
                self.ignore = None
                self.no_progress = True
                self.ui = False
                self.workers = 0
                self.cache_path = None
                self.thumbnails = False
                self.whatsapp = True
                self.whatsapp_date_update = True
                self.whatsapp_db = None
                self.command = "organize"
                self.dir1 = str(test_dir)
                self.dir2 = None
        
        args = MockArgs()
        Configuration.get().init(args)
        
        print("✓ Configuration initialized with whatsapp=True")
        
        # Load the media set
        print("\n" + "=" * 60)
        print("Loading media set...")
        print("=" * 60)
        
        media_set = MediaSet(str(test_dir))
        print(f"✓ Media set loaded with {len(media_set.media_file_list)} files")
        
        # Check initial modification times
        print("\n" + "=" * 60)
        print("Initial file modification times:")
        print("=" * 60)
        
        for file_path, expected_date in created_files:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"{file_path.name}: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run the batch processor
        print("\n" + "=" * 60)
        print("Running BatchUpdateWhatsAppDates...")
        print("=" * 60)
        
        batch = BatchUpdateWhatsAppDates(media_set)
        batch.execute()
        
        # Check final modification times
        print("\n" + "=" * 60)
        print("Final file modification times:")
        print("=" * 60)
        
        for file_path, expected_date in created_files:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"{file_path.name}: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if expected_date:
                expected_mtime = datetime.strptime(expected_date, "%Y-%m-%d")
                if mtime.date() == expected_mtime.date():
                    print(f"  ✓ Date correctly updated to {expected_date}")
                else:
                    print(f"  ✗ Date NOT updated (expected {expected_date})")
            else:
                print(f"  → Not a WhatsApp file (no change expected)")
        
        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)


if __name__ == "__main__":
    test_batch_update_whatsapp_dates()
