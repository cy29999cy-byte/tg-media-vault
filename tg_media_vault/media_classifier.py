"""Media classification helpers for TG Media Vault.

The Vault UI intentionally exposes four simple archive categories: photo, video,
gif and file. Telegram's lower-level document subtypes are normalized here.
"""

import os
from typing import Optional, Tuple


def _document_filename(document) -> Optional[str]:
    for attr in getattr(document, "attributes", []) or []:
        file_name = getattr(attr, "file_name", None)
        if file_name:
            return str(file_name)
    return None


def _is_animated_document(document) -> bool:
    mime_type = (getattr(document, "mime_type", "") or "").lower()
    if mime_type == "image/gif":
        return True

    for attr in getattr(document, "attributes", []) or []:
        if attr.__class__.__name__ == "DocumentAttributeAnimated":
            return True
    return False


def _has_video_attribute(document) -> bool:
    for attr in getattr(document, "attributes", []) or []:
        if attr.__class__.__name__ == "DocumentAttributeVideo":
            return True
        if bool(getattr(attr, "round_message", False)):
            return True
    return False


def classify_message(message) -> Optional[Tuple[str, object]]:
    """Return ``(vault_type, media_object)`` for a Telegram message.

    ``vault_type`` is one of ``photo``, ``video``, ``gif`` or ``file``.
    Messages without downloadable media return ``None``.
    """
    photo = getattr(message, "photo", None)
    if photo is not None:
        return "photo", photo

    document = getattr(message, "document", None)
    if document is None:
        return None

    if _is_animated_document(document):
        return "gif", document

    mime_type = (getattr(document, "mime_type", "") or "").lower()
    if mime_type.startswith("video/") or _has_video_attribute(document):
        return "video", document

    return "file", document


def candidate_filename(media_type: str, media_obj, message_id: int) -> str:
    """Build a stable display filename without touching the filesystem."""
    if media_type == "photo":
        media_id = getattr(media_obj, "id", message_id)
        return "photo_{0}.jpg".format(media_id)

    explicit = _document_filename(media_obj)
    if explicit:
        return os.path.basename(explicit)

    media_id = getattr(media_obj, "id", message_id)
    mime_type = (getattr(media_obj, "mime_type", "") or "").lower()
    extension = ""
    if "/" in mime_type:
        extension = mime_type.split("/", 1)[1].split("+", 1)[0]
    suffix = ".{0}".format(extension) if extension else ""
    return "{0}_{1}{2}".format(media_type, media_id, suffix)
