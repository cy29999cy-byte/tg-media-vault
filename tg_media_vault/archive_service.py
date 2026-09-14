"""Download queue and local archive service for TG Media Vault."""

import asyncio
import inspect
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from telethon import TelegramClient
from telethon.errors import FileReferenceExpiredError

from .models import DownloadRecord, MediaCandidate
from .vault_db import VaultDatabase


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


def safe_path_component(value: str, fallback: str = "telegram") -> str:
    """Return a Windows-safe folder/file component."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip(" .")
    return cleaned or fallback


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
        chat_folder = safe_path_component(chat_title, fallback=item.chat_id)
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
            target.parent.mkdir(parents=True, exist_ok=True)

            # Recover cleanly when a previous run wrote the file but crashed
            # before the SQLite transaction was committed.
            if target.exists() and target.is_file():
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

            await self._emit(
                hook,
                ArchiveProgress(item, index, total_items, 0, item.file_size, "starting"),
            )

            for attempt in range(self.retry_count):
                try:
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
                        file=str(target),
                        progress_callback=on_bytes,
                    )
                    if not downloaded:
                        raise RuntimeError(
                            "Telegram returned no file for message {0}".format(
                                item.message_id
                            )
                        )

                    final_path = Path(str(downloaded)).expanduser().resolve()
                    if not final_path.exists() and target.exists():
                        final_path = target

                    self.database.record_download(
                        DownloadRecord(
                            account_id=self.account_id,
                            chat_id=item.chat_id,
                            message_id=item.message_id,
                            media_id=item.media_id,
                            media_type=item.media_type,
                            file_name=final_path.name,
                            file_path=str(final_path),
                            file_size=(
                                final_path.stat().st_size
                                if final_path.exists()
                                else item.file_size
                            ),
                        )
                    )
                    actual_size = (
                        final_path.stat().st_size
                        if final_path.exists()
                        else item.file_size
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
                except (TimeoutError, FileReferenceExpiredError):
                    if attempt + 1 >= self.retry_count:
                        break
                    if self.retry_delay:
                        await asyncio.sleep(self.retry_delay)
                except Exception:
                    break

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
