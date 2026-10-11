# Next milestone — one-record read-only acquisition proof

**Decision: 2026-10-11.** After a proportionality review, freeze the Stage 1–2 synthetic foundation. The next milestone is **one real Writing record**, not comprehensive Writing mapping or another offline parser sprint.

**Scope of authorisation:** prepare a *minimal local* Chrome/CDP read-only probe and, when a human-authenticated Windows session-computer browser session is available, conduct **one human-controlled, single-record read-only validation**. Do not operate a live browser from Codex Cloud or ChatGPT, remotely authenticate, change site state, or expand to class-wide crawling. A multi-class downloader, grading and broad data collection are **not authorised**.

## Execution environment boundary
The target is a **resettable Windows session computer**, as with the existing Recordings downloader; no specific school PC, fixed workstation or persistent local account is required. The present manual Python/virtualenv/Chrome instructions demonstrate only an initial local probe and do **not** satisfy final portability. Plan reuse of the proven Recordings session-launch approach, and validate absence of prerequisites or their safe per-session bootstrap when practical. This is not permission for new framework/infrastructure work before the one-record acquisition result.

## Why this is the priority
GitHub source, Stage 1 formatter/ZIP/filter and Stage 2 synthetic state/markup model exist; Linux and Windows CI pass. The missing critical proof is acquisition and interpretation of **actual** Little Fox source. Synthetic `data-lfw-synthetic-rule` annotations are **not** observed website markup; stop refining invented examples until evidence exists.

## Smallest practical test
1. **Cloud coding, offline:** In a fresh feature branch, add only a tiny optional local Playwright/CDP read-only probe plus usage notes and synthetic offline tests. Reuse the human-started Chrome / localhost CDP pattern of the established Recordings downloader where verifiable; don't modify that downloader. Do not add a full class resolver, pagination, crawler, grading tool, GUI or server.
2. **Local execution, later:** Human launches the approved Chrome debugging profile, signs in normally and **manually opens one Writing detail page** via the site's navigation. The script attaches to that existing local tab; it does not initiate login or guess site URLs or IDs.
3. **Read-only preflight:** Confirm attach, expected signed-in Writing detail page, and availability of numbered source-state elements/fields. Read DOM only (e.g. `document.location.href`, `#contents_N`, `#writers_N`, `#regdate_N`). No `click`, `fill`, `submit`, `goto`, network POST, evaluation endpoint, or mutation. Do not publish full record URLs or student-bearing HTML to cloud, repo, logs or Drive.
4. **Single-record interpretation:** Locally determine latest actor, latest student source, outstanding/reviewed status, submission time, title, actual genre, class/name/code, and inherited annotation signatures **only where directly verified**. Compare extracted text against a human read of the same page. If source values or text rules are unknown, report **BLOCKED** with a sanitized reason rather than guessing.
5. **Output gate:** Only if the candidate is genuinely outstanding and all seven fields/clean text can be independently verified, preview locally and explicitly confirm writing **one** seven-field UTF-8 text file. Otherwise stop with the evidence gap; a partial or blocked case is a useful test outcome. No upload or automatic remote transfer.

## Evidence and confidentiality
Report non-sensitive diagnostics only: Chrome attach success/failure layer, number of source states, whether writer roles and timestamp are supported, relevant correction categories/structural patterns **sanitized without real content**, export pass/block, and exact next blocker. Keep any student-bearing local output outside GitHub/Drive mapping, Codex Cloud, and logs. Do not persist raw DOM or screenshots as shared source artifacts. No guessed actor encodings or hypothetical HTML rules may be treated as live findings.

The first clean initial submission can prove the acquisition path. A naturally occurring revision with markup is a **separate subsequent** representative case if needed; do not hunt extensively for it in this initial one-record proof.

## Stop conditions
Stop after one page, one record, and one candidate file (or documented block). Stop immediately if CDP attach fails, authentication is unavailable, the page is not reliably identified, an operation might write to the website, source metadata is contradictory, or correction-target semantics are uncertain. Do not respond to those failures by building more synthetic infrastructure.

## Acceptance for this milestone
- Human-authenticated local CDP attach verified.
- Actual Writing detail source read with zero site mutations.
- Latest state/source and required metadata correctly matched to the visible page.
- One seven-field text file correct on human inspection **or** a precise, sanitized blocker that directs the next small fix.
- Stage 1–2 CI remains green; no Stage 4 expansion.

## Codex task boundary
Prepare only the **local probe** and focused offline tests in a feature branch/PR; do **not** claim a live validation from Codex Cloud. Keep GPT-5.6 Sol Light as default. Separate local execution is necessary and must be done by a human with the approved browser. Do not merge without review.

## Evidence reuse and sequential acceptance gates

The existing canonical Writing technical map (Google Drive document ID `1_MIinu-WsJc0FVI4mGMae8UYFWMBuRj7coxmSm6t8c4`) already documents historically observed versioned Writing source states, validated source-HTML acquisition, revision markup carry-forward, and a 15-case rendered-text regression. Reuse those observations as historical evidence; do not re-map the site from scratch or assume all details are unchanged.

**Gate A — current packaged connectivity preflight:** prove local Chrome attachment and field presence on one human-opened page. The current report has only aggregate counts and fixed blocker codes. Exit status 3 alone cannot distinguish a successful read from an acquisition failure; examine the JSON. It neither classifies Writing nor exports a seven-field file.

**Gate B — separately bounded single-record interpretation:** only after the preflight succeeds, verify one record's source-state actor, outstanding status, required metadata and correction text against normal UI observations. Treat unknown source values and unsupported markup as blockers. The current probe does not implement this gate.

**Gate C — future batch operation:** class discovery, pagination, date-based selection and ZIP export require separate approval after the one-record verification. Do not extend synthetic parser development while Gate A remains untested.

## Gate B experimental local adapter after live Gate A success

The corrected Writing popup/CDP Gate A was confirmed in one authenticated
user-operated session (three embedded source states, source/writer/time fields
present). `run_one_record_review.cmd` in the separate session package now
offers a minimal human-verified one-record review. It reads only the already-open
popup; the operator must establish source actors, latest outstanding status,
five context/history fields and exact corrected-target text by comparing with
normal site pages. Unknown markup or unsupported state chains block rather than
export. Preview stays on the local computer. A single new seven-field TXT
requires explicit operator confirmation; no automatic site traversal.
This feature is offline-tested, not yet live-accepted. See
`docs/one-record-gate-b.md`. Gate C remains separate and unauthorised.
