from datetime import datetime
from pathlib import Path
from cv2 import cv2


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
            self.movie_data = cv2.imread(str(self.path))
            (self.width, self.height, _) = self.movie_data.shape
        except OSError:
            # TODO: add log
            pass
