import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from camerafile.core.Configuration import Configuration
from camerafile.core.Constants import CFM_CAMERA_MODEL, SIGNATURE, IMAGE_TYPE, WHATSAPP_SIDECAR_SUFFIX, \
    WHATSAPP_ORIG_LINK_SUFFIX
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.mdtools.XmpTool import XmpTool
from camerafile.processor.BatchTool import BatchElement, TaskWithProgression

LOGGER = Logger(__name__)

# WhatsApp filename pattern (same as BatchFindWhatsAppOriginals)
WHATSAPP_FILENAME_PATTERN = re.compile(r'^(VID|IMG)-([0-9]{8})-WA[0-9]{4}\.(jpg|jpeg|mp4)$', re.IGNORECASE)

# Default values
DEFAULT_DATE_WINDOW_DAYS = 30
DEFAULT_SIMILARITY_THRESHOLD = 10
EPOCH_DATE_CUTOFF = datetime(1970, 1, 2)
SIDECAR_SCHEMA = "cfm-wa-link-v2"
DEFAULT_RECIPIENT_LABEL = "unknown"
WHATSAPP_TAG_PREFIX = "WhatsApp"
XMP_SUFFIX = ".xmp"
STATUS_LINKED = "linked"
STATUS_REJECTED = "rejected"
STATUS_STALE = "stale"


