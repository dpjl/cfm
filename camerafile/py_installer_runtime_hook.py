import glob
import os
import signal
from camerafile.core.Resource import Resource

signal.signal(signal.SIGINT, signal.SIG_DFL)

for file in glob.glob(str(Resource.get_main_path() / "bin/*ffmpeg*")):
    os.environ['IMAGEIO_FFMPEG_EXE'] = file
    break
