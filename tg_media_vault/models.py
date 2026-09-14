"""Shared data models for TG Media Vault."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DialogSummary:
    """A Telegram channel or group that can be shown in the Vault UI."""

    id: int
    title: str
    username: Optional[str]
    is_channel: bool
    is_group: bool


@dataclass(frozen=True)
class MediaCandidate:
    """A media-bearing Telegram message discovered during a scan."""

    chat_id: str
    message_id: int
    media_id: Optional[str]
    media_type: str
    file_name: str
    file_size: int
    message_date: datetime


@dataclass(frozen=True)
class ScanResult:
    """Result of scanning one Telegram channel/group."""

    chat_id: str
    title: str
    items: List[MediaCandidate]
    counts: Dict[str, int]
    already_archived: int = 0


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


@dataclass(frozen=True)
class ArchiveHistoryItem:
    """One persisted archive item shown in history views."""

    account_id: str
    chat_id: str
    message_id: int
    media_id: Optional[str]
    media_type: str
    file_name: str
    file_path: str
    file_size: int
    downloaded_at: str
