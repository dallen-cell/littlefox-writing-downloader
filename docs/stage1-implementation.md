# Stage 1 implementation report

The repository now contains a standard-library offline foundation: domain models, pure Korea-aware filtering, exact correction-text formatting, deterministic safe ZIP production, explicit run diagnostics, and a synthetic-only preview/confirmation CLI.

No Little Fox access, browser automation, real identifiers, or real student data was used. The archived Recordings downloader was unavailable in this cloud checkout, so only the documented future localhost-CDP interface pattern was retained; no live behavior was inferred from it.

## Validation

The editable package and test dependency were installed with `python -m pip install -e ".[test]"`. The offline suite runs with `python -m unittest discover -s tests -v`; all 16 Stage 1 tests passed after review fixes. The installed CLI help, preview-only flow, confirmed synthetic ZIP creation, UTF-8 contents, and overwrite refusal were also exercised. The `tzdata` fallback was tested with `PYTHONTZPATH` empty, proving `Asia/Seoul` remains available without a system IANA database.

## Stage 1 review fixes

- ZIP filenames now follow the approved `student code - task title.txt` convention; student display names remain only in the exact seven-field file contents.
- Allocation reserves each complete archive path using a case-folded Windows-equivalent key. It checks generated candidates until unused, including collisions with natural `(2)` suffixes and class/file casing differences.
- Windows runtime installs the first-party `tzdata` package conditionally. The test extra installs it on every development platform so the no-system-database fallback is covered offline.

## Known limitations and exact Stage 2 boundary

- The three demo records are fictional and generated in memory.
- Cleaning and Initial/Revision classification are upstream contracts only; Stage 1 accepts already-cleaned, already-classified synthetic records.
- Missing timestamps can pass the `Any` mode because no date decision is required. Ambiguous or future timestamps are blocked. Any selected date filter also blocks missing timestamps.
- Partial exports are stopped rather than prompted for by this noninteractive Stage 1 CLI.

The exact next stage, requiring separate authorisation, is to define a non-mutating browser acquisition adapter and validate current-class discovery, pagination, chronology, task genre, timestamp, and correction-markup semantics against an explicitly approved human-authenticated local Chrome session. Do not begin that work under Stage 1 approval.

