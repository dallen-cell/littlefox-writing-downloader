from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from littlefox_writing.cli import run
from littlefox_writing.diagnostics import RunDiagnostics
from littlefox_writing.filters import KOREA


class DiagnosticsTests(unittest.TestCase):
    def test_complete_zero_is_distinct(self) -> None:
        complete = RunDiagnostics(2, 1, 1, 3, 0, 0, 0)
        self.assertTrue(complete.is_complete_zero)
        self.assertIn("Run status: complete-zero", complete.render())
        blocked = RunDiagnostics(2, 1, 1, 3, 1, 0, 1)
        self.assertFalse(blocked.is_complete_zero)
        self.assertTrue(blocked.is_partial)
        failed = RunDiagnostics(2, 1, 0, 0, 0, 0, 0, errors=("scan failed",), incomplete_scans=("DEMO-A",))
        self.assertIn("ERROR: scan failed", failed.render())
        self.assertIn("INCOMPLETE: DEMO-A", failed.render())

    def test_cli_previews_then_requires_confirmation(self) -> None:
        now = datetime(2026, 10, 11, 12, tzinfo=KOREA)
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo.zip"
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = run(["--demo", "--all-classes", "--output", str(output)], now=now)
            self.assertEqual(result, 0)
            self.assertFalse(output.exists())
            self.assertIn("Preview only", stdout.getvalue())

            with redirect_stdout(StringIO()):
                result = run(["--demo", "--all-classes", "--output", str(output), "--yes"], now=now)
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()

