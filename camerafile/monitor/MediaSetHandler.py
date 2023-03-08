from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler, FileSystemEvent

if TYPE_CHECKING:
    from camerafile.monitor.Watcher import Watcher


class MediaSetHandler(FileSystemEventHandler):

    def __init__(self, media_set, watcher: "Watcher"):
        self.media_set = media_set
        self.watcher = watcher

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self.watcher.wake_up(self.media_set, Path(event.src_path).parent.as_posix())
        else:
            self.watcher.wake_up(self.media_set, Path(event.src_path).as_posix())
