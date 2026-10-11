# Codex Stage 2 — offline Writing states and conservative markup cleaning

**Authorised by user on 2026-10-11 with “proceed”.** Stage 2 code is authorised **offline, synthetic-only**. Do not use authenticated Little Fox, browser/CDP navigation, live requests, real Writing captures, credentials, the school workstation session, or student-bearing fixtures. Those belong to an independently approved later live stage.

**Working baseline:** merged Stage 1 on `main` (Python model/filter/formatter/ZIP/CLI), with Linux and Windows GitHub Actions tests passing. Keep existing behavior intact. Create a **new implementation feature branch** and PR; do not merge automatically.

## Goal and stopping point
Implement and offline-test a conservative pipeline that receives **already acquired, normalized synthetic Writing source-state data** and:
1. identifies the latest student submission still awaiting teacher review, or returns a clear excluded/blocked decision;
2. determines Initial / Revision — Tagged / Revision — Clean from source chronology and **tag presence before cleaning**;
3. derives student-preserving correction-target text from the latest source HTML for only **explicitly supported** markup patterns;
4. emits a record compatible with the existing Stage 1 `SyntheticRecord` / formatter / date filter / ZIP writer, or a structured reason that it cannot do so safely.

Stop with a reviewable PR, tests and implementation report. Do **not** extend into a live discovery adapter, Chrome/CDP connector, website acquisition, broad curriculum mapping or Project 019 producer integration.

## Canonical evidence: what is known
Use repo `AGENTS.md` and `docs/requirements.md` as the software contract. The authoritative sanitized Writing system map is:
https://docs.google.com/document/d/1_MIinu-WsJc0FVI4mGMae8UYFWMBuRj7coxmSm6t8c4/edit

The source map supports:
- A history row is one **persistent task record** (`bsPID`), not one attempt; submitted/checked events can accumulate over many rounds.
- Detail uses a mixed ordered state chain. `#contents_N`, `#writers_N`, `#regdate_N`, `writes_cnt` and related variables expose source states. The **source index refers to one state**, not necessarily a student attempt; the latest source state must be classified by actor. Existing data supports source-index stability in sampled append-only cases, not a global guarantee.
- Normalized teacher review pairing is inferred through **actor/order adjacency**, not an explicit native student-to-review foreign key.
- Existing returned teacher markup can persist in later student HTML, but can also be removed by students.
- Source `#contents_N.innerHTML` is the validated acquisition layer. Distinguish immutable raw source HTML, rendered visible text, and correction-target text. Previous rendered-text parser regression 0.3.0 passed 15 cases, but correction-target derivation 0.3.0-provisional **is not validated for all tags**; Case semantics specifically remain unknown. Do not present those historic regression results as tests that this new Python code has passed.
- Site-confirmed completion uses two consecutive Good reviews, but the downloader's immediate question is only whether a **new student state lacks a later teacher state**. Do not infer outstanding work solely from status label, historical Try Again or one Good.
- Submission time must be from the latest student state, with full-year/zone assumptions remaining later validation concerns.

No real capture bytes are to be copied into GitHub. If Drive cannot be read, continue only from these source-grounded facts and repo requirements, without fabricating HTML selectors, state values or class names.

## Phase A: normalized source-state interpretation (offline)
Define a small typed input shape distinct from Stage 1 `SyntheticRecord`:
- Opaque synthetic record/task identity and display metadata for producing the final seven fields;
- Explicit ordered `source_index` per state; **normalized** actor `student` or `teacher`, plus explicit unknown actor state;
- Exact synthetic `source_html` for each student state; optional parsed full-year timestamp and raw list/status evidence as optional *diagnostic* inputs.
- Clearly document that a future browser adapter must establish which actual `#writers_N` values map to actors; **do not invent site-specific codes, JSON contracts or DOM reader code now**.

Interpret the last state in the observed sequence:
- Last state teacher -> no outstanding candidate.
- Last state student, no preceding review -> Initial candidate only if an unambiguous first submission.
- Last state student with preceding teacher review -> Revision candidate, classify Tagged/Clean based on latest student HTML.
- More complex valid review histories must work without arbitrary round limits; do not mark a reviewed earlier round as outstanding.
- Missing/ambiguous actor, duplicate/unordered source indices, a chronology inconsistency, incomplete/unreliable chain, or unsupported status/markup => structured **BLOCKED**; do not silently select an older round or infer actor by index parity.
- Cases with multiple consecutive student states, or otherwise unclear actor/review pairing, require an explicitly documented conservative decision; do not pretend the actual site semantics are verified.
- Source actor order and latest-student date must remain separate; do not substitute the first history Submitted time.

