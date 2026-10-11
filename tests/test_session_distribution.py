"""Offline tests for the separate resettable Windows session distribution."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_session_package.py"


class SessionDistributionTests(unittest.TestCase):
    def test_build_contains_launchers_and_only_source_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "LittleFoxWritingSession_Current.zip"
            completed = subprocess.run(
                [sys.executable, str(BUILDER), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with ZipFile(output) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), len(set(names)))
                for necessary in (
                    "README_SESSION.txt", "setup_session.cmd",
                    "setup_session.ps1", "run_one_record_probe.cmd",
                    "pyproject.toml", "README.md",
                    "src/littlefox_writing/one_record_probe.py",
                    "docs/one-record-probe.md",
                ):
                    self.assertIn(necessary, names)
                self.assertTrue(all(
                    name in {
                        "README_SESSION.txt", "setup_session.cmd", "setup_session.ps1",
                        "run_one_record_probe.cmd", "pyproject.toml", "README.md",
                        "docs/one-record-probe.md",
                    } or name.startswith("src/littlefox_writing/") and name.endswith(".py")
                    for name in names
                ))
                self.assertFalse(any(
                    marker in name.casefold()
                    for name in names
                    for marker in (".venv", "chrome-profile", "downloads", "__pycache__", ".git", ".env")
                ))
                self.assertIn("InstallAllUsers=0", archive.read("setup_session.ps1").decode())
                self.assertIn("playwright==1.62.0", archive.read("setup_session.ps1").decode())
                self.assertIn("--remote-debugging-port=9222", archive.read("run_one_record_probe.cmd").decode())

    def test_builder_never_overwrites_a_previous_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "LittleFoxWritingSession_Current.zip"
            output.write_text("existing distribution", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(BUILDER), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing distribution")


if __name__ == "__main__":
    unittest.main()
