"""Tests for TG Media Vault media classification."""

from types import SimpleNamespace

from tg_media_vault.media_classifier import candidate_filename, classify_message


class DocumentAttributeAnimated:
    pass


class RoundVideoAttribute:
    round_message = True


def test_classifies_photo():
    photo = SimpleNamespace(id=11)
    message = SimpleNamespace(photo=photo, document=None)
    media_type, media = classify_message(message)
    assert media_type == "photo"
    assert media is photo
    assert candidate_filename(media_type, media, 1) == "photo_11.jpg"


def test_classifies_animated_document_as_gif():
    document = SimpleNamespace(
        id=22,
        mime_type="video/mp4",
        attributes=[DocumentAttributeAnimated()],
    )
    message = SimpleNamespace(photo=None, document=document)
    media_type, media = classify_message(message)
    assert media_type == "gif"
    assert media is document


def test_classifies_video_and_file():
    video = SimpleNamespace(id=33, mime_type="video/mp4", attributes=[])
    video_message = SimpleNamespace(photo=None, document=video)
    assert classify_message(video_message)[0] == "video"

    document = SimpleNamespace(
        id=44,
        mime_type="application/pdf",
        attributes=[SimpleNamespace(file_name="guide.pdf")],
    )
    file_message = SimpleNamespace(photo=None, document=document)
    media_type, media = classify_message(file_message)
    assert media_type == "file"
    assert candidate_filename(media_type, media, 4) == "guide.pdf"


def test_round_video_is_video():
    document = SimpleNamespace(
        id=55,
        mime_type="application/octet-stream",
        attributes=[RoundVideoAttribute()],
    )
    message = SimpleNamespace(photo=None, document=document)
    assert classify_message(message)[0] == "video"
