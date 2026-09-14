"""SQLite persistence for TG Media Vault."""

from pathlib import Path
import sqlite3

from .models import DownloadRecord


class VaultDatabase:
    """Track downloaded Telegram media and prevent duplicate archiving."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    media_id TEXT,
                    media_type TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    downloaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(account_id, chat_id, message_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_chat ON media_items(account_id, chat_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_downloaded_at ON media_items(downloaded_at DESC)"
            )
            conn.commit()

    def was_downloaded(self, account_id: str, chat_id: str, message_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM media_items
                WHERE account_id = ? AND chat_id = ? AND message_id = ?
                LIMIT 1
                """,
                (account_id, chat_id, message_id),
            ).fetchone()
            return row is not None

    def record_download(self, record: DownloadRecord) -> bool:
        """Record one media item.

        Returns True when a new row was inserted and False when the Telegram
        message had already been archived for this account/chat.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO media_items (
                    account_id,
                    chat_id,
                    message_id,
                    media_id,
                    media_type,
                    file_name,
                    file_path,
                    file_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.account_id,
                    record.chat_id,
                    record.message_id,
                    record.media_id,
                    record.media_type,
                    record.file_name,
                    record.file_path,
                    record.file_size,
                ),
            )
            conn.commit()
            return cursor.rowcount == 1

    def count_for_chat(self, account_id: str, chat_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM media_items WHERE account_id = ? AND chat_id = ?",
                (account_id, chat_id),
            ).fetchone()
            return int(row["total"]) if row else 0
