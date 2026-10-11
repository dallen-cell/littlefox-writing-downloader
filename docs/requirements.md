# Little Fox Writing Downloader — Python v1 requirements

Status: **Design approved 2026-10-11**. Stages 1–2 offline development are merged and Linux/Windows CI-validated. A separate narrow approval permits one human-controlled read-only local Chrome/CDP probe against one manually opened Writing detail page; broader acquisition, class discovery and Stage 4 are not authorised. Current handoff: `docs/one-record-validation.md`.

## Goal
Discover latest outstanding student Writing submissions, export clean text for **human-led correction**, and **never** modify Little Fox. Execution target is **any suitable Windows session computer**, including resettable machines used for the Recordings downloader, with human-authenticated Chrome and local Python/Playwright CDP attachment. There is no dependency on a particular school computer. The implementation begins in Codex Cloud using **offline synthetic tests only**.

## Correction output: exactly seven fields
Each exported UTF-8 `.txt` must have:

```text
Class: [class code]
Student: [student display name]
Student Code: [student code]
Title: [Writing task title]
Type: [actual task genre]
Status: [Initial | Revision — Tagged | Revision — Clean]

Writing:
[latest submitted student text with prior teacher markup stripped]
```

Do not add writing prompts, instructions, dates, teacher comments, earlier submissions, original HTML, counts or internal metadata to correction files. Preserve student wording/errors, paragraphs and punctuation. Cleaning annotations is **not** correcting grammar.

Statuses:
- **Initial:** first student round with no earlier teacher review.
- **Revision — Tagged:** student resubmitted after teacher review; recognised inherited correction tags remain in the latest submitted source.
- **Revision — Clean:** student resubmitted after teacher review; no inherited correction tags remain.
Decide status on the original latest source *before* cleaning. Mark ambiguities as blocked, not guessed.

## Class selection
Allow **all currently accessible classes** or a selected subset of current class codes. Discover current classes from site-provided links; do not hardcode a roster or invent class IDs. Report missing/inaccessible selections. Classes without Writing submissions yield zero.

## Submission-date selection
Support one of four modes:
- **Any:** no submission-date restriction.
- **Older than N days:** strictly more than `N × 24 h` old.
- **Within N days:** between zero and `N × 24 h` old, inclusive.
- **Calendar date range:** inclusive start/end dates in `Asia/Seoul`; reject reversed ranges.

Use the **latest student submission's** timestamp, not task creation date or teacher check date. Capture run time once for filter consistency. Apply Korea timezone provisionally to site timestamps without zones; verify against the live UI later. Missing/ambiguous timestamps are blocked when a date filter is selected; no guessing omitted years or ignoring future timestamps.

## Retrieval design: later stages, not Stage 1
1. Use authenticated *human-controlled* Chrome, local Playwright/CDP, and current class discovery based on the known Recordings pattern.
2. Obtain student codes and class instances from site-provided class/student/Homework links; traverse every Writing history pagination page.
3. A Writing history row is a persistent student-task record (`bsPID`) with multiple student/teacher rounds, not a new record per attempt. The task's real **Type** is the genre supplied in the history/task field, not generic `Writing`.
4. The Writing detail contains ordered mixed actor states under `#contents_N`, `#writers_N`, `#regdate_N` and related fields. Include only the latest student round that has **not** been followed by a teacher review. Do not treat all historical Try Again records as outstanding.
5. Use exact `#contents_N.innerHTML` for the correct latest student source index. Do not assume the highest index is a student.
6. Detect inherited teacher tags before deriving cleaned text; faithfully preserve student wording and paragraph breaks. Known markup families: Case, Erase, Spelling, Word Form, Word Replacement, Insert Word, Punctuation, Undo. Some text semantics (notably Case) remain unverified. Fail closed on unsupported semantic markup rather than invent replacements.
7. Deduplicate within each run on persistent record identity **and** latest source round; no cross-session downloaded database in v1.

No authenticated site testing is authorised during Stages 1 or 2.

