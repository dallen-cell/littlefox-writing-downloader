from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from littlefox_writing.filters import DateFilter, DateMode, KOREA, select_records
from littlefox_writing.formatting import format_record
from littlefox_writing.interpretation import (
    Actor,
    DecisionKind,
    NormalizedWritingTask,
    ReasonCode,
    SourceState,
    interpret_task,
)
from littlefox_writing.models import SubmissionStatus


NOW = datetime(2026, 10, 11, 12, tzinfo=KOREA)


def state(
    index: int | None,
    actor: Actor,
    html: str | None = None,
    *,
    age_days: int | None = None,
    raw_status: str | None = None,
) -> SourceState:
    timestamp = None if age_days is None else NOW - timedelta(days=age_days)
    return SourceState(index, actor, html, timestamp, raw_status)


def task(*states: SourceState, **changes: object) -> NormalizedWritingTask:
    values: dict[str, object] = {
        "task_id": "synthetic-task",
        "class_code": "DEMO-A",
        "student_name": "Synthetic Student",
        "student_code": "SYN-100",
        "title": "An Imaginary Day",
        "genre": "Personal Narrative",
        "states": tuple(states),
    }
    values.update(changes)
    return NormalizedWritingTask(**values)  # type: ignore[arg-type]


class InterpretationTests(unittest.TestCase):
    def test_single_unreviewed_student_state_is_initial(self) -> None:
        decision = interpret_task(task(state(4, Actor.STUDENT, "<p>First typoo.</p>", age_days=2)))
        self.assertEqual(decision.kind, DecisionKind.CANDIDATE)
        self.assertEqual(decision.record.status, SubmissionStatus.INITIAL)
        self.assertEqual(decision.record.record_id, "synthetic-task:4")
        self.assertEqual(decision.record.writing, "First typoo.")

    def test_latest_teacher_excludes_earlier_student(self) -> None:
        decision = interpret_task(
            task(
                state(0, Actor.STUDENT, "Draft", raw_status="Submitted"),
                state(7, Actor.TEACHER, raw_status="Good"),
            )
        )
        self.assertEqual(decision.kind, DecisionKind.EXCLUDED)
        self.assertEqual(decision.reason, ReasonCode.LATEST_STATE_TEACHER)
        self.assertIsNone(decision.record)

    def test_revision_tagged_is_decided_before_supported_cleaning(self) -> None:
        latest = 'I <span data-lfw-synthetic-rule="struck-deletion">very </span>agree.'
        decision = interpret_task(
            task(
                state(0, Actor.STUDENT, "I very agree."),
                state(1, Actor.TEACHER, raw_status="Try Again"),
                state(2, Actor.STUDENT, latest, age_days=1),
            )
        )
        self.assertEqual(decision.kind, DecisionKind.CANDIDATE)
        self.assertEqual(decision.record.status, SubmissionStatus.REVISION_TAGGED)
        self.assertEqual(decision.record.writing, "I agree.")
        self.assertEqual(decision.markup.rendered_text, "I very agree.")

    def test_revision_without_inherited_tags_is_clean(self) -> None:
        decision = interpret_task(
            task(
                state(0, Actor.STUDENT, "Draft"),
                state(1, Actor.TEACHER, raw_status="Try Again"),
                state(9, Actor.STUDENT, "Revised typoo", age_days=3),
            )
        )
        self.assertEqual(decision.record.status, SubmissionStatus.REVISION_CLEAN)
        self.assertEqual(decision.record.writing, "Revised typoo")

    def test_reviewed_revision_is_excluded(self) -> None:
        decision = interpret_task(
            task(
                state(0, Actor.STUDENT, "Draft"),
                state(1, Actor.TEACHER, raw_status="Try Again"),
                state(2, Actor.STUDENT, "Revision"),
                state(3, Actor.TEACHER, raw_status="Good"),
            )
        )
        self.assertEqual(decision.kind, DecisionKind.EXCLUDED)

    def test_long_alternating_chain_has_no_round_limit(self) -> None:
        states: list[SourceState] = []
        for index in range(20):
            actor = Actor.STUDENT if index % 2 == 0 else Actor.TEACHER
            html = f"Draft {index}" if actor is Actor.STUDENT else None
            status = ("Good" if index % 4 == 1 else "Try Again") if actor is Actor.TEACHER else None
            states.append(state(index, actor, html, raw_status=status))
        states.append(state(20, Actor.STUDENT, "Latest", age_days=0))
        decision = interpret_task(task(*states))
        self.assertEqual(decision.kind, DecisionKind.CANDIDATE)
        self.assertEqual(decision.record.status, SubmissionStatus.REVISION_CLEAN)
        self.assertEqual(decision.record.writing, "Latest")

    def test_ambiguous_or_inconsistent_chains_block_with_structured_reasons(self) -> None:
        scenarios = [
            (ReasonCode.EMPTY_CHAIN, task()),
            (ReasonCode.INCOMPLETE_CHAIN, task(state(0, Actor.STUDENT, "x"), chain_complete=False)),
            (ReasonCode.UNRELIABLE_CHRONOLOGY, task(state(0, Actor.STUDENT, "x"), chronology_reliable=False)),
            (ReasonCode.UNKNOWN_STATUS, task(state(0, Actor.STUDENT, "x"), status_evidence_supported=False)),
            (ReasonCode.MISSING_SOURCE_INDEX, task(state(None, Actor.STUDENT, "x"))),
            (ReasonCode.INVALID_SOURCE_INDEX, task(state(-1, Actor.STUDENT, "x"))),
            (ReasonCode.DUPLICATE_SOURCE_INDEX, task(state(0, Actor.STUDENT, "x"), state(0, Actor.TEACHER))),
            (ReasonCode.NON_MONOTONE_SOURCE_INDEX, task(state(2, Actor.STUDENT, "x"), state(1, Actor.TEACHER))),
            (ReasonCode.UNKNOWN_ACTOR, task(state(0, Actor.UNKNOWN, "x"))),
            (ReasonCode.CHAIN_DOES_NOT_START_WITH_STUDENT, task(state(0, Actor.TEACHER))),
            (ReasonCode.CONSECUTIVE_STUDENT_STATES, task(state(0, Actor.STUDENT, "x"), state(1, Actor.STUDENT, "y"))),
            (ReasonCode.CONSECUTIVE_TEACHER_STATES, task(
                state(0, Actor.STUDENT, "x"), state(1, Actor.TEACHER), state(2, Actor.TEACHER)
            )),
            (ReasonCode.MISSING_STUDENT_HTML, task(state(0, Actor.STUDENT))),
            (ReasonCode.INVALID_SOURCE_INDEX, task(state("zero", Actor.STUDENT, "x"))),  # type: ignore[arg-type]
            (ReasonCode.INVALID_METADATA, task(state(0, Actor.STUDENT, "x"), student_code="")),
        ]
        for expected, item in scenarios:
            with self.subTest(expected=expected):
                decision = interpret_task(item)
                self.assertEqual(decision.kind, DecisionKind.BLOCKED)
                self.assertEqual(decision.reason, expected)
                self.assertIsNone(decision.record)

    def test_inherited_markup_without_a_review_blocks_initial_classification(self) -> None:
        decision = interpret_task(
            task(
                state(
                    0,
                    Actor.STUDENT,
                    'word<span data-lfw-synthetic-rule="empty-punctuation-placeholder"></span>',
                )
            )
        )
        self.assertEqual(decision.kind, DecisionKind.BLOCKED)
        self.assertEqual(decision.reason, ReasonCode.MARKUP_WITHOUT_REVIEW)

    def test_empty_sources_block_without_trimming_legitimate_whitespace(self) -> None:
        for source in ("", "<p></p>"):
            with self.subTest(source=source):
                decision = interpret_task(task(state(0, Actor.STUDENT, source)))
                self.assertEqual(decision.kind, DecisionKind.BLOCKED)
                self.assertEqual(decision.reason, ReasonCode.MISSING_STUDENT_HTML)

        whitespace = interpret_task(task(state(0, Actor.STUDENT, " \t\n")))
        self.assertEqual(whitespace.kind, DecisionKind.CANDIDATE)
        self.assertEqual(whitespace.record.writing, " \t\n")

        formatted = interpret_task(task(state(0, Actor.STUDENT, "<p> \n<br></p>")))
        self.assertEqual(formatted.kind, DecisionKind.CANDIDATE)
        self.assertEqual(formatted.record.writing, " \n\n")

    def test_unsupported_case_markup_blocks_without_guessing(self) -> None:
        decision = interpret_task(
            task(
                state(0, Actor.STUDENT, "draft"),
                state(1, Actor.TEACHER),
                state(2, Actor.STUDENT, '<span data-lfw-synthetic-rule="case">wORD</span>'),
            )
        )
        self.assertEqual(decision.kind, DecisionKind.BLOCKED)
        self.assertEqual(decision.reason, ReasonCode.UNSUPPORTED_MARKUP)
        self.assertIn("unsupported_correction_rule", decision.detail)

    def test_latest_student_timestamp_flows_to_existing_filter_and_format(self) -> None:
        latest_time = NOW - timedelta(days=2)
        item = task(
            state(0, Actor.STUDENT, "draft", age_days=40),
            SourceState(1, Actor.TEACHER, None, NOW - timedelta(days=30), "Try Again"),
            SourceState(2, Actor.STUDENT, "latest", latest_time, "Submitted"),
        )
        decision = interpret_task(item)
        self.assertEqual(decision.record.submitted_at, latest_time)
        selected = select_records(
            [decision.record],
            {"DEMO-A"},
            DateFilter(DateMode.WITHIN, days=3),
            NOW,
        )
        self.assertEqual(selected.eligible, (decision.record,))
        output = format_record(decision.record)
        labels = [line.split(":", 1)[0] for line in output.splitlines() if ":" in line]
        self.assertEqual(labels, ["Class", "Student", "Student Code", "Title", "Type", "Status", "Writing"])

    def test_blocked_input_does_not_create_an_archive(self) -> None:
        decision = interpret_task(task(state(0, Actor.STUDENT, "<unknown>text</unknown>")))
        self.assertEqual(decision.kind, DecisionKind.BLOCKED)
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "must-not-exist.zip"
            if decision.record is not None:  # The export boundary accepts candidates only.
                self.fail("Blocked interpretation unexpectedly returned an exportable record")
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()

