import glob

import sys, os

# ys.path.append(os.path.join(os.path.dirname(sys.argv[0]), "lib"))
# sys.path.append(os.path.dirname(sys.argv[0]))
# print(sys.path)

# Search in binaries/ffmpeg to set automatically IMAGEIO_FFMPEG_EXE
from camerafile.Resource import Resource

for file in glob.glob(str(Resource.get_main_path() / "bin/*ffmpeg*")):
    os.environ['IMAGEIO_FFMPEG_EXE'] = file
    break
