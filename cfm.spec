# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['./camerafile/cfm.py'],
             pathex=[],
             binaries=[],
             datas=[('./camerafile/data/models/links.txt', 'data/models'), ('./camerafile/conf/logging.json', 'conf'), ('./camerafile/conf/cfm.json', 'conf'), ('./camerafile/bin/' + os.environ['EXIF_TOOL'], './camerafile/bin/exiftool/')],
             hiddenimports=["camerafile.processor.BatchResetInternalMd"],
             hookspath=["./camerafile/hooks"],
             runtime_hooks=["./camerafile/py_installer_runtime_hook.py"],
             excludes=['matplotlib', 'PyQt5'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

#ignore=["mkl", "libopenblas"]

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

#def remove_from_list(input, keys):
#    outlist = []
#    for item in input:
#        name, _, _ = item
#        flag = 0
#        for key_word in keys:
#            if name.find(key_word) > -1:
#                flag = 1
#        if flag != 1:
#            outlist.append(item)
#    return outlist

#a.binaries = remove_from_list(a.binaries, ignore)

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
