# Little Fox Writing Downloader

Read-only Python downloader for outstanding student Writing submissions, intended to support **human-led correction**.

## Status
- Design: approved 2026-10-11.
- Implementation: **Stage 1 offline foundation authorised**; live authenticated Little Fox access and later stages are not authorised by this approval.
- Source of truth for code: this private GitHub repository.
- Site Map research and approved design: [Google Drive design](https://docs.google.com/document/d/1bZK24qxZ3d8e-8xYX93jfQ4FOHqh2DAbcm9EbR6aRxs/edit).

## Read first
- [AGENTS.md](AGENTS.md) — Codex's persistent project and safety instructions.
- [docs/requirements.md](docs/requirements.md) — approved functional/output specification.
- [docs/stage1-handoff.md](docs/stage1-handoff.md) — the next bounded Codex Cloud coding task.

## How development works
Use the existing Codex Cloud environment and work on a reviewable branch. Offline synthetic tests first. Keep real student submissions, identifiers, browser credentials and session state out of GitHub. Later authorised live tests will run with a human-authenticated school Chrome session through local Python/CDP. Do not claim a working live downloader until that separate validation is complete.

The existing Recordings downloader is a reference, preserved separately in Drive. Its working source should not be overwritten.
