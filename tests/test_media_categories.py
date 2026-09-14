"""Sticker/animation contracts using real Telethon document attributes."""

import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from telethon.tl.types import (
    Document,
    DocumentAttributeAnimated,
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeSticker,
    DocumentAttributeVideo,
    InputStickerSetEmpty,
    Message,
    MessageMediaDocument,
    PeerChannel,
)

import media_downloader as downloader


def run_async(coroutine):
    """Run without changing the event loop used by the existing unittest suite."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


def make_message(mime="image/webp", attributes=()):
    """Build an offline message with Telegram's actual document structure."""
    document = Document(
        id=123,
        access_hash=0,
        file_reference=b"",
        date=datetime(2026, 9, 15, tzinfo=timezone.utc),
        mime_type=mime,
        size=100,
        dc_id=1,
        attributes=list(attributes),
    )
    return Message(
        id=42, peer_id=PeerChannel(123), media=MessageMediaDocument(document=document)
    )


def sticker():
    return DocumentAttributeSticker(alt="", stickerset=InputStickerSetEmpty())


def video():
    return DocumentAttributeVideo(duration=1, w=128, h=128, round_message=False)


@pytest.mark.parametrize(
    "mime,attributes,expected",
    [
        ("image/webp", [sticker()], "sticker"),
        (
            "application/x-tgsticker",
            [DocumentAttributeAnimated(), sticker()],
            "sticker",
        ),
        ("video/webm", [video(), sticker()], "sticker"),
        ("video/webm", [sticker(), video()], "sticker"),
        ("video/mp4", [video(), DocumentAttributeAnimated()], "animation"),
        ("video/mp4", [DocumentAttributeAnimated(), video()], "animation"),
        ("image/gif", [], "animation"),
        (" IMAGE/GIF; charset=binary ", [], "animation"),
        ("video/mp4", [video()], "video"),
        (
            "video/mp4",
            [DocumentAttributeVideo(1, 128, 128, round_message=True)],
            "video_note",
        ),
        ("audio/ogg", [DocumentAttributeAudio(1, voice=True)], "voice"),
        ("audio/mpeg", [DocumentAttributeAudio(1, voice=False)], "audio"),
        ("image/webp", [], "document"),
        ("application/pdf", [], "document"),
        (
            "application/octet-stream",
            [DocumentAttributeFilename("sticker.gif")],
            "document",
        ),
    ],
)
def test_classification(mime, attributes, expected):
    assert downloader.get_media_type(make_message(mime, attributes)) == expected


@pytest.mark.parametrize(
    "mime,category,extension,expected_format",
    [
        ("image/webp", "sticker", ".webp", "webp"),
        ("application/x-tgsticker", "sticker", ".tgs", "tgs"),
        ("video/webm", "sticker", ".webm", "webm"),
        ("video/mp4", "animation", ".mp4", "mp4"),
        ("image/gif", "animation", ".gif", "gif"),
        ("application/pdf", "document", ".pdf", "pdf"),
        ("audio/mpeg", "audio", ".mp3", "mpeg"),
        ("video/quicktime", "video", ".mov", "quicktime"),
        ("application/x-unknown-media", "document", "", "x-unknown-media"),
        ("", "document", "", None),
    ],
)
def test_generated_names(tmp_path, mime, category, extension, expected_format):
    name, file_format = run_async(
        downloader._get_media_meta(
            make_message(mime).document, category, "chat", str(tmp_path)
        )
    )
    assert name == str(tmp_path / category / f"{category}_123{extension}")
    assert file_format == expected_format


@pytest.mark.parametrize(
    "filename", ["original.webp", "original", "中文.webp", "bad:name.webp"]
)
def test_original_names_preserved_and_sanitized(tmp_path, filename):
    message = make_message(
        "image/webp", [sticker(), DocumentAttributeFilename(filename)]
    )
    name, _ = run_async(
        downloader._get_media_meta(message.document, "sticker", "chat", str(tmp_path))
    )
    assert os.path.basename(name) == filename.replace(":", "_")


def test_missing_mime_uses_filename_extension(tmp_path):
    message = make_message("", [sticker(), DocumentAttributeFilename("original.TGS")])
    name, file_format = run_async(
        downloader._get_media_meta(message.document, "sticker", "chat", str(tmp_path))
    )
    assert name.endswith("original.TGS")
    assert file_format == "tgs"


@pytest.mark.parametrize(
    "mime,attributes,selected,formats,downloaded",
    [
        ("image/webp", [sticker()], ["document"], {"document": ["all"]}, True),
        (
            "application/x-tgsticker",
            [sticker()],
            ["document"],
            {"document": ["x-tgsticker"]},
            True,
        ),
        ("image/webp", [sticker()], ["document"], {"document": ["pdf"]}, False),
        ("video/webm", [video(), sticker()], ["video"], {"video": ["webm"]}, True),
        (
            "video/webm",
            [video(), sticker()],
            ["document"],
            {"document": ["all"]},
            False,
        ),
        (
            "video/mp4",
            [video(), DocumentAttributeAnimated()],
            ["video"],
            {"video": ["mp4"]},
            True,
        ),
        (
            "video/mp4",
            [video(), DocumentAttributeAnimated()],
            ["video"],
            {"video": ["mov"]},
            False,
        ),
        ("image/gif", [], ["document"], {"document": ["gif"]}, True),
        ("image/webp", [sticker()], ["sticker"], {}, True),
        (
            "application/x-tgsticker",
            [sticker()],
            ["sticker"],
            {"sticker": ["tgs"]},
            True,
        ),
        ("image/webp", [sticker()], ["sticker"], {"sticker": []}, False),
        (
            "image/webp",
            [sticker()],
            ["sticker", "document"],
            {"sticker": ["tgs"], "document": ["all"]},
            False,
        ),
        ("image/gif", [], ["animation"], {}, True),
        ("image/gif", [], ["animation"], {"animation": ["mp4"]}, False),
        ("image/gif", [], ["sticker"], {}, False),
        ("image/webp", [sticker()], [], {}, False),
    ],
)
def test_download_filter_and_history(
    tmp_path, mime, attributes, selected, formats, downloaded
):
    message = make_message(mime, attributes)
    client = AsyncMock()
    client.download_media.return_value = str(tmp_path / "saved")
    with patch.dict(downloader.DOWNLOADED_IDS, {}, clear=True), patch.dict(
        downloader.FAILED_IDS, {}, clear=True
    ), patch.dict(downloader.PROCESSED_IDS, {}, clear=True), patch.object(
        downloader.db, "record_download"
    ) as record:
        result = run_async(
            downloader.download_media(
                client, message, selected, formats, "chat", str(tmp_path)
            )
        )
        assert result == 42
        assert downloader.PROCESSED_IDS["chat"] == [42]
        assert client.download_media.await_count == int(downloaded)
        if downloaded:
            category = downloader.get_media_type(message)
            assert os.path.dirname(
                client.download_media.call_args.kwargs["file"]
            ) == str(tmp_path / category)
            assert record.call_args.args[-1] == category
            assert downloader.DOWNLOADED_IDS["chat"] == [42]
        else:
            record.assert_not_called()
