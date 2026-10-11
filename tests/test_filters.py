from datetime import date, datetime, timedelta, timezone
import unittest

from littlefox_writing.filters import (
    DateFilter,
    DateMode,
    KOREA,
    matches_date,
    select_records,
    validate_class_scope,
)
from littlefox_writing.models import SubmissionStatus, SyntheticRecord


NOW = datetime(2026, 10, 11, 12, tzinfo=KOREA)


def record(timestamp: datetime | None) -> SyntheticRecord:
    return SyntheticRecord(
        "id", "DEMO-A", "Synthetic Student", "SYN-1", "Title", "Genre",
        SubmissionStatus.INITIAL, "Text", timestamp,
    )


class DateFilterTests(unittest.TestCase):
    def test_older_than_is_strict_at_boundary(self) -> None:
        rule = DateFilter(DateMode.OLDER_THAN, days=3)
        self.assertFalse(matches_date(NOW - timedelta(days=3), rule, NOW))
        self.assertTrue(matches_date(NOW - timedelta(days=3, microseconds=1), rule, NOW))

    def test_within_is_inclusive_at_zero_and_boundary(self) -> None:
        rule = DateFilter(DateMode.WITHIN, days=3)
        self.assertTrue(matches_date(NOW, rule, NOW))
        self.assertTrue(matches_date(NOW - timedelta(days=3), rule, NOW))
        self.assertFalse(matches_date(NOW - timedelta(days=3, microseconds=1), rule, NOW))

    def test_calendar_range_is_inclusive_in_korea(self) -> None:
        rule = DateFilter(DateMode.CALENDAR_RANGE, start=date(2026, 10, 10), end=date(2026, 10, 11))
        utc_timestamp = datetime(2026, 10, 9, 15, tzinfo=timezone.utc)  # Korea midnight on Oct 10
        self.assertTrue(matches_date(utc_timestamp, rule, NOW))
        self.assertTrue(matches_date(datetime(2026, 10, 11, 23, 59, tzinfo=KOREA), rule, datetime(2026, 10, 12, tzinfo=KOREA)))
        self.assertFalse(matches_date(datetime(2026, 10, 9, 23, 59, tzinfo=KOREA), rule, NOW))

    def test_invalid_and_reversed_ranges_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires start and end"):
            DateFilter(DateMode.CALENDAR_RANGE, start=date(2026, 10, 1))
        with self.assertRaisesRegex(ValueError, "must not be after"):
            DateFilter(DateMode.CALENDAR_RANGE, start=date(2026, 10, 2), end=date(2026, 10, 1))
        with self.assertRaisesRegex(ValueError, "non-negative"):
            DateFilter(DateMode.WITHIN, days=-1)

    def test_ambiguous_missing_and_future_timestamps_are_blocked(self) -> None:
        items = [
            record(None),
            SyntheticRecord("naive", "DEMO-A", "N", "S", "T", "G", SubmissionStatus.INITIAL, "W", datetime(2026, 10, 1)),
            SyntheticRecord("future", "DEMO-A", "N", "S", "T", "G", SubmissionStatus.INITIAL, "W", NOW + timedelta(seconds=1)),
        ]
        result = select_records(items, {"DEMO-A"}, DateFilter(DateMode.WITHIN, days=30), NOW)
        self.assertEqual(result.eligible, ())
        self.assertEqual([reason for _, reason in result.blocked], [
            "Submission timestamp is missing",
            "Submission timestamp has no unambiguous timezone",
            "Submission timestamp is in the future",
        ])

    def test_any_allows_missing_but_still_rejects_ambiguous_or_future(self) -> None:
        result = select_records(
            [record(None), record(datetime(2026, 10, 1)), record(NOW + timedelta(seconds=1))],
            {"DEMO-A"}, DateFilter(), NOW,
        )
        self.assertEqual(len(result.eligible), 1)
        self.assertEqual(len(result.blocked), 2)

    def test_class_scope_validation(self) -> None:
        available = {"DEMO-A", "DEMO-B"}
        self.assertEqual(validate_class_scope(available, all_classes=True, requested=()), available)
        self.assertEqual(validate_class_scope(available, all_classes=False, requested=("DEMO-A",)), {"DEMO-A"})
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate_class_scope(available, all_classes=False, requested=())
        with self.assertRaisesRegex(ValueError, "Unknown or inaccessible"):
            validate_class_scope(available, all_classes=False, requested=("MISSING",))


if __name__ == "__main__":
    unittest.main()

