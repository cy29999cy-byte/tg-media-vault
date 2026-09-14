# ADR 0002: Treat Telegram animations and stickers as first-class media categories

- Status: Accepted
- Date: 2026-09-15

## Context
The existing `get_media_type()` distinguishes photos and Telegram documents by checking voice and round-video attributes, then falls back to `document`. This is sufficient for generic downloading but does not give GIF/animation and sticker media explicit filtering, naming, UI controls, storage organization, or tests.

Telegram may represent user-visible “GIFs” as animated documents/video-like media, and stickers can be static, animated, or video documents. Therefore file extension alone is not a reliable product taxonomy.

## Decision
Introduce explicit logical media categories based on Telethon document attributes and MIME metadata:

- `animation`: Telegram animation/GIF-style media, detected from animation attributes and compatible document/video metadata.
- `sticker`: sticker documents, including static, animated, and video sticker variants.

Preserve `document` as the fallback for documents that are not more specifically classified.

The logical category should control filtering, destination folders, history labels, and Web UI choices. The stored filename/extension should still reflect the actual downloaded representation.

## Compatibility
- Existing configurations that include `document` should continue to work without silently losing files.
- Keep the original attribute-based category as a compatibility selection route. Media formerly classified as `document` or `video` continues to match that selection and its original MIME-subtype format filter. Do not broaden `document` to include media it did not match before.
- Explicit `sticker`/`animation` selections take precedence and use their own extension-based format lists. Missing new format keys mean `all`; an explicit empty list matches nothing in the engine.
- Keep global/per-chat inheritance unchanged; no automatic YAML migration is required.
- Existing photo/video/audio/voice/video_note behavior must remain unchanged.

## Required tests before acceptance
- static sticker classification
- animated sticker classification
- video sticker classification
- Telegram animation/GIF-style classification
- generic document fallback
- filename/extension generation for media without a Telegram-provided filename
- configuration backward compatibility
- Web UI selection round-trip

## Storage and representation
New animation downloads live under `animation/`, even when represented as MP4.
All sticker subtypes share `sticker/`; their extensions retain the representation.
History records the logical category. Existing files and history remain untouched.
Sticker attributes take precedence over animated/video attributes. Raw GIF MIME
metadata also identifies animations, but extensions alone do not classify media.

## Verification
Tests cover all three sticker representations, classification precedence, raw GIF
and Telegram MP4 animations, legacy selections and format restrictions, explicit
selection precedence, generated names, download paths/history, and actual NiceGUI
selection/format save-and-reload behavior. See the PR for the latest test/CI results.
