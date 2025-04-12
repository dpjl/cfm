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
