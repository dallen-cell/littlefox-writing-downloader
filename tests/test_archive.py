from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from littlefox_writing.archive import archive_names, safe_component, write_archive
from littlefox_writing.filters import KOREA
from littlefox_writing.models import SubmissionStatus, SyntheticRecord


def item(record_id: str, name: str = "Same/Student", title: str = "A:Title") -> SyntheticRecord:
    return SyntheticRecord(
        record_id, "DEMO:A", name, f"SYN-{record_id}", title, "Genre",
        SubmissionStatus.REVISION_CLEAN, "One\n\n둘", datetime(2026, 10, 1, tzinfo=KOREA),
    )


class ArchiveTests(unittest.TestCase):
    def test_sanitises_names_and_handles_collisions_stably(self) -> None:
        records = (item("b"), item("a"))
        names = archive_names(records)
        self.assertEqual(names["a"], "DEMO_A/Same_Student - A_Title.txt")
        self.assertEqual(names["b"], "DEMO_A/Same_Student - A_Title (2).txt")
        self.assertEqual(archive_names(tuple(reversed(records))), names)
        self.assertEqual(safe_component("CON"), "_CON")

    def test_zip_is_utf8_grouped_and_does_not_overwrite(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "export.zip"
            paths = write_archive((item("a", name="한글 학생"),), destination)
            self.assertEqual(paths, ("DEMO_A/한글 학생 - A_Title.txt",))
            with ZipFile(destination) as archive:
                self.assertEqual(archive.namelist(), list(paths))
                text = archive.read(paths[0]).decode("utf-8")
                self.assertIn("Student: 한글 학생", text)
                self.assertTrue(text.endswith("One\n\n둘"))
            with self.assertRaises(FileExistsError):
                write_archive((item("a"),), destination)
            self.assertTrue(destination.exists())

    def test_duplicate_record_identity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate record identity"):
            archive_names((item("same", name="One"), item("same", name="Two")))


if __name__ == "__main__":
    unittest.main()

