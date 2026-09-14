"""Telegram dialog discovery for TG Media Vault."""

from typing import List

from telethon import TelegramClient

from .models import DialogSummary


async def list_media_dialogs(client: TelegramClient) -> List[DialogSummary]:
    """Return channels and groups visible to the authorized account.

    User-to-user chats are intentionally excluded from the V1 archive picker.
    """
    results: List[DialogSummary] = []
    async for dialog in client.iter_dialogs():
        if not (dialog.is_channel or dialog.is_group):
            continue

        entity = dialog.entity
        title = getattr(entity, "title", None) or dialog.name or str(dialog.id)
        username = getattr(entity, "username", None)
        results.append(
            DialogSummary(
                id=int(dialog.id),
                title=str(title),
                username=str(username) if username else None,
                is_channel=bool(dialog.is_channel),
                is_group=bool(dialog.is_group),
            )
        )

    return sorted(results, key=lambda item: item.title.casefold())
