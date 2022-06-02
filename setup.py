import glob
import os
import shutil
import stat
import tarfile
from pathlib import Path

import PyInstaller.__main__
from pyzipper import zipfile
from setuptools import setup, Command


class CreatePackage(Command):
    description = 'Create cfm package'
    user_options = [
        ('exiftool=', 'e', 'ExifTool location'),
        ('format=', 'f', 'Package format (zip or tar.gz)')
    ]

    def initialize_options(self):
        self.exiftool = None
        self.format = None

    def finalize_options(self):
        if self.exiftool is None:
            raise Exception("Parameter --exifttool is missing")

    @staticmethod
    def on_rm_error(func, path, exc_info):
        # remove read-only if necessary
        os.chmod(path, stat.S_IWRITE)
        os.unlink(path)

    @staticmethod
    def download_model(model_directory):

        import requests
        from pathlib import Path
        links_file = open(str(Path(model_directory) / 'links.txt'), 'r')
        links = links_file.readlines()
        links_file.close()

        for link in links:
            new_file_name = str(Path(model_directory) / link.strip().split("/")[-1])
            if not os.path.exists(new_file_name):
                print("Download " + new_file_name + ", please wait...")
                downloaded_file = requests.get(link.strip())
                file_on_disk = open(new_file_name, 'wb')
                file_on_disk.write(downloaded_file.content)
                file_on_disk.close()

    def reorganize_package(self):
        shutil.move("dist/cfm", "dist/lib")
        os.makedirs("dist/cfm/bin/exiftool")
        os.makedirs("dist/cfm/data")

        exiftool_path = "dist/lib/camerafile/bin/exiftool/" + self.exiftool
        if exiftool_path.endswith(".zip"):
            with zipfile.ZipFile(exiftool_path) as file:
                file.extractall("dist/cfm/bin/exiftool")
        elif exiftool_path.endswith(".tar.gz"):
            with tarfile.open(exiftool_path, "r:gz") as file:
                file.extractall("dist/cfm/bin/exiftool")
                file.close()
        else:
            shutil.move("dist/lib/camerafile/bin/exiftool/" + self.exiftool, "dist/cfm/bin/exiftool/" + self.exiftool)
        shutil.move("dist/lib/face_recognition_models/models", "dist/cfm/data")
        shutil.move("dist/lib/conf", "dist/cfm/conf")

        shutil.rmtree("dist/lib/face_recognition_models")
        shutil.rmtree("dist/lib/camerafile")

        shutil.move("dist/lib", "dist/cfm")

        if os.path.exists("dist/cfm/lib/cfm.exe"):
            os.symlink("./lib/cfm.exe", "dist/cfm/cfm.exe")
        else:
            os.symlink("./lib/cfm", "dist/cfm/cfm")



    @staticmethod
    def zip_dir(output_filename, source_dir):
        import zipfile
        zip_file = zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                zip_file.write(os.path.join(root, file),
                               os.path.relpath(os.path.join(root, file),
                                               os.path.join(source_dir, '..')))

        zip_file.close()

    @staticmethod
    def tar_dir(output_filename, source_dir):
        import tarfile
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

    def create_archive(self):
        if self.format == "zip":
            self.zip_dir('cfm.zip', 'dist/cfm')
        elif self.format == "tar.gz":
            self.tar_dir('cfm.tar.gz', 'dist/cfm')

    def delete_existing_package(self):
        os.environ['EXIF_TOOL'] = self.exiftool
        if os.path.exists("dist"):
            shutil.rmtree("dist", onerror=self.on_rm_error)

    def run(self):
        self.download_model("camerafile/data/models")
        self.delete_existing_package()
        PyInstaller.__main__.run(["cfm.spec"])
        self.reorganize_package()
        self.create_archive()


setup(name='camerafile',
      version='0.1',
      description='Camera File Manager',
      url='https://github.com/vivi-18133/vivi-cfm',
      author='dpjl',
      author_email='dpjl@gmail.com',
      license='MIT',
      packages=['camerafile'],
      package_data={'camerafile': ["bin/exiftool-11.94.exe", 'conf/logging.json']},
      data_files=[('bin', ['bin/exiftool-11.94.exe']), ('conf', ['conf/logging.json'])],
      entry_points={'console_scripts': ['cfm=camerafile.cfm:main']},
      cmdclass={'create_package': CreatePackage},
      zip_safe=False)
