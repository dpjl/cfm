# -*- coding: utf-8 -*-
"""
MediaIndexManager encapsulates the management of index mappings by date/size and date/signature.
"""
from typing import Any
import dhash

class MediaIndexManager:
    def __init__(self):
        # Mappings for indexing files based on their date and size,
        # and their date and signature.
        self.date_size_map = {}  # type: dict[Any, dict[Any, list]]
        self.date_sig_map = {}   # type: dict[Any, dict[Any, list]]

    @staticmethod
    def add_to_x_y_map(map_to_update: dict, x, y, media_file) -> None:
        if x not in map_to_update:
            map_to_update[x] = {}
        if y not in map_to_update[x]:
            map_to_update[x][y] = []
        if media_file not in map_to_update[x][y]:
            map_to_update[x][y].append(media_file)


    @staticmethod
    def exist_in_x_y_map(map_to_inspect, x, y):
        if x is not None and x in map_to_inspect:
            if y is not None and y in map_to_inspect[x]:
                return True
        return False

    @staticmethod
    def remove_from_x_y_map(map_to_update: dict, x, y, media_file) -> None:
        if x in map_to_update and y in map_to_update[x]:
            map_to_update[x][y].remove(media_file)
            if not map_to_update[x][y]:
                del map_to_update[x][y]
            if not map_to_update[x]:
                del map_to_update[x]

    def add_media_file_by_size(self, media_file) -> None:
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date is not None:
            MediaIndexManager.add_to_x_y_map(self.date_size_map, date, size, media_file)

    def remove_media_file_by_size(self, media_file) -> None:
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date is not None:
            MediaIndexManager.remove_from_x_y_map(self.date_size_map, date, size, media_file)

    def add_media_file_by_signature(self, media_file) -> None:
        date = media_file.get_exif_date()
        sig = media_file.get_signature()
        if date is not None and sig is not None:
            date_map = self.date_sig_map.setdefault(date, {})
            for existing_sig, media_list in date_map.items():
                if dhash.get_num_bits_different(sig, existing_sig) < 4:
                    if media_file not in media_list:
                        media_list.append(media_file)
                    return
            date_map[sig] = [media_file]

    def remove_media_file_by_signature(self, media_file) -> None:
        date = media_file.get_exif_date()
        sig = media_file.get_signature()
        if date is not None and sig is not None:
            dmap = self.date_sig_map.get(date, {})
            for existing_sig, media_list in list(dmap.items()):
                if media_file in media_list:
                    MediaIndexManager.remove_from_x_y_map(dmap, date, existing_sig, media_file)
                    return