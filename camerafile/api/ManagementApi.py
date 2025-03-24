from hashlib import new
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaSet import MediaSet
from camerafile.core.MediaFile import MediaFile
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from typing import Set, Optional
import mimetypes
import os
import io
import imghdr
from datetime import datetime
from camerafile.core.Logging import Logger
from camerafile.core.Constants import THUMBNAIL
from camerafile.core.OutputDirectory import OutputDirectory
from PIL import Image
LOGGER = Logger(__name__)

class ManagementApi:
    def __init__(self, media_set_1: MediaSet, media_set_2: MediaSet):
        self.media_set_1 = media_set_1
        self.thb_dir_1 = OutputDirectory.get(self.media_set_1.root_path).path / "thb"

        self.media_set_2 = media_set_2
        self.thb_dir_2 = OutputDirectory.get(self.media_set_2.root_path).path / "thb"

        self.app = FastAPI()
        self.setup_routes()
        self.setup_static_files()
    
    def setup_routes(self):

        @self.app.get("/")
        def read_root():
            return RedirectResponse(url="/index.html")

        @self.app.get("/thumbnail")
        async def get_thumbnail(id: str, directory: str):
            if directory == "source":
                thumbnail_path = f"{self.thb_dir_1}/{id}.thb"
            elif directory == "destination":
                thumbnail_path = f"{self.thb_dir_2}/{id}.thb"
            #media_type, _ = mimetypes.guess_type(image_path)
            return FileResponse(thumbnail_path, media_type="image/jpeg")

        @self.app.get("/media")
        async def get_media(directory: Optional[str] = None, id: Optional[str] = None):
            if directory:
                result = []
                if directory == "source":
                    media_file: MediaFile
                    for media_file in self.media_set_1:
                        #f not self.media_set_1.contains(media_file):
                        result += [media_file.file_desc.id]
                elif directory == "destination":
                    media_file: MediaFile
                    for media_file in self.media_set_2:
                        #not self.media_set_1.contains(media_file):
                        result += [media_file.file_desc.id]
                return result
            elif id:
                media_file: MediaFile = self.media_set_2[id]
                image_path = os.path.abspath(os.path.join(self.media_set_2.root_path, media_file.get_path()))
                media_type, _ = mimetypes.guess_type(image_path)
                return FileResponse(image_path, media_type=media_type)

        @self.app.get("/info")
        async def get_info(id: str, directory: str) -> dict:
            if directory == "source":
                media_file: MediaFile = self.media_set_1[id]
            elif directory == "destination":
                media_file: MediaFile = self.media_set_2[id]
            exif_date = media_file.get_date()
            return {"alt": media_file.file_desc.relative_path,
                    "createdAt": exif_date.isoformat() if exif_date is not None else datetime.now().isoformat()}


        class ReverseMediaDirectory:
            def __init__(self, dir):
                self.original_dir: MediaDirectory = dir
                self.children = []

        def create_reverse_tree(dirs: Set[MediaDirectory]):
            reverse_dirs = {dir: ReverseMediaDirectory(dir) for dir in dirs}
            for dir in dirs:
                if dir.parent_dir is not None:
                    reverse_dirs[dir.parent_dir].children.append(reverse_dirs[dir])
            root = next(reverse_dir for reverse_dir in reverse_dirs.values() if reverse_dir.original_dir.parent_dir is None)
            return root

        def build_tree_string(reverse_root: ReverseMediaDirectory):
            children = []
            for child in reverse_root.children:
                children += [build_tree_string(child)]
            name = reverse_root.original_dir.name
            if name == "":
                name = "/"
            if len(children) != 0:
                return {"id": reverse_root.original_dir.id, "name": name, "children": children}
            else:
                return {"id": reverse_root.original_dir.id, "name": name} 

        @self.app.get("/tree")
        async def get_tree():
            dirs = set()
            media_file: MediaFile
            for media_file in self.media_set_2:
                if not self.media_set_1.contains(media_file):
                    parent = media_file.parent_dir
                    while parent is not None:
                        dirs.add(parent)
                        parent = parent.parent_dir
            LOGGER.info(f"TMP: {dirs}")
            reverse_root = create_reverse_tree(dirs)
            LOGGER.info(f"TMP: {reverse_root}")
            result =  build_tree_string(reverse_root)
            LOGGER.info(result)
            return [result]

            #return [
            #        {"id": "directory1", "name": "Default Directory", "children": [{"id":"test", "name": "toto", "children": [{"id":"test2", "name": "toto2"}]}]},
            #        {"id": "directory2", "name": "Default Directory 2", "children": [{"id":"test2", "name": "toto2"}]}
            #       ]            

        @self.app.delete("/images")
        async def delete_images(request: Request) -> dict:
            data = await request.json()
            image_ids = data.get("imageIds", [])
            LOGGER.info(f"Ids of images to delete: {image_ids}")
            return {"success": True, "message": f"Deleted {len(image_ids)} images"}

    def setup_static_files(self):
        self.app.mount("/", StaticFiles(directory="/app/www", html=False), name="management")

    def get_app(self):
        return self.app