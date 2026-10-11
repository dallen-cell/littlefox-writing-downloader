"""Synthetic-only Stage 1 command-line interface."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

from .archive import write_archive
from .demo import DEMO_CLASSES, demo_records
from .diagnostics import RunDiagnostics
from .filters import DateFilter, DateMode, KOREA, select_records, validate_class_scope


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use an ISO date such as 2026-10-11") from error


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="littlefox-writing",
        description="Stage 1 offline exporter. Only synthetic --demo data is supported.",
    )
    result.add_argument("--demo", action="store_true", required=True, help="use bundled synthetic records only")
    scope = result.add_mutually_exclusive_group(required=True)
    scope.add_argument("--all-classes", action="store_true", help="select all synthetic demo classes")
    scope.add_argument("--class", dest="classes", action="append", default=[], help="select a demo class code; repeatable")
    dates = result.add_mutually_exclusive_group()
    dates.add_argument("--any-date", action="store_true", help="do not restrict the submission date (default)")
    dates.add_argument("--older-than", type=int, metavar="DAYS", help="strictly older than DAYS x 24 hours")
    dates.add_argument("--within", type=int, metavar="DAYS", help="zero through DAYS x 24 hours old, inclusive")
    dates.add_argument("--date-range", nargs=2, type=_date, metavar=("START", "END"), help="inclusive Korea dates")
    result.add_argument("--output", type=Path, default=Path("synthetic-writing.zip"), help="new ZIP path")
    result.add_argument("--yes", action="store_true", help="confirm ZIP creation; without this flag, preview only")
    return result


def _rule(args: argparse.Namespace) -> DateFilter:
    if args.older_than is not None:
        return DateFilter(DateMode.OLDER_THAN, days=args.older_than)
    if args.within is not None:
        return DateFilter(DateMode.WITHIN, days=args.within)
    if args.date_range is not None:
        return DateFilter(DateMode.CALENDAR_RANGE, start=args.date_range[0], end=args.date_range[1])
    return DateFilter()


def run(argv: list[str] | None = None, *, now: datetime | None = None) -> int:
    args = parser().parse_args(argv)
    reference = now or datetime.now(KOREA)  # captured exactly once per run
    try:
        selected_classes = validate_class_scope(
            DEMO_CLASSES, all_classes=args.all_classes, requested=tuple(args.classes)
        )
        rule = _rule(args)
    except ValueError as error:
        parser().error(str(error))

    records = demo_records(reference)
    selection = select_records(records, selected_classes, rule, reference)
    diagnostics = RunDiagnostics(
        discovered_classes=len(DEMO_CLASSES),
        selected_classes=len(selected_classes),
        scanned_classes=len(selected_classes),
        students_checked=sum(record.class_code in selected_classes for record in records),
        outstanding_records=sum(record.class_code in selected_classes for record in records),
        date_matches=len(selection.eligible),
        blocked_records=len(selection.blocked),
        exported=0,
    )
    for record, reason in selection.blocked:
        print(f"BLOCKED {record.record_id}: {reason}")
    print("Would export:")
    for record in selection.eligible:
        print(f"- {record.class_code}: {record.student_name} — {record.title}")

    if not args.yes:
        print(diagnostics.render())
        print("Preview only. Re-run with --yes to create the synthetic ZIP.")
        return 0
    if selection.blocked:
        print(diagnostics.render())
        print("Export stopped: blocked records require explicit resolution; no partial ZIP was created.")
        return 2

    paths = write_archive(selection.eligible, args.output)
    print(replace(diagnostics, exported=len(paths)).render())
    print(f"Created {args.output} with {len(paths)} synthetic record(s).")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

