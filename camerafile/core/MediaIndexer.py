import dhash

class MediaIndexer:
    """
    MediaIndexer centralizes the management of index mappings by date/size and date/signature.
    """
    def __init__(self):
        # Mapping {date: {size: [media_file, ...]}}
        self.date_size_map = {}  
        # Mapping {date: {signature: [media_file, ...]}}
        self.date_sig_map = {}   
        # Mapping {system_id: [media_file, ...]}
        self.system_id_map = {}

    # -------------------------
    # Private helper static methods
    # -------------------------

    @staticmethod
    def _add_to_x_y_map(map_to_update: dict, x, y, media_file) -> None:
        sub_map = map_to_update.setdefault(x, {})
        sub_list = sub_map.setdefault(y, [])
        if media_file not in sub_list:
            sub_list.append(media_file)

    @staticmethod
    def _exist_in_x_y_map(map_to_inspect: dict, x, y) -> bool:
        if x is None or y is None:
            return False
        return y in map_to_inspect.get(x, {})

    @staticmethod
    def _remove_from_x_y_map(map_to_update: dict, x, y, media_file) -> None:
        sub_map = map_to_update.get(x)
        if sub_map is None:
            return
        sub_list = sub_map.get(y)
        if sub_list is None:
            return
        if media_file in sub_list:
            sub_list.remove(media_file)
        if not sub_list:
            del sub_map[y]
        if not sub_map:
            del map_to_update[x]

    def _add_media_file_by_size(self, media_file) -> None:
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date and size:
            MediaIndexer._add_to_x_y_map(self.date_size_map, date, size, media_file)

    def _remove_media_file_by_size(self, media_file) -> None:
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date and size:
            MediaIndexer._remove_from_x_y_map(self.date_size_map, date, size, media_file)

    def _add_media_file_by_signature(self, media_file) -> None:
        date = media_file.get_exif_date()
        sig = media_file.get_signature()
        if date and sig:
            sig_map = self.date_sig_map.setdefault(date, {})
            for existing_sig, media_list in sig_map.items():
                # If the signatures are nearly identical (less than 4 bits difference)
                if dhash.get_num_bits_different(sig, existing_sig) < 4:
                    if media_file not in media_list:
                        media_list.append(media_file)
                    return
            # No similar signature found, add a new entry
            sig_map[sig] = [media_file]

    def _remove_media_file_by_signature(self, media_file) -> None:
        date = media_file.get_exif_date()
        sig = media_file.get_signature()
        if date and sig:
            dmap = self.date_sig_map.get(date, {})
            # Iterate over a copy of items to allow safe removal
            for existing_sig, media_list in list(dmap.items()):
                if media_file in media_list:
                    MediaIndexer._remove_from_x_y_map(self.date_sig_map, date, existing_sig, media_file)
                    return

    def _add_media_file_by_system_id(self, media_file) -> None:
        system_id = media_file.file_desc.system_id
        if system_id is not None:
            media_list = self.system_id_map.setdefault(system_id, [])
            if media_file not in media_list:
                media_list.append(media_file)

    def _remove_media_file_by_system_id(self, media_file) -> None:
        system_id = media_file.file_desc.system_id
        if system_id is not None and system_id in self.system_id_map:
            media_list = self.system_id_map[system_id]
            if media_file in media_list:
                media_list.remove(media_file)
            if not media_list:
                del self.system_id_map[system_id]

    # -------------------------
    # Public methods
    # -------------------------

    def add_media_file(self, media_file) -> None:
        """
        Indexes a media file by date and size, by date and signature, and by system_id.
        """
        self._add_media_file_by_size(media_file)
        self._add_media_file_by_signature(media_file)
        self._add_media_file_by_system_id(media_file)

    def remove_media_file(self, media_file) -> None:
        """
        Removes a media file from all index mappings.
        """
        self._remove_media_file_by_size(media_file)
        self._remove_media_file_by_signature(media_file)
        self._remove_media_file_by_system_id(media_file)

    def exists(self, media_file) -> bool:
        """
        Checks if a media file is already indexed (by system_id, date/size or by a similar signature).
        """
        # First check by system_id
        system_id = media_file.file_desc.system_id
        if system_id is not None and system_id in self.system_id_map:
            return True

        # Then check by date/size
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date and MediaIndexer._exist_in_x_y_map(self.date_size_map, date, size):
            return True

        # Question:
        # If the date is exactly the same down to the millisecond, and the height and width are identical
        # (even if the file sizes are different?), might we consider these as the same images?
        # This would avoid having to compute the signature.
        # Case of iPhone photos exported by two different tools.
        sig = media_file.get_signature()
        if sig and date and date in self.date_sig_map:
            for existing_sig in self.date_sig_map[date]:
                if dhash.get_num_bits_different(existing_sig, sig) < 4:
                    return True
        return False

    def get_similar_medias(self, media_file) -> list:
        """
        Retourne tous les MediaFile similaires à media_file (même signature ou doublon, ou même system_id).
        """
        result = set()
        # Par system_id
        system_id = media_file.file_desc.system_id
        if system_id is not None and system_id in self.system_id_map:
            result.update(self.system_id_map[system_id])
        # Par date/size
        date = media_file.get_exif_date()
        size = media_file.get_file_size()
        if date and size and date in self.date_size_map:
            for m in self.date_size_map[date].get(size, []):
                result.add(m)
        # Par signature
        sig = media_file.get_signature()
        if sig and date and date in self.date_sig_map:
            for existing_sig, media_list in self.date_sig_map[date].items():
                if dhash.get_num_bits_different(existing_sig, sig) < 4:
                    result.update(media_list)
        # Retirer le media_file lui-même si présent
        result.discard(media_file)
        return list(result)


