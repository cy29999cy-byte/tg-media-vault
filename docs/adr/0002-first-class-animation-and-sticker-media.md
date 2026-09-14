# ADR 0002: Treat Telegram animations and stickers as first-class media categories

- Status: Proposed
- Date: 2026-09-15

## Context
The existing `get_media_type()` distinguishes photos and Telegram documents by checking voice and round-video attributes, then falls back to `document`. This is sufficient for generic downloading but does not give GIF/animation and sticker media explicit filtering, naming, UI controls, storage organization, or tests.

Telegram may represent user-visible “GIFs” as animated documents/video-like media, and stickers can be static, animated, or video documents. Therefore file extension alone is not a reliable product taxonomy.

## Proposed decision
Introduce explicit logical media categories based on Telethon document attributes and MIME metadata:

- `animation`: Telegram animation/GIF-style media, detected from animation attributes and compatible document/video metadata.
- `sticker`: sticker documents, including static, animated, and video sticker variants.

Preserve `document` as the fallback for documents that are not more specifically classified.

The logical category should control filtering, destination folders, history labels, and Web UI choices. The stored filename/extension should still reflect the actual downloaded representation.

## Compatibility
- Existing configurations that include `document` should continue to work without silently losing files.
- A migration rule must be defined before implementation: either `document` implicitly includes the new subtypes for backward compatibility, or configuration migration expands existing `document` selections. This decision must be covered by tests.
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

## Open questions
1. Should legacy `document` selection include stickers and animations by default?
2. Should animation files live under `animation/` even when the underlying MIME type is video/mp4?
3. Should sticker subtypes be stored together or under subtype-specific folders?

This ADR remains Proposed until those compatibility questions are resolved during implementation planning.
