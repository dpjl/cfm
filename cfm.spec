# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['./camerafile/cfm.py'],
             pathex=[],
             binaries=[],
             datas=[('./camerafile/conf/logging.json', 'conf'),
                    ('./camerafile/conf/cfm.json', 'conf'),
                    ('./camerafile/ext-bin/' + os.environ['EXIF_TOOL'], './camerafile/ext-bin/exiftool/')],
             hiddenimports=["camerafile.processor.BatchResetInternalMd"],
             hookspath=["./camerafile/hooks"],
             runtime_hooks=["./camerafile/py_installer_runtime_hook.py"],
             excludes=['matplotlib', 'PyQt5', 'numpy'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure,
          a.zipped_data,
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
