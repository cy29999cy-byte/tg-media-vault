"""Tests for TG Media Vault channel scanning."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from tg_media_vault.scanner import scan_chat
from tg_media_vault.vault_db import VaultDatabase


class FakeScanClient:
    def __init__(self, messages):
        self.entity = SimpleNamespace(id=777, title="Reference Channel")
        self.messages = messages

    async def get_entity(self, chat_id):
        return self.entity

    def iter_messages(self, entity):
        async def iterator():
            for message in self.messages:
                yield message

        return iterator()


def test_scan_filters_types_dates_and_preserves_source_dialog_id(tmp_path):
    now = datetime.now(timezone.utc)
    messages = [
        SimpleNamespace(
            id=3,
            date=now,
            photo=SimpleNamespace(id=1003),
            document=None,
        ),
        SimpleNamespace(
            id=2,
            date=now - timedelta(days=2),
            photo=None,
            document=SimpleNamespace(
                id=1002,
                mime_type="video/mp4",
                size=2048,
                attributes=[],
            ),
        ),
        SimpleNamespace(
            id=1,
            date=now - timedelta(days=20),
            photo=SimpleNamespace(id=1001),
            document=None,
        ),
    ]
    client = FakeScanClient(messages)
    database = VaultDatabase(tmp_path / "vault.sqlite3")
    source_dialog_id = -100777

    result = asyncio.run(
        scan_chat(
            client=client,
            account_id="account-1",
            chat_id=source_dialog_id,
            database=database,
            media_types=["photo", "video"],
            start_date=now - timedelta(days=7),
        )
    )

    assert result.title == "Reference Channel"
    assert result.chat_id == str(source_dialog_id)
    assert result.counts["photo"] == 1
    assert result.counts["video"] == 1
    assert len(result.items) == 2
    assert {item.message_id for item in result.items} == {2, 3}
    assert {item.chat_id for item in result.items} == {str(source_dialog_id)}
