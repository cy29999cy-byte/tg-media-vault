"""Tests for TG Media Vault SQLite persistence."""

from tg_media_vault.models import DownloadRecord
from tg_media_vault.vault_db import VaultDatabase


def _record(file_path: str, message_id: int = 100) -> DownloadRecord:
    return DownloadRecord(
        account_id="42",
        chat_id="-100123",
        message_id=message_id,
        media_id="media-abc",
        media_type="photo",
        file_name="photo.jpg",
        file_path=file_path,
        file_size=1234,
    )


def test_record_download_prevents_duplicates(tmp_path):
    db = VaultDatabase(tmp_path / "vault.sqlite3")
    media_file = tmp_path / "photo.jpg"
    media_file.write_bytes(b"data")
    record = _record(str(media_file))

    assert db.record_download(record) is True
    assert db.record_download(record) is False
    assert db.was_downloaded("42", "-100123", 100) is True
    assert db.count_for_chat("42", "-100123") == 1


def test_message_identity_is_scoped_to_account_and_chat(tmp_path):
    db = VaultDatabase(tmp_path / "vault.sqlite3")
    first_file = tmp_path / "first.jpg"
    second_file = tmp_path / "second.jpg"
    first_file.write_bytes(b"first")
    second_file.write_bytes(b"second")

    first = _record(str(first_file), message_id=7)
    second = DownloadRecord(
        account_id="99",
        chat_id=first.chat_id,
        message_id=first.message_id,
        media_id=first.media_id,
        media_type=first.media_type,
        file_name="other.jpg",
        file_path=str(second_file),
        file_size=4321,
    )

    assert db.record_download(first) is True
    assert db.record_download(second) is True
    assert db.count_for_chat("42", "-100123") == 1
    assert db.count_for_chat("99", "-100123") == 1


def test_missing_local_file_invalidates_stale_database_row(tmp_path):
    db = VaultDatabase(tmp_path / "vault.sqlite3")
    missing_file = tmp_path / "deleted.jpg"
    record = _record(str(missing_file), message_id=88)

    assert db.record_download(record) is True
    assert db.count_for_chat("42", "-100123") == 1
    assert db.was_downloaded("42", "-100123", 88) is False
    assert db.count_for_chat("42", "-100123") == 0


def test_archived_message_ids_bulk_loads_valid_files_and_prunes_stale_rows(tmp_path):
    db = VaultDatabase(tmp_path / "vault.sqlite3")
    existing_file = tmp_path / "existing.jpg"
    existing_file.write_bytes(b"exists")
    missing_file = tmp_path / "missing.jpg"

    assert db.record_download(_record(str(existing_file), message_id=1)) is True
    assert db.record_download(_record(str(missing_file), message_id=2)) is True

    assert db.archived_message_ids("42", "-100123") == {1}
    assert db.count_for_chat("42", "-100123") == 1


def test_recent_downloads_returns_account_scoped_newest_first(tmp_path):
    db = VaultDatabase(tmp_path / "vault.sqlite3")
    first_file = tmp_path / "first.jpg"
    second_file = tmp_path / "second.jpg"
    other_file = tmp_path / "other.jpg"
    first_file.write_bytes(b"first")
    second_file.write_bytes(b"second")
    other_file.write_bytes(b"other")

    assert db.record_download(_record(str(first_file), message_id=1)) is True
    assert db.record_download(_record(str(second_file), message_id=2)) is True
    assert (
        db.record_download(
            DownloadRecord(
                account_id="99",
                chat_id="-100123",
                message_id=3,
                media_id="other",
                media_type="photo",
                file_name="other.jpg",
                file_path=str(other_file),
                file_size=5,
            )
        )
        is True
    )

    history = db.recent_downloads("42", limit=10)

    assert [item.message_id for item in history] == [2, 1]
    assert all(item.account_id == "42" for item in history)
    assert history[0].file_path == str(second_file)
