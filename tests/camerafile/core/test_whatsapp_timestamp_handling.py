import sqlite3
from datetime import datetime
from pathlib import Path

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.fileaccess.FileDescription import FileDescription


def _create_msgstore_with_duplicate_filename(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        "CREATE TABLE message_association (parent_message_row_id INTEGER, child_message_row_id INTEGER, association_type INTEGER)"
    )
    cur.execute("CREATE TABLE jid (_id INTEGER PRIMARY KEY, raw_string TEXT)")
    cur.execute("CREATE TABLE jid_map (lid_row_id INTEGER, jid_row_id INTEGER)")
    cur.execute("CREATE TABLE lid_display_name (lid_row_id INTEGER, display_name TEXT)")
    cur.execute("CREATE TABLE chat (_id INTEGER PRIMARY KEY, jid_row_id INTEGER, subject TEXT)")
    cur.execute(
        "CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER, sender_jid_row_id INTEGER, received_timestamp INTEGER, from_me INTEGER)"
    )
    cur.execute(
        "CREATE TABLE message_media (message_row_id INTEGER PRIMARY KEY, media_name TEXT, file_path TEXT, media_transcode_quality INTEGER)"
    )

    cur.execute("INSERT INTO jid (_id, raw_string) VALUES (1, '123@s.whatsapp.net')")
    cur.execute("INSERT INTO chat (_id, jid_row_id, subject) VALUES (1, 1, 'Test chat')")
    cur.execute(
        "INSERT INTO message (_id, chat_row_id, sender_jid_row_id, received_timestamp, from_me) VALUES (1, 1, 1, 1757773143644, 0)"
    )
    cur.execute(
        "INSERT INTO message (_id, chat_row_id, sender_jid_row_id, received_timestamp, from_me) VALUES (2, 1, 1, 0, 1)"
    )
    cur.execute(
        "INSERT INTO message_media (message_row_id, media_name, file_path, media_transcode_quality) VALUES (1, NULL, 'Media/WhatsApp Images/IMG-20250913-WA0028.jpg', 0)"
    )
    cur.execute(
        "INSERT INTO message_media (message_row_id, media_name, file_path, media_transcode_quality) VALUES (2, NULL, 'Media/WhatsApp Images/IMG-20250913-WA0028.jpg', 0)"
    )

    conn.commit()
    conn.close()


def test_load_whatsapp_db_does_not_overwrite_valid_timestamp_with_zero(tmp_path):
    db_path = tmp_path / "msgstore.db"
    _create_msgstore_with_duplicate_filename(db_path)

    conf = Configuration()
    conf.load_whatsapp_db(str(db_path))

    entry = conf.whatsapp_db["IMG-20250913-WA0028.jpg"]
    assert entry["timestamp_ms"] == 1757773143644


def test_read_whatsapp_info_ignores_zero_timestamp_and_falls_back_to_filename(monkeypatch):
    class DummyConfig:
        whatsapp = True
        whatsapp_db = {"IMG-20250913-WA0028.jpg": {"timestamp_ms": 0}}

    class DummyFileAccess(FileAccess):
        def get_last_modification_date(self):
            return datetime(1970, 1, 1)

    file_desc = FileDescription("WhatsApp Images/IMG-20250913-WA0028.jpg")
    file_access = DummyFileAccess("/tmp", file_desc)
    monkeypatch.setattr(Configuration, "get", staticmethod(lambda: DummyConfig()))

    wa_date, wa_label = file_access.read_whatsapp_info()

    assert wa_date == datetime(2025, 9, 13)
    assert wa_label == "WhatsApp"
