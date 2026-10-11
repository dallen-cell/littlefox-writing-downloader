"""Clearly fictional records for the Stage 1 demo."""

from datetime import datetime, timedelta

from .filters import KOREA
from .models import SubmissionStatus, SyntheticRecord

DEMO_CLASSES = {"DEMO-A", "DEMO-B"}


def demo_records(now: datetime) -> tuple[SyntheticRecord, ...]:
    return (
        SyntheticRecord(
            "demo-001", "DEMO-A", "하늘 별", "SYN-001", "My Imaginary Pet", "Personal Narrative",
            SubmissionStatus.INITIAL, "My pet is a cloud.\n\nIt likes blue umbrellas!", now - timedelta(days=2),
        ),
        SyntheticRecord(
            "demo-002", "DEMO-A", "Alex Example", "SYN-002", "A Rainy Day", "Descriptive Writing",
            SubmissionStatus.REVISION_CLEAN, "Rain taps the window. I keep my spelling mistakes.", now - timedelta(days=10),
        ),
        SyntheticRecord(
            "demo-003", "DEMO-B", "Sample Student", "SYN-003", "Space Picnic", "Creative Writing",
            SubmissionStatus.REVISION_TAGGED, "We ate 별-shaped sandwiches on Mars.", now - timedelta(hours=12),
        ),
    )

