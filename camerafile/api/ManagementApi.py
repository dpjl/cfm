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
        async def get_media_list(directory: Optional[str] = None, folder: Optional[str] = None, filter: Optional[str] = None, pathRegex: Optional[str] = None):
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
            media_set = self.media_set_1 if directory == "source" else self.media_set_2
            other_media_set = self.media_set_2 if directory == "source" else self.media_set_1
            if folder and folder not in ["directory1", "directory2"]:
                media_list = media_set.get_media_in_directory_recursive(str(folder))
            else:
                media_list = media_set.get_date_sorted_media_list()[::-1]
            if filter == "exclusive":
                media_list = media_set.get_filtered_media(other_media_set, "only_here", media_list)
            elif filter == "common":
                media_list = media_set.get_filtered_media(other_media_set, "common", media_list)
            elif filter == "common_identical":
                media_list = media_set.get_filtered_media(other_media_set, "common_exact", media_list)
            elif filter == "common_copied":
                media_list = media_set.get_filtered_media(other_media_set, "common_excluding_exact", media_list)
            elif filter == "exclusive_conflicted":
                media_list = get_conflicted_media(self.media_set_1, self.media_set_2, media_list)
            # Filtrage par regexp sur le chemin relatif
            if pathRegex:
                import re
                try:
                    pattern = re.compile(pathRegex)
                    media_list = [m for m in media_list if pattern.search(m.file_desc.relative_path)]
                except re.error:
                    pass  # Ignore le filtre si la regexp est invalide
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

        def build_directory_tree(media_dir: MediaDirectory):
            # Get children and sort them alphabetically by name
            children = []
            for child_dir in sorted(media_dir.children_dirs, key=lambda d: d.file_desc.name):
                children.append(build_directory_tree(child_dir))
            
            name = media_dir.file_desc.name
            if name == "":
                name = "/"
                
            if children:
                return {"id": media_dir.file_desc.id, "name": name, "children": children}
            else:
                return {"id": media_dir.file_desc.id, "name": name}

        @self.app.get("/tree")
        async def get_tree(directory: str):
            if directory not in ["source", "destination"]:
                return JSONResponse(status_code=400, content={"error": "Invalid directory parameter"})
                
            cache_key = directory
            if cache_key in self.tree_cache:
                return self.tree_cache[cache_key]
                
            # Select the correct media_set based on directory
            media_set = self.media_set_1 if directory == "source" else self.media_set_2
            
            # Get the root directory
            root_dir = media_set.media_dir_list[""]
            
            # Build the tree starting from root
            result = build_directory_tree(root_dir)
            
            self.tree_cache[cache_key] = [result]
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
        
        @self.app.get("/filters")
        async def get_filters():
            return [
                {
                    "id": "all",
                    "label": "all",
                    "icon": "Folder",
                    "description": "Show all media items"
                },
                {
                    "id": "unique",
                    "label": "unique",
                    "icon": "ImageIcon",
                    "description": "Show only unique media items"
                },
                {
                    "id": "duplicates",
                    "label": "duplicates",
                    "icon": "Copy",
                    "description": "Show only duplicate media items"
                },
                {
                    "id": "exclusive",
                    "label": "only_here",
                    "icon": "Fingerprint",
                    "description": "Show media items that exist only in this gallery"
                },
                {
                    "id": "common",
                    "label": "common",
                    "icon": "Files",
                    "description": "Show media items that exist in both galleries"
                },
                {
                    "id": "common_copied",
                    "label": "common_copied",
                    "icon": "Files",
                    "description": "Show media items that exist in both galleries, but are different files"
                },
                {
                    "id": "common_identical",
                    "label": "common_identical",
                    "icon": "Files",
                    "description": "Show media items that exist in both galleries, and are identical files"
                },
                {
                    "id": "exclusive_conflicted",
                    "label": "only_here_conflicted",
                    "icon": "Files",
                    "description": "Show media items that exist only in this gallery, but cannot be copied (generated path in other gallery allready exists)"
                }
            ]

    def setup_static_files(self):
        self.app.mount("/", StaticFiles(directory="/app/www", html=False), name="static")

    def get_app(self):
        return self.app

def get_conflicted_media(media_set1, media_set2, media_list):
    from camerafile.processor.BatchCopy import BatchCopy
    from camerafile.fileaccess.FileAccess import CopyMode
    batch = BatchCopy(media_set1, media_set2, CopyMode.HARD_LINK)
    copy_elements = batch.get_copy_elements_without_duplicates()
    existing_paths = set(m.file_desc.relative_path for m in media_set2.media_file_list)
    media_set = set(media_list)
    conflicted = [
        cp_element.media
        for cp_element in copy_elements
        if cp_element.destination.as_posix() in existing_paths and cp_element.media in media_set
    ]
    return conflicted