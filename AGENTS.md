# Codex project instructions

## Project and current authorisation
Develop a **read-only Python downloader** for outstanding student Writing in the authenticated Little Fox manager website.

**Approved as of 2026-10-11: Stages 1 and 2 OFFLINE ONLY.** Stage 1 is merged and independently CI-tested; Stage 2 authorises Python state/markup parsing and synthetic regression tests. You may **not** sign in to Little Fox, perform live browser/CDP/site access, acquire real submissions, implement the authenticated adapter, or proceed to Stages 3–4 without separate authorisation. Do not confuse offline development approval with live integration authority.

Read `docs/requirements.md` and the **current** `docs/stage2-handoff.md` before Stage 2 work; `docs/stage1-handoff.md` is the completed historical Stage 1 task. These are the code contract; the Google Drive Little Fox Site Map remains the authoritative technical research record.

## Safety and data
- Never grade, comment, review, submit, evaluate, save, delete, alter statuses, award stickers, complete lessons, or use any site write controls.
- Do not use live Little Fox accounts, passwords, cookies, session tokens, authentication headers or remote/browser proxies in Codex Cloud.
- Do not collect, commit, log or include real student names, codes, writing, teacher comments, captures, full student-specific URLs or any operational student data in the repository, issues or pull requests.
- Synthetic student examples only. No guessed student, class-instance or Writing-record identifiers. Later read-only navigation must use actual site-provided controls and links.
- Do not introduce server deployment, Google Colab, Chrome extensions, Project 019 intake, automated grading or bulk extraction beyond the approved v1 scope.

## Implementation conventions
- Python with a small, modular architecture and transparent unit tests. Prefer standard-library code for pure date filtering, output formatting and ZIP production.
- Respect the agreed seven output fields **exactly**, including Initial / Revision — Tagged / Revision — Clean. Do not insert dates, prompts, teacher feedback, metadata or history into the correction text.
- Separate browser acquisition, queue classification, text-cleaning rules, filter logic and output generation.
- Fail explicitly on ambiguous or unsupported status, date or semantic correction markup; do not silently lose student text or claim incomplete scans are empty.
- During Stage 2, implement only offline source-state interpretation and conservative markup cleaning from synthetic fixtures; **never open Little Fox**. Do not add a live browser connector or assume undocumented site-side markup semantics.

## Git and handoff discipline
- **GitHub is canonical for source and tests**; Google Drive is canonical for Site Map records and approved design. Do not maintain competing authoritative source archives.
- Work on a feature branch, produce reviewable changes and report test commands/results honestly.
- Commit durable milestones. Do not rely on Codex task conversations or uncommitted workspaces persisting.
- Limit scope to the authorised stage. Propose alternatives or escalation only when a verified blocker appears.
- Do not edit the existing known-good Recordings downloader. Its archived ZIP is an external reference, not something to blindly copy into this repository.
- No speculative new dependencies, infrastructure or workflows without a demonstrated need.
