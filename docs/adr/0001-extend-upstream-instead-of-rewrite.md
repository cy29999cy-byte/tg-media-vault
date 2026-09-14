# ADR 0001: Extend the upstream Telethon downloader instead of rewriting from zero

- Status: Accepted
- Date: 2026-09-15

## Context
The repository already contains a working async Telethon downloader, YAML configuration, multi-chat support, download pacing, checkpoint/resume logic, SQLite history, a NiceGUI Web UI, tests, and project tooling. Rebuilding these capabilities from zero would spend effort recreating solved infrastructure and would increase regression risk.

## Decision
Use the current repository as the product base and evolve it incrementally. Prefer focused additions and refactors protected by tests. Preserve compatibility with the existing configuration where practical.

Before implementing a new subsystem, search for reusable Agent Skills and mature open-source components, but only adopt them when their maintenance state, license, security posture, and fit are understood.

## Consequences
### Positive
- Faster path to a usable product.
- Existing tests and behavior become regression guards.
- Web UI, history, pacing, and resume logic remain reusable.
- Easier comparison with upstream fixes.

### Negative
- Some existing architectural debt must be carried and reduced incrementally.
- Media taxonomy and state persistence were not originally designed around all desired categories.
- Large functions in `media_downloader.py` may need later decomposition.

## Guardrails
- Do not replace Telethon, configuration, database, or Web UI merely for stylistic preference.
- Architectural replacements require a separate ADR with measurable justification.
- Keep the MIT license and upstream attribution intact.
