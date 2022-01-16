from datetime import datetime
from pathlib import Path
from moviepy.video.io.VideoFileClip import VideoFileClip


class Movie:

    def __init__(self, path):
        self.path = Path(path)
        self.movie_data = None
        self.date = None
        self.width = None
        self.height = None
        self.read_movie()

    def read_movie(self):
        
        # TODO: Check performances of different methods to get modification date
        # self.date = time.ctime(os.path.getmtime(self.path))
        self.date = datetime.fromtimestamp(self.path.stat().st_mtime)
        try:
            self.movie_data = VideoFileClip(str(self.path))
            self.width, self.height = self.movie_data.size
        except OSError:
            # TODO: add log
            pass
