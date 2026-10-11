# Little Fox Writing Downloader

Read-only Python downloader for outstanding student Writing submissions, intended to support **human-led correction**.

## Status
- Design: approved 2026-10-11.
- Implementation: **Stages 1–2 offline complete and CI-tested on Linux/Windows.** Next: narrowly authorised, human-controlled local read-only acquisition proof for **one manually opened Writing record**. No full live downloader or multi-class operation yet.
- Source of truth for code: this private GitHub repository.
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
