"""Local user settings for TG Media Vault."""

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

APP_DIR = Path.home() / ".tg-media-vault"
SETTINGS_PATH = APP_DIR / "settings.yaml"
SESSION_DIR = APP_DIR / "sessions"
DATABASE_PATH = APP_DIR / "vault.sqlite3"


def default_download_directory() -> str:
    downloads = Path.home() / "Downloads"
    base = downloads if downloads.exists() else Path.home()
    return str(base / "TG Media Vault")


@dataclass
class AppSettings:
    """Small set of values required by the V1 desktop-first UI."""

    api_id: Optional[int] = None
    api_hash: str = ""
    download_directory: str = ""
    max_concurrent_downloads: int = 4

    def normalized_download_directory(self) -> str:
        return self.download_directory.strip() or default_download_directory()


def load_settings(path: Path = SETTINGS_PATH) -> AppSettings:
    if not path.exists():
        return AppSettings(download_directory=default_download_directory())
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return AppSettings(download_directory=default_download_directory())

    api_id = data.get("api_id")
    try:
        api_id = int(api_id) if api_id not in (None, "") else None
    except (TypeError, ValueError):
        api_id = None

    try:
        concurrency = max(1, int(data.get("max_concurrent_downloads", 4)))
    except (TypeError, ValueError):
        concurrency = 4

    return AppSettings(
        api_id=api_id,
        api_hash=str(data.get("api_hash", "") or ""),
        download_directory=str(
            data.get("download_directory", "") or default_download_directory()
        ),
        max_concurrent_downloads=concurrency,
    )


def save_settings(settings: AppSettings, path: Path = SETTINGS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
    try:
        os.chmod(path, 0o600)
    except OSError:
        # Windows ACLs are managed by the operating system; chmod may be limited.
        pass


def session_path(name: str = "main") -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR / name
