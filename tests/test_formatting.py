from datetime import datetime
import unittest

from littlefox_writing.filters import KOREA
from littlefox_writing.formatting import format_record
from littlefox_writing.models import SubmissionStatus, SyntheticRecord


class FormattingTests(unittest.TestCase):
    def test_exact_seven_fields_unicode_and_paragraphs(self) -> None:
        writing = "첫 문단의 틀린 문법.\n\nSecond paragraph—unchanged!\n"
        item = SyntheticRecord(
            "synthetic-1", "가상-A", "예시 학생", "SYN-007", "나의 하루", "Personal Narrative",
            SubmissionStatus.REVISION_TAGGED, writing, datetime(2026, 10, 1, tzinfo=KOREA),
        )
        expected = (
            "Class: 가상-A\n"
            "Student: 예시 학생\n"
            "Student Code: SYN-007\n"
            "Title: 나의 하루\n"
            "Type: Personal Narrative\n"
            "Status: Revision — Tagged\n\n"
            "Writing:\n"
            + writing
        )
        actual = format_record(item)
        self.assertEqual(actual, expected)
        self.assertTrue(actual.endswith(writing))
        labels = [line.split(":", 1)[0] for line in actual.splitlines() if ":" in line]
        self.assertEqual(labels, ["Class", "Student", "Student Code", "Title", "Type", "Status", "Writing"])


if __name__ == "__main__":
    unittest.main()

