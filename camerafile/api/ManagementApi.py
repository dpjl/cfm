import os
import mimetypes
from datetime import datetime
from typing import Optional, Set
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from camerafile.core.Constants import INTERNAL
from camerafile.core.MediaDirectory import MediaDirectory
from camerafile.core.MediaSet import MediaSet
from camerafile.core.MediaFile import MediaFile
from camerafile.core.Logging import Logger
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.task.GenerateThumbnail import GenerateThumbnail
from camerafile.core.OutputDirectory import OutputDirectory
from fastapi.middleware.cors import CORSMiddleware

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
        # Use build_sync_id_maps for two maps: source and destination
        from camerafile.core.MediaSetComparator import MediaSetComparator
        self.sync_id_map_source, self.sync_id_map_dest = MediaSetComparator.build_sync_id_maps(self.media_set_1, self.media_set_2)
        # Reverse maps: media_file -> sync_id
        self.reverse_sync_id_map_source = {v: k for k, v in self.sync_id_map_source.items()}
        self.reverse_sync_id_map_dest = {v: k for k, v in self.sync_id_map_dest.items()}
        self.app = FastAPI()
        if os.environ.get("CFM_DEV_MODE") == "1":
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://localhost:8080"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        self.setup_routes()
        self.tree_cache = {}

    def _get_media_file_by_sync_id(self, sync_id: str, directory: str) -> Optional[MediaFile]:
        if directory == "source":
            return self.sync_id_map_source.get(sync_id)
        elif directory == "destination":
            return self.sync_id_map_dest.get(sync_id)
        return None

    async def generate_thumbnail(self, directory, sync_id, thumbnail_path):
        media_file = self._get_media_file_by_sync_id(sync_id, directory)
        if media_file is None:
            return
        root_dir = media_file.parent_set.root_path
        await run_in_threadpool(
            GenerateThumbnail.generate_thumbnail,
            root_dir,
            media_file.file_desc,
            thumbnail_path,
            media_file.metadata[INTERNAL].get_orientation()
        )

    def setup_routes(self):
        @self.app.get("/thumbnail")
        async def get_thumbnail(id: str, directory: str, background_tasks: BackgroundTasks):
            # directory is ignored, kept for compatibility
            media_file = self._get_media_file_by_sync_id(id, directory)
            if media_file is None:
                return JSONResponse(status_code=404, content={"error": "ID not found"})
            original_id = media_file.file_desc.id
            thb_dir = self.thb_dir_1 if media_file.parent_set is self.media_set_1 else self.thb_dir_2
            thumbnail_path = thb_dir / f"{original_id}.thb"
            if not thumbnail_path.exists():
                await self.generate_thumbnail(directory, id, thumbnail_path)
            return FileResponse(thumbnail_path, media_type="image/jpeg")

        @self.app.get("/media")
        async def get_media(directory: Optional[str] = None, id: Optional[str] = None):
            # directory is ignored, kept for compatibility
            media_file = self._get_media_file_by_sync_id(id, directory)
            if media_file is None:
                return JSONResponse(status_code=404, content={"error": "ID not found"})
            root_dir = media_file.parent_set.root_path
            image_path = os.path.abspath(os.path.join(root_dir, media_file.get_path()))
            media_type, _ = mimetypes.guess_type(image_path)
            return FileResponse(image_path, media_type=media_type)

        @self.app.get("/info")
        async def get_info(id: str, directory: str) -> dict:
            # directory is ignored, kept for compatibility
            media_file = self._get_media_file_by_sync_id(id, directory)
            if media_file is None:
                return JSONResponse(status_code=404, content={"error": "ID not found"})
            exif_date = media_file.get_date()
            return {
                "alt": media_file.file_desc.relative_path,
                "createdAt": exif_date.isoformat() if exif_date is not None else datetime.now().isoformat()
            }

        @self.app.get("/list")
        async def get_media_list(directory: Optional[str] = None, folder: Optional[str] = None, filter: Optional[str] = None):
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
            media_set = self.media_set_1 if directory == "source" else self.media_set_2
            other_media_set = self.media_set_2 if directory == "source" else self.media_set_1
            if folder and folder not in ["directory1", "directory2"]:
                media_list = media_set.get_media_in_directory_recursive(str(folder))
            else:
                media_list = media_set.get_date_sorted_media_list()[::-1]
            if filter == "exclusive":
                media_list = media_set.get_only_here(other_media_set, media_list)
            elif filter == "common":
                media_list = media_set.get_in_both(other_media_set, media_list)
            date_to_ids = {}
            for media_file in media_list:
                date = media_file.get_str_date(format="%Y-%m-%d") or datetime.now().strftime("%Y-%m-%d")
                if directory == "source":
                    sync_id = self.reverse_sync_id_map_source.get(media_file)
                else:
                    sync_id = self.reverse_sync_id_map_dest.get(media_file)
                if sync_id is None:
                    continue
                if date not in date_to_ids:
                    date_to_ids[date] = []
                date_to_ids[date].append(sync_id)
            return date_to_ids

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
            # Select the correct media_set based on directory
            media_set = self.media_set_1 if directory == "source" else self.media_set_2
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
        
        @self.app.get("/")
        async def serve_root():
            return FileResponse("/app/www/index.html")
        

    def setup_static_files(self):
        self.app.mount("/", StaticFiles(directory="/app/www", html=False), name="static")

    def get_app(self):
        return self.app