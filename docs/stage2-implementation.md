# Stage 2 offline state and markup implementation

Stage 2 accepts already acquired, normalized **synthetic** state chains. It validates chronology, decides whether the latest state is an outstanding student submission, derives Initial / Revision status from the chain and raw tag presence, and returns either a Stage 1-compatible record or a structured excluded/blocked decision. It contains no browser, network, selector or Little Fox actor-value implementation.

## Evidence boundary

| Source-grounded fact used | Synthetic convention used only for tests |
| --- | --- |
| A task has an ordered mixed student/teacher state chain. | `Actor.STUDENT`, `Actor.TEACHER` and `Actor.UNKNOWN` are already-normalized adapter inputs. No site value mapping is implied. |
| A final teacher state means no student submission is currently awaiting review. | Synthetic integer source indices exercise ordering; parity is never used to infer actors. |
| A student state after teacher review is a revision; inherited tag presence is detected before cleaning. | `data-lfw-synthetic-rule` is an invented, clearly namespaced fixture signature and is not claimed to exist on Little Fox. |
| Exact latest-student source HTML and timestamp must be used. | Fictional metadata, HTML and status strings are created in unit tests only. Raw status strings are diagnostic and never used to infer actors or pairing. |
| Genuine correction signatures and several correction semantics remain unverified. | Three narrow fixture rules have locally defined semantics so pipeline behavior can be tested without claiming site compatibility. |

A future adapter must prove the mapping from actual writer values to normalized actors, chain completeness/reliability, source-index ordering and real correction markup signatures. Unknown actors, unsupported status evidence, incomplete chains, duplicate/missing/non-monotone indices, non-alternating actors and unsafe markup all return structured `BLOCKED` decisions. Recognized inherited markup in a purported first submission also blocks because there is no preceding review to explain it.

## Markup rule registry

All signatures below use the hypothetical `data-lfw-synthetic-rule` test attribute.

| Rule | Stage 2 behavior | Provenance |
| --- | --- | --- |
| `struck-deletion` | Supported for synthetic tests: visible in rendered text and omitted from correction-target text. | Hypothetical fixture convention only. |
| `empty-insertion-placeholder` | Supported only when empty; omitted from correction-target text. Nonempty content blocks. | Hypothetical fixture convention only. |
| `empty-punctuation-placeholder` | Supported only when empty; omitted from correction-target text. Nonempty content blocks. | Hypothetical fixture convention only. |
| `case` | Blocked; no capitalization behavior is guessed. | Known tool category, genuine semantics/signature unresolved. |
| `erase`, `spelling`, `word-form`, `word-replacement`, `insert-word`, `punctuation`, `undo-reset` | Blocked. Categories do not establish safe cleaning semantics. | Known tool categories, genuine semantics/signatures unresolved. |
| Any other rule, semantic attribute, unsupported tag, nested annotation or malformed structure | Blocked. | Unknown. |

Plain text and attribute-free `p`, `div`, `br`, `span`, `strong`, `em`, `b` and `i` are supported. Entities are decoded once. Literal source newlines and U+2060 are preserved. `<br>` produces one newline; paragraph transitions produce two. These facts remain distinct, so a trailing `<br>`, a paragraph transition and a literal source newline can intentionally produce three newlines. Rendered visible text and correction-target text remain separate internal values and are never added to the seven-field export.

### Review corrections

- Pending `HTMLParser` input is checked before `close()` can reinterpret it as text. Truncated terminal tags, comments, declarations and entities now block as `malformed_html`; correctly encoded `&lt;` remains student text.
- Empty-only insertion and punctuation placeholders reject any child markup, including `<br>`, as `nonempty_placeholder`. Genuinely empty placeholders remain supported.
- Byte-empty source HTML and structurally empty correction targets block as `missing_student_html`. No trimming is performed: genuine whitespace, literal newlines and supported paragraph/break formatting remain unchanged when nonempty.

## Validation

Run:

```bash
python -m pip install -e ".[test]"
python -m pip check
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

The Stage 1 suite remains included. Stage 2 adds synthetic chronology, long-chain, structured-blocking, tag-before-cleaning, exact-text, unsupported-Case, timestamp propagation, seven-field and no-blocked-export coverage. After the parser review corrections, the complete local suite contains 35 passing tests.

## Unresolved gates and exact next action

Unresolved: actual `#writers_N` actor values; genuine markup signatures for every correction tool; Case and other correction semantics; whether source indices are globally stable/contiguous; real full-year timestamp parsing and Korea timezone mapping; and live chain completeness/pagination behavior.

The exact next action is review and CI validation of this offline PR. Any subsequent Stage 3 action requires separate user authorization and a bounded plan for representative, read-only validation through a human-authenticated local Chrome session. No live adapter or site access should begin under Stage 2 authorization.

