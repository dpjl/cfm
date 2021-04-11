from signal import SIG_IGN

IMAGE_TYPE = [".jpg", ".jpeg", ".png", ".thm"]
VIDEO_TYPE = [".mp4", ".mov", ".avi"]
AUDIO_TYPE = [".wav", ".mp3"]
TYPE = IMAGE_TYPE + VIDEO_TYPE + AUDIO_TYPE
CFM_CAMERA_MODEL = "cfm-cm"
CAMERA_MODEL = "cm"
INTERNAL = "internal"
SIGNATURE = "hash"
THUMBNAIL = "thumbnail"
FACES = "faces"
DATE = "date"
WIDTH = "width"
HEIGHT = "height"
ORIENTATION = "orient"
THUMBNAIL = "thumbnail"
ORIGINAL_COPY_PATH = "ori-cp-path"
DESTINATION_COPY_PATH = "dest-cp-path"
ORIGINAL_MOVE_PATH = "ori-mv-path"
DESTINATION_MOVE_PATH = "dest-mv-path"
UNKNOWN = "Unknown"
original_sigint_handler = None
