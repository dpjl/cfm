import ast
import logging
import os
import re
from argparse import Namespace
from multiprocessing import cpu_count
from pathlib import Path

from camerafile.core.Constants import WHATSAPP_ORIG_LINK_REGEX, WHATSAPP_SIDECAR_REGEX

LOGGER = logging.getLogger(__name__)
PHONE_LIKE_LABEL_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-().]{5,}$")
GROUP_LIKE_LABEL_PATTERN = re.compile(r"^[0-9]{6,}(?:-[0-9]{6,})?$")


class Configuration:
    __instance = None

    def __init__(self):
        self.args = None
        self.cfm_sync_password = None
        self.nb_sub_process = cpu_count()
        self.thumbnails = False
        self.face_detection_keep_image_size = False
        self.use_dump_for_cache = False
        self.save_db = False
        self.exit_on_error = False
        self.org_format = None
        self.debug = False
        self.initialized = False
        self.exif_tool = False
        self.internal_read = True
        self.first_output_directory = None
        self.cache_path = None
        self.ignore_list = None
        self.collision_policy = None
        self.ignore_duplicates = False
        self.watch = False
        self.sync_delay = 60
        self.copy_mode = None
        self.progress = True
        self.pp_script = None
        self.whatsapp = False
        self.whatsapp_date_update = False
        self.whatsapp_sidecar_links = False
        self.whatsapp_db = None
        self.whatsapp_db_name = None
        self.contacts_db_name = None
        self.contacts_name_by_jid = {}
        self.contacts_name_by_number = {}
        self.ui = False

    @staticmethod
    def get() -> "Configuration":
        if Configuration.__instance is None:
            Configuration.__instance = Configuration()
        return Configuration.__instance

    def load(self, key):
        pass
    
    def get_command(self):
        return self.get_param("COMMAND", "command")
        
    def get_dir1(self):
        return self.get_param("DIR1", "dir1")
    
    def get_dir2(self):
        return self.get_param("DIR2", "dir2")

    def get_arg_value(self, arg_name, default_value=None):
        return getattr(self.args, arg_name, default_value)
        
    def get_param(self, env_name, arg_name, default_value=None):
        if os.getenv(env_name) is not None:
            return os.getenv(env_name)
        else:
            return self.get_arg_value(arg_name, default_value)
        
    def get_int_param(self, env_name, arg_name, default_value=None):
        if os.getenv(env_name) is not None:
            return int(os.getenv(env_name))
        else:
            return self.get_arg_value(arg_name, default_value)
        
    def get_bool_param(self, env_name, arg_name, default_value=None):
        if os.getenv(env_name) is not None:
            return os.getenv(env_name).lower() in ["1", "true"]
        else:
            return self.get_arg_value(arg_name, default_value)


    def init(self, args):
        if not self.initialized:
            from camerafile.cfm import ANALYZE_CMD
            from camerafile.cfm import ORGANIZE_CMD
            from camerafile.task.CopyFile import CollisionPolicy


            self.args: Namespace = args

            if args.debug:
                self.debug = True
                logging.getLogger("camerafile").setLevel(logging.DEBUG)

            nb_workers = self.get_int_param("NB_WORKERS", "workers")
            if nb_workers is not None:
                self.nb_sub_process = nb_workers
            
            self.cache_path = self.get_param("CACHE_PATH", "cache_path")
            self.use_dump_for_cache = args.use_dump
            self.save_db = self.get_bool_param("SAVE_DB", "save_db")
            self.exit_on_error = args.exit_on_error
            self.thumbnails = self.get_bool_param("THUMBNAILS", "thumbnails")
            self.ignore_list = args.ignore
            self.ui = self.get_bool_param("UI", "ui")
            self.whatsapp_date_update = self.get_bool_param("WHATSAPP_DATE_UPDATE", "whatsapp_date_update")
            self.whatsapp_sidecar_links = self.get_bool_param("WHATSAPP_SIDECAR_LINKS", "whatsapp_sidecar_links")
            self.whatsapp_db_name = self.get_param("WHATSAPP_DB", "whatsapp_db")
            self.contacts_db_name = self.get_param("CONTACTS_DB", "contacts_db")
            self.whatsapp = self.get_bool_param("WHATSAPP", "whatsapp")
            if self.whatsapp_date_update or self.whatsapp_db_name or self.whatsapp_sidecar_links:
                self.whatsapp = True
            self.load_contacts_db(self.contacts_db_name)
            self.load_whatsapp_db(self.whatsapp_db_name)

            default_ignore_from_env = ast.literal_eval(os.getenv("IGNORE")) if os.getenv("IGNORE") is not None else None
            if self.ignore_list is None:
                self.ignore_list = default_ignore_from_env
            if self.whatsapp_sidecar_links:
                if self.ignore_list is None:
                    self.ignore_list = []
                elif not isinstance(self.ignore_list, list):
                    self.ignore_list = list(self.ignore_list)
                for pattern in (WHATSAPP_ORIG_LINK_REGEX, WHATSAPP_SIDECAR_REGEX):
                    if pattern not in self.ignore_list:
                        self.ignore_list.append(pattern)

            self.progress = self.get_bool_param("PROGRESS", "progress", True)
            if args.no_progress:
                self.progress = False

            # Read this even in analyze mode, because it is used to filter the media list in UI
            self.ignore_duplicates = self.get_bool_param("IGNORE_DUPLICATES", "ignore_duplicates")
            self.org_format = self.get_param("ORG_FORMAT", "format")
            self.collision_policy = CollisionPolicy(self.get_param("COLLISION_POLICY", "collision_policy", CollisionPolicy.RENAME_PARENT))

            if self.get_command() == ANALYZE_CMD:
                self.internal_read = not self.get_bool_param("NO_INTERNAL_READ", "no_internal_read", False)

            if self.get_command() == ORGANIZE_CMD:
                from camerafile.fileaccess.FileAccess import CopyMode
                
                self.copy_mode = CopyMode(self.get_param("MODE", "mode", CopyMode.HARD_LINK))
                self.watch = self.get_bool_param("WATCH", "watch")
                self.pp_script = self.get_param("POST_PROCESSING_SCRIPT", "post_processing_script")

                self.sync_delay = self.get_int_param("SYNC_DELAY", "sync_delay", self.sync_delay)
                
            self.initialized = True

    @staticmethod
    def _clean_label(value):
        if value is None:
            return None
        label = str(value).replace("\u200e", "").strip()
        if not label:
            return None
        return label

    @staticmethod
    def _jid_to_label(raw_jid):
        if raw_jid is None:
            return None
        base = str(raw_jid).split("@", 1)[0]
        base = base.replace("\u200e", "").strip()
        return base if base else None

    @staticmethod
    def _normalize_digits(value):
        if value is None:
            return None
        number = "".join(ch for ch in str(value) if ch.isdigit())
        return number if number else None

    @staticmethod
    def _is_valid_whatsapp_timestamp(timestamp_ms):
        try:
            return timestamp_ms is not None and int(timestamp_ms) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _is_unknown_or_phone_like(label):
        cleaned = Configuration._clean_label(label)
        if cleaned is None:
            return True
        if cleaned.lower() == "unknown":
            return True
        return bool(PHONE_LIKE_LABEL_PATTERN.fullmatch(cleaned) or GROUP_LIKE_LABEL_PATTERN.fullmatch(cleaned))

    def _resolve_contact_label(self, current_label, raw_jid, jid_aliases):
        cleaned_current = self._clean_label(current_label)
        if not self._is_unknown_or_phone_like(cleaned_current):
            return cleaned_current
        clean_raw_jid = self._clean_label(raw_jid)
        if clean_raw_jid is None:
            return cleaned_current

        candidates = [clean_raw_jid]
        mapped_jid = jid_aliases.get(clean_raw_jid)
        if mapped_jid and mapped_jid not in candidates:
            candidates.append(mapped_jid)

        for candidate in candidates:
            clean_candidate = self._clean_label(candidate)
            if clean_candidate is None:
                continue

            contact_name = self.contacts_name_by_jid.get(clean_candidate)
            if contact_name:
                return contact_name

            number = self._normalize_digits(self._jid_to_label(clean_candidate))
            if number is None:
                continue
            contact_name = self.contacts_name_by_number.get(number)
            if contact_name:
                return contact_name

        return cleaned_current

    def load_contacts_db(self, contacts_db):
        self.contacts_name_by_jid = {}
        self.contacts_name_by_number = {}
        if contacts_db is None:
            return

        import sqlite3
        file_connection = None
        try:
            file_connection = sqlite3.connect(contacts_db)
            cursor = file_connection.cursor()

            jid_to_names = {}
            cursor.execute(
                """SELECT
                        data.data1,
                        raw_contacts.display_name
                    FROM
                        data
                    INNER JOIN mimetypes
                        ON mimetypes._id = data.mimetype_id
                    INNER JOIN raw_contacts
                        ON raw_contacts._id = data.raw_contact_id
                    WHERE
                        mimetypes.mimetype = 'vnd.android.cursor.item/vnd.com.whatsapp.profile'
                        AND raw_contacts.deleted = 0"""
            )
            for raw_jid, display_name in cursor:
                clean_jid = self._clean_label(raw_jid)
                clean_name = self._clean_label(display_name)
                if clean_jid is None or clean_name is None:
                    continue
                if clean_jid not in jid_to_names:
                    jid_to_names[clean_jid] = set()
                jid_to_names[clean_jid].add(clean_name)

            raw_contacts = {}
            cursor.execute(
                """SELECT
                        raw_contacts._id,
                        raw_contacts.contact_id,
                        raw_contacts.display_name,
                        contacts.name_raw_contact_id
                    FROM
                        raw_contacts
                    LEFT JOIN contacts
                        ON contacts._id = raw_contacts.contact_id
                    WHERE
                        raw_contacts.deleted = 0"""
            )
            for raw_contact_id, contact_id, display_name, name_raw_contact_id in cursor:
                raw_contacts[raw_contact_id] = {
                    "contact_id": contact_id,
                    "display_name": self._clean_label(display_name),
                    "name_raw_contact_id": name_raw_contact_id
                }

            contact_name_by_id = {}
            for raw_contact_id, raw_contact in raw_contacts.items():
                contact_id = raw_contact["contact_id"]
                if contact_id is None or contact_id in contact_name_by_id:
                    continue
                selected_name = None
                name_raw_contact_id = raw_contact["name_raw_contact_id"]
                if name_raw_contact_id in raw_contacts:
                    selected_name = raw_contacts[name_raw_contact_id]["display_name"]
                if selected_name is None:
                    selected_name = raw_contact["display_name"]
                if selected_name:
                    contact_name_by_id[contact_id] = selected_name

            for raw_contact in raw_contacts.values():
                contact_id = raw_contact["contact_id"]
                if contact_id is None or contact_id in contact_name_by_id:
                    continue
                selected_name = raw_contact["display_name"]
                if selected_name:
                    contact_name_by_id[contact_id] = selected_name

            number_to_names = {}
            cursor.execute("SELECT raw_contact_id, normalized_number FROM phone_lookup")
            for raw_contact_id, normalized_number in cursor:
                raw_contact = raw_contacts.get(raw_contact_id)
                if raw_contact is None:
                    continue
                contact_id = raw_contact["contact_id"]
                if contact_id is None:
                    continue
                contact_name = contact_name_by_id.get(contact_id)
                if contact_name is None:
                    continue
                normalized_digits = self._normalize_digits(normalized_number)
                if normalized_digits is None:
                    continue
                if normalized_digits not in number_to_names:
                    number_to_names[normalized_digits] = set()
                number_to_names[normalized_digits].add(contact_name)

            self.contacts_name_by_jid = {
                key: next(iter(value))
                for key, value in jid_to_names.items()
                if len(value) == 1
            }
            self.contacts_name_by_number = {
                key: next(iter(value))
                for key, value in number_to_names.items()
                if len(value) == 1
            }

            LOGGER.debug(
                "%s: %s WhatsApp JID label(s), %s phone label(s) loaded",
                contacts_db,
                len(self.contacts_name_by_jid),
                len(self.contacts_name_by_number)
            )
        except sqlite3.Error as exc:
            LOGGER.warning("Unable to load contacts db %s: %s", contacts_db, exc)
        finally:
            if file_connection is not None:
                file_connection.close()

    def load_whatsapp_db(self, whatsapp_db):
        if whatsapp_db is not None:
            import sqlite3
            self.whatsapp_db = {}
            file_connection = sqlite3.connect(whatsapp_db)
            cursor = file_connection.cursor()

            def _pick_label(*values):
                for value in values:
                    label = self._clean_label(value)
                    if label:
                        return label
                return None

            try:
                hd_parent_to_child = {}
                hd_child_to_parent = {}
                try:
                    cursor.execute(
                        """SELECT
                                parent_message_row_id,
                                child_message_row_id
                            FROM
                                message_association
                            WHERE
                                association_type IN (12, 7)"""
                    )
                    for parent_message_row_id, child_message_row_id in cursor:
                        if parent_message_row_id is None or child_message_row_id is None:
                            continue
                        hd_parent_to_child[parent_message_row_id] = child_message_row_id
                        hd_child_to_parent[child_message_row_id] = parent_message_row_id
                except sqlite3.Error:
                    hd_parent_to_child = {}
                    hd_child_to_parent = {}

                entries_by_message_row_id = {}
                try:
                    jid_aliases = {}
                    cursor.execute(
                        """SELECT
                                lid_jid.raw_string,
                                phone_jid.raw_string
                            FROM
                                jid_map
                            INNER JOIN jid lid_jid
                                ON lid_jid._id = jid_map.lid_row_id
                            INNER JOIN jid phone_jid
                                ON phone_jid._id = jid_map.jid_row_id"""
                    )
                    for lid_raw_jid, phone_raw_jid in cursor:
                        clean_lid_raw_jid = self._clean_label(lid_raw_jid)
                        clean_phone_raw_jid = self._clean_label(phone_raw_jid)
                        if clean_lid_raw_jid and clean_phone_raw_jid:
                            jid_aliases[clean_lid_raw_jid] = clean_phone_raw_jid
                except sqlite3.Error:
                    jid_aliases = {}

                cursor.execute(
                    """SELECT
                            message_media.media_name,
                            message_media.file_path,
                            message._id,
                            message.timestamp,
                            message.from_me,
                            chat.subject,
                            chat_jid.raw_string,
                            chat_display.display_name,
                            sender_jid.raw_string,
                            sender_display.display_name,
                            message_media.media_transcode_quality
                        FROM
                            message_media
                        INNER JOIN message
                            ON message._id = message_media.message_row_id
                        LEFT JOIN chat
                            ON chat._id = message.chat_row_id
                        LEFT JOIN jid chat_jid
                            ON chat_jid._id = chat.jid_row_id
                        LEFT JOIN jid_map chat_jid_map
                            ON chat_jid_map.jid_row_id = chat_jid._id
                        LEFT JOIN lid_display_name chat_display
                            ON chat_display.lid_row_id = chat_jid_map.lid_row_id
                        LEFT JOIN jid sender_jid
                            ON sender_jid._id = message.sender_jid_row_id
                        LEFT JOIN jid_map sender_jid_map
                            ON sender_jid_map.jid_row_id = sender_jid._id
                        LEFT JOIN lid_display_name sender_display
                            ON sender_display.lid_row_id = sender_jid_map.lid_row_id
                        WHERE
                            message_media.media_name IS NOT NULL
                            OR message_media.file_path IS NOT NULL"""
                )
                for (media_name, file_path, message_row_id, timestamp, from_me, subject, chat_raw_jid, chat_display_name,
                     sender_raw_jid, sender_display_name, media_transcode_quality) in cursor:
                    name = None
                    if file_path:
                        name = Path(file_path).name or None
                    if not name and media_name:
                        name = Path(media_name).name or None
                    if name is None:
                        continue

                    has_hd_duplicate = message_row_id in hd_parent_to_child
                    hd_parent_row_id = hd_child_to_parent.get(message_row_id)
                    hd_child_row_id = hd_parent_to_child.get(message_row_id)
                    is_hd = media_transcode_quality == 4 or hd_parent_row_id is not None
                    if is_hd:
                        wa_quality_kind = "HD"
                    elif media_transcode_quality == 3:
                        wa_quality_kind = "Reduit"
                    else:
                        wa_quality_kind = None

                    hd_peer_message_row_id = hd_child_row_id if hd_child_row_id is not None else hd_parent_row_id

                    is_sent = bool(from_me) if from_me is not None else False
                    chat_label = _pick_label(subject, chat_display_name, self._jid_to_label(chat_raw_jid))
                    sender_label = _pick_label(sender_display_name, self._jid_to_label(sender_raw_jid))
                    chat_label = self._resolve_contact_label(chat_label, chat_raw_jid, jid_aliases)
                    sender_label = self._resolve_contact_label(sender_label, sender_raw_jid, jid_aliases)

                    direction = "Env" if is_sent else "Rec"
                    if is_sent:
                        party_label = chat_label or "unknown"
                        party_id = chat_raw_jid
                    else:
                        party_label = sender_label or chat_label or "unknown"
                        party_id = sender_raw_jid or chat_raw_jid

                    new_entry = {
                        "filename": name,
                        "timestamp_ms": timestamp,
                        "from_me": from_me,
                        "direction": direction,
                        "party_label": party_label,
                        "party_id": party_id,
                        "recipient_label": chat_label or "unknown",
                        "recipient_id": chat_raw_jid,
                        "sender_label": (sender_label or chat_label or "unknown") if not is_sent else "unknown",
                        "sender_id": (sender_raw_jid or chat_raw_jid) if not is_sent else None,
                        "message_row_id": message_row_id,
                        "wa_quality_kind": wa_quality_kind,
                        "media_transcode_quality": media_transcode_quality,
                        "has_hd_duplicate": has_hd_duplicate,
                        "hd_peer_message_row_id": hd_peer_message_row_id,
                        "hd_peer_filename": None
                    }
                    existing_entry = self.whatsapp_db.get(name)
                    if (
                            existing_entry is not None
                            and self._is_valid_whatsapp_timestamp(existing_entry.get("timestamp_ms"))
                            and not self._is_valid_whatsapp_timestamp(timestamp)
                    ):
                        selected_entry = existing_entry
                    else:
                        self.whatsapp_db[name] = new_entry
                        selected_entry = self.whatsapp_db[name]

                    entries_by_message_row_id[message_row_id] = selected_entry

                for entry in entries_by_message_row_id.values():
                    hd_peer_message_row_id = entry.get("hd_peer_message_row_id")
                    if hd_peer_message_row_id is None:
                        continue
                    peer_entry = entries_by_message_row_id.get(hd_peer_message_row_id)
                    if peer_entry is None:
                        continue
                    entry["hd_peer_filename"] = peer_entry.get("filename")
            except sqlite3.Error:
                cursor.execute("""SELECT 
                                    message_media.file_path, available_message_view.timestamp
                                FROM
                                    available_message_view INNER JOIN message_media
                                ON
                                    available_message_view._id = message_media.message_row_id""")
                for (file_path, timestamp) in cursor:
                    if file_path is not None:
                        direction = "Env" if "/Sent/" in file_path else "Rec"
                        name = Path(file_path).name
                        new_entry = {
                            "filename": name,
                            "timestamp_ms": timestamp,
                            "from_me": 1 if direction == "Env" else 0,
                            "direction": direction,
                            "party_label": "unknown",
                            "party_id": None,
                            "recipient_label": "unknown",
                            "recipient_id": None,
                            "sender_label": "unknown",
                            "sender_id": None,
                            "message_row_id": None,
                            "wa_quality_kind": None,
                            "media_transcode_quality": None,
                            "has_hd_duplicate": False,
                            "hd_peer_message_row_id": None,
                            "hd_peer_filename": None
                        }
                        existing_entry = self.whatsapp_db.get(name)
                        if (
                                existing_entry is None
                                or not self._is_valid_whatsapp_timestamp(existing_entry.get("timestamp_ms"))
                                or self._is_valid_whatsapp_timestamp(timestamp)
                        ):
                            self.whatsapp_db[name] = new_entry
            finally:
                file_connection.close()
            LOGGER.debug("%s: %s media loaded", whatsapp_db, len(self.whatsapp_db))
