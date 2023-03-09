import json
import sys
import os
from pathlib import Path


class Resource:
    exiftool_executable = None
    program_path = None
    cfm_configuration = None
    original_sigint_handler = None
    dlib_predictor_dir = None
    dlib_predictor = None

    @staticmethod
    def get_main_path():
        try:
            return Path(sys._MEIPASS) / ".."
        except AttributeError:
            return Path(os.path.dirname(__file__)) / ".."

    @staticmethod
    def init():
        Resource.program_path = Resource.get_main_path()
        cfm_configuration_file = Resource.program_path / "conf" / "cfm.json"
        with open(cfm_configuration_file, 'r') as f:
            Resource.cfm_configuration = json.load(f)

        Resource.exiftool_executable = Resource.program_path / Path(Resource.cfm_configuration["exiftool-" + os.name])
        Resource.dlib_predictor_dir = (
                Resource.program_path / Path(Resource.cfm_configuration["dlib-predictor-dir"])).resolve()
        Resource.dlib_predictor = str(
            (Resource.dlib_predictor_dir / Path(Resource.cfm_configuration["dlib-predictor"])).resolve())
        Resource.extract_exiftool()

    @staticmethod
    def extract_exiftool():
        if not Resource.exiftool_executable.exists():
            archive = Resource.program_path / Path(Resource.cfm_configuration["exiftool-archive-" + os.name])
            archive = archive.resolve()
            destination = Resource.exiftool_executable.parent
            print(f"Extract {archive} to {destination} (only done the first time)")
            if str(archive).endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(archive) as file:
                    file.extractall(destination)
            elif str(archive).endswith(".tar.gz"):
                import tarfile
                with tarfile.open(archive, "r:gz") as file:
                    file.extractall(destination.parent)
                    file.close()

    @staticmethod
    def download_model():

        import requests
        import bz2
        links_file = open(str(Resource.dlib_predictor_dir / 'links.txt'), 'r')
        links = links_file.readlines()
        links_file.close()

        for link in links:
            new_file_name = str(Resource.dlib_predictor_dir / link.strip().split("/")[-1])
            if not os.path.exists(new_file_name[:-4]):
                print("Download " + new_file_name + ", please wait...")
                downloaded_file = requests.get(link.strip())
                file_on_disk = open(new_file_name, 'wb')
                file_on_disk.write(downloaded_file.content)
                file_on_disk.close()
                with open(new_file_name[:-4], 'wb') as new_file, bz2.BZ2File(new_file_name, 'rb') as file:
                    new_file.write(file.read())
                os.remove(new_file_name)
