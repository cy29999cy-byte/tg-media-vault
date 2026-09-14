"""Tests for the TG Media Vault archive queue."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from tg_media_vault.archive_service import ArchiveService, safe_path_component
from tg_media_vault.models import MediaCandidate
from tg_media_vault.vault_db import VaultDatabase


class FakeTelegramClient:
    def __init__(self, fail_first=False):
        self.download_calls = 0
        self.fail_first = fail_first

    async def get_messages(self, chat_id, ids):
        return SimpleNamespace(id=ids, chat=SimpleNamespace(id=chat_id))

    async def download_media(self, message, file, progress_callback=None):
        self.download_calls += 1
        target = Path(file)
        target.parent.mkdir(parents=True, exist_ok=True)

        if self.fail_first and self.download_calls == 1:
            target.write_bytes(b"partial")
            raise TimeoutError("simulated interrupted transfer")

        payload = b"vault-test"
        if progress_callback:
            progress_callback(5, len(payload))
        target.write_bytes(payload)
        if progress_callback:
            progress_callback(len(payload), len(payload))
        return str(target)


def _candidate(chat_id="1001"):
    return MediaCandidate(
        chat_id=str(chat_id),
        message_id=42,
        media_id="9001",
        media_type="photo",
        file_name="camera:reference.jpg",
        file_size=10,
        message_date=datetime.now(timezone.utc),
    )


def test_safe_path_component_is_windows_friendly():
    assert safe_path_component('A:B/C\\D?E*F"G') == "A_B_C_D_E_F_G"
    assert safe_path_component("CON") == "_CON"
    assert len(safe_path_component("x" * 400)) == 120


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


def test_archive_service_recovers_complete_existing_file_without_redownload(tmp_path):
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
    target = service._target_path(
        "Photography:References", item
    )  # pylint: disable=protected-access
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"vault-test")

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


def test_archive_service_redownloads_incomplete_existing_file(tmp_path):
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
    target = service._target_path(
        "Photography:References", item
    )  # pylint: disable=protected-access
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"bad")

    result = asyncio.run(
        service.archive_items(
            chat_id=1001,
            chat_title="Photography:References",
            items=[item],
        )
    )
    assert result.downloaded == 1
    assert result.failed == 0
    assert client.download_calls == 1
    assert target.read_bytes() == b"vault-test"


def test_archive_service_retries_partial_transfer_without_leaving_part_file(tmp_path):
    client = FakeTelegramClient(fail_first=True)
    database = VaultDatabase(tmp_path / "vault.sqlite3")
    service = ArchiveService(
        client=client,
        database=database,
        account_id="account-1",
        root_directory=tmp_path / "archive",
        retry_count=2,
        retry_delay=0,
    )
    item = _candidate()
    target = service._target_path(
        "Photography:References", item
    )  # pylint: disable=protected-access
    partial = service._partial_path(target)  # pylint: disable=protected-access

    result = asyncio.run(
        service.archive_items(
            chat_id=1001,
            chat_title="Photography:References",
            items=[item],
        )
    )
    assert result.downloaded == 1
    assert result.failed == 0
    assert client.download_calls == 2
    assert target.read_bytes() == b"vault-test"
    assert not partial.exists()


def test_archive_paths_separate_channels_with_same_title(tmp_path):
    service = ArchiveService(
        client=FakeTelegramClient(),
        database=VaultDatabase(tmp_path / "vault.sqlite3"),
        account_id="account-1",
        root_directory=tmp_path / "archive",
        retry_delay=0,
    )
    first = service._target_path(
        "Same title", _candidate("1001")
    )  # pylint: disable=protected-access
    second = service._target_path(
        "Same title", _candidate("1002")
    )  # pylint: disable=protected-access

    assert first != second
    assert "1001" in str(first.parent.parent)
    assert "1002" in str(second.parent.parent)
