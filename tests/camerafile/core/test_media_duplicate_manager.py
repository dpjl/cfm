import unittest
from typing import Any, Dict, List

# Import constants and the class to test
from camerafile.core.Constants import CFM_CAMERA_MODEL, SIGNATURE
from camerafile.core.MediaDuplicateManager import MediaDuplicateManager

# Dummy classes to simulate minimal behavior for MediaFile, file description and metadata.
class DummyFileDesc:
    def __init__(self, name: str):
        self.name = name

class DummyMeta:
    def __init__(self, value: Any = None):
        self.value = value

class DummyMediaFile:
    def __init__(self, name: str, signature: Any = None, camera_model: Any = None):
        self.file_desc = DummyFileDesc(name)
        # Use the keys SIGNATURE and CFM_CAMERA_MODEL for metadata simulation.
        self.metadata: Dict[str, DummyMeta] = {
            SIGNATURE: DummyMeta(signature),
            CFM_CAMERA_MODEL: DummyMeta(camera_model)
        }
    def __repr__(self):
        return f"DummyMediaFile({self.file_desc.name})"

# A fake index manager to simulate the behavior of MediaIndexer.
class FakeIndexManager:
    def __init__(self):
        # date_size_map: mapping from date string to dict from file size to list of DummyMediaFile
        self.date_size_map: Dict[str, Dict[Any, List[DummyMediaFile]]] = {}
        # date_sig_map: mapping from date string to dict from signature to list of DummyMediaFile
        self.date_sig_map: Dict[str, Dict[Any, List[DummyMediaFile]]] = {}
        self.reindexed: List[DummyMediaFile] = []
    def add_media_file(self, media_file: DummyMediaFile) -> None:
        # For testing propagation methods, just record the media file was re-indexed.
        self.reindexed.append(media_file)

# Dummy media set to wrap FakeIndexManager as its indexer.
class DummyMediaSet:
    def __init__(self, fake_index: FakeIndexManager):
        self.indexer = fake_index

