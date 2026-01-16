from pathlib import Path
from typing import List

from camerafile.core.Logging import Logger
from camerafile.mdtools.ExifToolReader import ExifTool
from camerafile.mdtools.MdException import MdException

LOGGER = Logger(__name__)


class XmpTool:
    TAGS_LIST = "XMP-digiKam:TagsList"

    @staticmethod
    def read_digikam_tags(xmp_path: Path) -> List[str]:
        if not xmp_path.exists():
            return []
        try:
            out, _ = ExifTool.execute(
                "-s3",
                "-sep",
                "\n",
                f"-{XmpTool.TAGS_LIST}",
                str(xmp_path)
            )
        except MdException as exc:
            LOGGER.info(f"Failed to read XMP tags from {xmp_path}: {exc}")
            return []
        return [line.strip() for line in out.splitlines() if line.strip()]

    @staticmethod
    def add_digikam_tag(xmp_path: Path, tag: str) -> bool:
        return XmpTool._write_args(xmp_path, [f"-{XmpTool.TAGS_LIST}+={tag}"])

    @staticmethod
    def remove_digikam_tag(xmp_path: Path, tag: str) -> bool:
        return XmpTool._write_args(xmp_path, [f"-{XmpTool.TAGS_LIST}-={tag}"])

    @staticmethod
    def ensure_digikam_tag(original_path: Path, xmp_path: Path, tag: str) -> bool:
        if xmp_path.exists():
            return XmpTool.add_digikam_tag(xmp_path, tag)

        if XmpTool._write_args(xmp_path, [f"-{XmpTool.TAGS_LIST}={tag}"]):
            return True

        if original_path is None or not original_path.exists():
            return False
        return XmpTool._create_from_original(original_path, xmp_path, tag)

    @staticmethod
    def _write_args(xmp_path: Path, args: List[str]) -> bool:
        try:
            ExifTool.execute("-overwrite_original", *args, str(xmp_path))
            return True
        except MdException as exc:
            LOGGER.info(f"Failed to update XMP {xmp_path}: {exc}")
            return False

    @staticmethod
    def _create_from_original(original_path: Path, xmp_path: Path, tag: str) -> bool:
        try:
            ExifTool.execute(
                "-o",
                str(xmp_path),
                f"-{XmpTool.TAGS_LIST}={tag}",
                str(original_path)
            )
            return True
        except MdException as exc:
            LOGGER.info(f"Failed to create XMP {xmp_path}: {exc}")
            return False
