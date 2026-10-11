# Automatic acquisition slice

This branch adds a conservative, read-only bridge from one selected class to
Writing record metadata. It replaces the Gate B transcription of class code,
student name, student code, title, and genre only when page links and visible
history-row headings support those values. It does not change the validated
popup/source-state reader.

## Evidence boundary

The implementation uses actual anchors found on the current page. It never
constructs a Little Fox URL. The supported relationships are:

- a class link has one `scpid`; its visible text supplies the class code;
- a student link preserves `scpid` and has one `bsWriterID`; visible text
  supplies the student name and `bsWriterID` supplies the student code;
- a history link preserves those values and has one persistent `bsPID`;
- title comes from a visible `Title` field, or the record link text when no row
  title exists; genre comes only from `Type`, `Genre`, or `Writing Type`.

Missing, conflicting, duplicated, or ambiguous evidence blocks that context.
No actor codes, correction signatures, route URLs, selectors, or values are
guessed. Multiple source states can be attached to one acquired `bsPID` and
passed to the existing Stage 2 interpreter; a revision is not a new task.

The collector reads generic anchors and semantic table headings. The only
intermediate route labels accepted are the documented `Homework` and
`Writing`. These mappings still require local live validation.

## Bounded Windows dry-run

Use the session package on the authorised Windows computer. Run
`run_one_record_probe.cmd` far enough to open and authenticate its dedicated
Chrome session, leave Chrome running, then run:

```text
run_one_class_dry_run.cmd
```

Enter one exact class code shown by the site. The command follows only
same-origin GET links captured from the page, scans at most 100 students and
1,000 current-page record contexts, opens no Writing detail, submits no form,
and creates no files. JSON output contains only counts and fixed blocker codes;
it never serializes acquired names, identifiers, titles, URLs, or genres.

The dry-run deliberately does not scan pagination. It reports
`pagination_scanned: false` and `history_pagination_unverified`, returning
status 3 even when it finds complete current-page contexts. A partial page is
therefore never represented as a complete class acquisition.

## Offline validation and remaining live questions

Synthetic tests verify metadata propagation, one persistent ID across revision
history, title/genre extraction, missing and ambiguous evidence, same-origin
site-provided navigation, bounded no-file behavior, and sanitized diagnostics.

Still unverified on Little Fox: consistency of the live query relationships;
the route and column labels; whether student code is exactly `bsWriterID`;
history pagination; and the join between acquired `bsPID` and popup numbered
source states. Until checked locally, this is discovery evidence—not an
automatic downloader.
