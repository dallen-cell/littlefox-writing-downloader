# Stage 1 — Codex Cloud offline foundation

**This stage has user approval (2026-10-11). Do not proceed to Stage 2 or live Little Fox access without further instruction.**

Read `AGENTS.md` and `docs/requirements.md` first.

## Required deliverables
1. Small installable Python package, CLI help, explicit synthetic/demo mode and validation of class scope and date-mode options.
2. Pure selection/date-filter functions: strict `older-than`, inclusive `within`, inclusive Korea calendar range, invalid/reversed dates, ambiguous/future timestamps and one reference time per run.
3. Exact seven-field UTF-8 text formatter, retaining student text unchanged after upstream cleaning.
4. ZIP generation for synthetic eligible records, grouped by class; filenames sanitised with stable collision handling and no silent overwrites.
5. Diagnostics that distinguish a complete zero from errors, blocked records and incomplete scans.
6. Offline unit tests and synthetic fixtures, including all date-boundary cases, Unicode, paragraph breaks, seven-field exactness, filename collisions and rerun safety.
7. Concise Windows session-PC installation/launcher documentation, based on the established manual Chrome authentication + localhost CDP pattern but **without** live browser interaction at this stage.
8. Brief implementation report: committed files, test commands and pass/fail results, known limitations and exact Stage 2 work.

## Constraints
- Default to standard library; add `pytest` if useful and justify it. No browser installation or Little Fox network calls just to test pure functions.
- Keep source separate from operational student data. Do not commit any real records or capture files.
- If the previous Recordings ZIP is unavailable to Codex Cloud, use documented interface patterns as design guidance, flag the reuse limitation, and do not invent live implementation findings.
- Work on a reviewable branch and preserve tested source in GitHub.
- Stop when the offline foundation and tests are complete.

## Development environment
Prefer current working Codex Cloud published environment and **GPT-5.6 Sol Light** as the cost-conscious default, escalating only for demonstrated complex parser bugs or critical review. Do not override an existing Codex environment setup without reviewing it.
