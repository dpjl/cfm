# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

face_models = [
  ('./camerafile/data/models/dlib_face_recognition_resnet_model_v1.dat', './face_recognition_models/models'),
  ('./camerafile/data/models/mmod_human_face_detector.dat', './face_recognition_models/models'),
  ('./camerafile/data/models/shape_predictor_5_face_landmarks.dat', './face_recognition_models/models'),
  ('./camerafile/data/models/shape_predictor_68_face_landmarks.dat', './face_recognition_models/models')
]

a = Analysis(['./camerafile/cfm.py'],
             pathex=[],
             binaries=face_models,
             datas=[('./camerafile/conf/logging.json', 'conf'), ('./camerafile/conf/cfm.json', 'conf'), ('./camerafile/bin/exiftool/' + os.environ['EXIF_TOOL'], './camerafile/bin/exiftool/' + os.environ['EXIF_TOOL'])],
             hiddenimports=[],
             hookspath=["./camerafile/hooks"],
             runtime_hooks=["./camerafile/py_installer_runtime_hook.py"],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz, 
          a.scripts, 
          exclude_binaries=True, 
          console=True, 
          debug=False, 
          name='cfm', 
          strip=False, 
          upx=True)

collect = COLLECT(exe,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='cfm',
          strip=False,
          upx=True)
