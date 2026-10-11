"""Run diagnostics that do not confuse failures with an empty result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunDiagnostics:
    discovered_classes: int
    selected_classes: int
    scanned_classes: int
    students_checked: int
    outstanding_records: int
    date_matches: int
    blocked_records: int
    errors: tuple[str, ...] = ()
    incomplete_scans: tuple[str, ...] = ()
    exported: int = 0

    @property
    def is_complete_zero(self) -> bool:
        return (
            self.date_matches == 0
            and self.blocked_records == 0
            and not self.errors
            and not self.incomplete_scans
            and self.scanned_classes == self.selected_classes
        )

    @property
    def is_partial(self) -> bool:
        return bool(self.errors or self.incomplete_scans or self.blocked_records)

    def render(self) -> str:
        state = "complete-zero" if self.is_complete_zero else ("partial" if self.is_partial else "complete")
        lines = [
            f"Run status: {state}",
            f"Classes: {self.discovered_classes} discovered, {self.selected_classes} selected, {self.scanned_classes} scanned",
            f"Students checked: {self.students_checked}",
            f"Outstanding records: {self.outstanding_records}",
            f"Date-filter matches: {self.date_matches}",
            f"Blocked records: {self.blocked_records}",
            f"Errors: {len(self.errors)}",
            f"Exported: {self.exported}",
        ]
        lines.extend(f"ERROR: {error}" for error in self.errors)
        lines.extend(f"INCOMPLETE: {item}" for item in self.incomplete_scans)
        return "\n".join(lines)

