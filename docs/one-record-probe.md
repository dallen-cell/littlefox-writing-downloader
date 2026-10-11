# One-record local CDP probe

This probe is for one human-controlled validation on a suitable Windows session computer (resettable/disposable machines are the intended deployment target, not a particular school computer). It attaches to an already-running, manually authenticated Chrome debugging session and reads the DOM of one manually opened Writing detail **popup**. The Little Fox manager/main window remains open alongside that popup. It never navigates, clicks, fills, submits, evaluates work, writes to Little Fox, discovers classes, follows pagination or creates a correction file.

Do not run it in Codex Cloud. Do not paste full URLs, field values, HTML, Writing text, screenshots or student details into GitHub, chat, logs or shared Drive documents.

## Provisional local setup for the first probe

This manual recipe assumes `py -3.11` and pip are available **for the current session only**. It is not a portable end-user launcher, and must not be treated as the final deployment solution. If Python, package installation, or Chrome debug flags are unavailable, stop and record that precise environmental obstacle; do not assume the machine has the prerequisite or ask for administrator rights. Before routine release, establish a repeatable, no-admin session bootstrap based on the existing Recordings workflow.

Open Command Prompt in the repository:

```bat
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[probe,test]"
.venv\Scripts\python -m unittest discover -s tests -v
```

The Playwright package is required only for this optional probe. Do **not** run `playwright install`: the probe attaches to the locally installed Chrome and needs no downloaded browser.

## Human-controlled browser preparation

Start a dedicated local debugging profile (no need to close other unrelated Chrome profiles):

```bat
"%ProgramFiles%\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\LittleFoxWritingProbeChrome" "https://school.littlefox.co.kr/main/"
```

If Chrome is installed elsewhere, use its actual local executable path without changing the remaining arguments. In that Chrome window, the human operator must:

1. Sign in normally using the approved local workflow. Never give credentials or cookies to the script.
2. Navigate normally through the main manager site to exactly one Writing detail popup.
3. **Keep the main manager window and Writing popup open.** The probe selects by the observed numbered DOM field families, not tab count or order. Other ordinary tabs do not block it; two qualifying Writing detail popups do.
4. Visually confirm the intended popup before running the command below.

## Run exactly one read-only preflight

In a second Command Prompt, from the session's working directory:

```bat
.venv\Scripts\littlefox-one-record-probe.exe --cdp-endpoint http://127.0.0.1:9222
```

The expected first-run exit status is `3`, meaning the read-only acquisition completed but interpretation/export remains blocked. A status of `2` is local command configuration error. Attach/read failures are sanitized and also return `3`.

The JSON output contains only:

- whether local CDP attachment succeeded;
- how many open pages matched the three numbered field families;
- source-state count;
- whether writer, timestamp and source-HTML fields were nonempty;
- aggregate HTML element and attribute counts, plus the number of source states containing elements; never tag names, attribute names, values or text;
- sanitized blocker codes; and
- confirmation that no export was created.

It does not print or save the page URL, writer/timestamp values, source HTML, student Writing, student identity, tag names, attribute names or other seven-field values. Structural diagnostics are numeric aggregates so even arbitrary person-like element or attribute names cannot enter serialized output.

The offline implementation was validated with the complete 42-test Stage 1–2–probe suite, `pip check`, byte compilation and console-help execution. Tests include arbitrary synthetic person-like tag and attribute names and prove they do not serialize. They use synthetic fake pages only; they do not start Chrome or connect to a website.

## What this run can and cannot prove

This preflight can prove local CDP attachment, unique-popup matching, numbered `contents_N` / `writers_N` / `regdate_N` alignment, field presence and aggregate structural counts with no scripted page action. It cannot reveal structural names, or prove real writer-to-actor mappings, timestamp parsing/timezone, metadata selectors, outstanding/reviewed status, actual correction signatures or semantics, cleaned text, the seven fields, or a safe export. Those remain explicit blockers rather than guesses.

Stop after this one command. A per-session restart/reinstallation requirement is not evidence of a permanent school-PC dependency. Do not browse to another record for the probe, rerun across students, or work around a blocker by adding selectors locally. Record only the sanitized JSON and the human's pass/block assessment for review before any next bounded change.


## Preferred session-computer package

The hand-written `py -3.11` commands above are provisional development instructions. For a resettable Windows session computer, use the separately built `LittleFoxWritingSession_Current.zip` from the Windows GitHub Actions artifact. Unzip it into a local writable folder, run `setup_session.cmd`, then run `run_one_record_probe.cmd`. The setup follows the existing Recordings session bootstrap: per-user Python installation if missing, `.venv`, and Playwright. The launcher discovers Chrome, opens the real Little Fox main page in a dedicated local debugging profile and waits for the human to sign in and manually open **one** Writing detail popup before calling the probe. Leave the main window open. It creates no export. Refer to the package's `README_SESSION.txt` for local privacy/cleanup rules.

Internet access is needed for the Python installer or pip packages if not available locally. If session policy blocks the install, CDP or Chrome startup, stop and record the environmental blocker. Do not request administrator elevation or move authentication to a server to work around it.
