import hashlib
import logging

import dhash

from camerafile.tools.CFMImage import CFMImage

LOGGER = logging.getLogger(__name__)


class Hash:
    image_hash_lib = None

    # Before, imagehash.phash was used but:
    # - imagehash depends on numpy/scipy that are big libraries (in size in the final package)
    # - As we only use this hash to compare images that have a same date, it is not necessary to have a very
    #   optimized image hash.
    # - As we do not compare each image of one mediaSet to each image of another, we can compute
    #   distances between two hashes to decide their equality (it remains sufficiently quick).
    # - After some tests, the result seems as good as before (to be verified more precisely)
    @staticmethod
    def image_hash(cfm_image: CFMImage):
        try:
            return dhash.dhash_int(cfm_image.image_data)
        except BaseException as e:
            LOGGER.debug("image_hash: %s / %s", str(e), cfm_image.filename)
            md5_hash = hashlib.md5(cfm_image.get_bytes()).hexdigest()
            return int(md5_hash, 16)
