"""Offline tests of the human-gated one-record adapter: no real browser or site."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from littlefox_writing.one_record_review import LocalBlock, review_browser

from test_one_record_probe import FakeBrowser, FakeElement, FakePage


def source_page(html: str = "<p>My spellingg stays.</p>") -> FakePage:
    return FakePage([
        FakeElement("contents_1", html="<p>Old draft.</p>"),
        FakeElement("writers_1", value="LOCAL-STUDENT-EVIDENCE"),
        FakeElement("regdate_1", value="LOCAL-TIMESTAMP-1"),
        FakeElement("contents_2", html="<p>Teacher mark.</p>"),
        FakeElement("writers_2", value="LOCAL-TEACHER-EVIDENCE"),
        FakeElement("regdate_2", value="LOCAL-TIMESTAMP-2"),
        FakeElement("contents_3", html=html),
        FakeElement("writers_3", value="LOCAL-STUDENT-EVIDENCE"),
        FakeElement("regdate_3", value="LOCAL-TIMESTAMP-3"),
    ])


def responses(*items: str):
    answers = iter(items)
    prompts = []

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    return ask, prompts


class GateBReviewTests(unittest.TestCase):
    def test_preview_requires_human_actor_and_metadata_checks(self) -> None:
        page = source_page()
        ask, prompts = responses(
            "YES", "S", "T", "S", "YES", "YES",
            "D3A", "Test Student", "TEST-000", "Practice Narrative", "Retelling", "YES",
            "YES", "",  # precise text comparison, then preview only
        )
        display = []
        result = review_browser(FakeBrowser([FakePage([]), page]), ask=ask, emit=display.append)
        self.assertEqual(result, {"outcome": "preview_verified_no_file", "export_created": False})
        self.assertTrue(any("Writing:\nMy spellingg stays." in line for line in display))
        self.assertTrue(any("actor shown by the site" in item for item in prompts))
        self.assertEqual(page.actions, [])
        self.assertIn("LOCAL-STUDENT-EVIDENCE", "\n".join(display))

    def test_full_one_record_export_requires_confirmation_and_never_overwrites(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "one_record.txt"
            initial = (
                "YES", "S", "T", "S", "YES", "YES",
                "D3A", "Test Student", "TEST-000", "Practice Narrative", "Retelling",
                "YES", "YES", "EXPORT"
            )
            ask, _ = responses(*initial)
            result = review_browser(FakeBrowser([FakePage([]), source_page()]), ask=ask, emit=lambda _: None, output=output)
            self.assertTrue(result["export_created"])
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "Class: D3A\nStudent: Test Student\nStudent Code: TEST-000\n"
                "Title: Practice Narrative\nType: Retelling\nStatus: Revision — Clean\n"
                "\nWriting:\nMy spellingg stays.",
            )
            ask, _ = responses(*initial)
            with self.assertRaisesRegex(LocalBlock, "output_already_exists"):
                review_browser(FakeBrowser([source_page()]), ask=ask, emit=lambda _: None, output=output)

    def test_declining_status_or_metadata_blocks_before_export(self) -> None:
        ask, _ = responses("YES", "S", "T", "S", "YES", "no")
        with self.assertRaisesRegex(LocalBlock, "outstanding_status_unverified"):
            review_browser(FakeBrowser([source_page()]), ask=ask, emit=lambda _: None)
        ask, _ = responses(
            "YES", "S", "T", "S", "YES", "YES",
            "D3A", "Test Student", "TEST-000", "Practice Narrative", "Retelling", "no",
        )
        with self.assertRaisesRegex(LocalBlock, "required_metadata_mapping_unverified"):
            review_browser(FakeBrowser([source_page()]), ask=ask, emit=lambda _: None)

    def test_reviewed_latest_teacher_is_excluded(self) -> None:
        page = FakePage([
            FakeElement("contents_1", html="student"),
            FakeElement("writers_1", value="student-field"),
            FakeElement("regdate_1", value="timestamp-a"),
            FakeElement("contents_2", html="teacher"),
            FakeElement("writers_2", value="teacher-field"),
            FakeElement("regdate_2", value="timestamp-b"),
        ])
        ask, _ = responses("YES", "S", "T", "YES")
        result = review_browser(FakeBrowser([page]), ask=ask, emit=lambda _: None)
        self.assertEqual(result, {"outcome": "excluded", "reason": "latest_state_teacher", "export_created": False})

    def test_unsupported_real_markup_fails_closed(self) -> None:
        tagged = source_page('<span style="color:red">Do not guess.</span>')
        ask, _ = responses(
            "YES", "S", "T", "S", "YES", "YES",
            "D3A", "Test Student", "TEST-000", "Practice Narrative", "Retelling", "YES",
        )
        result = review_browser(FakeBrowser([tagged]), ask=ask, emit=lambda _: None)
        self.assertEqual(result["outcome"], "blocked")
        self.assertEqual(result["reason"], "unsupported_markup")
        self.assertFalse(result["export_created"])

    def test_unverified_and_competing_popup_refuse_acquisition(self) -> None:
        ask, _ = responses("no")
        with self.assertRaisesRegex(LocalBlock, "actor_or_chronology_not_verified"):
            review_browser(FakeBrowser([source_page()]), ask=ask, emit=lambda _: None)
        with self.assertRaisesRegex(LocalBlock, "multiple_matching_detail_pages"):
            review_browser(FakeBrowser([source_page(), source_page()]), ask=lambda _: "YES", emit=lambda _: None)

    def test_source_change_at_confirmation_blocks_output(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.txt"
            page = source_page()
            answers = iter([
                "YES", "S", "T", "S", "YES", "YES",
                "D3A", "Test Student", "TEST-000", "Practice Narrative", "Retelling", "YES", "YES",
            ])
            def ask(prompt: str) -> str:
                if prompt.startswith("Write ONE"):
                    raise AssertionError("Must not prompt for export once source changed")
                if "Optional:" in prompt:
                    page.elements[6].html = "<p>Site changed after review.</p>"
                    return str(path)
                return next(answers)
            with self.assertRaisesRegex(LocalBlock, "source_changed_since_review"):
                review_browser(FakeBrowser([page]), ask=ask, emit=lambda _: None)
            self.assertFalse(path.exists())

    def test_invalid_metadata_cannot_inject_extra_fields(self) -> None:
        ask, _ = responses("YES", "S", "T", "S", "YES", "YES", "D3A\nStatus: Faked")
        with self.assertRaisesRegex(LocalBlock, "invalid_manual_metadata"):
            review_browser(FakeBrowser([source_page()]), ask=ask, emit=lambda _: None)


if __name__ == "__main__":
    unittest.main()
