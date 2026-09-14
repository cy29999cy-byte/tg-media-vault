"""Tests for the TG Media Vault archive queue."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from tg_media_vault.archive_service import ArchiveService, safe_path_component
from tg_media_vault.models import MediaCandidate
from tg_media_vault.vault_db import VaultDatabase


class FakeTelegramClient:
    def __init__(self):
        self.download_calls = 0

    async def get_messages(self, chat_id, ids):
        return SimpleNamespace(id=ids, chat=SimpleNamespace(id=chat_id))

    async def download_media(self, message, file, progress_callback=None):
        self.download_calls += 1
        target = Path(file)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = b"vault-test"
        if progress_callback:
            progress_callback(5, len(payload))
        target.write_bytes(payload)
        if progress_callback:
            progress_callback(len(payload), len(payload))
        return str(target)


def _candidate():
    return MediaCandidate(
        chat_id="1001",
        message_id=42,
        media_id="9001",
        media_type="photo",
        file_name="camera:reference.jpg",
        file_size=10,
        message_date=datetime.now(timezone.utc),
    )


def test_safe_path_component_is_windows_friendly():
    assert safe_path_component('A:B/C\\D?E*F"G') == "A_B_C_D_E_F_G"


def test_archive_service_downloads_once_then_skips(tmp_path):
    client = FakeTelegramClient()
    database = VaultDatabase(tmp_path / "vault.sqlite3")
    service = ArchiveService(
        client=client,
        database=database,
        account_id="account-1",
        root_directory=tmp_path / "archive",
        max_concurrent_downloads=2,
        retry_delay=0,
    )
    item = _candidate()

    first = asyncio.run(
        service.archive_items(
            chat_id=1001,
            chat_title="Photography:References",
            items=[item],
        )
    )
    assert first.downloaded == 1
    assert first.skipped == 0
    assert first.failed == 0
    assert client.download_calls == 1
    assert database.was_downloaded("account-1", "1001", 42)

    second = asyncio.run(
        service.archive_items(
            chat_id=1001,
            chat_title="Photography:References",
            items=[item],
        )
    )
    assert second.downloaded == 0
    assert second.skipped == 1
    assert second.failed == 0
    assert client.download_calls == 1


def test_archive_service_recovers_existing_file_without_redownload(tmp_path):
    client = FakeTelegramClient()
    database = VaultDatabase(tmp_path / "vault.sqlite3")
    service = ArchiveService(
        client=client,
        database=database,
        account_id="account-1",
        root_directory=tmp_path / "archive",
        retry_delay=0,
    )
    item = _candidate()
    target = service._target_path("Photography:References", item)  # pylint: disable=protected-access
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"already-here")

    result = asyncio.run(
        service.archive_items(
            chat_id=1001,
            chat_title="Photography:References",
            items=[item],
        )
    )
    assert result.skipped == 1
    assert client.download_calls == 0
    assert database.was_downloaded("account-1", "1001", 42)
