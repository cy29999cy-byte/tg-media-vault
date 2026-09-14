"""Shared data models for TG Media Vault."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DialogSummary:
    """A Telegram channel or group that can be shown in the Vault UI."""

    id: int
    title: str
    username: Optional[str]
    is_channel: bool
    is_group: bool


@dataclass(frozen=True)
class DownloadRecord:
    """Persistent identity and local metadata for a downloaded Telegram item."""

    account_id: str
    chat_id: str
    message_id: int
    media_id: Optional[str]
    media_type: str
    file_name: str
    file_path: str
    file_size: int
