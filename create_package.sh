mkdir dist/lib
mv dist/cfm/* dist/lib

mv dist/lib/cfm.exe dist/cfm

mkdir dist/cfm/bin
mv dist/lib/camerafile/bin/* dist/cfm/bin
rm -rf dist/lib/camerafile
mv dist/lib/imageio_ffmpeg/binaries/ffmpeg* dist/cfm/bin
rm -rf mv dist/lib/imageio_ffmpeg/binaries

mkdir dist/cfm/data
mv dist/lib/face_recognition_models/models dist/cfm/data
rm -rf dist/lib/face_recognition_models/models


mv dist/lib/conf dist/cfm/conf

mv dist/lib dist/cfm