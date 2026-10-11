import unittest

from littlefox_writing.acquisition import SiteLinkEvidence
from littlefox_writing.one_class_discovery import ClassControlEvidence, _go_class_arguments, discover_one_class

from test_one_record_probe import FakeBrowser


ORIGIN = "https://synthetic.invalid"
LESSONS = ORIGIN + "/Manager/Class/Lessons.php"
STUDENT = ORIGIN + "/Manager/Student/Student_main.php?ulID=SYN-001"
HOMEWORK = ORIGIN + "/Manager/Student/Student_homework2.php?ulID=SYN-001"
LAUNCHER = ORIGIN + "/Manager/Class/Homework_write.php?bsWriterID=SYN-001&scpid=instance-9"
HISTORY = ORIGIN + "/Manager/Homework/writing/list.php?scpid=instance-9&bsWriterID=SYN-001"
DETAIL = (ORIGIN + "/Manager/Homework/writing/view_editor.php?bsPID=record-1&bsWriterID=SYN-001"
          "&scpid=instance-9&qpid=task-2&la_pid=activity-3")


class FakeNavigationPage:
    def __init__(self, evidence: dict[str, tuple[SiteLinkEvidence, ...]]) -> None:
        self.url = LESSONS
        self.evidence = evidence
        self.actions: list[tuple[str, str]] = []
        self.after_class: tuple[SiteLinkEvidence, ...] = ()
        self.control = ClassControlEvidence(
            "DEMO-A", ("ref", "scno-7", "time", "teacher", "level", "mode"), object(), self,
        )

    def goto(self, href: str, *, wait_until: str) -> None:
        self.actions.append(("goto", href))
        if href not in self.evidence:
            raise AssertionError("navigation used a URL absent from site evidence")
        self.url = href


def reader(page: FakeNavigationPage) -> tuple[SiteLinkEvidence, ...]:
    return page.evidence[page.url]


def controls(page: FakeNavigationPage) -> tuple[tuple[ClassControlEvidence, ...], int]:
    return (page.control,), 1


def activate(control: ClassControlEvidence) -> None:
    page = control.surface
    page.actions.append(("click-GoClass", "site-control"))
    page.evidence[LESSONS] = page.after_class


class OneClassDiscoveryTests(unittest.TestCase):
    def test_documented_go_class_and_writing_routes_propagate_context(self) -> None:
        evidence = {
            LESSONS: (),
            STUDENT: (SiteLinkEvidence(HOMEWORK, "Homework"),),
            HOMEWORK: (SiteLinkEvidence(LAUNCHER, "Writing"),),
            LAUNCHER: (SiteLinkEvidence(HISTORY, "Writing history"),),
            HISTORY: (SiteLinkEvidence(
                DETAIL, "Imaginary Journey",
                (("Title", "Imaginary Journey"), ("Type", "Personal Narrative")),
            ),),
        }
        page = FakeNavigationPage(evidence)
        page.after_class = (SiteLinkEvidence(STUDENT, "Synthetic One"),)
        outcome = discover_one_class(
            FakeBrowser([page]), "DEMO-A", link_reader=reader,
            class_control_reader=controls, class_activator=activate,
        )
        self.assertEqual(outcome.report.students_discovered, 1)
        self.assertEqual(outcome.report.complete_contexts, 1)
        self.assertEqual(outcome.contexts[0].student_code, "SYN-001")
        self.assertEqual(outcome.contexts[0].scpid, "instance-9")
        self.assertEqual(outcome.contexts[0].bspid, "record-1")
        self.assertNotEqual(page.control.arguments[1], outcome.contexts[0].scpid)
        self.assertEqual(page.actions, [
            ("click-GoClass", "site-control"), ("goto", STUDENT), ("goto", HOMEWORK),
            ("goto", LAUNCHER), ("goto", HISTORY),
        ])
        self.assertFalse(outcome.report.scan_complete)
        self.assertIsNone(outcome.report.outstanding_writing)
        self.assertIn("history_pagination_unverified", outcome.report.blocker_counts)
        for private in ("Synthetic One", "SYN-001", "instance-9", "record-1"):
            self.assertNotIn(private, outcome.report.sanitized_json())

    def test_go_class_parser_is_exact_and_does_not_accept_unknown_functions(self) -> None:
        parsed = _go_class_arguments("GoClass('r','scno','t','teacher','l','m');")
        self.assertEqual(len(parsed), 6)
        self.assertIsNone(_go_class_arguments("GoClass('too','few')"))
        self.assertIsNone(_go_class_arguments("Unknown('r','s','t','n','l','m')"))

    def test_go_list_requirement_is_incomplete_not_zero(self) -> None:
        page = FakeNavigationPage({LESSONS: ()})
        outcome = discover_one_class(
            FakeBrowser([page]), "MISSING", link_reader=reader,
            class_control_reader=lambda unused: ((), 2), class_activator=activate,
        )
        self.assertEqual(outcome.report.blocker_counts, {"class_list_selection_required": 1})
        self.assertFalse(outcome.report.scan_complete)
        self.assertIsNone(outcome.report.outstanding_writing)
        self.assertEqual(page.actions, [])

    def test_unknown_history_parameters_block(self) -> None:
        unsafe_history = HISTORY + "&action=delete"
        evidence = {
            LESSONS: (), STUDENT: (SiteLinkEvidence(HOMEWORK, "Homework"),),
            HOMEWORK: (SiteLinkEvidence(LAUNCHER, "Writing"),),
            LAUNCHER: (SiteLinkEvidence(unsafe_history, "Writing history"),),
        }
        page = FakeNavigationPage(evidence)
        page.after_class = (SiteLinkEvidence(STUDENT, "Synthetic One"),)
        outcome = discover_one_class(
            FakeBrowser([page]), "DEMO-A", link_reader=reader,
            class_control_reader=controls, class_activator=activate,
        )
        self.assertIn("unsupported_or_unsafe_writing_history_route", outcome.report.blocker_counts)
        self.assertFalse(outcome.report.scan_complete)
        self.assertIsNone(outcome.report.outstanding_writing)

    def test_detail_requires_confirmed_path_and_identity_keys(self) -> None:
        unsafe_detail = ORIGIN + "/Manager/Homework/writing/process.php?bsPID=record-1"
        evidence = {
            LESSONS: (), STUDENT: (SiteLinkEvidence(HOMEWORK, "Homework"),),
            HOMEWORK: (SiteLinkEvidence(LAUNCHER, "Writing"),),
            LAUNCHER: (SiteLinkEvidence(HISTORY, "Writing history"),),
            HISTORY: (SiteLinkEvidence(unsafe_detail, "Task", (("Title", "Task"), ("Type", "Essay"))),),
        }
        page = FakeNavigationPage(evidence)
        page.after_class = (SiteLinkEvidence(STUDENT, "Synthetic One"),)
        outcome = discover_one_class(
            FakeBrowser([page]), "DEMO-A", link_reader=reader,
            class_control_reader=controls, class_activator=activate,
        )
        self.assertIn("unsupported_writing_detail_link", outcome.report.blocker_counts)
        self.assertEqual(outcome.contexts, ())


if __name__ == "__main__":
    unittest.main()
