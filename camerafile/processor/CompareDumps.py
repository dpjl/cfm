from camerafile.core.MediaSetDump import MediaSetDump


class CompareDumps:

    def __init__(self, cache_dir1, cache_dir2):
        print(f"Compare dump of {cache_dir1} with dump of {cache_dir2}")
        media_set_1 = MediaSetDump(cache_dir1).load()
        media_set_2 = MediaSetDump(cache_dir2).load()

        for media_file in media_set_1:
            media_file.compare_with(media_set_2[media_file.id])
