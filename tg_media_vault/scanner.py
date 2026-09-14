"""Channel/group media scanning for TG Media Vault."""

from datetime import datetime, timezone
from typing import Optional, Sequence, Set

from telethon import TelegramClient

from .media_classifier import candidate_filename, classify_message
from .models import MediaCandidate, ScanResult
from .vault_db import VaultDatabase


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def scan_chat(
    client: TelegramClient,
    account_id: str,
    chat_id,
    database: Optional[VaultDatabase] = None,
    media_types: Optional[Sequence[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    max_items: Optional[int] = None,
) -> ScanResult:
    """Scan media visible in one chat without downloading it.

    ``chat_id`` is kept as the source identity on every candidate. In the UI this
    is the marked Telethon dialog id (for example a ``-100...`` channel id), so a
    later download can always address the original chat even if the UI selection
    changes after scanning.
    """
    entity = await client.get_entity(chat_id)
    source_chat_id = str(chat_id)

    title = getattr(entity, "title", None) or getattr(entity, "username", None) or str(chat_id)
    normalized_types: Set[str] = set(media_types or ["photo", "video", "gif", "file"])
    start_utc = _as_utc(start_date)
    end_utc = _as_utc(end_date)

    items = []
    counts = {"photo": 0, "video": 0, "gif": 0, "file": 0}
    already_archived = 0

    async for message in client.iter_messages(entity):
        message_date = _as_utc(getattr(message, "date", None))
        if message_date is None:
            continue
        if end_utc is not None and message_date > end_utc:
            continue
        if start_utc is not None and message_date < start_utc:
            break

        classified = classify_message(message)
        if classified is None:
            continue

        media_type, media_obj = classified
        if media_type not in normalized_types:
            continue

        message_id = int(message.id)
        if database and database.was_downloaded(account_id, source_chat_id, message_id):
            already_archived += 1
            continue

        media_id_raw = getattr(media_obj, "id", None)
        media_id = str(media_id_raw) if media_id_raw is not None else None
        file_size = int(getattr(media_obj, "size", 0) or 0)
        item = MediaCandidate(
            chat_id=source_chat_id,
            message_id=message_id,
            media_id=media_id,
            media_type=media_type,
            file_name=candidate_filename(media_type, media_obj, message_id),
            file_size=file_size,
            message_date=message_date,
        )
        items.append(item)
        counts[media_type] += 1

        if max_items is not None and len(items) >= max_items:
            break

    return ScanResult(
        chat_id=source_chat_id,
        title=str(title),
        items=items,
        counts=counts,
        already_archived=already_archived,
    )
