"""Stage 1 domain objects containing synthetic data only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SubmissionStatus(StrEnum):
    INITIAL = "Initial"
    REVISION_TAGGED = "Revision — Tagged"
    REVISION_CLEAN = "Revision — Clean"


@dataclass(frozen=True, slots=True)
class SyntheticRecord:
    """A cleaned, synthetic record ready for offline selection/export."""

    record_id: str
    class_code: str
    student_name: str
    student_code: str
    title: str
    genre: str
    status: SubmissionStatus
    writing: str
    submitted_at: datetime | None

    def __post_init__(self) -> None:
        required = {
            "record_id": self.record_id,
            "class_code": self.class_code,
            "student_name": self.student_name,
            "student_code": self.student_code,
            "title": self.title,
            "genre": self.genre,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Required fields are empty: {', '.join(missing)}")

