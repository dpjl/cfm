from typing import List, Dict

from camerafile.core.Constants import CFM_CAMERA_MODEL, SIGNATURE
from camerafile.core.MediaFile import MediaFile


class MediaDuplicateManager:
    """
    This class centralizes the management of duplicates in a media set.
    It relies on a MediaIndexer instance to access the indexes by date/size and date/signature.
    The duplicates detection follow those principles:
        1) if two medias have different dates, we always consider they are different files
        2) if two medias have the same date, and the same size, we directly consider them as duplicates
        3) if two medias have the same date, but different sizes: then we compute signatures, to try to determine if they are duplicates 
    As a consequence:
        - we do not detect duplicates of a file with date metadata (exif and system) removed/modified since its creation.
        - we could detect as duplicates files that have exactly the same number of bytes, and the same dates.    
    """

    @staticmethod
    def get_possibly_duplicates(media_set) -> List[MediaFile]:
        """
        Traverses the size index (date_size_map) and returns, for each date with multiple file sizes, 
        the first file of each size group as a candidate for duplication. Only the first is required,
        as data will be propagated later to other medias with exactly same date and size.
        """
        indexer = media_set.indexer
        result: List[MediaFile] = []
        for date, size_map in indexer.date_size_map.items():
            if len(size_map) > 1:
                for file_size, media_files in size_map.items():
                    if media_files:
                        result.append(media_files[0])
        return result

    @staticmethod
    def duplicates_map(media_set) -> Dict[int, List[List[MediaFile]]]:
        """
        Constructs a duplicates map, by number of duplicates.
        For each date, if there is a single group (in date_size_map), that group is processed,
        otherwise, the groups based on signature (date_sig_map) are iterated.
        """
        indexer = media_set.indexer
        duplicates_map: Dict[int, List[List[MediaFile]]] = {}
        for date, size_map in indexer.date_size_map.items():
            if len(size_map) == 1:
                # Only one group for this date (if multiple medias, they all have the same size)
                _, media_list = next(iter(size_map.items()))
                MediaDuplicateManager._update_duplicates_map(duplicates_map, media_list)
            else:
                # Multiple groups of different sizes => use groups based on signature.
                # We should always have at least one signature group in this case.
                sig_map = indexer.date_sig_map.get(date, {})
                if len(sig_map) == 0:
                    raise ValueError(f"date_sig map should contain an entry for date {date}.")
                for media_list in sig_map.values():
                    MediaDuplicateManager._update_duplicates_map(duplicates_map, media_list)
        return duplicates_map
    
    @staticmethod
    def _update_duplicates_map(duplicates_map: Dict[int, List[List[MediaFile]]], media_list: List[MediaFile]):
        nb_copy = len(media_list)
        if nb_copy not in duplicates_map:
            duplicates_map[nb_copy] = []
        duplicates_map[nb_copy] += [media_list]

    @staticmethod
    def duplicates_info(media_set) -> Dict[MediaFile, tuple]:
        """
        The associated structure maps each MediaFile to a tuple (total_copies, group_id, duplicate_id).
        """
        indexer = media_set.indexer
        duplicates_infos_by_media: Dict[MediaFile, tuple] = {}
        for date, size_map in indexer.date_size_map.items():
            if len(size_map) == 1:
                _, media_list = next(iter(size_map.items()))
                MediaDuplicateManager._update_duplicates_info(duplicates_infos_by_media, media_list)
            else:
                sig_map = indexer.date_sig_map.get(date, {})
                for media_list in sig_map.values():
                    MediaDuplicateManager._update_duplicates_info(duplicates_infos_by_media, media_list)
        return duplicates_infos_by_media
    
    @staticmethod
    def get_duplicates_report(media_set, duplicates):
        str_list = ["All media files: " + str(len(media_set.media_file_list)),
                    "Distinct elements: {distinct}".format(distinct=str(sum(map(len, duplicates.values()))))]
        for n_copy, media_list_list in sorted(duplicates.items()):
            str_list.append("%s elem. found %s times" % (len(media_list_list), n_copy))
        return str_list
    
    @staticmethod
    def _update_duplicates_info(duplicates_infos_by_media: Dict[MediaFile, tuple], media_list: List[MediaFile]) -> None:
        """
        Sorts the media list by filename, then for each file creates a tuple describing:
           - the total number of copies,
           - a group identifier based on the first file's name,
           - an incremental duplicate identifier.
        The result is stored in duplicates_infos_by_media.
        """
        if not media_list:
            return

        nb_copy = len(media_list)
        # Sort by file name to have a stable group_id across multiple executions
        media_list.sort(key=lambda x: x.file_desc.name)
        group_id = media_list[0].file_desc.name
        dup_id = 1
        for media_file in media_list:
            duplicates_infos_by_media[media_file] = (nb_copy, group_id, dup_id)
            dup_id += 1

    @staticmethod
    def propagate_metadata_value(metadata_name: str, media_file_list: List[MediaFile]) -> bool:
        """
        Propagates a metadata value: if within a group of media there exists a non-null
        value, it is applied to the other media files that lack it.
        Returns True if a value was found and propagated.
        """
        not_empty_metadata_value = None
        if len(media_file_list) > 1:
            for media_file in media_file_list:
                current_metadata_value = media_file.metadata[metadata_name].value
                if current_metadata_value is not None:
                    not_empty_metadata_value = current_metadata_value
            if not_empty_metadata_value is not None:
                for media_file in media_file_list:
                    if media_file.metadata[metadata_name].value is None:
                        media_file.metadata[metadata_name].value = not_empty_metadata_value
        return not_empty_metadata_value is not None

    @staticmethod
    def propagate_signature(media_set) -> None:
        """
        Traverses the size index and for each group with multiple files,
        attempts to propagate the signature. If a value is propagated, the file is re-indexed
        by adding the signature using the index_manager.
        """
        indexer = media_set.indexer
        for date, size_map in indexer.date_size_map.items():
            for file_size, media_files in size_map.items():
                if len(media_files) > 1:
                    if MediaDuplicateManager.propagate_metadata_value(SIGNATURE, media_files):
                        for media_file in media_files:
                            indexer.add_media_file(media_file)

    @staticmethod
    def propagate_camera_model(media_set) -> None:
        """
        Propagates the camera model in all duplicate groups.
        Traverses the size and signature indexes and tries to propagate the value
        of CFM_CAMERA_MODEL in each group.
        """
        indexer = media_set.indexer
        for date, size_map in indexer.date_size_map.items():
            for file_size, media_files in size_map.items():
                MediaDuplicateManager.propagate_metadata_value(CFM_CAMERA_MODEL, media_files)
        for date, sig_map in indexer.date_sig_map.items():
            for sig, media_files in sig_map.items():
                MediaDuplicateManager.propagate_metadata_value(CFM_CAMERA_MODEL, media_files)
