import dhash

from camerafile.core.Logging import Logger

LOGGER = Logger(__name__)


class Hash:
    image_hash_lib = None

    # Before, imagehash.phash was used but:
    # - imagehash depends on numpy/scipy that are big libraries (in size in the final package)
    # - As we only use this hash to compare images that have a same date, it is not necessary to have a very
    #   optimized image hash.
    # - As we do not compare each image of one mediaSet to each image of another, we can compute
    #   distances between two hashes to decide their equality (it remains sufficiently quick).
    # - After some tests, the result seems as good as before (to be verified more precisely one day)
    @staticmethod
    def image_hash(pil_image):
        return dhash.dhash_int(pil_image)
