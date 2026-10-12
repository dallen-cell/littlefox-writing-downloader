import unittest

from littlefox_writing.acquisition import SiteLinkEvidence
from littlefox_writing.one_class_discovery import (
    DOCUMENTED_ROUTE_POLICY,
    ClassControlEvidence,
    _documented_read_only_link,
    _go_class_arguments,
    _javascript_call_arguments,
    _javascript_string,
    discover_one_class,
    discover_one_class_live,
)

from test_one_record_probe import FakeBrowser


ORIGIN = "https://synthetic.invalid"
LESSONS = ORIGIN + "/Manager/Class/Lessons.php"
STUDENT = ORIGIN + "/Manager/Student/Student_main.php?ulID=SYN-001"
HOMEWORK = ORIGIN + "/Manager/Student/Student_homework2.php?ulID=SYN-001"
LAUNCHER = ORIGIN + "/Manager/Class/Homework_write.php?bsWriterID=SYN-001&scpid=instance-9"
HISTORY = ORIGIN + "/Manager/Homework/writing/list.php?scpid=instance-9&bsWriterID=SYN-001"
DETAIL = (ORIGIN + "/Manager/Homework/writing/view_editor.php?bsPID=record-1&bsWriterID=SYN-001"
          "&scpid=instance-9&qpid=task-2&la_pid=activity-3&page=1")


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


class FakePopup:
    def __init__(self, url: str) -> None:
        self.url = url
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def is_closed(self) -> bool:
        return self.closed


def reader(page: FakeNavigationPage) -> tuple[SiteLinkEvidence, ...]:
    return page.evidence[page.url]


def controls(page: FakeNavigationPage) -> tuple[tuple[ClassControlEvidence, ...], int]:
    return (page.control,), 1


def activate(control: ClassControlEvidence) -> None:
    page = control.surface
    page.actions.append(("click-GoClass", "site-control"))
    page.evidence[LESSONS] = page.after_class


class OneClassDiscoveryTests(unittest.TestCase):
    def test_live_control_orchestration_propagates_one_roster_record(self) -> None:
        manager = FakeNavigationPage({})
        manager.url = ORIGIN + "/Manager/index.html"
        profile = FakePopup(STUDENT)
        history = FakePopup(HISTORY + "&_ISmine=Y&baBID=SB004")
        menus: list[tuple[str, str]] = []

        def open_menu(page, label, path):
            menus.append((label, path))
            return page

        def open_profile(unused_manager, unused_control, student_code, unused_policy):
            self.assertEqual(student_code, "SYN-001")
            return profile

        def open_history(unused_profile, student_code, unused_policy):
            self.assertEqual(student_code, "SYN-001")
            return history, "instance-9", 3

        def read_records(unused_history, student, unused_policy):
            self.assertEqual(student.class_code, "DEMO-A")
            self.assertEqual(student.student_code, "SYN-001")
            return (
                SiteLinkEvidence(
                    DETAIL,
                    "Imaginary Journey",
                    (("Title", "Imaginary Journey"), ("Type", "Personal Narrative")),
                ),
            ), 2

        outcome = discover_one_class_live(
            FakeBrowser([manager]),
            "DEMO-A",
            menu_opener=open_menu,
            class_control_reader=lambda unused: ((manager.control,), 0),
            roster_reader=lambda unused, class_code: ((object(), "Synthetic One", "SYN-001"),),
            profile_opener=open_profile,
            history_opener=open_history,
            record_reader=read_records,
        )
        self.assertEqual(menus, [
            ("Classes", "/Manager/Class/Lessons.php"),
            ("Students", "/Manager/Student/list.php"),
        ])
        self.assertEqual(outcome.report.students_discovered, 1)
        self.assertEqual(outcome.report.students_scanned, 1)
        self.assertEqual(outcome.report.complete_contexts, 1)
        self.assertEqual(outcome.contexts[0].bspid, "record-1")
        self.assertEqual(outcome.contexts[0].genre, "Personal Narrative")
        self.assertTrue(profile.closed)
        self.assertTrue(history.closed)
        self.assertIn("history_pagination_unverified", outcome.report.blocker_counts)

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
        prefixed = _go_class_arguments("JavaScript:GoClass('r','scno','t','teacher','l','m');")
        self.assertEqual(len(prefixed), 6)
        self.assertIsNone(_go_class_arguments("GoClass('too','few')"))
        self.assertIsNone(_go_class_arguments("Unknown('r','s','t','n','l','m')"))

    def test_verified_javascript_controls_are_parsed_without_evaluation(self) -> None:
        arguments = _javascript_call_arguments(
            "javascript:ViewStudent('SYN-001','main');", "ViewStudent", 2,
        )
        self.assertEqual(_javascript_string(arguments[0]), "SYN-001")
        self.assertEqual(_javascript_string(arguments[1]), "main")
        self.assertIsNone(_javascript_call_arguments("javascript:DeleteStudent('SYN-001');", "ViewStudent", 2))
        self.assertIsNone(_javascript_string("studentVariable"))
        launcher = _javascript_call_arguments(
            "new_win('/Manager/Class/Homework_write.php?bsWriterID=SYN-001&scpid=instance-9',"
            "'Writing',972,1080,1);",
            "new_win",
            5,
        )
        self.assertEqual(
            _javascript_string(launcher[0]),
            "/Manager/Class/Homework_write.php?bsWriterID=SYN-001&scpid=instance-9",
        )
        detail = _javascript_call_arguments(
            "javascript:doView('record-1','1','','','SYN-001','','D3','0','instance-9','','task-2','activity-3');",
            "doView",
            12,
        )
        self.assertEqual(_javascript_string(detail[0]), "record-1")
        self.assertEqual(_javascript_string(detail[4]), "SYN-001")
        self.assertEqual(_javascript_string(detail[8]), "instance-9")

    def test_live_history_and_detail_query_keys_are_bounded_by_route_family(self) -> None:
        history = HISTORY + "&_ISmine=Y&baBID=SB004"
        self.assertTrue(_documented_read_only_link(history, DOCUMENTED_ROUTE_POLICY, "writing_history"))
        self.assertTrue(_documented_read_only_link(DETAIL, DOCUMENTED_ROUTE_POLICY, "writing_detail"))
        self.assertFalse(_documented_read_only_link(HISTORY.replace("bsWriterID=SYN-001", ""), DOCUMENTED_ROUTE_POLICY, "writing_history"))
        self.assertFalse(_documented_read_only_link(DETAIL.replace("&page=1", ""), DOCUMENTED_ROUTE_POLICY, "writing_detail"))
        self.assertFalse(_documented_read_only_link(history + "&action=delete", DOCUMENTED_ROUTE_POLICY, "writing_history"))
        self.assertFalse(_documented_read_only_link(DETAIL + "&mode=save", DOCUMENTED_ROUTE_POLICY, "writing_detail"))

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


