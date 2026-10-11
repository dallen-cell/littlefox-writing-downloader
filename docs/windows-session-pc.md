# Windows session-PC setup (Stage 1)

Stage 1 is offline and synthetic only. It does not install a browser, attach to Chrome, contact Little Fox, or accept operational student data.

## Install for the current Windows session

Open Command Prompt in the repository and run:

```bat
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --no-deps -e .
.venv\Scripts\python -m unittest discover -s tests -v
```

Preview a synthetic export (no ZIP is written):

```bat
run-demo.cmd --within 7
```

After reviewing the preview, explicitly confirm creation and choose a new filename:

```bat
run-demo.cmd --within 7 --output synthetic-writing.zip --yes
```

Existing ZIP files are never overwritten. Delete or rename an old *synthetic* export yourself, or choose another output name.

## Planned later-session pattern (not implemented or authorised here)

A later approved stage is expected to use a staff member's manually authenticated Chrome session on the local school PC and attach local Python/Playwright through a localhost CDP debugging port. Credentials, cookies, student data, and browser profiles must remain outside this repository. Stage 1 has no Playwright dependency and contains no operational browser adapter.

