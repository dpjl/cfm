import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from camerafile.core.Configuration import Configuration
from camerafile.core.Constants import CFM_CAMERA_MODEL, SIGNATURE, IMAGE_TYPE, MANAGED_TYPE, WHATSAPP_SIDECAR_SUFFIX, \
    WHATSAPP_ORIG_LINK_SUFFIX
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.fileaccess.StandardFileDescription import StandardFileDescription
from camerafile.mdtools.XmpTool import XmpTool
from camerafile.processor.BatchTool import BatchElement, TaskWithProgression

LOGGER = Logger(__name__)

# Default values
DEFAULT_DATE_WINDOW_DAYS = 30
DEFAULT_SIMILARITY_THRESHOLD = 10
SIDECAR_SCHEMA = "cfm-wa-link-v4"
DEFAULT_PARTY_LABEL_DB = "unknown"
DEFAULT_PARTY_LABEL_TAG = "Inconnu"
WHATSAPP_TAG_PREFIX = "WA"
TAG_SENT = "Env"
TAG_RECEIVED = "Rec"
TAG_ORIGINAL = "Orig"
TAG_REDUCED = "Reduit"
TAG_HD = "HD"
DUPLICATE_REDUCED_HD_TAG = "WA_ReduitDupliqueHD"
FRENCH_MONTH_NAMES = (
    "Janvier",
    "Fevrier",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Aout",
    "Septembre",
    "Octobre",
    "Novembre",
    "Decembre"
)
XMP_SUFFIX = ".xmp"
WHATSAPP_DATE_PATTERN = re.compile(r'^(?:VID|IMG)-([0-9]{8})-WA[0-9]{4}\.[^.]+$', re.IGNORECASE)
STATUS_LINKED = "linked"
STATUS_REDUCED = "reduced"
STATUS_REJECTED = "rejected"


