import unittest

from littlefox_writing.acquisition import SiteLinkEvidence
from littlefox_writing.one_class_discovery import discover_one_class

from test_one_record_probe import FakeBrowser


class FakeNavigationPage:
    def __init__(self, start_url: str, evidence: dict[str, tuple[SiteLinkEvidence, ...]]) -> None:
        self.url = start_url
        self.evidence = evidence
        self.actions: list[tuple[str, str]] = []

    def goto(self, href: str, *, wait_until: str) -> None:
        self.actions.append(("goto", href))
        if href not in self.evidence:
            raise AssertionError("navigator used a URL that was not supplied by synthetic site evidence")
        self.url = href


def reader(page: FakeNavigationPage) -> tuple[SiteLinkEvidence, ...]:
    return page.evidence[page.url]


ORIGIN = "https://synthetic.invalid"
MAIN = ORIGIN + "/manager"
CLASS = ORIGIN + "/class?scpid=class-token"
STUDENT_1 = ORIGIN + "/student?scpid=class-token&bsWriterID=SYN-001"
STUDENT_2 = ORIGIN + "/student?scpid=class-token&bsWriterID=SYN-002"
HOMEWORK_1 = ORIGIN + "/homework?scpid=class-token&bsWriterID=SYN-001"
WRITING_1 = ORIGIN + "/writing?scpid=class-token&bsWriterID=SYN-001"
RECORD_1 = ORIGIN + "/detail?bsPID=persistent-1"
RECORD_2 = ORIGIN + "/detail?bsPID=persistent-2"


class OneClassDiscoveryTests(unittest.TestCase):
    def test_one_class_dry_run_follows_only_supplied_links_and_propagates_context(self) -> None:
        evidence = {
            MAIN: (SiteLinkEvidence(CLASS, "DEMO-A"),),
            CLASS: (
                SiteLinkEvidence(STUDENT_1, "Synthetic One"),
                SiteLinkEvidence(STUDENT_2, "Synthetic Two"),
            ),
            STUDENT_1: (SiteLinkEvidence(HOMEWORK_1, "Homework"),),
            HOMEWORK_1: (SiteLinkEvidence(WRITING_1, "Writing"),),
            WRITING_1: (
                SiteLinkEvidence(
                    RECORD_1,
                    "Imaginary Journey",
                    (("Title", "Imaginary Journey"), ("Type", "Personal Narrative")),
                ),
                # The same persistent task link is not a second submission round.
                SiteLinkEvidence(
                    RECORD_1,
                    "Imaginary Journey",
                    (("Title", "Imaginary Journey"), ("Type", "Personal Narrative")),
                ),
            ),
            STUDENT_2: (
                SiteLinkEvidence(
                    RECORD_2,
                    "Second Task",
                    (("Title", "Second Task"),),  # genre absent: explicit blocker
                ),
            ),
        }
        page = FakeNavigationPage(MAIN, evidence)
        outcome = discover_one_class(FakeBrowser([page]), "DEMO-A", link_reader=reader)
        self.assertEqual(outcome.report.students_discovered, 2)
        self.assertEqual(outcome.report.students_scanned, 2)
        self.assertEqual(outcome.report.complete_contexts, 1)
        self.assertEqual(outcome.contexts[0].bspid, "persistent-1")
        self.assertEqual(outcome.contexts[0].student_code, "SYN-001")
        self.assertEqual(outcome.contexts[0].title, "Imaginary Journey")
        self.assertEqual(outcome.contexts[0].genre, "Personal Narrative")
        self.assertIn("missing_or_ambiguous_writing_genre", outcome.report.blocker_counts)
        self.assertIn("history_pagination_unverified", outcome.report.blocker_counts)
        self.assertFalse(outcome.report.pagination_scanned)
        self.assertEqual(
            page.actions,
            [
                ("goto", CLASS),
                ("goto", STUDENT_1),
                ("goto", HOMEWORK_1),
                ("goto", WRITING_1),
                ("goto", STUDENT_2),
            ],
        )
        serialized = outcome.report.sanitized_json()
        for private in ("Synthetic One", "SYN-001", "Imaginary Journey", "persistent-1"):
            self.assertNotIn(private, serialized)

    def test_missing_selected_class_does_not_navigate(self) -> None:
        page = FakeNavigationPage(MAIN, {MAIN: (SiteLinkEvidence(CLASS, "DEMO-A"),)})
        outcome = discover_one_class(FakeBrowser([page]), "MISSING", link_reader=reader)
        self.assertEqual(outcome.contexts, ())
        self.assertEqual(outcome.report.blocker_counts, {"selected_class_missing": 1})
        self.assertEqual(page.actions, [])

    def test_cross_origin_and_ambiguous_intermediate_links_block(self) -> None:
        unsafe_student = ORIGIN + "/student?scpid=class-token&bsWriterID=SYN-003"
        evidence = {
            MAIN: (SiteLinkEvidence(CLASS, "DEMO-A"),),
            CLASS: (SiteLinkEvidence(unsafe_student, "Synthetic Three"),),
            unsafe_student: (
                SiteLinkEvidence("https://other.invalid/homework", "Homework"),
                SiteLinkEvidence(ORIGIN + "/other-homework", "Homework"),
            ),
        }
        page = FakeNavigationPage(MAIN, evidence)
        outcome = discover_one_class(FakeBrowser([page]), "DEMO-A", link_reader=reader)
        self.assertIn("ambiguous_homework_link", outcome.report.blocker_counts)
        self.assertEqual(outcome.contexts, ())
        self.assertTrue(all(action == "goto" for action, _ in page.actions))


if __name__ == "__main__":
    unittest.main()

