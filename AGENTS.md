# Codex project instructions

## Project and current authorisation
Develop a **read-only Python downloader** for outstanding student Writing in the authenticated Little Fox manager website.

**Current approved boundaries (2026-10-11):** Stages 1 and 2 are completed offline; **one tightly bounded Stage 3 read-only local Writing-record validation** is approved following the proportionality review. Codex Cloud may develop a small local CDP probe with synthetic tests, but must **not** access a live Little Fox session itself. A human on a suitable Windows session computer can later test one manually opened, authenticated Writing detail page with read-only DOM access only. Class-wide collection, Stage 4 and website mutations remain unauthorised.

Read `docs/requirements.md` and **current** `docs/one-record-validation.md` before further coding. Previous `docs/stage1-handoff.md` and `docs/stage2-handoff.md` describe completed offline stages. These are the code contract; the Google Drive Little Fox Site Map remains the authoritative technical research record.

## Portable session-computer requirement
- **Deployment target is any suitable Windows session computer**, not a named school machine. Assume user profiles and locally installed tools may be reset/removed between visits; do not depend on machine-specific paths, permanent installs, administrator privileges or persistent authentication.
- Reuse the established Recordings project's proven session bootstrap/launcher where appropriate after inspecting it. Avoid imposing a new installer or repeated setup burden merely because the development machine has Python.
- The current Python 3.11/virtualenv/manual Chrome commands are an **interim probe procedure**, not evidence that the final session-computer workflow is usable. Before release, verify a portable or reliably bootstrapped launcher on a resetting Windows session environment. Do not assume that Python or Playwright is preinstalled.

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
- Next priority: a minimal local read-only CDP probe of **one human-opened Writing detail page**, not further synthetic parser expansion. Codex Cloud prepares the probe offline; actual site access occurs only when a human runs it locally. A failed acquisition gate must stop with a sanitized diagnostic, not trigger speculative code or broader crawling.

## Git and handoff discipline
- **GitHub is canonical for source and tests**; Google Drive is canonical for Site Map records and approved design. Do not maintain competing authoritative source archives.
- Work on a feature branch, produce reviewable changes and report test commands/results honestly.
- Commit durable milestones. Do not rely on Codex task conversations or uncommitted workspaces persisting.
- Limit scope to the authorised stage. Propose alternatives or escalation only when a verified blocker appears.
- Do not edit the existing known-good Recordings downloader. Its archived ZIP is an external reference, not something to blindly copy into this repository.
- No speculative new dependencies, infrastructure or workflows without a demonstrated need.
