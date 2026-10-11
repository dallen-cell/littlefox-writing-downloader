from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from littlefox_writing.archive import archive_names, safe_component, write_archive
from littlefox_writing.filters import KOREA
from littlefox_writing.models import SubmissionStatus, SyntheticRecord


def item(
    record_id: str,
    name: str = "Same/Student",
    title: str = "A:Title",
    student_code: str | None = None,
    class_code: str = "DEMO:A",
) -> SyntheticRecord:
    return SyntheticRecord(
        record_id, class_code, name, student_code or f"SYN-{record_id}", title, "Genre",
        SubmissionStatus.REVISION_CLEAN, "One\n\n둘", datetime(2026, 10, 1, tzinfo=KOREA),
    )


class ArchiveTests(unittest.TestCase):
    def test_sanitises_names_and_handles_collisions_stably(self) -> None:
        records = (item("b", student_code="SYN"), item("a", student_code="SYN"))
        names = archive_names(records)
        self.assertEqual(names["a"], "DEMO_A/SYN - A_Title.txt")
        self.assertEqual(names["b"], "DEMO_A/SYN - A_Title (2).txt")
        self.assertEqual(archive_names(tuple(reversed(records))), names)
        self.assertEqual(safe_component("CON"), "_CON")

    def test_natural_suffix_and_windows_case_equivalents_are_unique(self) -> None:
        records = (
            item("base-1", title="Task", student_code="SYN-1"),
            item("base-2", title="Task", student_code="SYN-1"),
            item("natural", title="Task (2)", student_code="SYN-1"),
            item("case", title="task", student_code="syn-1", class_code="demo:a"),
        )
        names = archive_names(records)
        windows_paths = [path.casefold() for path in names.values()]
        self.assertEqual(len(windows_paths), len(set(windows_paths)))
        self.assertEqual(names["base-1"], "DEMO_A/SYN-1 - Task.txt")
        self.assertEqual(names["base-2"], "DEMO_A/SYN-1 - Task (2).txt")
        self.assertEqual(names["natural"], "DEMO_A/SYN-1 - Task (2) (2).txt")
        self.assertEqual(names["case"], "demo_a/syn-1 - task (3).txt")

    def test_zip_is_utf8_grouped_and_does_not_overwrite(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "export.zip"
            paths = write_archive((item("a", name="한글 학생"),), destination)
            self.assertEqual(paths, ("DEMO_A/SYN-a - A_Title.txt",))
            with ZipFile(destination) as archive:
                self.assertEqual(archive.namelist(), list(paths))
                text = archive.read(paths[0]).decode("utf-8")
                self.assertIn("Student: 한글 학생", text)
                self.assertIn("Student Code: SYN-a", text)
                self.assertTrue(text.endswith("One\n\n둘"))
            with self.assertRaises(FileExistsError):
                write_archive((item("a"),), destination)
            self.assertTrue(destination.exists())

    def test_duplicate_record_identity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate record identity"):
            archive_names((item("same", name="One"), item("same", name="Two")))


if __name__ == "__main__":
    unittest.main()