class BatchFindWhatsAppOriginalsSidecar(TaskWithProgression):
    """
    Finds original files for WhatsApp-sent images by comparing dhash signatures.
    Instead of writing metadata, writes a JSON sidecar and creates a link to the original.
    """

    def __init__(self, media_set: MediaSet, date_window_days: int = DEFAULT_DATE_WINDOW_DAYS,
                 similarity_threshold: int = DEFAULT_SIMILARITY_THRESHOLD):
        self.media_set = media_set
        self.date_window_days = date_window_days
        self.similarity_threshold = similarity_threshold
        self.whatsapp_sent_files: List[MediaFile] = []
        self.matches_found = 0
        self.links_created = 0
        self.skipped_rejected = 0
        self.skipped_existing = 0
        TaskWithProgression.__init__(
            self,
            batch_title="Find WhatsApp-sent originals (sidecar)",
            nb_sub_process=0
        )

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

        self.whatsapp_sent_files = self._get_whatsapp_sent_images()
        if not self.whatsapp_sent_files:
            LOGGER.info("No WhatsApp-sent image files found")
            return
        self._compute_whatsapp_signatures()

    def _get_whatsapp_sent_candidates(self) -> List[MediaFile]:
        result = []
        excluded_invalid_date = 0
        for media_file in self.media_set.media_file_list:
            if not isinstance(media_file.file_desc, StandardFileDescription):
                continue
            if media_file.file_desc.extension not in IMAGE_TYPE:
                continue
            if media_file.metadata[CFM_CAMERA_MODEL].value != "WhatsApp-sent":
                continue
            if not WHATSAPP_FILENAME_PATTERN.match(media_file.file_desc.name):
                continue
            wa_date = media_file.get_date()
            if wa_date is None or wa_date <= EPOCH_DATE_CUTOFF:
                excluded_invalid_date += 1
                continue
            result.append(media_file)
        LOGGER.info(f"WhatsApp-sent candidate files: {len(result)}")
        if excluded_invalid_date:
            LOGGER.info(
                f"Excluded {excluded_invalid_date} WhatsApp-sent file(s) with missing/epoch date"
            )
        return result

    def _get_whatsapp_sent_images(self) -> List[MediaFile]:
        result = []
        for media_file in self._get_whatsapp_sent_candidates():
            sidecar_data = self._read_sidecar(media_file)
            if sidecar_data and sidecar_data.get("status") == STATUS_REJECTED:
                self._remove_xmp_for_rejected(media_file, sidecar_data)
                self.skipped_rejected += 1
                continue
            result.append(media_file)
        return result

    def compute_required_date_range(self) -> Optional[Tuple[datetime, datetime]]:
        candidates = self._get_whatsapp_sent_candidates()
        if not candidates:
            return None
        eligible = []
        for media_file in candidates:
            sidecar_data = self._read_sidecar(media_file)
            if sidecar_data and sidecar_data.get("status") == STATUS_REJECTED:
                continue
            eligible.append(media_file)
        return self._compute_required_date_range(eligible)

    @staticmethod
    def _extract_whatsapp_date(media_file: MediaFile) -> Optional[datetime]:
        match = WHATSAPP_FILENAME_PATTERN.match(media_file.file_desc.name)
        if match:
            date_str = match.group(2)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                return None
        return None

    @staticmethod
    def _start_of_day(date_value: datetime) -> datetime:
        return date_value.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _end_of_day(date_value: datetime) -> datetime:
        return date_value.replace(hour=23, minute=59, second=59, microsecond=999999)

    @staticmethod
    def _parse_wa_date(wa_date_str: Optional[str]) -> Optional[datetime]:
        if not wa_date_str:
            return None
        try:
            return datetime.strptime(wa_date_str, '%Y/%m/%d %H:%M:%S.%f')
        except ValueError:
            return None

    def _get_whatsapp_db_entry(self, media_file: MediaFile) -> Optional[Dict[str, Any]]:
        whatsapp_db = Configuration.get().whatsapp_db
        if not whatsapp_db:
            return None
        entry = whatsapp_db.get(media_file.file_desc.name)
        if entry is None:
            return None
        if isinstance(entry, dict):
            return entry
        if isinstance(entry, (int, float)):
            return {
                "timestamp_ms": entry,
                "recipient_label": DEFAULT_RECIPIENT_LABEL,
                "recipient_id": None,
                "from_me": None
            }
        return None

    def _get_whatsapp_date_info(
        self, media_file: MediaFile
    ) -> Optional[Tuple[datetime, str, datetime, datetime, Optional[Dict[str, Any]]]]:
        wa_entry = self._get_whatsapp_db_entry(media_file)
        timestamp_ms = wa_entry.get("timestamp_ms") if wa_entry else None
        if timestamp_ms is not None:
            try:
                wa_date = datetime.fromtimestamp(timestamp_ms / 1000)
                date_source = "whatsapp_db"
                date_end = wa_date
                date_start = wa_date - timedelta(days=self.date_window_days)
                return wa_date, date_source, date_start, date_end, wa_entry
            except (ValueError, OSError, OverflowError):
                pass

        wa_date = media_file.get_date()
        filename_date = self._extract_whatsapp_date(media_file)

        if wa_date is None:
            if filename_date is None:
                return None
            date_source = "filename"
            date_end = self._end_of_day(filename_date)
            date_start = self._start_of_day(filename_date - timedelta(days=self.date_window_days))
            return filename_date, date_source, date_start, date_end, wa_entry

        if filename_date and wa_date.time() == datetime.min.time() and wa_date.date() == filename_date.date():
            date_source = "filename"
            date_end = self._end_of_day(wa_date)
            date_start = self._start_of_day(wa_date - timedelta(days=self.date_window_days))
            return wa_date, date_source, date_start, date_end, wa_entry

        date_source = "metadata"
        date_end = wa_date
        date_start = wa_date - timedelta(days=self.date_window_days)
        return wa_date, date_source, date_start, date_end, wa_entry

    def _compute_required_date_range(
        self, media_files: Optional[List[MediaFile]] = None
    ) -> Optional[Tuple[datetime, datetime]]:
        if media_files is None:
            media_files = self.whatsapp_sent_files
        if not media_files:
            return None

        min_date = None
        max_date = None

        for media_file in media_files:
            date_info = self._get_whatsapp_date_info(media_file)
            if date_info is None:
                continue
            _, _, date_start, date_end, _ = date_info
            if min_date is None or date_start < min_date:
                min_date = date_start
            if max_date is None or date_end > max_date:
                max_date = date_end

        if min_date is None or max_date is None:
            return None
        return min_date, max_date

    def _compute_whatsapp_signatures(self):
        for media_file in self.whatsapp_sent_files:
            if media_file.metadata[SIGNATURE].value is None:
                try:
                    file_access = FileAccessFactory.get(media_file.parent_set.root_path, media_file.file_desc)
                    media_file.metadata[SIGNATURE].value = file_access.hash()
                except Exception as e:
                    LOGGER.debug(f"Failed to compute signature for {media_file.get_path()}: {e}")

    def task_getter(self):
        return self._find_original

    def arguments(self) -> List[BatchElement]:
        return [BatchElement(media_file, media_file.get_path()) for media_file in self.whatsapp_sent_files]

    def _find_original(self, batch_element: BatchElement):
        media_file = batch_element.args

        sidecar_data = self._read_sidecar(media_file)
        if sidecar_data and sidecar_data.get("status") == STATUS_REJECTED:
            batch_element.result = {"status": "skipped_rejected", "media_file": media_file}
            return batch_element

        if sidecar_data and sidecar_data.get("status") == STATUS_LINKED:
            if self._ensure_link_from_sidecar(media_file, sidecar_data):
                self._ensure_xmp_from_sidecar(media_file, sidecar_data)
                batch_element.result = {"status": "skipped_existing", "media_file": media_file}
                return batch_element

        date_info = self._get_whatsapp_date_info(media_file)
        if date_info is None:
            batch_element.result = {"status": "unmatched", "media_file": media_file, "sidecar": sidecar_data}
            return batch_element

        wa_date, date_source, date_start, date_end, wa_entry = date_info

        signature = media_file.metadata[SIGNATURE].value
        if signature is None:
            batch_element.result = {"status": "unmatched", "media_file": media_file, "sidecar": sidecar_data}
            return batch_element

        date_start_str = date_start.strftime('%Y/%m/%d %H:%M:%S.%f')
        date_end_str = date_end.strftime('%Y/%m/%d %H:%M:%S.%f')
        similar_files = self.media_set.indexer.find_similar_in_date_range(
            signature, date_start_str, date_end_str, self.similarity_threshold
        )

        best_match = None
        best_date_diff = None
        best_hamming = None

        for candidate, hamming_distance in similar_files:
            if candidate == media_file:
                continue
            if candidate.metadata[CFM_CAMERA_MODEL].value in ["WhatsApp", "WhatsApp-sent"]:
                continue
            if not isinstance(candidate.file_desc, StandardFileDescription):
                continue

            candidate_date = candidate.get_date()
            if candidate_date is None:
                continue

            date_diff = abs((wa_date - candidate_date).total_seconds())
            if best_match is None:
                best_match = candidate
                best_date_diff = date_diff
                best_hamming = hamming_distance
                continue

            if hamming_distance < best_hamming:
                best_match = candidate
                best_date_diff = date_diff
                best_hamming = hamming_distance
                continue

            if hamming_distance == best_hamming and date_diff < best_date_diff:
                best_match = candidate
                best_date_diff = date_diff
                best_hamming = hamming_distance

        if best_match is None:
            batch_element.result = {"status": "unmatched", "media_file": media_file, "sidecar": sidecar_data}
            return batch_element

        batch_element.result = {
            "status": "matched",
            "media_file": media_file,
            "original": best_match,
            "wa_date": wa_date,
            "date_source": date_source,
            "wa_info": wa_entry,
            "wa_signature": signature,
            "hamming": best_hamming,
            "date_diff_s": int(best_date_diff) if best_date_diff is not None else None,
            "sidecar": sidecar_data
        }
        return batch_element

    def post_task(self, result, progress_bar, replace=False):
        status = result.get("status")
        media_file = result.get("media_file")

        if status == "matched":
            original = result.get("original")
            link_info = self._create_link_for_match(media_file, original)
            xmp_info = self._create_xmp_for_match(
                original=original,
                wa_date=result.get("wa_date"),
                wa_info=result.get("wa_info")
            )
            sidecar_data = self._build_sidecar_data(
                media_file=media_file,
                original=original,
                wa_date=result.get("wa_date"),
                date_source=result.get("date_source"),
                wa_info=result.get("wa_info"),
                wa_signature=result.get("wa_signature"),
                hamming=result.get("hamming"),
                date_diff_s=result.get("date_diff_s"),
                link_info=link_info,
                xmp_info=xmp_info,
                existing_sidecar=result.get("sidecar")
            )
            self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)
            self.matches_found += 1
            if link_info.get("created"):
                self.links_created += 1
            LOGGER.debug(f"Matched: {media_file.get_path()} -> {original.get_path()}")
        elif status == "unmatched":
            sidecar_data = result.get("sidecar")
            if sidecar_data and sidecar_data.get("status") != STATUS_REJECTED:
                self._mark_sidecar_stale(media_file, sidecar_data)
        elif status == "skipped_rejected":
            self.skipped_rejected += 1
        elif status == "skipped_existing":
            self.skipped_existing += 1

        progress_bar.increment()

    def finalize(self):
        LOGGER.info(
            f"Found {self.matches_found} WhatsApp-sent files with matching originals "
            f"({self.links_created} link(s) created, {self.skipped_existing} reused, "
            f"{self.skipped_rejected} rejected)"
        )

    def display_final_status(self, progress_bar):
        print(
            f"{progress_bar.position} WhatsApp-sent files processed, "
            f"{self.matches_found} originals found in {progress_bar.processing_time}"
        )

    def _get_sidecar_path(self, media_file: MediaFile) -> Path:
        wa_path = Path(self.media_set.root_path) / media_file.file_desc.relative_path
        sidecar_name = f"{wa_path.stem}{WHATSAPP_SIDECAR_SUFFIX}"
        return wa_path.with_name(sidecar_name)

    def _get_link_path(self, media_file: MediaFile, original_extension: str) -> Path:
        wa_path = Path(self.media_set.root_path) / media_file.file_desc.relative_path
        link_name = f"{wa_path.stem}{WHATSAPP_ORIG_LINK_SUFFIX}{original_extension}"
        return wa_path.with_name(link_name)

    def _read_sidecar(self, media_file: MediaFile) -> Optional[Dict[str, Any]]:
        sidecar_path = self._get_sidecar_path(media_file)
        if not sidecar_path.exists():
            return None
        try:
            with open(sidecar_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            LOGGER.info(f"Failed to read sidecar {sidecar_path}: {exc}")
            return None

    def _write_sidecar(self, sidecar_path: Path, data: Dict[str, Any]) -> None:
        tmp_path = sidecar_path.with_name(sidecar_path.name + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=True)
        os.replace(tmp_path, sidecar_path)

    def _mark_sidecar_stale(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> None:
        sidecar_data["status"] = STATUS_STALE
        sidecar_data["updated_at"] = self._now_iso()
        self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)

    def _ensure_link_from_sidecar(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> bool:
        original_rel = sidecar_data.get("original", {}).get("path")
        if not original_rel:
            return False

        original_abs = Path(self.media_set.root_path) / original_rel
        if not original_abs.exists():
            return False

        link_rel = sidecar_data.get("link", {}).get("path")
        if link_rel:
            link_abs = Path(self.media_set.root_path) / link_rel
        else:
            original_ext = Path(original_rel).suffix
            link_abs = self._get_link_path(media_file, original_ext)

        if link_abs.exists():
            try:
                if os.path.samefile(original_abs, link_abs):
                    return True
            except OSError:
                return True
            LOGGER.info(f"Link path already exists and does not point to original: {link_abs}")
            return True

        link_info = self._create_link(original_abs, link_abs)
        sidecar_data["link"] = link_info
        self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)
        if link_info.get("created"):
            self.links_created += 1
        return True

    def _create_link_for_match(self, media_file: MediaFile, original: MediaFile) -> Dict[str, Any]:
        original_abs = Path(self.media_set.root_path) / original.file_desc.relative_path
        link_abs = self._get_link_path(media_file, original.file_desc.extension)
        return self._create_link(original_abs, link_abs)

    def _create_link(self, original_abs: Path, link_abs: Path) -> Dict[str, Any]:
        link_rel = os.path.relpath(link_abs, self.media_set.root_path)
        link_info = {
            "path": link_rel,
            "type": "none",
            "fallback": "symlink",
            "created": False
        }

        if link_abs.exists():
            try:
                if os.path.samefile(original_abs, link_abs):
                    link_info["type"] = "symlink" if os.path.islink(link_abs) else "hardlink"
                    return link_info
            except OSError:
                return link_info
            link_info["type"] = "blocked"
            return link_info

        try:
            os.link(original_abs, link_abs)
            link_info["type"] = "hardlink"
            link_info["created"] = True
            return link_info
        except Exception:
            try:
                rel_target = os.path.relpath(original_abs, link_abs.parent)
                os.symlink(rel_target, link_abs)
                link_info["type"] = "symlink"
                link_info["created"] = True
                return link_info
            except Exception:
                return link_info

    @staticmethod
    def _sanitize_recipient_label(label: Optional[str]) -> str:
        if not label:
            return DEFAULT_RECIPIENT_LABEL
        sanitized = label.strip()
        sanitized = re.sub(r"[\\/|]+", "_", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized)
        if not sanitized:
            return DEFAULT_RECIPIENT_LABEL
        return sanitized

    def _build_whatsapp_tag(self, recipient_label: Optional[str], wa_date: Optional[datetime]) -> Optional[str]:
        if wa_date is None:
            return None
        recipient = self._sanitize_recipient_label(recipient_label)
        date_str = wa_date.strftime("%Y-%m-%d")
        return f"{WHATSAPP_TAG_PREFIX}/{recipient}/{date_str}"

    @staticmethod
    def _is_unknown_recipient(label: Optional[str]) -> bool:
        if label is None:
            return True
        return label.strip().lower() == DEFAULT_RECIPIENT_LABEL

    @staticmethod
    def _is_unknown_tag(tag: Optional[str]) -> bool:
        if not tag:
            return True
        prefix = f"{WHATSAPP_TAG_PREFIX}/{DEFAULT_RECIPIENT_LABEL}/".lower()
        return tag.strip().lower().startswith(prefix)

    @staticmethod
    def _get_xmp_path(original_abs: Path) -> Path:
        return original_abs.with_name(original_abs.name + XMP_SUFFIX)

    def _create_xmp_for_match(
        self,
        original: MediaFile,
        wa_date: Optional[datetime],
        wa_info: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        tag = self._build_whatsapp_tag(
            recipient_label=wa_info.get("recipient_label") if wa_info else None,
            wa_date=wa_date
        )
        if not tag:
            return None
        original_abs = Path(self.media_set.root_path) / original.file_desc.relative_path
        xmp_abs = self._get_xmp_path(original_abs)
        existing_tags = set(XmpTool.read_digikam_tags(xmp_abs))
        if tag not in existing_tags:
            if not XmpTool.ensure_digikam_tag(original_abs, xmp_abs, tag):
                return None
        xmp_rel = os.path.relpath(xmp_abs, self.media_set.root_path)
        return {"path": xmp_rel, "tag": tag}

    def _build_tag_from_sidecar(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> Optional[str]:
        wa_data = sidecar_data.get("wa", {})
        recipient_label = wa_data.get("recipient_label")
        if not recipient_label:
            wa_entry = self._get_whatsapp_db_entry(media_file)
            if wa_entry:
                recipient_label = wa_entry.get("recipient_label")

        wa_date = self._get_tag_date(media_file, sidecar_data)
        return self._build_whatsapp_tag(recipient_label, wa_date)

    def _get_tag_date(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> Optional[datetime]:
        wa_data = sidecar_data.get("wa", {})
        wa_date = self._parse_wa_date(wa_data.get("date"))
        if wa_date is None:
            date_info = self._get_whatsapp_date_info(media_file)
            if date_info is not None:
                wa_date = date_info[0]
        return wa_date

    def _get_upgrade_tag_and_entry(
        self, media_file: MediaFile, sidecar_data: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        wa_data = sidecar_data.get("wa", {})
        if not self._is_unknown_recipient(wa_data.get("recipient_label")):
            return None, None

        wa_entry = self._get_whatsapp_db_entry(media_file)
        if not wa_entry:
            return None, None

        recipient_label = wa_entry.get("recipient_label")
        if self._is_unknown_recipient(recipient_label):
            return None, None

        wa_date = self._get_tag_date(media_file, sidecar_data)
        if wa_date is None:
            return None, None

        return self._build_whatsapp_tag(recipient_label, wa_date), wa_entry

    @staticmethod
    def _apply_wa_upgrade(sidecar_data: Dict[str, Any], wa_entry: Dict[str, Any]) -> None:
        wa_data = sidecar_data.get("wa", {})
        wa_data["recipient_label"] = wa_entry.get("recipient_label")
        if wa_data.get("recipient_id") is None:
            wa_data["recipient_id"] = wa_entry.get("recipient_id")
        if wa_data.get("from_me") is None:
            wa_data["from_me"] = wa_entry.get("from_me")
        if wa_data.get("sent_at_ms") is None:
            wa_data["sent_at_ms"] = wa_entry.get("timestamp_ms")
        sidecar_data["wa"] = wa_data

    def _get_xmp_path_from_sidecar(self, sidecar_data: Dict[str, Any], original_abs: Path) -> Path:
        xmp_rel = sidecar_data.get("xmp", {}).get("path")
        if xmp_rel:
            return Path(self.media_set.root_path) / xmp_rel
        return self._get_xmp_path(original_abs)

    def _ensure_xmp_from_sidecar(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> bool:
        original_rel = sidecar_data.get("original", {}).get("path")
        if not original_rel:
            return False
        original_abs = Path(self.media_set.root_path) / original_rel
        if not original_abs.exists():
            return False

        xmp_abs = self._get_xmp_path_from_sidecar(sidecar_data, original_abs)
        current_tag = sidecar_data.get("xmp", {}).get("tag")
        upgrade_tag, upgrade_entry = self._get_upgrade_tag_and_entry(media_file, sidecar_data)
        tags = set(XmpTool.read_digikam_tags(xmp_abs))

        if upgrade_tag and self._is_unknown_tag(current_tag):
            if not xmp_abs.exists():
                if not XmpTool.ensure_digikam_tag(original_abs, xmp_abs, upgrade_tag):
                    return False
            else:
                if current_tag and current_tag in tags:
                    if not XmpTool.remove_digikam_tag(xmp_abs, current_tag):
                        return False
                    tags.discard(current_tag)
                if upgrade_tag not in tags:
                    if not XmpTool.add_digikam_tag(xmp_abs, upgrade_tag):
                        return False
            self._apply_wa_upgrade(sidecar_data, upgrade_entry)
            sidecar_data["xmp"] = {
                "path": os.path.relpath(xmp_abs, self.media_set.root_path),
                "tag": upgrade_tag
            }
            self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)
            return True

        if not current_tag:
            current_tag = self._build_tag_from_sidecar(media_file, sidecar_data)
            if current_tag:
                sidecar_data["xmp"] = {
                    "path": os.path.relpath(xmp_abs, self.media_set.root_path),
                    "tag": current_tag
                }
                self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)

        if not current_tag:
            return False

        if not xmp_abs.exists():
            if not XmpTool.ensure_digikam_tag(original_abs, xmp_abs, current_tag):
                return False
            return True

        if current_tag not in tags:
            if not XmpTool.add_digikam_tag(xmp_abs, current_tag):
                return False
        return True

    def _remove_xmp_for_rejected(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> None:
        xmp_rel = sidecar_data.get("xmp", {}).get("path")
        if xmp_rel:
            xmp_abs = Path(self.media_set.root_path) / xmp_rel
        else:
            original_rel = sidecar_data.get("original", {}).get("path")
            if not original_rel:
                return
            original_abs = Path(self.media_set.root_path) / original_rel
            xmp_abs = self._get_xmp_path(original_abs)
        if not xmp_abs.exists():
            return
        try:
            xmp_abs.unlink()
        except Exception as exc:
            LOGGER.info(f"Failed to remove XMP {xmp_abs}: {exc}")

    def _build_sidecar_data(
        self,
        media_file: MediaFile,
        original: MediaFile,
        wa_date: Optional[datetime],
        date_source: Optional[str],
        wa_info: Optional[Dict[str, Any]],
        wa_signature: Optional[int],
        hamming: Optional[int],
        date_diff_s: Optional[int],
        link_info: Dict[str, Any],
        xmp_info: Optional[Dict[str, Any]],
        existing_sidecar: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        created_at = None
        if existing_sidecar:
            created_at = existing_sidecar.get("created_at")
        if not created_at:
            created_at = self._now_iso()

        wa_date_str = wa_date.strftime('%Y/%m/%d %H:%M:%S.%f') if wa_date else None
        wa_recipient_label = wa_info.get("recipient_label") if wa_info else None
        wa_recipient_id = wa_info.get("recipient_id") if wa_info else None
        wa_from_me = wa_info.get("from_me") if wa_info else None
        wa_timestamp_ms = wa_info.get("timestamp_ms") if wa_info else None

        data = {
            "schema": SIDECAR_SCHEMA,
            "status": STATUS_LINKED,
            "created_at": created_at,
            "wa": {
                "path": media_file.get_path(),
                "filename": media_file.file_desc.name,
                "media_id": media_file.file_desc.id,
                "signature": self._signature_to_hex(wa_signature),
                "date": wa_date_str,
                "date_source": date_source,
                "sent_at_ms": wa_timestamp_ms,
                "recipient_label": wa_recipient_label,
                "recipient_id": wa_recipient_id,
                "from_me": wa_from_me,
                "camera_model": media_file.metadata[CFM_CAMERA_MODEL].value
            },
            "original": {
                "path": original.get_path(),
                "filename": original.file_desc.name,
                "media_id": original.file_desc.id,
                "system_id": original.file_desc.system_id,
                "signature": self._signature_to_hex(original.metadata[SIGNATURE].value)
            },
            "match": {
                "hamming": hamming,
                "date_diff_s": date_diff_s,
                "threshold": self.similarity_threshold,
                "window_days": self.date_window_days
            },
            "link": link_info
        }
        if xmp_info:
            data["xmp"] = xmp_info
        return data

    @staticmethod
    def _now_iso() -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    @staticmethod
    def _signature_to_hex(signature: Optional[int]) -> Optional[str]:
        if signature is None:
            return None
        return hex(signature)
