IMAGE_TYPE = [".jpg", ".jpeg", ".png", ".thm", ".heic", ".heif"]
VIDEO_TYPE = [".mp4", ".mov", ".avi"]
QT_TYPE = [".mp4", ".mov"]
AVI_TYPE = [".avi"]
AUDIO_TYPE = [".wav", ".mp3"]
MANAGED_TYPE = IMAGE_TYPE + VIDEO_TYPE + AUDIO_TYPE
ARCHIVE_TYPE = [".zip"]
CFM_CAMERA_MODEL = "cfm-cm"
INTERNAL = "internal"
SIGNATURE = "hash"
THUMBNAIL = "thumbnail"
FACES = "faces"
SIZE = "size"
ORIGINAL_PATH = "ori-path"
ORIGINAL_COPY_PATH = "ori-cp-path"
DESTINATION_COPY_PATH = "dest-cp-path"
ORIGINAL_MOVE_PATH = "ori-mv-path"
DESTINATION_MOVE_PATH = "dest-mv-path"
UNKNOWN = "Unknown"

# consider that files are identical if creation date, dimensions and file size are identical
COMP_STRICT = "strict"
# same as strict but ignore metadata (only image data are compared)
COMP_STRICT_LIGHT = "strict-image"
# consider that files are identical if creation date, and image hash are identical (robust to resize)
COMP_SIMILAR = "similar"

# First compare similar. Then for images with no exif creation date (only them), compare diff with all other signatures
# (required to compate signature of all the images)
COMP_SIMILAR_AND_ANALYSE_UNEXIFED = "..."

original_sigint_handler = None
