"""Tests for TG Media Vault SQLite persistence."""

from tg_media_vault.models import DownloadRecord
from tg_media_vault.vault_db import VaultDatabase


def _record(message_id: int = 100) -> DownloadRecord:
    return DownloadRecord(
        account_id="42",
        chat_id="-100123",
        message_id=message_id,
        media_id="media-abc",
        media_type="photo",
        file_name="photo.jpg",
        file_path="/tmp/photo.jpg",
        file_size=1234,
    )


def test_record_download_prevents_duplicates(tmp_path):
    db = VaultDatabase(tmp_path / "vault.sqlite3")
    record = _record()

    assert db.record_download(record) is True
    assert db.record_download(record) is False
    assert db.was_downloaded("42", "-100123", 100) is True
    assert db.count_for_chat("42", "-100123") == 1


def test_message_identity_is_scoped_to_account_and_chat(tmp_path):
    db = VaultDatabase(tmp_path / "vault.sqlite3")

    first = _record(message_id=7)
    second = DownloadRecord(
        account_id="99",
        chat_id=first.chat_id,
        message_id=first.message_id,
        media_id=first.media_id,
        media_type=first.media_type,
        file_name="other.jpg",
        file_path="/tmp/other.jpg",
        file_size=4321,
    )

    assert db.record_download(first) is True
    assert db.record_download(second) is True
    assert db.count_for_chat("42", "-100123") == 1
    assert db.count_for_chat("99", "-100123") == 1
