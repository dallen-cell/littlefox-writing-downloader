# Gate B: one-record local human review (experimental)

**Boundary:** ONE manually opened authenticated Writing detail popup, while the main manager page remains open. Gate A (three source-field families/Chrome CDP) has passed in a real Windows session. This new adapter is an offline-developed experiment and has **not** been validated on real Writing. It performs no site navigation, requests to the website, grading, clicking, form submission, or automatic class scan.

## Use on a Windows session computer

Download the newest GitHub Actions artifact containing `LittleFoxWritingSession_Current.zip`, extract it into a writable folder, and run `setup_session.cmd` if dependencies are not already installed. Open Little Fox through `run_one_record_probe.cmd` (or retain the existing authenticated dedicated Chrome profile), and manually open **one** Writing detail popup. Keep the manager page open.

Then run `run_one_record_review.cmd`. This attaches to existing Chrome without opening another page. It displays **on your own computer only** the raw writer and timestamp field values for each numbered source index; compare each against normal Little Fox version navigation. Explicitly identify student/teacher actors. Confirm the latest student submission is awaiting teacher review. For that same task, transcribe five fields from the actual site: class code, student display name, student code from provided navigation; title and genuine genre from its Writing history row. Do not paste full record URLs anywhere.

The program runs the existing conservative offline interpreter. If the text/markup is unsupported, it **blocks** instead of guessing a correction. If interpretation succeeds, it shows a seven-field local preview; compare every word, spelling error, punctuation mark, paragraph break and annotation to the site. Only after you type YES for exact text comparison may you optionally enter a new, private local `.txt` output path and type EXPORT. The file is created exclusively; existing files are never overwritten. A second read immediately before saving refuses to write if the page source changed.

**Privacy:** The interactive display and preview can contain student data and must stay on the local computer. Do not capture, redirect, upload or paste that display into ChatGPT, GitHub, Drive documentation, or logs. Only the final **SANITIZED SUMMARY** object (outcome, fixed blocker reason and export boolean) is shareable. The utility retains no cookies, saved HTML, local manifests or results, and creates no file unless expressly approved. Keep the resulting correction TXT in a suitably private destination that you control, not a Git checkout or public folder.

## What remains unresolved

The source's `writers_N` values, teacher markup families and metadata selectors have not been automatically mapped. User confirmations are evidence of a human-guided **single** run, not rules to generalize across records. Unsupported real markup will probably block; do not weaken the parser or replace marked text with a guessed interpretation to force an export. A clean first submission might be an easier initial example, but do not hunt broadly for one.

A successful local seven-field preview/file is only the first Gate B acceptance result. Gate C (class discovery, date filtering and batch ZIP) remains **separately unauthorized**. If source, metadata, actor role, chronology or clean correction text is uncertain, stop and share the sanitized blocker only.