For output, use the existing Stage 1 record/format model or a simple adapter. Existing filters and ZIP functions must remain unchanged unless a Stage 2 integration test demonstrates an exact bug.

## Phase B: conservative HTML interpretation (offline)
Use Python built-in `html.parser` / `html` if adequate. Avoid a broad dependency, JavaScript browser emulator or copied Project 019 parser. The parser must preserve text, HTML entities, Unicode, literal source newlines and `<br>`/paragraph boundaries under explicit tested rules. Do not double-unescape entities, drop student spelling/punctuation or invent teacher-intended replacements. Handle or explicitly block HTML nesting ambiguities.

Keep separate return values for:
- **rendered visible text** (if known and supported), and
- **correction-target text** for export, with a provenance/rule identifier;
- recognized inherited teacher-markup presence **before** stripping, plus blocked reason if cleaning cannot be proven.
Do not add these internal layers to correction TXT output.

Markup rule registry must be explicit and narrow:
- Allow plain student text and documented harmless structural formatting only after tests.
- Recognize only annotation patterns with concrete supported signatures and validated stripping semantics. If the available sanitized documentation proves the correction-tool *categories* but not the exact HTML signatures, **do not invent selectors/styles**. Implement synthetic examples explicitly marked as hypothetical tests, and leave real signatures pending future permitted validation.
- Known teacher tools: Case, Erase, Spelling, Word Form, Word Replacement/Other, Insert Word, Punctuation, Undo/Reset. **Do not assume those categories share stripping behavior.** Case should be an explicit unsupported/blocked case until directly validated; unknown semantically relevant spans/styles and ambiguous insert/delete markup must fail closed.
- Known provisional rule examples: omit actual struck-through deletion spans and insertion/punctuation placeholders only when the exact rule is supported; otherwise keep as blocked. Never erase unrelated student text just because a span is coloured.
- Treat technical U+2060 and serialized newlines only by tested, clearly explained rules.

If zero real correction-tag signatures can be established offline, that is an acceptable **partial Stage 2** outcome. A reliable conservative parser with explicit unsupported-markup reports is preferable to fabricated coverage.

## Offline acceptance tests
Add synthetic-only regression tests for:
1. Initial submitted/unreviewed state; last state teacher excludes an earlier submission.
2. Student->teacher->student outstanding revision; student->teacher->student->teacher excluded.
3. Several review cycles including Good then resubmission, Try Again then resubmission, and long chains.
4. Ambiguous actors or actor order, unknown status, consecutive student states, missing indexes and duplicate/non-monotone indexes block cleanly.
5. Revision tagged vs clean classification made on raw HTML before text cleanup.
6. Paragraphs, consecutive/trailing `<br>`, HTML entities, Unicode, U+2060, literal source newlines and student typos preserved according to explicit rules; malformed/unknown semantic correction markup blocks.
7. Case markup remains blocked unless independently supported; no guessed corrections to student words.
8. Latest-student timestamp propagation into existing Stage 1 date filtering; no fallback to task creation or teacher time.
9. Structured blocked reasons and no accidental ZIP file for blocked inputs; existing seven-field output remains **exactly seven**.
10. Linux/Windows GitHub Actions existing 16 tests remain green and expanded tests are independently run.

## Deliverables / reporting
Produce a single reviewable GitHub PR on a new Stage 2 feature branch, with:
- changed source modules and synthetic test fixtures;
- concise mapping of **observed source facts** vs **hypothetical fixture conventions**;
- implemented/supported vs blocked markup rule table with exact provenance;
- test commands, number passed, CI result, and failures;
- explicit unresolved gates (raw site actor values, genuine markup signatures, Case behavior, timestamp/year/zone mapping), not presented as already solved;
- `docs/stage2-implementation.md` and exact next bounded action.

Do not edit shared Site Map maps with operational student content. Do not merge the PR yourself. Default to **GPT-5.6 Sol Light** as previously effective; only propose higher-cost effort if objective test failures warrant it.

**Stop condition:** Offline parsing/state normalization plus tests and a reviewable PR; no live site access or broader architecture work.
