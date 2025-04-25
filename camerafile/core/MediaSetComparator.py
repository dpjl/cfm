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
        # Tri chronologique inverse (plus récent d'abord)
        all_media = sorted(
            list(media_set1.media_file_list) + list(media_set2.media_file_list),
            key=lambda m: (m.get_date() or 0),
            reverse=True
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
