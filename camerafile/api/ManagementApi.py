import os
import mimetypes
from datetime import datetime
from typing import Optional, Set
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaSet import MediaSet
from camerafile.core.MediaFile import MediaFile
from camerafile.core.Logging import Logger
from camerafile.task.GenerateThumbnail import GenerateThumbnail
from camerafile.core.OutputDirectory import OutputDirectory

LOGGER = Logger(__name__)

# Assume LOGGER, MediaSet, MediaFile, MediaDirectory, OutputDirectory,
# and GenerateThumbnail are defined elsewhere.

class ManagementApi:
    def __init__(self, media_set_1: MediaSet, media_set_2: MediaSet):
        self.media_set_1 = media_set_1
        self.thb_dir_1 = OutputDirectory.get(self.media_set_1.root_path).path / "thb"
        os.makedirs(self.thb_dir_1, exist_ok=True)

        self.media_set_2 = media_set_2
        self.thb_dir_2 = OutputDirectory.get(self.media_set_2.root_path).path / "thb"
        os.makedirs(self.thb_dir_2, exist_ok=True)
        
        self.simple_ids_map = {}

        self.app = FastAPI()
        self.setup_routes()
        self.setup_static_files()
        self.tree_cache = {}

    def _select_media_set(self, directory: str) -> tuple:
        """Helper method to select the media set and root directory based on the given directory."""
        if directory == "source":
            return self.media_set_1, self.media_set_1.root_path
        elif directory == "destination":
            return self.media_set_2, self.media_set_2.root_path
        else:
            return None, None

    async def generate_thumbnail(self, directory, id, thumbnail_path):
        media_set, root_dir = self._select_media_set(directory)
        if media_set is None:
            return
        media_file: MediaFile = media_set[id]
        await run_in_threadpool(
            GenerateThumbnail.generate_thumbnail,
            root_dir,
            media_file.file_desc,
            thumbnail_path
        )

    def setup_routes(self):

        @self.app.get("/thumbnail")
        async def get_thumbnail(id: str, directory: str, background_tasks: BackgroundTasks):
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
            if directory not in self.simple_ids_map or id not in self.simple_ids_map[directory]:
                return JSONResponse(status_code=404, content={"error": "ID not found"})
            original_id = self.simple_ids_map[directory][id]
            if directory == "source":
                thumbnail_path = self.thb_dir_1 / f"{original_id}.thb"
            elif directory == "destination":
                thumbnail_path = self.thb_dir_2 / f"{original_id}.thb"
            if not thumbnail_path.exists():
                await self.generate_thumbnail(directory, original_id, thumbnail_path)
            return FileResponse(thumbnail_path, media_type="image/jpeg")

        @self.app.get("/list")
        async def get_media_list(directory: Optional[str] = None, folder: Optional[str] = None, filter: Optional[str] = None):
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
            media_ids = []
            media_dates = []
            media_set, _ = self._select_media_set(directory)
            sorted_list = media_set.get_date_sorted_media_list()
            sorted_list_newest_first = reversed(sorted_list)
            simple_id = 0
            self.simple_ids_map[directory] = {}
            for media_file in sorted_list_newest_first:
                date = media_file.get_str_date(format="%Y-%m-%d")
                self.simple_ids_map[directory][str(simple_id)] = media_file.file_desc.id
                media_ids.append(str(simple_id))
                media_dates.append(date if date is not None else datetime.now().strftime("%Y-%m-%d"))
                simple_id += 1
            return {"mediaIds": media_ids, "mediaDates": media_dates}

        @self.app.get("/media")
        async def get_media(directory: Optional[str] = None, id: Optional[str] = None):
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
            if directory not in self.simple_ids_map or id not in self.simple_ids_map[directory]:
                return JSONResponse(status_code=404, content={"error": "ID not found"})
            original_id = self.simple_ids_map[directory][id]
            media_set, root_dir = self._select_media_set(directory)
            media_file: MediaFile = media_set[original_id]
            image_path = os.path.abspath(os.path.join(root_dir, media_file.get_path()))
            media_type, _ = mimetypes.guess_type(image_path)
            return FileResponse(image_path, media_type=media_type)

        @self.app.get("/info")
        async def get_info(id: str, directory: str) -> dict:
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
            if directory not in self.simple_ids_map or id not in self.simple_ids_map[directory]:
                return JSONResponse(status_code=404, content={"error": "ID not found"})
            original_id = self.simple_ids_map[directory][id]
            media_set, _ = self._select_media_set(directory)
            media_file: MediaFile = media_set[original_id]
            exif_date = media_file.get_date()
            return {
                "alt": media_file.file_desc.relative_path,
                "createdAt": exif_date.isoformat() if exif_date is not None else datetime.now().isoformat()
            }

        class ReverseMediaDirectory:
            def __init__(self, dir):
                self.original_dir: MediaDirectory = dir
                self.children = []

        def create_reverse_tree(dirs: Set[MediaDirectory]):
            reverse_dirs = {dir: ReverseMediaDirectory(dir) for dir in dirs}
            for directory in dirs:
                if directory.parent_dir is not None:
                    reverse_dirs[directory.parent_dir].children.append(reverse_dirs[directory])
            root = next(reverse_dir for reverse_dir in reverse_dirs.values() if reverse_dir.original_dir.parent_dir is None)
            return root

        def build_tree_string(reverse_root: ReverseMediaDirectory):
            children = []
            for child in reverse_root.children:
                children.append(build_tree_string(child))
            name = reverse_root.original_dir.name
            if name == "":
                name = "/"
            if children:
                return {"id": reverse_root.original_dir.id, "name": name, "children": children}
            else:
                return {"id": reverse_root.original_dir.id, "name": name} 

        @self.app.get("/tree")
        async def get_tree(directory: str):
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
            cache_key = directory
            if cache_key in self.tree_cache:
                return self.tree_cache[cache_key]
            media_set, _ = self._select_media_set(directory)
            dirs = set()
            for media_file in media_set:
                parent = media_file.parent_dir
                while parent is not None:
                    dirs.add(parent)
                    parent = parent.parent_dir
            reverse_root = create_reverse_tree(dirs)
            result = build_tree_string(reverse_root)
            self.tree_cache[cache_key] = [result]
            LOGGER.info(result)
            return [result]

        @self.app.delete("/images")
        async def delete_images(request: Request) -> dict:
            data = await request.json()
            image_ids = data.get("imageIds", [])
            LOGGER.info(f"Ids of images to delete: {image_ids}")
            return {"success": True, "message": f"Deleted {len(image_ids)} images"}
        
        
        #@self.app.get("/")
        #def read_root():
        #    return RedirectResponse(url="/index.html")
        
        @self.app.get("/")
        async def serve_root():
            return FileResponse("/app/www/index.html")
        


    def setup_static_files(self):
        self.app.mount("/", StaticFiles(directory="/app/www", html=False), name="static")

    def get_app(self):
        return self.app