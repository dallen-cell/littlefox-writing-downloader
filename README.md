# Little Fox Writing Downloader

Read-only Python downloader for outstanding student Writing submissions, intended to support **human-led correction**.

## Status
- Design: approved 2026-10-11.
- Implementation: **Stages 1–2 offline complete. Gate A passed. A source-grounded, one-class automatic-acquisition dry-run is offline-tested and pending local live validation.** No automatic export or multi-class operation yet.
- Source of truth for code: this public GitHub repository.
- Site Map research and approved design: [Google Drive design](https://docs.google.com/document/d/1bZK24qxZ3d8e-8xYX93jfQ4FOHqh2DAbcm9EbR6aRxs/edit).

## Read first
- [AGENTS.md](AGENTS.md) — Codex's persistent project and safety instructions.
- [docs/requirements.md](docs/requirements.md) — approved functional/output specification.
- [docs/one-record-validation.md](docs/one-record-validation.md) — **current** one-record, read-only local proof and stop conditions.
- [docs/stage2-handoff.md](docs/stage2-handoff.md) — completed offline Stage 2 task.
- [docs/stage1-handoff.md](docs/stage1-handoff.md) — historical completed Stage 1 instructions.

## How development works
Use the existing Codex Cloud environment and work on a reviewable branch. Offline synthetic tests first. Keep real student submissions, identifiers, browser credentials and session state out of GitHub. Later authorised live tests will run with a human-authenticated Chrome session on a suitable Windows session computer through local Python/CDP. Do not claim a working live downloader until that separate validation is complete.

**Deployment requirement:** Work on resettable/disposable Windows session computers, not a specific school PC. Reuse the proven Recordings downloader's session setup/launcher where feasible. Do not assume permanent Python/Playwright installations, admin rights, or saved Chrome login state. The manual setup described today is only a first diagnostic, not the accepted end-user delivery workflow.

The existing Recordings downloader is a reference, preserved separately in Drive. Its working source should not be overwritten.

## Stage 1 offline demo

Python 3.11 or newer is required. Install the local package and its test extra:

```bash
python -m pip install -e ".[test]"
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

## Stage 2 offline interpretation

The package also contains an offline-only normalized state interpreter and conservative synthetic markup parser. Its rule/evidence boundary and unresolved live-validation gates are documented in the [Stage 2 implementation report](docs/stage2-implementation.md). These modules do not discover or contact Little Fox.

## One-record local validation probe

The optional [one-record probe runbook](docs/one-record-probe.md) describes the separately run, human-controlled Windows session-computer preflight. The probe attaches only to loopback CDP and reads one manually opened detail tab without navigation or mutation. It intentionally blocks interpretation and export until actual actor, metadata and markup evidence is reviewed.


## Resettable Windows session-computer distribution

**The standard delivery format is a separate session ZIP**, based on the established Recordings package model; this is not tied to a school PC. CI creates `LittleFoxWritingSession_Current.zip` as a Windows job artifact. It includes `setup_session.cmd`, `setup_session.ps1`, `run_one_record_probe.cmd`, the Writing package, and `README_SESSION.txt`. Unzip locally, run setup once for the current session, then use the launcher. The bootstrap mirrors the Recordings distribution: user-local Python 3.13.15 if needed, local `.venv`, pinned Playwright, and a dedicated local Chrome debugging profile.

The **current** session ZIP launches only the authorised one-record read-only probe; it cannot download or grade student Writing. No credentials, Chrome profiles or operational exports are included in the archive. The session distribution can be rebuilt from source via `python tools/build_session_package.py`. The eventual full Writing downloader will need its own validated session-computer launcher and packaging without copying Recordings-specific extraction logic.

## Gate B local human review (experimental)

Gate A **passed on one real authenticated session-computer Writing popup**:
Chrome attached and the numbered source fields were readable. The next
separately packaged command, `run_one_record_review.cmd`, is now an
**offline-tested, human-guided, one-record-only** Gate B adapter. It attaches
to the existing Chrome profile, never navigates, requires the human to verify
source actors, latest outstanding state, history title/genre and student/class
context, and previews text locally. It reuses the Stage 2 interpreter and
seven-field formatter, failing closed on unsupported real markup. A new local
TXT can be created only after exact preview confirmation and the word EXPORT.
No full class downloader, automatic mapping or grading is implemented.
See [Gate B runbook](docs/one-record-gate-b.md). Do not copy the private local
review display into chat or any repository.

## One-class automatic-acquisition dry-run

The [automatic acquisition slice](docs/automatic-acquisition.md) replaces the
five manually transcribed metadata values when class, student, and Writing
history links provide consistent evidence. It uses `scpid`, `bsWriterID`, and
persistent `bsPID` without treating revision rounds as separate tasks. The
packaged `run_one_class_dry_run.cmd` performs a bounded, read-only current-page
scan, creates no files, and reports only sanitized counts and blocker codes.
Pagination, live labels, and the record-to-popup join remain unverified; this
dry-run is not yet an automatic downloader.
