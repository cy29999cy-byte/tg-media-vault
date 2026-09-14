# TG Media Vault — Implementation Plan

Status: Phase 1 implemented on `codex-skill-audit`; PR validation records the latest test and CI results. Phases 2–5 remain planned.

## Baseline discovered in the current repository

The current codebase already provides the right base for the product:

- Telethon async download engine.
- Six explicit media categories: photo, video, document, audio, voice, video_note.
- Global/per-chat configuration inheritance.
- Bounded concurrency and optional pacing delay.
- Retry tracking and batch checkpoints.
- Graceful Ctrl+C resumption logic.
- SQLite download history.
- NiceGUI configuration, execution, and history screens.
- pytest coverage plus code-quality workflows.

The fork currently matches the upstream repository head, so product-specific work should begin as focused changes on top of that baseline rather than as a rewrite.

## Audit findings that matter most

### 1. GIF/animation and stickers are not first-class media types

`get_media_type()` explicitly detects photo, voice/audio, and video-note/video, then falls back to `document`. There is no dedicated sticker or animation classification. The Web UI and example configuration also expose only the existing six categories.

This means some sticker/animation files may already pass through as generic document/video media, but users cannot reliably select, label, organize, or test them as their own product categories.

### 2. Files without an explicit Telegram filename need stronger naming

For non-voice/non-video-note media without a Telegram-provided filename, `_get_media_meta()` falls back to `<type>_<id>` and does not always append the MIME-derived extension. First-class sticker/animation support should fix this deterministically.

### 3. Telegram FloodWait is not handled explicitly

The download path has dedicated handling for expired file references and timeouts, then a broad exception fallback. There is no explicit `FloodWaitError` branch. The current semaphore/delay settings reduce risk, but they are not a substitute for obeying a server-requested wait duration.

### 4. Retry state is functional but coarse

Failures are currently recorded mostly as message IDs. A future product-quality UX should distinguish transient, exhausted, and permanent failures and expose attempts/reason in history without creating a second competing source of truth.

## Delivery sequence

### Phase 0 — Establish a verified baseline

Before feature code:

- Create a feature branch from current `master`.
- Install the project-scoped Codex Skill Pack from `docs/CODEX_SKILLS.md`.
- Run the existing test suite and code checks without modifications.
- Record the exact baseline results. Do not begin feature work if the baseline is red without first identifying whether the failure is environmental or pre-existing.

Verification targets:

```bash
pytest tests/ -v
pre-commit run --all-files
```

Use the repository CI workflows as an additional verification gate on the PR.

### Phase 1 — First-class sticker and animation taxonomy

Primary files expected to change:

- `media_downloader.py`
- `config.yaml.example`
- `webui/config_tab.py`
- `tests/test_media_downloader.py`
- `tests/test_webui.py`
- README/config documentation as needed

Implementation goals:

1. Detect Telegram sticker documents using Telethon document attributes rather than filename guesses.
2. Detect Telegram animation/GIF-style media using Telethon document attributes and MIME metadata.
3. Introduce logical `sticker` and `animation` categories.
4. Preserve generic `document` fallback for everything else.
5. Ensure fallback-generated filenames include a correct extension when MIME metadata provides one.
6. Add both categories to global and per-chat Web UI selectors.
7. Add representative unit tests for:
   - static sticker
   - animated sticker
   - video sticker
   - animation/GIF-style document
   - generic document
   - media without an explicit filename

Accepted backward-compatibility rule (ADR 0002):

Existing `document`/`video` selections keep matching media under its original classification and MIME format filters. Explicit `sticker`/`animation` selections take precedence and use their own extension filters. New folders/history use the logical category. No YAML migration is needed. Classification, filtering, naming, download history, and Web UI round trips are covered by tests.

### Phase 2 — Rate-limit-aware retries

Primary files expected to change:

- `media_downloader.py`
- `tests/test_media_downloader.py`
- possibly `db.py` if failure metadata is persisted

Implementation goals:

1. Add explicit Telethon `FloodWaitError` handling.
2. Sleep for the server-requested duration, subject to a documented safety policy.
3. Retry within a bounded attempt budget.
4. Keep `FileReferenceExpiredError` refetch behavior independent from FloodWait behavior.
5. Distinguish retryable timeout/network failures from permanent failures.
6. Log the reason and next action clearly enough for the Web UI to surface later.

Required tests:

- FloodWait sleeps for the requested duration and retries.
- Retry budget is bounded.
- Exhausted retry is persisted for next run.
- Successful retry removes the message from retry state.
- Existing timeout and expired-reference behavior remains correct.

### Phase 3 — Durable run state and Web UI observability

Primary files expected to change:

- `db.py`
- `webui/execution_tab.py`
- `webui/history_tab.py`
- downloader progress hook integration
- corresponding tests

Desired run states:

- idle
- running
- stopping
- completed
- completed_with_failures
- failed

Per-chat UI should show at minimum:

- active chat/channel
- processed count
- downloaded count
- failed/retry count
- current item
- latest checkpoint

Do not invent a second progress database if the existing SQLite layer can represent this cleanly. If a new persistence model is necessary, write an ADR first.

### Phase 4 — Interruption and resume hardening

Test scenarios:

- Ctrl+C in the middle of a partially processed batch.
- Process termination after a checkpoint.
- One failed item among otherwise successful concurrent downloads.
- Multiple chats with one slow/failing chat.
- Restart with `ids_to_retry` plus new messages.
- Existing file/name collisions.

Acceptance criterion: restarting must not silently skip unprocessed media and must not create avoidable duplicate downloads.

### Phase 5 — Windows-friendly packaging

Only after the engine and Web UI are stable:

- define a supported Python version for desktop packaging;
- evaluate a simple launcher/package approach;
- keep Telegram session/API secrets outside distributable artifacts;
- validate long paths, invalid Windows filename characters, Unicode filenames, and shutdown behavior;
- document upgrade and backup behavior.

Packaging is deliberately last: a polished installer around an unreliable engine would make debugging harder.

## Completion gate for every phase

A phase is not complete because code was written. It is complete only when:

- targeted tests pass;
- full tests pass;
- code-quality checks pass;
- CI is green;
- behavior is demonstrated against the acceptance criteria;
- docs/config examples match the implemented behavior;
- no credentials or Telegram session files are committed.

Use `verification-before-completion` before making a final success claim.
