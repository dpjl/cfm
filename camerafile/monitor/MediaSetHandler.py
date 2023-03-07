from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent


class MediaSetHandler(FileSystemEventHandler):

    def __init__(self, media_set, watcher: "Watcher"):
        self.media_set = media_set
        self.watcher = watcher

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self.watcher.wake_up(self.media_set, Path(event.src_path).parent)
        else:
            self.watcher.wake_up(self.media_set, Path(event.src_path))
