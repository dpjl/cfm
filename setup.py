import os
import shutil
import stat
import tarfile

import PyInstaller.__main__
from pyzipper import zipfile
from setuptools import setup, Command


class CreatePackage(Command):
    description = 'Create cfm package'
    user_options = [
        ('exiftool=', 'e', 'ExifTool location'),
        ('format=', 'f', 'Package format (zip or tar.gz)')
    ]

    def __init__(self, dist, **kw):
        super().__init__(dist, **kw)
        self.exiftool = None
        self.format = None

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

    def reorganize_package(self):
        shutil.move("dist/cfm", "dist/bin")
        os.makedirs("dist/cfm/ext-bin/exiftool")
        os.makedirs("dist/cfm/data")

        exiftool_path = "dist/bin/camerafile/ext-bin/exiftool/" + self.exiftool
        if exiftool_path.endswith(".zip"):
            with zipfile.ZipFile(exiftool_path) as file:
                file.extractall("dist/cfm/ext-bin/exiftool")
        elif exiftool_path.endswith(".tar.gz"):
            with tarfile.open(exiftool_path, "r:gz") as file:
                file.extractall("dist/cfm/ext-bin/exiftool")
                file.close()
        else:
            shutil.move("dist/bin/camerafile/ext-bin/exiftool/" + self.exiftool,
                        "dist/cfm/ext-bin/exiftool/" + self.exiftool)
        shutil.move("dist/bin/conf", "dist/cfm/conf")

        shutil.rmtree("dist/bin/camerafile")

        shutil.move("dist/bin", "dist/cfm")

        if os.path.exists("dist/cfm/bin/cfm.exe"):
            shutil.copy2("resources/cfm.bat", "dist/cfm/cfm.bat")
        else:
            shutil.copy2("resources/cfm", "dist/cfm/cfm")

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
            self.zip_dir('dist/cfm.zip', 'dist/cfm')
        elif self.format == "tar.gz":
            self.tar_dir('dist/cfm.tar.gz', 'dist/cfm')

    def delete_existing_package(self):
        os.environ['EXIF_TOOL'] = self.exiftool
        if os.path.exists("dist"):
            shutil.rmtree("dist", onerror=self.on_rm_error)

    def run(self):
        self.delete_existing_package()
        PyInstaller.__main__.run(["cfm.spec"])
        self.reorganize_package()
        self.create_archive()


setup(name='camerafile',
      version='0.1',
      description='Camera File Manager',
      url='https://github.com/dpjl',
      author='dpjl',
      author_email='dpjl@gmail.com',
      license='MIT',
      packages=['camerafile'],
      entry_points={'console_scripts': ['cfm=camerafile.cfm:main']},
      cmdclass={'create_package': CreatePackage},
      zip_safe=False)
