"""Download queue and local archive service for TG Media Vault."""

import asyncio
import inspect
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from telethon import TelegramClient
from telethon.errors import FileReferenceExpiredError

from .models import DownloadRecord, MediaCandidate
from .vault_db import VaultDatabase

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArchiveProgress:
    """Progress event emitted while archiving media."""

    item: MediaCandidate
    index: int
    total_items: int
    current_bytes: int
    total_bytes: int
    status: str
    target_path: Optional[str] = None


@dataclass(frozen=True)
class ArchiveSummary:
    """Aggregate result of one archive run."""

    requested: int
    downloaded: int
    skipped: int
    failed: int


ProgressHook = Callable[[ArchiveProgress], object]

_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def safe_path_component(value: str, fallback: str = "telegram", max_length: int = 120) -> str:
    """Return a Windows-safe, reasonably short folder/file component."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip(" .")
    cleaned = cleaned or fallback

    stem_name = cleaned.split(".", 1)[0].upper()
    if stem_name in _WINDOWS_RESERVED_NAMES:
        cleaned = "_{0}".format(cleaned)

    if len(cleaned) <= max_length:
        return cleaned

    stem, extension = os.path.splitext(cleaned)
    if extension and len(extension) < max_length // 2:
        allowed_stem = max(1, max_length - len(extension))
        return "{0}{1}".format(stem[:allowed_stem], extension)
    return cleaned[:max_length]


class ArchiveService:
    """Archive scanned Telegram media into deterministic local folders."""

    def __init__(
        self,
        client: TelegramClient,
        database: VaultDatabase,
        account_id: str,
        root_directory,
        max_concurrent_downloads: int = 4,
        retry_count: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        self.client = client
        self.database = database
        self.account_id = str(account_id)
        self.root_directory = Path(root_directory).expanduser().resolve()
        self.root_directory.mkdir(parents=True, exist_ok=True)
        self.max_concurrent_downloads = max(1, int(max_concurrent_downloads))
        self.retry_count = max(1, int(retry_count))
        self.retry_delay = max(0.0, float(retry_delay))

    @staticmethod
    def _message_from_result(result):
        if isinstance(result, (list, tuple)):
            return result[0] if result else None
        return result

    def _target_path(self, chat_title: str, item: MediaCandidate) -> Path:
        # Include the stable chat identity so two channels with the same display
        # title can never collide in the local archive.
        chat_folder = safe_path_component(
            "{0} [{1}]".format(chat_title, item.chat_id), fallback=item.chat_id
        )
        type_folder = safe_path_component(item.media_type, fallback="file")
        original_name = safe_path_component(
            os.path.basename(item.file_name), fallback="media_{0}".format(item.message_id)
        )
        return (
            self.root_directory
            / chat_folder
            / type_folder
            / "{0}_{1}".format(item.message_id, original_name)
        )

    @staticmethod
    def _partial_path(target: Path) -> Path:
        return target.with_name("{0}.part".format(target.name))

    @staticmethod
    def _existing_file_is_complete(item: MediaCandidate, target: Path) -> bool:
        if not target.exists() or not target.is_file():
            return False
        size = target.stat().st_size
        if item.file_size > 0:
            return size == item.file_size
        return size > 0

    async def _emit(self, hook: Optional[ProgressHook], progress: ArchiveProgress) -> None:
        if hook is None:
            return
        result = hook(progress)
        if inspect.isawaitable(result):
            await result

    def _record_existing(self, item: MediaCandidate, target: Path) -> None:
        self.database.record_download(
            DownloadRecord(
                account_id=self.account_id,
                chat_id=item.chat_id,
                message_id=item.message_id,
                media_id=item.media_id,
                media_type=item.media_type,
                file_name=target.name,
                file_path=str(target),
                file_size=target.stat().st_size if target.exists() else item.file_size,
            )
        )

    @staticmethod
    def _remove_partial(path: Path) -> None:
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            logger.warning("Unable to remove partial archive file %s", path)

    async def _archive_one(
        self,
        chat_id,
        chat_title: str,
        item: MediaCandidate,
        index: int,
        total_items: int,
        hook: Optional[ProgressHook],
        semaphore: asyncio.Semaphore,
    ) -> str:
        async with semaphore:
            if self.database.was_downloaded(
                self.account_id, item.chat_id, item.message_id
            ):
                await self._emit(
                    hook,
                    ArchiveProgress(item, index, total_items, 0, item.file_size, "skipped"),
                )
                return "skipped"

            target = self._target_path(chat_title, item)
            partial = self._partial_path(target)
            target.parent.mkdir(parents=True, exist_ok=True)

            # Recover cleanly when a previous run completed the final file but
            # crashed before the SQLite transaction was committed. A size
            # mismatch is treated as incomplete and will be downloaded again.
            if self._existing_file_is_complete(item, target):
                self._record_existing(item, target)
                await self._emit(
                    hook,
                    ArchiveProgress(
                        item,
                        index,
                        total_items,
                        target.stat().st_size,
                        target.stat().st_size,
                        "skipped",
                        str(target),
                    ),
                )
                return "skipped"

            self._remove_partial(partial)
            await self._emit(
                hook,
                ArchiveProgress(item, index, total_items, 0, item.file_size, "starting"),
            )

            for attempt in range(self.retry_count):
                try:
                    # Never stream directly into the final filename. If the
                    # process is interrupted, only the .part file can be left
                    # behind, so the next run cannot mistake it for a completed
                    # archive item.
                    self._remove_partial(partial)
                    message_result = await self.client.get_messages(
                        chat_id, ids=item.message_id
                    )
                    message = self._message_from_result(message_result)
                    if message is None:
                        raise RuntimeError(
                            "Telegram message {0} is no longer available".format(
                                item.message_id
                            )
                        )

                    def on_bytes(current: int, total: int) -> None:
                        if hook is None:
                            return
                        progress = ArchiveProgress(
                            item=item,
                            index=index,
                            total_items=total_items,
                            current_bytes=int(current or 0),
                            total_bytes=int(total or item.file_size or 0),
                            status="downloading",
                            target_path=str(target),
                        )
                        result = hook(progress)
                        if inspect.isawaitable(result):
                            asyncio.get_running_loop().create_task(result)

                    downloaded = await self.client.download_media(
                        message,
                        file=str(partial),
                        progress_callback=on_bytes,
                    )
                    if not downloaded:
                        raise RuntimeError(
                            "Telegram returned no file for message {0}".format(
                                item.message_id
                            )
                        )

                    downloaded_path = Path(str(downloaded)).expanduser().resolve()
                    if downloaded_path.exists() and downloaded_path != partial.resolve():
                        # Telethon may normalize the provided path. Move whatever
                        # it returned into our controlled partial location first.
                        os.replace(str(downloaded_path), str(partial))

                    if not partial.exists():
                        raise RuntimeError(
                            "Telegram download did not create the expected file for message {0}".format(
                                item.message_id
                            )
                        )

                    if item.file_size > 0 and partial.stat().st_size != item.file_size:
                        raise RuntimeError(
                            "Downloaded size mismatch for message {0}: expected {1}, got {2}".format(
                                item.message_id,
                                item.file_size,
                                partial.stat().st_size,
                            )
                        )

                    os.replace(str(partial), str(target))
                    final_path = target.resolve()
                    actual_size = final_path.stat().st_size

                    self.database.record_download(
                        DownloadRecord(
                            account_id=self.account_id,
                            chat_id=item.chat_id,
                            message_id=item.message_id,
                            media_id=item.media_id,
                            media_type=item.media_type,
                            file_name=final_path.name,
                            file_path=str(final_path),
                            file_size=actual_size,
                        )
                    )
                    await self._emit(
                        hook,
                        ArchiveProgress(
                            item,
                            index,
                            total_items,
                            actual_size,
                            actual_size,
                            "done",
                            str(final_path),
                        ),
                    )
                    return "downloaded"
                except (TimeoutError, FileReferenceExpiredError) as exc:
                    logger.warning(
                        "Retryable Telegram download error for message %s: %s",
                        item.message_id,
                        exc,
                    )
                except Exception as exc:  # Keep queue alive when one item fails.
                    logger.warning(
                        "Archive attempt %s/%s failed for message %s: %s",
                        attempt + 1,
                        self.retry_count,
                        item.message_id,
                        exc,
                    )

                self._remove_partial(partial)
                if attempt + 1 < self.retry_count and self.retry_delay:
                    await asyncio.sleep(self.retry_delay)

            self._remove_partial(partial)
            await self._emit(
                hook,
                ArchiveProgress(
                    item, index, total_items, 0, item.file_size, "failed", str(target)
                ),
            )
            return "failed"

    async def archive_items(
        self,
        chat_id,
        chat_title: str,
        items: Iterable[MediaCandidate],
        progress_hook: Optional[ProgressHook] = None,
    ) -> ArchiveSummary:
        """Archive media concurrently and return aggregate counts."""
        item_list: List[MediaCandidate] = list(items)
        if not item_list:
            return ArchiveSummary(0, 0, 0, 0)

        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        results = await asyncio.gather(
            *[
                self._archive_one(
                    chat_id,
                    chat_title,
                    item,
                    index,
                    len(item_list),
                    progress_hook,
                    semaphore,
                )
                for index, item in enumerate(item_list, start=1)
            ]
        )
        return ArchiveSummary(
            requested=len(item_list),
            downloaded=results.count("downloaded"),
            skipped=results.count("skipped"),
            failed=results.count("failed"),
        )
