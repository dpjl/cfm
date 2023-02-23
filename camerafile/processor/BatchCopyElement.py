from datetime import datetime

from camerafile.core.MediaFile import MediaFile


class BatchCopyElement:
    def __init__(self, media_file, modification_date):
        self.media: MediaFile = media_file
        self.modification_date: datetime = modification_date
        self.destination: str = ""
        self.collision_policy = None

    def set_destination(self, destination):
        self.destination = destination