## Portability and session-computer deployment
- Treat disposable/resetting Windows session computers as the primary supported environment, not a single named school computer. Local profiles, Python installations and packages may be absent each visit.
- The eventual launcher/setup must be repeatable without assuming administrator rights, persistent machine state, or preinstalled Python/Playwright. Verify a portable runtime or bounded per-session bootstrap that can be launched from a user-controlled working folder; reuse verified practices from the established Recordings downloader rather than inventing a parallel installer.
- Chrome sign-in remains manual and local, and any debugging profile is session-scoped. Neither authentication state nor sensitive student output can depend on machine persistence. Save operational exports to a user-selected suitable destination.
- Current `py -3.11`/pip/virtualenv instructions are provisional probe instructions, **not proof** of an acceptable final session-computer installation. Portability acceptance requires testing on a resetting Windows session environment.

## Launcher, archive and error handling
- Minimal command-line or text-menu interaction, plus a simple Windows launcher; no custom web GUI.
- Offer preview/dry-run and explicit confirmation before creating the batch.
- Write **one ZIP** with UTF-8 text files grouped under class folders; safe deterministic file names with collision handling. No manifest or diagnostics inside the correction ZIP by default.
- Do not overwrite existing exports. Repeated downloads of still-outstanding Writing are allowed.
- Report discovered/selected/scanned classes, students checked, outstanding records, date-filter matches, blocked/ambiguous records, errors and exported counts. Do not report failed scans as empty.
- Any partial export must be clearly identified and explicitly confirmed. Operational ZIP remains local until the user manually transfers it into an appropriately restricted Drive destination.
- No automated grading, website changes, remote server deployment or automatic Drive upload.

## Development-stage gates
Stage 1: Completed and merged. Pure filters, CLI, seven-field formatter, synthetic ZIP, errors and Linux/Windows CI.
Stage 2: Authorised for **offline-only** normalized state chronology, outstanding classification and conservative markup/text rules with synthetic fixtures; use `docs/stage2-handoff.md`. Actual site actor encodings and markup signatures still require later validation and must not be invented.
Stage 3: A **single human-controlled, read-only, manually opened Writing record probe** is authorised. Broader live adapter, automated class discovery and class-wide retrieval remain unauthorised; see `docs/one-record-validation.md`.
Stage 4: Not authorised — controlled multi-class live validation.

## Release criteria
Live acceptance gates, requiring separately authorised validation: complete current-class coverage and pagination; accurate latest student-vs-teacher chronology; correct Initial/Revision statuses; verified correction-markup stripping without student-text loss; correct age/date boundaries; true task genre; exactly seven fields; comprehensive exceptions; zero site mutations; and reproducible setup on a resetting Windows session computer.

## Authoritative references
- [Approved full design and acceptance criteria](https://docs.google.com/document/d/1bZK24qxZ3d8e-8xYX93jfQ4FOHqh2DAbcm9EbR6aRxs/edit)
- [Little Fox Writing technical map](https://docs.google.com/document/d/1_MIinu-WsJc0FVI4mGMae8UYFWMBuRj7coxmSm6t8c4/edit)
- [Recordings baseline, preserved ZIP](https://drive.google.com/file/d/1JVJulnvU6PxZdsoL3IgeHJgZjkcMf1rB/view)


## Separate session-computer deliverable (2026-10-11 refinement)
In addition to GitHub's canonical source, ship a **distinct resettable Windows session-computer distribution** as a versioned ZIP, following the Recordings project's established `LittleFoxRecordingsSession_Current.zip` model. The verified Recordings reference includes per-user Python setup (`setup_session.cmd` + `setup_session.ps1`), creation of a local virtual environment, pinned Playwright, a dedicated Chrome debug profile and a command launcher. Keep the Writing adapter/classification separate; do not import the Recordings collection business logic.

For now, deliver `LittleFoxWritingSession_Current.zip` with this setup pattern and the **one-record probe only**. Before acceptance of the full downloader, produce/update a distinct session-computer operational launcher supporting the approved class/date choices and ZIP export. The general Python repository is not, by itself, sufficient evidence of operational session-computer readiness. Do not include browser profiles, tokens, student files, `.venv`, or other session state in generated ZIPs. Network access for bootstrap is a documented prerequisite when dependencies are absent; never escalate privileges without explicit approval.
