from datetime import datetime, timedelta
import unittest

from littlefox_writing.acquisition import (
    ClassContext,
    SiteLinkEvidence,
    StudentContext,
    class_contexts,
    query_value,
    student_contexts,
    writing_record_contexts,
)
from littlefox_writing.filters import DateFilter, DateMode, KOREA, select_records
from littlefox_writing.interpretation import Actor, DecisionKind, SourceState, interpret_task
from littlefox_writing.models import SubmissionStatus


NOW = datetime(2026, 10, 11, 12, tzinfo=KOREA)


class AcquisitionEvidenceTests(unittest.TestCase):
    def test_site_provided_class_student_and_history_metadata_propagates(self) -> None:
        classes, class_issues = class_contexts(
            (SiteLinkEvidence("https://synthetic.invalid/class?scpid=class-token", "DEMO-A"),)
        )
        self.assertEqual(class_issues, ())
        self.assertEqual(classes, (ClassContext("DEMO-A", "class-token", classes[0].href),))

        students, student_issues = student_contexts(
            classes[0],
            (
                SiteLinkEvidence(
                    "https://synthetic.invalid/student?scpid=class-token&bsWriterID=SYN-007",
                    "Synthetic Student",
                ),
            ),
        )
        self.assertEqual(student_issues, ())
        self.assertEqual(students[0].student_code, "SYN-007")
        self.assertEqual(students[0].student_name, "Synthetic Student")

        records, record_issues = writing_record_contexts(
            students[0],
            (
                SiteLinkEvidence(
                    "https://synthetic.invalid/writing?bsPID=persistent-task",
                    "Imaginary Journey",
                    (("Title", "Imaginary Journey"), ("Type", "Personal Narrative")),
                ),
            ),
        )
        self.assertEqual(record_issues, ())
        self.assertEqual(records[0].class_code, "DEMO-A")
        self.assertEqual(records[0].student_name, "Synthetic Student")
        self.assertEqual(records[0].student_code, "SYN-007")
        self.assertEqual(records[0].title, "Imaginary Journey")
        self.assertEqual(records[0].genre, "Personal Narrative")
        self.assertEqual(records[0].bspid, "persistent-task")

    def test_persistent_task_is_distinct_from_multiple_submission_rounds(self) -> None:
        context = writing_record_contexts(
            StudentContext("DEMO-A", "class-token", "Synthetic Student", "SYN-007", "student-link"),
            (
                SiteLinkEvidence(
                    "https://synthetic.invalid/writing?bsPID=persistent-task",
                    "Same Task",
                    (("Title", "Same Task"), ("Genre", "Creative Writing")),
                ),
            ),
        )[0][0]
        latest = NOW - timedelta(days=2)
        states = (
            SourceState(1, Actor.STUDENT, "First draft", NOW - timedelta(days=20), "Submitted"),
            SourceState(3, Actor.TEACHER, None, NOW - timedelta(days=10), "Try Again"),
            SourceState(8, Actor.STUDENT, "Second draft", latest, "Submitted"),
        )
        decision = interpret_task(context.normalized_task(states))
        self.assertEqual(decision.kind, DecisionKind.CANDIDATE)
        self.assertEqual(decision.record.status, SubmissionStatus.REVISION_CLEAN)
        self.assertEqual(decision.record.record_id, "persistent-task:8")
        self.assertEqual(decision.record.title, "Same Task")
        self.assertEqual(decision.record.genre, "Creative Writing")
        selected = select_records(
            [decision.record], {"DEMO-A"}, DateFilter(DateMode.WITHIN, days=3), NOW
        )
        self.assertEqual(selected.eligible, (decision.record,))

    def test_missing_metadata_and_ambiguous_links_block_contexts(self) -> None:
        selected_class = ClassContext("DEMO-A", "class-token", "class-link")
        students, issues = student_contexts(
            selected_class,
            (
                SiteLinkEvidence("https://synthetic.invalid/s?scpid=class-token&bsWriterID=SYN-1", "First Name"),
                SiteLinkEvidence("https://synthetic.invalid/s?scpid=class-token&bsWriterID=SYN-1", "Other Name"),
            ),
        )
        self.assertEqual(students, ())
        self.assertIn("ambiguous_student_link", {issue.code for issue in issues})

        student = StudentContext("DEMO-A", "class-token", "Synthetic Student", "SYN-1", "student-link")
        records, issues = writing_record_contexts(
            student,
            (
                SiteLinkEvidence(
                    "https://synthetic.invalid/w?bsPID=task-1",
                    "Task Without Type",
                    (("Title", "Task Without Type"),),
                ),
                SiteLinkEvidence(
                    "https://synthetic.invalid/w?bsPID=task-2&bsWriterID=OTHER",
                    "Wrong Student",
                    (("Title", "Wrong Student"), ("Type", "Retelling")),
                ),
            ),
        )
        self.assertEqual(records, ())
        self.assertEqual(
            {issue.code for issue in issues},
            {"missing_or_ambiguous_writing_genre", "record_student_mismatch"},
        )

    def test_query_values_must_be_unique_and_are_never_invented(self) -> None:
        self.assertEqual(query_value("https://synthetic.invalid/?bsPID=actual-link-value", "bsPID"), "actual-link-value")
        self.assertIsNone(query_value("https://synthetic.invalid/", "bsPID"))
        self.assertIsNone(query_value("https://synthetic.invalid/?bsPID=one&bsPID=two", "bsPID"))
        self.assertIsNone(query_value("https://synthetic.invalid/?bsPID=", "bsPID"))


if __name__ == "__main__":
    unittest.main()

