# Windows session-computer setup (Stage 1 offline demo)

Stage 1 is offline and synthetic only. It does not install a browser, attach to Chrome, contact Little Fox, or accept operational student data.

## Provisional installation for the current Windows session

The commands below assume Python is available. This is an offline **development demonstration**, not a validated portable deployment or final launcher. Session-computer compatibility must not rely on a persistent Python installation or administrator rights.

Open Command Prompt in the repository and run:

```bat
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[test]"
.venv\Scripts\python -m unittest discover -s tests -v
```

The normal Windows installation (`pip install -e .`) installs the first-party `tzdata` package because Windows does not normally provide the IANA timezone database used by Python's `zoneinfo`. The `[test]` extra above also installs `tzdata` on non-Windows development machines so the fallback can be tested with the system timezone database disabled. Do not use `--no-deps`; that would omit required Windows timezone data.

Preview a synthetic export (no ZIP is written):

```bat
run-demo.cmd --within 7
```

After reviewing the preview, explicitly confirm creation and choose a new filename:

```bat
run-demo.cmd --within 7 --output synthetic-writing.zip --yes
```

Existing ZIP files are never overwritten. Delete or rename an old *synthetic* export yourself, or choose another output name.

## Current scope and separate read-only probe

The narrowly authorised one-record probe uses a human's manually authenticated Chrome session on a suitable Windows session computer and attach local Python/Playwright through a localhost CDP debugging port. Credentials, cookies, student data, and browser profiles must remain outside this repository. Stage 1 has no Playwright dependency and contains no operational browser adapter.


## Separate session version now provided

The project builds `LittleFoxWritingSession_Current.zip` using `tools/build_session_package.py`; the Windows CI job publishes the ZIP as an artifact. Its `setup_session.cmd`/`setup_session.ps1` use the established Recordings session-computer bootstrap (current-user Python, virtual environment and pinned Playwright). `run_one_record_probe.cmd` launches the user-controlled Chrome debug profile and the existing one-record read-only probe.

This is a **probe distribution**, not the full Writing downloader. The eventual operational version will retain a separate session-computer launcher. Do not treat the manual Stage 1 demo steps above as mandatory prerequisites on every session computer.
