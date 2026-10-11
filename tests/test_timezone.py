import os
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest


class TimezoneDependencyTests(unittest.TestCase):
    def test_project_declares_windows_runtime_and_cross_platform_test_tzdata(self) -> None:
        configuration = tomllib.loads(
            (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        )
        project = configuration["project"]
        self.assertIn(
            "tzdata>=2024.1; platform_system == 'Windows'",
            project["dependencies"],
        )
        self.assertIn("tzdata>=2024.1", project["optional-dependencies"]["test"])

    def test_tzdata_fallback_supplies_asia_seoul_without_system_database(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONTZPATH"] = ""
        script = (
            "from datetime import datetime, timedelta; "
            "from zoneinfo import ZoneInfo; "
            "zone = ZoneInfo('Asia/Seoul'); "
            "assert datetime(2026, 1, 1, tzinfo=zone).utcoffset() == timedelta(hours=9)"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
