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

## Stage 1 offline demo

Python 3.11 or newer is required. Install the local package without dependencies:

```bash
python -m pip install --no-deps -e .
python -m unittest discover -s tests -v
```

Preview synthetic records (does not create a ZIP):

```bash
littlefox-writing --demo --all-classes --within 7
```

Create a new synthetic ZIP only after reviewing the preview:

```bash
littlefox-writing --demo --all-classes --within 7 --output synthetic-writing.zip --yes
```

See [Windows session-PC setup](docs/windows-session-pc.md) and the [Stage 1 implementation report](docs/stage1-implementation.md). No live-browser functionality exists in Stage 1.
