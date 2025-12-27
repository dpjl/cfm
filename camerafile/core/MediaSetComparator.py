from typing import List, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet

class MediaSetComparator:
    @staticmethod
    def get_possibly_already_exists(media_set1: 'MediaSet', media_set2: 'MediaSet') -> List[Any]:
        result = []
        for date, size_map1 in media_set1.indexer.date_size_map.items():
            size_map2 = media_set2.indexer.date_size_map.get(date)
            if size_map2:
                if len(size_map1) > 1 or len(size_map2) > 1:
                    for file_size in size_map1:
                        result.append(size_map1[file_size][0])
                    for file_size in size_map2:
                        result.append(size_map2[file_size][0])
        return result

    @staticmethod
    def cmp(media_set1: 'MediaSet', media_set2: 'MediaSet') -> Tuple[List[Any], List[Any]]:
        in_both, only_in_self = [], []
        for date, size_map in media_set1.indexer.date_size_map.items():
            if len(size_map) == 1:
                _, unique_media_list = next(iter(size_map.items()))
                if media_set2.contains(unique_media_list[0]):
                    in_both.append(unique_media_list)
                else:
                    only_in_self.append(unique_media_list)
            else:
                for media_list in media_set1.indexer.date_sig_map.get(date, {}).values():
                    if media_set2.contains(media_list[0]):
                        in_both.append(media_list)
                    else:
                        only_in_self.append(media_list)
        return in_both, only_in_self

    @staticmethod
    def exact_cmp(media_set1: 'MediaSet', media_set2: 'MediaSet') -> Tuple[List[Any], List[Any]]:
        """
        Strictly compare two media sets based on system_id.
        
        Args:
            media_set1: First media set to compare
            media_set2: Second media set to compare
            
        Returns:
            Tuple containing:
            - List of media files present in both sets
            - List of media files only in media_set1
        """
        in_both = [
            media_file for media_file in media_set1.media_file_list 
            if media_file.file_desc.system_id in media_set2.indexer.system_id_map
        ]
        
        only_in_self = [
            media_file for media_file in media_set1.media_file_list
            if media_file.file_desc.system_id not in media_set2.indexer.system_id_map
        ]
        
        return in_both, only_in_self

    @staticmethod
    def build_sync_id_map(media_set1: 'MediaSet', media_set2: 'MediaSet') -> dict:
        """
        Returns a dict {sync_id: media_file} for the union of both media_sets.
        sync_id = [v]id[.replica] where:
          - v = video prefix if video
          - id = unique integer for each group (0, 1, 2, ...)
          - .replica = suffix for each duplicate (if several in the same gallery)
        All identical media between media_set1 and media_set2 share the same base id, but each media_file gets a unique sync_id.
        """
        from camerafile.core.MediaFile import MediaFile
        all_media = list(media_set1.media_file_list) + list(media_set2.media_file_list)
        treated = set()
        sync_id_map = {}
        group_counter = 0
        for media in all_media:
            if media in treated:
                continue
            group = set([media])
            group.update(media.parent_set.indexer.get_similar_medias(media))
            other_set = media_set2 if media.parent_set is media_set1 else media_set1
            group.update(other_set.indexer.get_similar_medias(media))
            for m in group:
                treated.add(m)
            group = list(group)
            group.sort(key=lambda m: (m.parent_set is media_set1, m.file_desc.id))
            base_media = group[0]
            is_video = base_media.file_desc.is_video()
            base_id = group_counter
            prefix = 'v' if is_video else ''
            for idx, m in enumerate(group):
                replica_suffix = f'.{idx+1}' if len(group) > 1 else ''
                sync_id = f'{prefix}{base_id}{replica_suffix}'
                sync_id_map[sync_id] = m
            group_counter += 1
        return sync_id_map

    @staticmethod
    def build_sync_id_maps(media_set1: 'MediaSet', media_set2: 'MediaSet') -> tuple[dict, dict]:
        """
        Returns two dicts: (map_source, map_destination) where each is {sync_id: media_file}.
        - Identical or similar media in both sets get the same sync_id (incremental group id, .replica suffix if needed).
        - Uses get_similar_medias to group all similar/identical media across both sets.
        - Guarantees perfect alignment of sync_id between both sets.
        - all_media is sorted in reverse chronological order.
        """
        from camerafile.core.MediaFile import MediaFile
        map_source = {}
        map_dest = {}
        system_id_to_sync_id = {}
        group_counter = 0
        treated = set()
        # Tri chronologique normal (plus ancien d'abord) pour que les nouvelles photos aient de nouveaux IDs
        # et que les anciennes photos gardent leurs IDs (utile pour l'affichage dans la galerie)
        all_media = sorted(
            list(media_set1.media_file_list) + list(media_set2.media_file_list),
            key=lambda m: (m.get_date() or 0),
            reverse=False
        )
        for media in all_media:
            if media in treated:
                continue
            # Regrouper tous les similaires dans les deux media_sets
            group = set([media])
            group.update(media.parent_set.indexer.get_similar_medias(media))
            other_set = media_set2 if media.parent_set is media_set1 else media_set1
            group.update(other_set.indexer.get_similar_medias(media))
            for m in group:
                treated.add(m)
            is_video = media.file_desc.is_video()
            prefix = 'v' if is_video else ''
            for idx, m in enumerate(sorted(group, key=lambda x: x.file_desc.id)):
                sid = getattr(m.file_desc, 'system_id', None)
                # Si déjà vu, réutiliser le sync_id
                if sid and sid in system_id_to_sync_id:
                    sync_id = system_id_to_sync_id[sid]
                else:
                    replica_suffix = f'.{idx+1}' if len(group) > 1 else ''
                    sync_id = f'{prefix}{group_counter}{replica_suffix}'
                    if sid:
                        system_id_to_sync_id[sid] = sync_id
                if m.parent_set is media_set1:
                    map_source[sync_id] = m
                elif m.parent_set is media_set2:
                    map_dest[sync_id] = m
            group_counter += 1
        return map_source, map_dest

    @staticmethod
    def similar_excluding_exact(media_set1: 'MediaSet', media_set2: 'MediaSet') -> List[Any]:
        """
        Returns media files that are similar between two media_sets, excluding those that are exactly identical (same system_id).
        """
        similar, _ = MediaSetComparator.cmp(media_set1, media_set2)
        exact, _ = MediaSetComparator.exact_cmp(media_set1, media_set2)
        exact_ids = {m.file_desc.system_id for m in exact}
        # 'similar' is a list of lists (groups of similar media files)
        result = [media for group in similar for media in group if media.file_desc.system_id not in exact_ids]
        return result
