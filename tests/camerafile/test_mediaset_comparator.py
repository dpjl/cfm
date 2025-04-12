import pytest
from typing import List, Dict
from camerafile.core.MediaSetComparator import MediaSetComparator

class DummyMediaFile:
    def __init__(self, id, path):
        self.file_desc = type('desc', (), {'id': id, 'extension': 'jpg'})()
        self._path = path
        self.metadata = {}
    def get_path(self):
        return self._path
    def __repr__(self):
        return f"DummyMediaFile(id={self.file_desc.id}, path={self._path})"
    def __eq__(self, other):
        return isinstance(other, DummyMediaFile) and self.file_desc.id == other.file_desc.id
    def __hash__(self):
        return hash(self.file_desc.id)

class DummyMediaSet:
    def __init__(self, date_size_map, date_sig_map=None):
        self.indexer = type('indexer', (), {})()
        self.indexer.date_size_map = date_size_map
        self.indexer.date_sig_map = date_sig_map or {}
        self._contains_set = set()
        for size_map in date_size_map.values():
            for files in size_map.values():
                for f in files:
                    self._contains_set.add(f)
        for sig_map in (date_sig_map or {}).values():
            for files in sig_map.values():
                for f in files:
                    self._contains_set.add(f)
    def contains(self, item):
        return item in self._contains_set

def build_map(files_by_date_and_size: Dict[str, Dict[int, List[DummyMediaFile]]]):
    return files_by_date_and_size.copy()

def build_sig_map(files_by_date_and_sig: Dict[str, Dict[str, List[DummyMediaFile]]]):
    return files_by_date_and_sig.copy()

def test_no_duplicates_no_common():
    f1 = DummyMediaFile('A', '/a')
    f2 = DummyMediaFile('B', '/b')
    set1 = DummyMediaSet({'2023-01-01T12:00:00': {100: [f1]}})
    set2 = DummyMediaSet({'2023-01-02T13:45:23': {200: [f2]}})
    assert MediaSetComparator.get_possibly_already_exists(set1, set2) == []
    in_both, only_in_self = MediaSetComparator.cmp(set1, set2)
    assert in_both == []
    assert only_in_self == [[f1]]

def test_duplicates_in_both_sets():
    f1 = DummyMediaFile('A', '/a')
    f2 = DummyMediaFile('B', '/b')
    f3 = DummyMediaFile('C', '/c')
    f4 = DummyMediaFile('D', '/d')
    set1 = DummyMediaSet({'2023-01-01T10:10:10': {100: [f1], 200: [f2]}})
    set2 = DummyMediaSet({'2023-01-01T10:10:10': {300: [f3], 400: [f4]}})
    result = MediaSetComparator.get_possibly_already_exists(set1, set2)
    assert set(result) == {f1, f2, f3, f4}

def test_unique_file_in_both():
    f1 = DummyMediaFile('A', '/a')
    set1 = DummyMediaSet({'2023-01-01T08:30:00': {100: [f1]}})
    set2 = DummyMediaSet({'2023-01-01T08:30:00': {100: [f1]}})
    in_both, only_in_self = MediaSetComparator.cmp(set1, set2)
    assert in_both == [[f1]]
    assert only_in_self == []

def test_unique_file_only_in_self():
    f1 = DummyMediaFile('A', '/a')
    set1 = DummyMediaSet({'2023-01-01T09:00:01': {100: [f1]}})
    set2 = DummyMediaSet({'2023-01-01T09:00:01': {}})
    in_both, only_in_self = MediaSetComparator.cmp(set1, set2)
    assert in_both == []
    assert only_in_self == [[f1]]

def test_mixed_unique_and_duplicates():
    f1 = DummyMediaFile('A', '/a')
    f2 = DummyMediaFile('B', '/b')
    f3 = DummyMediaFile('C', '/c')
    set1 = DummyMediaSet({'2023-01-01T15:45:59': {100: [f1], 200: [f2]}})
    set2 = DummyMediaSet({'2023-01-01T15:45:59': {100: [f3]}})
    result = MediaSetComparator.get_possibly_already_exists(set1, set2)
    assert set(result) == {f1, f2, f3}

def test_sig_map_multiple():
    f1 = DummyMediaFile('A', '/a')
    f2 = DummyMediaFile('B', '/b')
    f3 = DummyMediaFile('C', '/c')
    sig_map = {'sig1': [f1], 'sig2': [f2], 'sig3': [f3]}
    set1 = DummyMediaSet({'2023-01-01T18:00:00': {100: [f1], 200: [f2], 300: [f3]}}, {'2023-01-01T18:00:00': sig_map})
    set2 = DummyMediaSet({'2023-01-01T18:00:00': {}})
    in_both, only_in_self = MediaSetComparator.cmp(set1, set2)
    assert in_both == []
    assert only_in_self == [[f1], [f2], [f3]]
