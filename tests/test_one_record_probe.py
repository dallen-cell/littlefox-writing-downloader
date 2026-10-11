from pathlib import Path
import tomllib
import unittest

from littlefox_writing.one_record_probe import (
    ProbeConfigurationError,
    inspect_browser,
    run_probe,
    validate_cdp_endpoint,
)


class FakeElement:
    def __init__(self, element_id: str, *, value: str | None = None, text: str = "", html: str = "") -> None:
        self.element_id = element_id
        self.value = value
        self.text = text
        self.html = html

    def get_attribute(self, name: str) -> str | None:
        if name == "id":
            return self.element_id
        if name == "value":
            return self.value
        return None

    def text_content(self) -> str:
        return self.text

    def inner_html(self) -> str:
        return self.html


class FakeLocator:
    def __init__(self, elements: list[FakeElement]) -> None:
        self.elements = elements

    def count(self) -> int:
        return len(self.elements)

    def nth(self, position: int) -> FakeElement:
        return self.elements[position]


class FakePage:
    def __init__(self, elements: list[FakeElement]) -> None:
        self.elements = elements
        self.actions: list[str] = []

    def locator(self, selector: str) -> FakeLocator:
        prefix = selector.split('"')[1]
        return FakeLocator([element for element in self.elements if element.element_id.startswith(prefix)])


class FakeContext:
    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages


class FakeBrowser:
    def __init__(self, pages: list[FakePage]) -> None:
        self.contexts = [FakeContext(pages)]


def detail_page(*, missing_writer: bool = False) -> FakePage:
    return FakePage(
        [
            FakeElement("contents_2", html='<p class="synthetic">Student secret text</p>'),
            FakeElement("writers_2", value="" if missing_writer else "synthetic-writer-value"),
            FakeElement("regdate_2", value="2099-01-01 synthetic timestamp"),
            FakeElement("contents_7", html="<div>Second secret</div>"),
            FakeElement("writers_7", text="synthetic-teacher-value"),
            FakeElement("regdate_7", text="2099-01-02 synthetic timestamp"),
        ]
    )


class OneRecordProbeTests(unittest.TestCase):
    def test_playwright_is_an_optional_probe_dependency(self) -> None:
        configuration = tomllib.loads(
            (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        )
        probe_dependencies = configuration["project"]["optional-dependencies"]["probe"]
        self.assertEqual(probe_dependencies, ["playwright>=1.48,<2"])

    def test_endpoint_is_restricted_to_explicit_loopback_http(self) -> None:
        self.assertEqual(validate_cdp_endpoint("http://127.0.0.1:9222"), "http://127.0.0.1:9222")
        self.assertEqual(validate_cdp_endpoint("http://[::1]:9333"), "http://[::1]:9333")
        rejected = (
            "https://127.0.0.1:9222",
            "http://example.test:9222",
            "http://127.0.0.1",
            "http://user:pass@127.0.0.1:9222",
            "http://127.0.0.1:9222/json",
        )
        for endpoint in rejected:
            with self.subTest(endpoint=endpoint), self.assertRaises(ProbeConfigurationError):
                validate_cdp_endpoint(endpoint)

    def test_single_page_report_is_sanitized_and_performs_no_page_actions(self) -> None:
        page = detail_page()
        report = inspect_browser(FakeBrowser([page]))
        self.assertTrue(report.attach_succeeded)
        self.assertEqual(report.matching_pages, 1)
        self.assertEqual(report.source_state_count, 2)
        self.assertTrue(report.writer_fields_complete)
        self.assertTrue(report.timestamp_fields_complete)
        self.assertTrue(report.source_html_complete)
        self.assertEqual(report.html_element_count, 2)
        self.assertEqual(report.html_attribute_count, 1)
        self.assertEqual(report.states_with_html_elements, 2)
        self.assertIn("actor_mapping_unverified", report.blockers)
        self.assertFalse(report.export_created)
        self.assertEqual(page.actions, [])
        serialized = report.sanitized_json()
        for secret in ("Student secret text", "Second secret", "synthetic-writer-value", "2099-01-01"):
            self.assertNotIn(secret, serialized)

    def test_person_like_tag_and_attribute_names_never_serialize(self) -> None:
        page = FakePage(
            [
                FakeElement(
                    "contents_0",
                    html='<alex-person taylor-person="synthetic">Private synthetic text</alex-person>',
                ),
                FakeElement("writers_0", value="synthetic-writer"),
                FakeElement("regdate_0", value="2099-01-01"),
            ]
        )
        report = inspect_browser(FakeBrowser([page]))
        serialized = report.sanitized_json().casefold()
        self.assertEqual(report.html_element_count, 1)
        self.assertEqual(report.html_attribute_count, 1)
        self.assertEqual(report.states_with_html_elements, 1)
        self.assertNotIn("alex-person", serialized)
        self.assertNotIn("taylor-person", serialized)
        self.assertNotIn("private synthetic text", serialized)

    def test_missing_mismatched_and_multiple_pages_block(self) -> None:
        no_match = inspect_browser(FakeBrowser([FakePage([])]))
        self.assertEqual(no_match.blockers, ("no_matching_detail_page",))
        multiple = inspect_browser(FakeBrowser([detail_page(), detail_page()]))
        self.assertEqual(multiple.blockers, ("multiple_open_pages",))
        self.assertEqual(multiple.matching_pages, 0)

        mismatched = FakePage(
            [
                FakeElement("contents_0", html="synthetic"),
                FakeElement("writers_0", value="writer"),
                FakeElement("regdate_1", value="timestamp"),
            ]
        )
        report = inspect_browser(FakeBrowser([mismatched]))
        self.assertIn("mismatched_numbered_state_fields", report.blockers)
        self.assertEqual(report.source_state_count, 0)

    def test_missing_field_values_are_reported_without_values(self) -> None:
        report = inspect_browser(FakeBrowser([detail_page(missing_writer=True)]))
        self.assertFalse(report.writer_fields_complete)
        self.assertIn("writer_evidence_missing", report.blockers)
        self.assertNotIn("synthetic-teacher-value", report.sanitized_json())

    def test_attach_failure_is_sanitized(self) -> None:
        class BrokenChromium:
            def connect_over_cdp(self, endpoint: str) -> None:
                raise RuntimeError("secret local URL and profile details")

        class FakePlaywright:
            chromium = BrokenChromium()

            def __enter__(self) -> "FakePlaywright":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        report = run_probe("http://localhost:9222", playwright_factory=FakePlaywright)
        self.assertFalse(report.attach_succeeded)
        self.assertEqual(report.blockers, ("cdp_attach_or_read_failed:RuntimeError",))
        self.assertNotIn("secret", report.sanitized_json())


if __name__ == "__main__":
    unittest.main()

