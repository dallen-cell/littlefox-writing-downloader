Little Fox Writing — session-computer distribution (one-record probe)

INTENDED ENVIRONMENT
Windows session computers whose programs/user profiles may be reset between visits.
No particular school PC, permanent Python installation or administrator access is assumed.

CURRENT TEST ONLY — NOT THE COMPLETE WRITING DOWNLOADER
1. Unzip THIS package to a local writable folder for the current session.
2. Run setup_session.cmd once for this session.
   - Reuses the Recordings session install pattern: user-local Python 3.13.15
     if unavailable, .venv, Playwright 1.62.0.
   - Requires network access for Python/pip when dependencies are absent.
3. Run run_one_record_probe.cmd.
4. In the dedicated Chrome window, sign in normally, and manually open exactly
   one Writing detail page via the site's controls.
5. Return to the launcher and continue the one-time read-only probe.
6. Copy ONLY the sanitized JSON report for technical review.

The probe NEVER downloads Writing, performs grading, changes website state,
or creates an output file. It intentionally blocks interpretation/export.
Exit status 3 may be expected; check the sanitized report for the failure layer.

Chrome's dedicated local profile is kept in chrome-profile during this session.
Do not upload that folder, tokens, cookies, downloaded HTML or student content.
Remove the unpacked session directory when finished if the computer does not
reset automatically.

SOURCE AND FUTURE OPERATION
This ZIP is a generated session distribution from the canonical public
GitHub repository dallen-cell/littlefox-writing-downloader. Do not copy the
Recordings collection logic into the Writing project. A subsequent session
distribution may launch the validated full downloader once separately
authorised. The current package contains NO class bulk scanning or export.
