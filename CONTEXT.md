# TG Media Vault — Project Context

## Product goal
Build a reliable Telegram media archiver on top of the existing Telethon downloader rather than rewriting the project from zero. The tool should be easy to run on Windows, recover cleanly after interruption, and expose a practical Web UI for configuration, execution status, and download history.

## Primary user workflow
1. Authenticate with a Telegram user account through the supported Telethon flow.
2. Select one or more chats/channels the account can access.
3. Choose media categories and an output directory.
4. Start or resume an archive run.
5. Download media with bounded concurrency and rate-aware pacing.
6. Persist progress frequently enough that interruption does not force a large re-scan.
7. Inspect completed and failed items in the Web UI/history database.

## Required media coverage
The product should support these as first-class user-facing categories where Telegram exposes them through the normal API:
- photos
- videos
- audio
- voice messages
- video notes
- generic documents/files
- GIF / animation media
- stickers, including common static, animated, and video sticker representations when Telethon exposes them as documents

The current upstream code has first-class categories for photo, video, audio, voice, video_note, and document. GIF/animation and sticker media currently fall through the generic document/video logic rather than being explicitly classified, named, filtered, and tested. This is a planned product gap, not a reason to replace the existing downloader.

## Architecture we are keeping
- `media_downloader.py`: async Telethon download engine and orchestration.
- `config_manager.py`: YAML configuration loading/saving.
- `db.py`: persistent download history used by the Web UI.
- `webui.py` + `webui/`: NiceGUI-based interface.
- `tests/`: pytest suite with mocked Telegram/file I/O behavior.
- `AGENTS.md`: persistent coding-agent operating instructions.

## Non-negotiable engineering requirements
- Preserve async/await and bounded concurrency.
- Respect Telegram rate limits; use pacing and explicit FloodWait-aware behavior rather than blind immediate retry loops.
- Keep resumability/checkpointing correct under Ctrl+C, process crashes, and transient network failures.
- Never commit API hashes, phone/session credentials, Telegram session files, proxy credentials, or user download history.
- Use the existing database/history path instead of adding a second competing state store unless an ADR explicitly justifies it.
- Add tests for every new media classification and recovery behavior before calling the work complete.
- Run the full test suite and repository quality checks before claiming completion.
- Work only with media the authenticated account can access through normal Telegram/Telethon APIs; do not add protocol/client-protection circumvention mechanisms.

## Current strengths
- Mature upstream base instead of a greenfield rewrite.
- Telethon migration already complete.
- Multi-chat support and optional parallel chat processing.
- Per-chat/global configuration inheritance.
- Download pacing via semaphore plus configurable delay.
- Batch checkpointing and gentle-exit resume logic.
- SQLite-backed history plus NiceGUI Web UI.
- Large pytest suite and lint/type-check tooling.

## Current gaps to address next
1. First-class GIF/animation and sticker detection, naming, filtering, storage, UI choices, and tests.
2. Explicit Telegram `FloodWaitError` handling with bounded sleep/retry and observability.
3. Stronger retry taxonomy: transient vs permanent failures, maximum attempt accounting, and clearer history status.
4. Durable run-state UX in the Web UI: running/paused/stopped/failed/completed plus per-chat progress.
5. Validation of resumability under partial batches and process termination.
6. Packaging/deployment path for a straightforward Windows desktop/user workflow after the core engine is stable.

## Coding-agent workflow
For substantial changes, do not jump directly into implementation.

1. Inspect `CONTEXT.md`, `AGENTS.md`, relevant code, tests, and existing ADRs.
2. Search for an existing Agent Skill and mature upstream/open-source implementation that can be reused.
3. Model the domain and identify unresolved decisions.
4. Write/update an ADR when a decision changes architecture, persistence, media taxonomy, or public configuration.
5. Produce a concrete implementation plan.
6. Implement the smallest coherent change.
7. Debug by root cause, not by repeated speculative patches.
8. Run tests and quality checks.
9. Verify evidence before claiming success.
10. Review architecture after the feature works; refactor only when evidence justifies it.
