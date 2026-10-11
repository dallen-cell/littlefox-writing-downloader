"""Pure class and submission-date selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from .models import SyntheticRecord

KOREA = ZoneInfo("Asia/Seoul")


class DateMode(StrEnum):
    ANY = "any"
    OLDER_THAN = "older-than"
    WITHIN = "within"
    CALENDAR_RANGE = "calendar-range"


@dataclass(frozen=True, slots=True)
class DateFilter:
    mode: DateMode = DateMode.ANY
    days: int | None = None
    start: date | None = None
    end: date | None = None

    def __post_init__(self) -> None:
        if self.mode in (DateMode.OLDER_THAN, DateMode.WITHIN):
            if self.days is None or self.days < 0:
                raise ValueError(f"{self.mode.value} requires a non-negative day count")
            if self.start is not None or self.end is not None:
                raise ValueError("Day filters cannot include calendar dates")
        elif self.mode is DateMode.CALENDAR_RANGE:
            if self.start is None or self.end is None:
                raise ValueError("calendar-range requires start and end dates")
            if self.start > self.end:
                raise ValueError("Calendar start date must not be after end date")
            if self.days is not None:
                raise ValueError("Calendar range cannot include a day count")
        elif any(value is not None for value in (self.days, self.start, self.end)):
            raise ValueError("any does not accept date parameters")


@dataclass(frozen=True, slots=True)
class Selection:
    eligible: tuple[SyntheticRecord, ...]
    blocked: tuple[tuple[SyntheticRecord, str], ...]


def matches_date(submitted_at: datetime, rule: DateFilter, now: datetime) -> bool:
    """Return whether a timestamp matches, rejecting ambiguous/future values."""
    if submitted_at.tzinfo is None or submitted_at.utcoffset() is None:
        raise ValueError("Submission timestamp has no unambiguous timezone")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Reference time has no unambiguous timezone")

    submitted = submitted_at.astimezone(KOREA)
    reference = now.astimezone(KOREA)
    age = reference - submitted
    if age < timedelta(0):
        raise ValueError("Submission timestamp is in the future")

    if rule.mode is DateMode.ANY:
        return True
    if rule.mode is DateMode.OLDER_THAN:
        return age > timedelta(days=rule.days)
    if rule.mode is DateMode.WITHIN:
        return age <= timedelta(days=rule.days)
    return rule.start <= submitted.date() <= rule.end


def select_records(
    records: tuple[SyntheticRecord, ...] | list[SyntheticRecord],
    selected_classes: set[str],
    rule: DateFilter,
    now: datetime,
) -> Selection:
    """Select matching classes and dates, retaining explicit blocked reasons."""
    if not selected_classes:
        raise ValueError("At least one class must be selected")

    eligible: list[SyntheticRecord] = []
    blocked: list[tuple[SyntheticRecord, str]] = []
    for record in records:
        if record.class_code not in selected_classes:
            continue
        if record.submitted_at is None:
            if rule.mode is DateMode.ANY:
                eligible.append(record)
            else:
                blocked.append((record, "Submission timestamp is missing"))
            continue
        try:
            if matches_date(record.submitted_at, rule, now):
                eligible.append(record)
        except ValueError as error:
            blocked.append((record, str(error)))
    return Selection(tuple(eligible), tuple(blocked))


def validate_class_scope(
    available: set[str], *, all_classes: bool, requested: tuple[str, ...]
) -> set[str]:
    if all_classes == bool(requested):
        raise ValueError("Choose exactly one of all classes or selected class codes")
    missing = set(requested) - available
    if missing:
        raise ValueError(f"Unknown or inaccessible classes: {', '.join(sorted(missing))}")
    return set(available if all_classes else requested)

