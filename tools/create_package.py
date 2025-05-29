#!/usr/bin/env python3
import os
import shutil
import stat
import tarfile
import argparse
import sys

import PyInstaller.__main__
from pyzipper import zipfile


def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)

def reorganize_package(exiftool, format):
    shutil.move("dist/cfm", "dist/bin")
    os.makedirs("dist/cfm/ext-bin/exiftool")
    os.makedirs("dist/cfm/data")

    exiftool_path = "dist/bin/camerafile/ext-bin/exiftool/" + exiftool
    if exiftool_path.endswith(".zip"):
        with zipfile.ZipFile(exiftool_path) as file:
            file.extractall("dist/cfm/ext-bin/exiftool")
    elif exiftool_path.endswith(".tar.gz"):
        with tarfile.open(exiftool_path, "r:gz") as file:
            file.extractall("dist/cfm/ext-bin/exiftool")
    else:
        shutil.move("dist/bin/camerafile/ext-bin/exiftool/" + exiftool,
                    "dist/cfm/ext-bin/exiftool/" + exiftool)
    shutil.move("dist/bin/conf", "dist/cfm/conf")

    shutil.rmtree("dist/bin/camerafile")
    shutil.move("dist/bin", "dist/cfm")

    if os.path.exists("dist/cfm/bin/cfm.exe"):
        shutil.copy2("resources/cfm.bat", "dist/cfm/cfm.bat")
    else:
        shutil.copy2("resources/cfm", "dist/cfm/cfm")

def zip_dir(output_filename, source_dir):
    import zipfile
    zip_file = zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            zip_file.write(os.path.join(root, file),
                           os.path.relpath(os.path.join(root, file),
                                           os.path.join(source_dir, '..')))
    zip_file.close()

def tar_dir(output_filename, source_dir):
    import tarfile
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def create_archive(format):
    if format == "zip":
        zip_dir('dist/cfm.zip', 'dist/cfm')
    elif format == "tar.gz":
        tar_dir('dist/cfm.tar.gz', 'dist/cfm')

def delete_existing_package(exiftool):
    os.environ['EXIF_TOOL'] = exiftool
    if os.path.exists("dist"):
        shutil.rmtree("dist", onerror=on_rm_error)

def main():
    parser = argparse.ArgumentParser(description='Create cfm package')
    parser.add_argument('--exiftool', '-e', required=True, help='ExifTool location')
    parser.add_argument('--format', '-f', choices=['zip', 'tar.gz'], default='zip', help='Package format (zip or tar.gz)')
    args = parser.parse_args()

    try:
        delete_existing_package(args.exiftool)
        PyInstaller.__main__.run(["cfm.spec"])
        reorganize_package(args.exiftool, args.format)
        create_archive(args.format)
        print("Package created successfully.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 