class TestMediaDuplicateManager(unittest.TestCase):

    def setUp(self):
        self.fake_index = FakeIndexManager()
        self.dummy_set = DummyMediaSet(self.fake_index)

    def test_get_possibly_duplicates(self):
        # Setup a date with multiple size groups.
        date = "2021-01-01"
        file1 = DummyMediaFile("imgA.jpg")
        file2 = DummyMediaFile("imgB.jpg")
        file3 = DummyMediaFile("imgC.jpg")
        # Let date_size_map have two groups (e.g. by file size)
        self.fake_index.date_size_map = {
            date: {
                100: [file1, file2],  # group with multiple files
                200: [file3]          # single-file group
            }
        }
        result = MediaDuplicateManager.get_possibly_duplicates(self.dummy_set)
        self.assertIn(file1, result)
        self.assertIn(file3, result)
        self.assertEqual(len(result), 2)

    def test_duplicates_map(self):
        # For date1 (single group), simulate a single size group.
        date1 = "2021-02-01"
        file1 = DummyMediaFile("a.jpg")
        file2 = DummyMediaFile("b.jpg")
        self.fake_index.date_size_map = {
            date1: { 150: [file1, file2] }
        }
        # For date2 (multiple groups), we need len(size_map) > 1.
        # We'll simulate that by providing two different size groups.
        date2 = "2021-03-01"
        file3 = DummyMediaFile("c.jpg")
        file4 = DummyMediaFile("d.jpg")
        # For date2, we set two groups in date_size_map.
        self.fake_index.date_size_map[date2] = {
            200: [file3],
            210: [file4]
        }
        # The code for duplicates_map (the else branch) ignores the size_map and uses date_sig_map,
        # so for date2 we set date_sig_map to define the groups to be used.
        # Let's set date_sig_map[date2] with one group containing file4 and file5.
        file5 = DummyMediaFile("e.jpg")
        self.fake_index.date_sig_map[date2] = {
            "sigX": [file4, file5]
        }
        dup_map = MediaDuplicateManager.duplicates_map(self.dummy_set)
        # For date1, we expect a group of 2 files (from size group [file1, file2]).
        self.assertIn(2, dup_map)
        groups_for_date1 = dup_map[2]
        found_date1_group = any(set(group) == set([file1, file2]) for group in groups_for_date1)
        self.assertTrue(found_date1_group)
        # For date2, the duplicates_map returns groups derived from date_sig_map.
        # We expect a group containing file4 and file5.
        self.assertIn(2, dup_map)
        groups_for_date2 = dup_map[2]
        found_date2_group = any(set(group) == set([file4, file5]) for group in groups_for_date2)
        self.assertTrue(found_date2_group)

    def test_propagate_metadata_value(self):
        # Test propagate_metadata_value directly.
        file1 = DummyMediaFile("pic1.jpg", signature="sig-prop")
        file2 = DummyMediaFile("pic2.jpg", signature=None)
        file3 = DummyMediaFile("pic3.jpg", signature=None)
        media_list = [file1, file2, file3]
        # Before propagation, file1 has a signature; file2 and file3 do not.
        self.assertEqual(file1.metadata[SIGNATURE].value, "sig-prop")
        self.assertIsNone(file2.metadata[SIGNATURE].value)
        self.assertIsNone(file3.metadata[SIGNATURE].value)
        # Propagate using the static method (without needing index_manager)
        changed = MediaDuplicateManager.propagate_metadata_value(SIGNATURE, media_list)
        self.assertTrue(changed)
        self.assertEqual(file2.metadata[SIGNATURE].value, "sig-prop")
        self.assertEqual(file3.metadata[SIGNATURE].value, "sig-prop")

    def test_propagate_signature(self):
        # Test propagate_signature by setting up a group in date_size_map.
        date = "2021-05-01"
        file1 = DummyMediaFile("photo1.jpg", signature="original_sig")
        file2 = DummyMediaFile("photo2.jpg", signature=None)
        # Set up a group with two files for that date & size.
        self.fake_index.date_size_map = {
            date: {100: [file1, file2]}
        }
        # Clear reindex record
        self.fake_index.reindexed.clear()
        # Call propagate_signature
        MediaDuplicateManager.propagate_signature(self.dummy_set)
        # file2 should now have the signature propagated.
        self.assertEqual(file2.metadata[SIGNATURE].value, "original_sig")
        # Both files should be re-indexed via add_media_file_by_signature.
        self.assertIn(file1, self.fake_index.reindexed)
        self.assertIn(file2, self.fake_index.reindexed)

    def test_propagate_camera_model(self):
        # Test propagate_camera_model by setting up groups in both date_size_map and date_sig_map.
        date = "2021-06-01"
        file1 = DummyMediaFile("cam1.jpg", camera_model="Nikon D500")
        file2 = DummyMediaFile("cam2.jpg", camera_model=None)
        file3 = DummyMediaFile("cam3.jpg", camera_model=None)
        # Setup a group in date_size_map for file1 and file2.
        self.fake_index.date_size_map = {
            date: {250: [file1, file2]}
        }
        # Also add a group in date_sig_map for file3.
        self.fake_index.date_sig_map = {
            date: {"dummy_sig": [file3]}
        }
        # Before propagation, file2 and file3 lack camera model.
        self.assertIsNone(file2.metadata[CFM_CAMERA_MODEL].value)
        self.assertIsNone(file3.metadata[CFM_CAMERA_MODEL].value)
        # Call propagate_camera_model
        MediaDuplicateManager.propagate_camera_model(self.dummy_set)
        # Now file2 should have Nikon D500 from file1
        self.assertEqual(file2.metadata[CFM_CAMERA_MODEL].value, "Nikon D500")
        # For the signature group, nothing changes because file3 remains alone.
        self.assertIsNone(file3.metadata[CFM_CAMERA_MODEL].value)

if __name__ == '__main__':
    unittest.main()
