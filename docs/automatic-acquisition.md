# Automatic acquisition slice

This branch adds a conservative, read-only bridge from one selected class to
Writing record metadata. It replaces the Gate B transcription of class code,
student name, student code, title, and genre only when page links and visible
history-row headings support those values. It does not change the validated
popup/source-state reader.

## Evidence boundary

The implementation uses the actual `GoClass` control and anchors found on the
current page. It never constructs a Little Fox URL. The supported relationships are:

- the class list is `/Manager/Class/Lessons.php` in `mainFrame`; an exact
  six-argument `GoClass` control supplies the class selection operation;
- `scno` remains opaque class-navigation evidence and is never treated as the
  Writing class instance `scpid`;
- a student link uses `/Manager/Student/Student_main.php` with one `ulID`;
  its visible text supplies the name and `ulID` supplies the login code;
- Student Homework preserves `ulID`; the Writing launcher then supplies that
  login code as `bsWriterID` together with the actual `scpid`;
- the history and detail links must preserve those identities, and `bsPID` is
  the persistent record rather than a submission attempt;
- title comes from a visible `Title` field, or the record link text when no row
  title exists; genre comes only from `Type`, `Genre`, or `Writing Type`.

Missing, conflicting, duplicated, or ambiguous evidence blocks that context.
No actor codes, correction signatures, route URLs, selectors, or values are
guessed. Multiple source states can be attached to one acquired `bsPID` and
passed to the existing Stage 2 interpreter; a revision is not a new task.

The collector reads exact `GoClass` calls, including the live
`JavaScript:GoClass(...)` form, then opens the manager's Students area. It
matches the requested current-class label to exactly one `sClass` option and
uses the roster's same-page GET filter. If the roster is hidden, it invokes
`show_list()` only after verifying that the live function merely toggles
`#list_div.style.display`; the operational `change_class()` control is never
used. Student profiles are opened only through visible `ViewStudent` controls.
The profile's `StHomework` control and the Homework page's exact `new_win`
Writing launcher lead to the student's history popup.

History records use the site's 12-argument `doView` controls. The collector
activates each current-page control, validates the resulting detail URL and
identity tuple, reads title and genre from the six-column history row, then
returns through browser history. It never reconstructs or evaluates a control's
arguments. A site-supplied, same-origin link is not sufficient permission to
navigate: each GET must also match an exact documented read-only route family
and that family's permitted identity query keys. Unknown paths, extra query
keys (including action/process parameters), credentials, cross-origin links,
and every redirect block before further acquisition.

`DOCUMENTED_ROUTE_POLICY` contains only the confirmed Lessons, Student,
Student Homework, Writing launcher, Writing history, and Writing detail paths.
Student and launcher parameters are exact. Writing history additionally allows
only the observed `_ISmine` and `baBID` keys; Writing detail additionally
requires the observed `page` key. Other parameters block.

`GoList` controls are detected but not invoked: the handoff confirms their
behavior but does not establish which actual list contains a requested class.
If the desired `GoClass` control is not already present while `GoList` controls
exist, the report is `class_list_selection_required`. No `scno`, list, selector,
URL, or parameter is manufactured. This is acquisition failure, never zero.

## Bounded Windows dry-run

Use the session package on the authorised Windows computer. Run
`run_one_record_probe.cmd` far enough to open and authenticate its dedicated
Chrome session, leave Chrome running, then run:

```text
run_one_class_dry_run.cmd
```

Enter one exact class code shown by the site. The command activates only a
matching `GoClass` control and follows confirmed same-origin GET links captured
from the page. It scans at most 100 students and
1,000 current-page record contexts, opens no Writing detail, submits no form,
and creates no files. JSON output contains only counts and fixed blocker codes;
it never serializes acquired names, identifiers, titles, URLs, or genres.

The dry-run deliberately does not scan pagination. Every report carries
`scan_complete: false`, `pagination_scanned: false`, and
`outstanding_writing: null`; it also reports `history_pagination_unverified`
after a current-page scan. Missing navigation and acquisition failures retain
the same incomplete/null result. A partial or failed scan is therefore never
represented as zero outstanding Writing.

## Offline validation and remaining live questions

Synthetic tests verify metadata propagation, permanent suppression of
conflicted class/student/record identities, one persistent ID across revision
history, title/genre extraction, missing and ambiguous evidence, strict
read-only route policies, unsafe endpoints and redirects, bounded no-file
behavior, incomplete-scan reporting, and sanitized diagnostics.

Still unverified live: whether the visible class label uniquely identifies the
desired `GoClass` control; how to choose a `GoList` without an already-visible
class; whether `GoClass` remains in `Lessons.php` and immediately exposes
Student links; the launcher-to-history link shape and any additional history
parameters; history table headings and detail-link extras; pagination; and the
join between `bsPID` and popup numbered states. Until checked locally, this is
discovery evidence—not an automatic downloader.