class BatchFindWhatsAppOriginalsSidecar(TaskWithProgression):
    """
    Finds originals for WhatsApp media by comparing signatures for images.
    Instead of writing metadata, writes a JSON sidecar and creates a link to the original.
    """

    def __init__(self, media_set: MediaSet, date_window_days: int = DEFAULT_DATE_WINDOW_DAYS,
                 similarity_threshold: int = DEFAULT_SIMILARITY_THRESHOLD):
        self.media_set = media_set
        self.date_window_days = date_window_days
        self.similarity_threshold = similarity_threshold
        self.whatsapp_files: List[MediaFile] = []
        self.matches_found = 0
        self.reduced_tagged = 0
        self.links_created = 0
        self.skipped_rejected = 0
        self.skipped_existing = 0
        TaskWithProgression.__init__(
            self,
            batch_title="Find WhatsApp originals (sidecar)",
            nb_sub_process=0
        )

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

        self.whatsapp_files = self._get_whatsapp_files()
        if not self.whatsapp_files:
            LOGGER.info("No WhatsApp media files found")
            return
        self._compute_whatsapp_signatures()

    @staticmethod
    def _is_whatsapp_file(media_file: MediaFile) -> bool:
        camera_model = media_file.metadata[CFM_CAMERA_MODEL].value
        return camera_model in ["WhatsApp", "WhatsApp-sent"]

    @staticmethod
    def _is_searchable_for_original(media_file: MediaFile) -> bool:
        return media_file.file_desc.extension in IMAGE_TYPE

    def _get_whatsapp_candidates(self) -> List[MediaFile]:
        result = []
        for media_file in self.media_set.media_file_list:
            if not isinstance(media_file.file_desc, StandardFileDescription):
                continue
            if media_file.file_desc.extension not in MANAGED_TYPE:
                continue
            if not self._is_whatsapp_file(media_file):
                continue
            result.append(media_file)
        LOGGER.info(f"WhatsApp candidate files: {len(result)}")
        return result

    def _get_whatsapp_files(self) -> List[MediaFile]:
        result = []
        for media_file in self._get_whatsapp_candidates():
            sidecar_data = self._read_sidecar(media_file)
            if sidecar_data and sidecar_data.get("status") == STATUS_REJECTED:
                self._remove_xmp_for_rejected(media_file, sidecar_data)
                self.skipped_rejected += 1
                continue
            result.append(media_file)
        return result

    def compute_required_date_range(self) -> Optional[Tuple[datetime, datetime]]:
        candidates = self._get_whatsapp_candidates()
        if not candidates:
            return None
        eligible = []
        for media_file in candidates:
            if not self._is_searchable_for_original(media_file):
                continue
            sidecar_data = self._read_sidecar(media_file)
            if sidecar_data and sidecar_data.get("status") == STATUS_REJECTED:
                continue
            eligible.append(media_file)
        return self._compute_required_date_range(eligible)

    @staticmethod
    def _extract_whatsapp_date(media_file: MediaFile) -> Optional[datetime]:
        match = WHATSAPP_DATE_PATTERN.match(media_file.file_desc.name)
        if match:
            date_str = match.group(1)
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
                "filename": media_file.file_desc.name,
                "timestamp_ms": entry,
                "from_me": None,
                "direction": None,
                "party_label": DEFAULT_PARTY_LABEL_DB,
                "party_id": None,
                "recipient_label": DEFAULT_PARTY_LABEL_DB,
                "recipient_id": None,
                "sender_label": DEFAULT_PARTY_LABEL_DB,
                "sender_id": None,
                "message_row_id": None,
                "wa_quality_kind": None,
                "media_transcode_quality": None,
                "has_hd_duplicate": False,
                "hd_peer_message_row_id": None,
                "hd_peer_filename": None
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
            media_files = self.whatsapp_files
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
        for media_file in self.whatsapp_files:
            if not self._is_searchable_for_original(media_file):
                continue
            if media_file.metadata[SIGNATURE].value is None:
                try:
                    file_access = FileAccessFactory.get(media_file.parent_set.root_path, media_file.file_desc)
                    media_file.metadata[SIGNATURE].value = file_access.hash()
                except Exception as e:
                    LOGGER.debug(f"Failed to compute signature for {media_file.get_path()}: {e}")

    def task_getter(self):
        return self._find_original

    def arguments(self) -> List[BatchElement]:
        return [BatchElement(media_file, media_file.get_path()) for media_file in self.whatsapp_files]

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
        if sidecar_data and sidecar_data.get("status") == STATUS_REDUCED:
            if self._ensure_xmp_from_sidecar(media_file, sidecar_data):
                batch_element.result = {"status": "skipped_existing", "media_file": media_file}
                return batch_element

        date_info = self._get_whatsapp_date_info(media_file)
        if date_info is None:
            batch_element.result = {"status": "skipped_no_date", "media_file": media_file}
            return batch_element

        wa_date, date_source, date_start, date_end, wa_entry = date_info
        wa_info = self._build_wa_info(media_file, wa_entry)
        wa_info["date_source"] = date_source
        wa_info["timestamp_ms"] = wa_entry.get("timestamp_ms") if wa_entry else None

        # Only image signatures are comparable with current matching strategy.
        if not self._is_searchable_for_original(media_file):
            batch_element.result = {
                "status": STATUS_REDUCED,
                "media_file": media_file,
                "wa_date": wa_date,
                "wa_info": wa_info,
                "sidecar": sidecar_data
            }
            return batch_element

        signature = media_file.metadata[SIGNATURE].value
        if signature is None:
            batch_element.result = {
                "status": STATUS_REDUCED,
                "media_file": media_file,
                "wa_date": wa_date,
                "wa_info": wa_info,
                "wa_signature": None,
                "sidecar": sidecar_data
            }
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
            batch_element.result = {
                "status": STATUS_REDUCED,
                "media_file": media_file,
                "wa_date": wa_date,
                "wa_info": wa_info,
                "wa_signature": signature,
                "sidecar": sidecar_data
            }
            return batch_element

        batch_element.result = {
            "status": STATUS_LINKED,
            "media_file": media_file,
            "original": best_match,
            "wa_date": wa_date,
            "date_source": date_source,
            "wa_info": wa_info,
            "wa_signature": signature,
            "hamming": best_hamming,
            "date_diff_s": int(best_date_diff) if best_date_diff is not None else None,
            "sidecar": sidecar_data
        }
        return batch_element

    def post_task(self, result, progress_bar, replace=False):
        status = result.get("status")
        media_file = result.get("media_file")

        if status == STATUS_LINKED:
            original = result.get("original")
            link_info = self._create_link_for_match(media_file, original)
            xmp_info = self._create_xmp_for_media(
                target_media=original,
                wa_date=result.get("wa_date"),
                wa_info=result.get("wa_info"),
                tag_kind=TAG_ORIGINAL
            )
            sidecar_data = self._build_sidecar_data(
                status=STATUS_LINKED,
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
        elif status == STATUS_REDUCED:
            reduced_tag_kind = self._reduced_tag_kind(result.get("wa_info"))
            extra_tags = self._build_extra_xmp_tags(reduced_tag_kind, result.get("wa_info"))
            xmp_info = self._create_xmp_for_media(
                target_media=media_file,
                wa_date=result.get("wa_date"),
                wa_info=result.get("wa_info"),
                tag_kind=reduced_tag_kind,
                extra_tags=extra_tags
            )
            sidecar_data = self._build_sidecar_data(
                status=STATUS_REDUCED,
                media_file=media_file,
                original=None,
                wa_date=result.get("wa_date"),
                date_source=result.get("wa_info", {}).get("date_source"),
                wa_info=result.get("wa_info"),
                wa_signature=result.get("wa_signature"),
                hamming=None,
                date_diff_s=None,
                link_info=None,
                xmp_info=xmp_info,
                existing_sidecar=result.get("sidecar")
            )
            self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)
            self.reduced_tagged += 1
        elif status == "skipped_rejected":
            self.skipped_rejected += 1
        elif status == "skipped_existing":
            self.skipped_existing += 1
        elif status == "skipped_no_date":
            LOGGER.debug(f"Skipping WhatsApp file without valid date: {media_file.get_path()}")

        progress_bar.increment()

    def finalize(self):
        LOGGER.info(
            f"Found {self.matches_found} WhatsApp files with matching originals, "
            f"{self.reduced_tagged} tagged as reduced "
            f"({self.links_created} link(s) created, {self.skipped_existing} reused, "
            f"{self.skipped_rejected} rejected)"
        )

    def display_final_status(self, progress_bar):
        print(
            f"{progress_bar.position} WhatsApp files processed, "
            f"{self.matches_found} originals found, {self.reduced_tagged} reduced in {progress_bar.processing_time}"
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
    def _sanitize_party_label(label: Optional[str]) -> str:
        if not label:
            return DEFAULT_PARTY_LABEL_TAG
        sanitized = label.strip()
        sanitized = re.sub(r"[\\/|]+", "_", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized)
        sanitized = sanitized.replace("\u200e", "").strip()
        if not sanitized:
            return DEFAULT_PARTY_LABEL_TAG
        if sanitized.lower() == DEFAULT_PARTY_LABEL_DB:
            return DEFAULT_PARTY_LABEL_TAG
        return sanitized

    @staticmethod
    def _compute_direction(media_file: Optional[MediaFile], wa_info: Optional[Dict[str, Any]]) -> str:
        if wa_info:
            direction = wa_info.get("direction")
            if direction in (TAG_SENT, TAG_RECEIVED):
                return direction
            from_me = wa_info.get("from_me")
            if from_me in (1, True):
                return TAG_SENT
            if from_me in (0, False):
                return TAG_RECEIVED
        if media_file and media_file.metadata[CFM_CAMERA_MODEL].value == "WhatsApp-sent":
            return TAG_SENT
        return TAG_RECEIVED

    def _build_wa_info(self, media_file: MediaFile, wa_entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        wa_info = dict(wa_entry) if wa_entry else {}
        wa_info["direction"] = self._compute_direction(media_file, wa_entry)
        party_label = wa_info.get("party_label")
        party_id = wa_info.get("party_id")
        if not party_label:
            if wa_info["direction"] == TAG_SENT:
                party_label = wa_info.get("recipient_label")
                party_id = party_id or wa_info.get("recipient_id")
            else:
                party_label = wa_info.get("sender_label")
                party_id = party_id or wa_info.get("sender_id")
        if not party_label:
            party_label = DEFAULT_PARTY_LABEL_DB
        wa_info["party_id"] = party_id
        wa_info["party_label"] = party_label
        if wa_info.get("wa_quality_kind") is None:
            quality_value = wa_info.get("media_transcode_quality")
            if quality_value == 4:
                wa_info["wa_quality_kind"] = TAG_HD
            elif quality_value == 3:
                wa_info["wa_quality_kind"] = TAG_REDUCED
        if wa_info.get("has_hd_duplicate") is not None:
            wa_info["has_hd_duplicate"] = bool(wa_info.get("has_hd_duplicate"))
        return wa_info

    @staticmethod
    def _reduced_tag_kind(wa_info: Optional[Dict[str, Any]]) -> str:
        if wa_info and wa_info.get("wa_quality_kind") == TAG_HD:
            return TAG_HD
        return TAG_REDUCED

    @staticmethod
    def _build_extra_xmp_tags(tag_kind: str, wa_info: Optional[Dict[str, Any]]) -> List[str]:
        if tag_kind != TAG_REDUCED:
            return []
        if wa_info and bool(wa_info.get("has_hd_duplicate")):
            return [DUPLICATE_REDUCED_HD_TAG]
        return []

    def _build_whatsapp_tag(
        self,
        wa_date: Optional[datetime],
        wa_info: Optional[Dict[str, Any]],
        tag_kind: str
    ) -> Optional[str]:
        if wa_date is None:
            return None
        year_str = wa_date.strftime("%Y")
        month_str = f"{wa_date.strftime('%m')}-{FRENCH_MONTH_NAMES[wa_date.month - 1]}"
        day_str = wa_date.strftime("%d")
        direction = self._compute_direction(None, wa_info)
        party = self._sanitize_party_label(wa_info.get("party_label") if wa_info else None)
        return f"{WHATSAPP_TAG_PREFIX}/{year_str}/{month_str}/{day_str}/{direction}/{party}/{tag_kind}"

    @staticmethod
    def _is_unknown_party(label: Optional[str]) -> bool:
        if label is None:
            return True
        normalized = label.strip().replace("\u200e", "")
        return normalized.lower() in {DEFAULT_PARTY_LABEL_DB, DEFAULT_PARTY_LABEL_TAG.lower()}

    @staticmethod
    def _is_unknown_tag(tag: Optional[str]) -> bool:
        if not tag:
            return True
        return f"/{DEFAULT_PARTY_LABEL_TAG.lower()}/" in tag.strip().lower()

    @staticmethod
    def _get_xmp_path(original_abs: Path) -> Path:
        return original_abs.with_name(original_abs.name + XMP_SUFFIX)

    def _create_xmp_for_media(
        self,
        target_media: MediaFile,
        wa_date: Optional[datetime],
        wa_info: Optional[Dict[str, Any]],
        tag_kind: str,
        extra_tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        main_tag = self._build_whatsapp_tag(wa_date=wa_date, wa_info=wa_info, tag_kind=tag_kind)
        if not main_tag:
            return None

        tags_to_ensure = [main_tag]
        if extra_tags:
            for extra_tag in extra_tags:
                if extra_tag and extra_tag not in tags_to_ensure:
                    tags_to_ensure.append(extra_tag)

        target_abs = Path(self.media_set.root_path) / target_media.file_desc.relative_path
        xmp_abs = self._get_xmp_path(target_abs)
        existing_tags = set(XmpTool.read_digikam_tags(xmp_abs))
        for tag_to_ensure in tags_to_ensure:
            if tag_to_ensure in existing_tags:
                continue
            if not XmpTool.ensure_digikam_tag(target_abs, xmp_abs, tag_to_ensure):
                return None
            existing_tags.add(tag_to_ensure)

        xmp_rel = os.path.relpath(xmp_abs, self.media_set.root_path)
        return {"path": xmp_rel, "tag": main_tag, "tags": tags_to_ensure, "kind": tag_kind}

    def _build_tag_from_sidecar(
        self, media_file: MediaFile, sidecar_data: Dict[str, Any], tag_kind: str
    ) -> Optional[str]:
        wa_data = sidecar_data.get("wa", {})
        wa_info = self._build_wa_info(media_file, wa_data)
        wa_date = self._get_tag_date(media_file, sidecar_data)
        return self._build_whatsapp_tag(wa_date=wa_date, wa_info=wa_info, tag_kind=tag_kind)

    def _get_tag_date(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> Optional[datetime]:
        wa_data = sidecar_data.get("wa", {})
        wa_date = self._parse_wa_date(wa_data.get("date"))
        if wa_date is None:
            date_info = self._get_whatsapp_date_info(media_file)
            if date_info is not None:
                wa_date = date_info[0]
        return wa_date

    def _get_upgrade_tag_and_entry(
        self, media_file: MediaFile, sidecar_data: Dict[str, Any], tag_kind: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        wa_data = sidecar_data.get("wa", {})
        if not self._is_unknown_party(wa_data.get("party_label")):
            return None, None

        wa_entry = self._get_whatsapp_db_entry(media_file)
        if not wa_entry:
            return None, None
        wa_info = self._build_wa_info(media_file, wa_entry)

        party_label = wa_info.get("party_label")
        if self._is_unknown_party(party_label):
            return None, None

        wa_date = self._get_tag_date(media_file, sidecar_data)
        if wa_date is None:
            return None, None

        return self._build_whatsapp_tag(wa_date=wa_date, wa_info=wa_info, tag_kind=tag_kind), wa_info

    @staticmethod
    def _apply_wa_upgrade(sidecar_data: Dict[str, Any], wa_entry: Dict[str, Any]) -> None:
        wa_data = sidecar_data.get("wa", {})
        wa_data["party_label"] = wa_entry.get("party_label")
        wa_data["direction"] = wa_entry.get("direction")
        if wa_data.get("party_id") is None:
            wa_data["party_id"] = wa_entry.get("party_id")
        if wa_data.get("from_me") is None:
            wa_data["from_me"] = wa_entry.get("from_me")
        if wa_data.get("sent_at_ms") is None:
            wa_data["sent_at_ms"] = wa_entry.get("timestamp_ms")
        if wa_data.get("recipient_label") is None:
            wa_data["recipient_label"] = wa_entry.get("recipient_label")
        if wa_data.get("recipient_id") is None:
            wa_data["recipient_id"] = wa_entry.get("recipient_id")
        if wa_data.get("sender_label") is None:
            wa_data["sender_label"] = wa_entry.get("sender_label")
        if wa_data.get("sender_id") is None:
            wa_data["sender_id"] = wa_entry.get("sender_id")
        if wa_data.get("message_row_id") is None:
            wa_data["message_row_id"] = wa_entry.get("message_row_id")
        if wa_data.get("wa_quality_kind") is None:
            wa_data["wa_quality_kind"] = wa_entry.get("wa_quality_kind")
        if wa_data.get("media_transcode_quality") is None:
            wa_data["media_transcode_quality"] = wa_entry.get("media_transcode_quality")
        if not wa_data.get("has_hd_duplicate"):
            wa_data["has_hd_duplicate"] = bool(wa_entry.get("has_hd_duplicate"))
        if wa_data.get("hd_peer_message_row_id") is None:
            wa_data["hd_peer_message_row_id"] = wa_entry.get("hd_peer_message_row_id")
        if wa_data.get("hd_peer_filename") is None:
            wa_data["hd_peer_filename"] = wa_entry.get("hd_peer_filename")
        sidecar_data["wa"] = wa_data

    def _get_xmp_path_from_sidecar(self, sidecar_data: Dict[str, Any], original_abs: Path) -> Path:
        xmp_rel = sidecar_data.get("xmp", {}).get("path")
        if xmp_rel:
            return Path(self.media_set.root_path) / xmp_rel
        return self._get_xmp_path(original_abs)

    @staticmethod
    def _tag_kind_from_sidecar(sidecar_data: Dict[str, Any]) -> str:
        status = sidecar_data.get("status")
        if status == STATUS_LINKED:
            return TAG_ORIGINAL
        wa_data = sidecar_data.get("wa", {})
        return TAG_HD if wa_data.get("wa_quality_kind") == TAG_HD else TAG_REDUCED

    def _get_xmp_target_path(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> Optional[Path]:
        status = sidecar_data.get("status")
        if status == STATUS_LINKED:
            original_rel = sidecar_data.get("original", {}).get("path")
            if not original_rel:
                return None
            return Path(self.media_set.root_path) / original_rel
        return Path(self.media_set.root_path) / media_file.file_desc.relative_path

    def _ensure_xmp_from_sidecar(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> bool:
        target_abs = self._get_xmp_target_path(media_file, sidecar_data)
        if target_abs is None:
            return False
        if not target_abs.exists():
            return False

        xmp_abs = self._get_xmp_path_from_sidecar(sidecar_data, target_abs)
        tag_kind = self._tag_kind_from_sidecar(sidecar_data)
        extra_tags = self._build_extra_xmp_tags(tag_kind, sidecar_data.get("wa", {}))
        current_tag = sidecar_data.get("xmp", {}).get("tag")
        upgrade_tag, upgrade_entry = self._get_upgrade_tag_and_entry(media_file, sidecar_data, tag_kind)
        tags = set(XmpTool.read_digikam_tags(xmp_abs))

        if upgrade_tag and self._is_unknown_tag(current_tag):
            if not xmp_abs.exists():
                if not XmpTool.ensure_digikam_tag(target_abs, xmp_abs, upgrade_tag):
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
            full_tags = [upgrade_tag]
            for extra_tag in extra_tags:
                if extra_tag and extra_tag not in full_tags:
                    full_tags.append(extra_tag)
            sidecar_data["xmp"] = {
                "path": os.path.relpath(xmp_abs, self.media_set.root_path),
                "tag": upgrade_tag,
                "tags": full_tags,
                "kind": tag_kind
            }
            self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)
            current_tag = upgrade_tag
            tags = set(XmpTool.read_digikam_tags(xmp_abs))

        if not current_tag:
            current_tag = self._build_tag_from_sidecar(media_file, sidecar_data, tag_kind)
            if current_tag:
                full_tags = [current_tag]
                for extra_tag in extra_tags:
                    if extra_tag and extra_tag not in full_tags:
                        full_tags.append(extra_tag)
                sidecar_data["xmp"] = {
                    "path": os.path.relpath(xmp_abs, self.media_set.root_path),
                    "tag": current_tag,
                    "tags": full_tags,
                    "kind": tag_kind
                }
                self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)

        if not current_tag:
            return False

        desired_tags = [current_tag]
        for extra_tag in extra_tags:
            if extra_tag and extra_tag not in desired_tags:
                desired_tags.append(extra_tag)

        if not xmp_abs.exists():
            for desired_tag in desired_tags:
                if not XmpTool.ensure_digikam_tag(target_abs, xmp_abs, desired_tag):
                    return False
            return True

        for desired_tag in desired_tags:
            if desired_tag in tags:
                continue
            if not XmpTool.add_digikam_tag(xmp_abs, desired_tag):
                return False
            tags.add(desired_tag)

        xmp_updated = sidecar_data.get("xmp", {})
        if xmp_updated.get("tag") != current_tag or xmp_updated.get("tags") != desired_tags or xmp_updated.get("kind") != tag_kind:
            sidecar_data["xmp"] = {
                "path": os.path.relpath(xmp_abs, self.media_set.root_path),
                "tag": current_tag,
                "tags": desired_tags,
                "kind": tag_kind
            }
            self._write_sidecar(self._get_sidecar_path(media_file), sidecar_data)

        return True

    def _remove_xmp_for_rejected(self, media_file: MediaFile, sidecar_data: Dict[str, Any]) -> None:
        xmp_rel = sidecar_data.get("xmp", {}).get("path")
        if xmp_rel:
            xmp_abs = Path(self.media_set.root_path) / xmp_rel
        else:
            target_abs = self._get_xmp_target_path(media_file, sidecar_data)
            if target_abs is None:
                return
            xmp_abs = self._get_xmp_path(target_abs)
        if not xmp_abs.exists():
            return
        try:
            xmp_abs.unlink()
        except Exception as exc:
            LOGGER.info(f"Failed to remove XMP {xmp_abs}: {exc}")

    def _build_sidecar_data(
        self,
        status: str,
        media_file: MediaFile,
        original: Optional[MediaFile],
        wa_date: Optional[datetime],
        date_source: Optional[str],
        wa_info: Optional[Dict[str, Any]],
        wa_signature: Optional[int],
        hamming: Optional[int],
        date_diff_s: Optional[int],
        link_info: Optional[Dict[str, Any]],
        xmp_info: Optional[Dict[str, Any]],
        existing_sidecar: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        created_at = None
        if existing_sidecar:
            created_at = existing_sidecar.get("created_at")
        if not created_at:
            created_at = self._now_iso()

        wa_date_str = wa_date.strftime('%Y/%m/%d %H:%M:%S.%f') if wa_date else None
        wa_direction = wa_info.get("direction") if wa_info else self._compute_direction(media_file, None)
        wa_party_label = wa_info.get("party_label") if wa_info else DEFAULT_PARTY_LABEL_DB
        wa_party_id = wa_info.get("party_id") if wa_info else None
        wa_recipient_label = wa_info.get("recipient_label") if wa_info else None
        wa_recipient_id = wa_info.get("recipient_id") if wa_info else None
        wa_sender_label = wa_info.get("sender_label") if wa_info else None
        wa_sender_id = wa_info.get("sender_id") if wa_info else None
        wa_from_me = wa_info.get("from_me") if wa_info else None
        wa_timestamp_ms = wa_info.get("timestamp_ms") if wa_info else None
        wa_message_row_id = wa_info.get("message_row_id") if wa_info else None
        wa_quality_kind = wa_info.get("wa_quality_kind") if wa_info else None
        wa_media_transcode_quality = wa_info.get("media_transcode_quality") if wa_info else None
        wa_has_hd_duplicate = bool(wa_info.get("has_hd_duplicate")) if wa_info else False
        wa_hd_peer_message_row_id = wa_info.get("hd_peer_message_row_id") if wa_info else None
        wa_hd_peer_filename = wa_info.get("hd_peer_filename") if wa_info else None

        data = {
            "schema": SIDECAR_SCHEMA,
            "status": status,
            "created_at": created_at,
            "wa": {
                "path": media_file.get_path(),
                "filename": media_file.file_desc.name,
                "media_id": media_file.file_desc.id,
                "signature": self._signature_to_hex(wa_signature),
                "date": wa_date_str,
                "date_source": date_source,
                "sent_at_ms": wa_timestamp_ms,
                "direction": wa_direction,
                "party_label": wa_party_label,
                "party_id": wa_party_id,
                "recipient_label": wa_recipient_label,
                "recipient_id": wa_recipient_id,
                "sender_label": wa_sender_label,
                "sender_id": wa_sender_id,
                "from_me": wa_from_me,
                "message_row_id": wa_message_row_id,
                "wa_quality_kind": wa_quality_kind,
                "media_transcode_quality": wa_media_transcode_quality,
                "has_hd_duplicate": wa_has_hd_duplicate,
                "hd_peer_message_row_id": wa_hd_peer_message_row_id,
                "hd_peer_filename": wa_hd_peer_filename,
                "camera_model": media_file.metadata[CFM_CAMERA_MODEL].value
            }
        }
        if original is not None:
            data["original"] = {
                "path": original.get_path(),
                "filename": original.file_desc.name,
                "media_id": original.file_desc.id,
                "system_id": original.file_desc.system_id,
                "signature": self._signature_to_hex(original.metadata[SIGNATURE].value)
            }
            data["match"] = {
                "hamming": hamming,
                "date_diff_s": date_diff_s,
                "threshold": self.similarity_threshold,
                "window_days": self.date_window_days
            }
        if link_info is not None:
            data["link"] = link_info
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
