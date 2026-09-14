"""Tests for TG Media Vault local settings."""

from tg_media_vault.settings import AppSettings, load_settings, save_settings


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.yaml"
    original = AppSettings(
        api_id=123456,
        api_hash="secret-hash",
        download_directory=str(tmp_path / "downloads"),
        max_concurrent_downloads=6,
    )

    save_settings(original, path)
    loaded = load_settings(path)

    assert loaded.api_id == 123456
    assert loaded.api_hash == "secret-hash"
    assert loaded.download_directory == str(tmp_path / "downloads")
    assert loaded.max_concurrent_downloads == 6


def test_settings_invalid_values_fall_back(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text(
        "api_id: nope\nmax_concurrent_downloads: nope\ndownload_directory: ''\n",
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.api_id is None
    assert loaded.max_concurrent_downloads == 4
    assert loaded.normalized_download_directory()
