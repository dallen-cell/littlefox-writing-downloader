"""Bounded, read-only discovery of Writing contexts for one selected class.

Navigation uses only documented class controls and anchor hrefs read from the
current same-origin page. It does not construct site URLs, submit forms,
paginate, open record details, interpret source actors, or create files.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from typing import Any, Callable
from urllib.parse import parse_qsl, urljoin, urlsplit

from .acquisition import (
    SiteLinkEvidence,
    StudentContext,
    WritingRecordContext,
    query_value,
    writing_record_contexts,
)
from .one_record_probe import ProbeConfigurationError, validate_cdp_endpoint


_MAX_STUDENTS = 100
_MAX_RECORDS = 1000
_CLASS_LIST_PATH = "/Manager/Class/Lessons.php"


@dataclass(frozen=True, slots=True)
class ReadOnlyRoutePolicy:
    """Exact documented GET paths for each acquisition navigation family."""

    class_paths: frozenset[str] = frozenset({_CLASS_LIST_PATH})
    student_paths: frozenset[str] = frozenset({"/Manager/Student/Student_main.php"})
    homework_paths: frozenset[str] = frozenset({"/Manager/Student/Student_homework2.php"})
    writing_launcher_paths: frozenset[str] = frozenset({"/Manager/Class/Homework_write.php"})
    writing_history_paths: frozenset[str] = frozenset({"/Manager/Homework/writing/list.php"})
    writing_detail_paths: frozenset[str] = frozenset({"/Manager/Homework/writing/view_editor.php"})


DOCUMENTED_ROUTE_POLICY = ReadOnlyRoutePolicy()

_ALLOWED_QUERY_KEYS = {
    "class": frozenset(),
    "student": frozenset({"ulID"}),
    "homework": frozenset({"ulID"}),
    "writing_launcher": frozenset({"scpid", "bsWriterID"}),
    "writing_history": frozenset({"scpid", "bsWriterID"}),
    "writing_detail": frozenset({"bsPID", "bsWriterID", "scpid", "qpid", "la_pid"}),
}

_REQUIRED_QUERY_KEYS = {family: keys for family, keys in _ALLOWED_QUERY_KEYS.items()}


@dataclass(frozen=True, slots=True)
class ClassControlEvidence:
    """One exact GoClass control and its actual six site-provided arguments."""

    text: str
    arguments: tuple[str, ...]
    element: Any
    surface: Any


@dataclass(frozen=True, slots=True)
class StudentSelection:
    class_code: str
    student_name: str
    student_code: str
    href: str


class DiscoveryBlock(Exception):
    """Fail-closed navigation or evidence condition with a fixed code."""


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    attach_succeeded: bool
    class_links_discovered: int
    selected_class_found: bool
    students_discovered: int
    students_scanned: int
    history_records_discovered: int
    complete_contexts: int
    navigation_gets: int
    pagination_scanned: bool
    scan_complete: bool
    outstanding_writing: int | None
    blocker_counts: dict[str, int]
    files_created: int = 0

    def sanitized_json(self) -> str:
        """Serialize counts and fixed diagnostic codes, never metadata values."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)


@dataclass(frozen=True, slots=True)
class DiscoveryOutcome:
    report: DiscoveryReport
    contexts: tuple[WritingRecordContext, ...]


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    return parsed.scheme, parsed.hostname or "", parsed.port


def _row_fields(anchor: Any) -> tuple[tuple[str, str], ...]:
    """Read semantic table headers/cells when the anchor is inside a row."""
    row = anchor.locator("xpath=ancestor::tr[1]")
    if row.count() != 1:
        return ()
    cells = tuple(row.locator("th, td").all_text_contents())
    table = row.locator("xpath=ancestor::table[1]")
    if table.count() != 1:
        return ()
    header_rows = table.locator("thead tr")
    if header_rows.count():
        headers = tuple(header_rows.nth(header_rows.count() - 1).locator("th, td").all_text_contents())
    else:
        rows = table.locator("tr")
        if not rows.count():
            return ()
        headers = tuple(rows.nth(0).locator("th").all_text_contents())
    if len(headers) != len(cells) or not headers:
        return ()
    return tuple(zip(headers, cells))


def _split_call_arguments(source: str) -> tuple[str, ...] | None:
    """Count opaque JS arguments without evaluating or reusing their values."""
    values: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    for position, character in enumerate(source):
        if escaped:
            escaped = False
        elif character == "\\" and quote is not None:
            escaped = True
        elif character in ("'", '"'):
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
        elif character == "," and quote is None:
            values.append(source[start:position].strip())
            start = position + 1
    if quote is not None:
        return None
    values.append(source[start:].strip())
    return tuple(values) if all(values) else None


def _go_class_arguments(handler: str) -> tuple[str, ...] | None:
    cleaned = handler.strip()
    if cleaned.casefold().startswith("javascript:"):
        cleaned = cleaned[len("javascript:"):].strip()
    if cleaned.startswith("return "):
        cleaned = cleaned[7:].strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    prefix = "GoClass("
    if not cleaned.startswith(prefix) or not cleaned.endswith(")"):
        return None
    arguments = _split_call_arguments(cleaned[len(prefix):-1])
    return arguments if arguments is not None and len(arguments) == 6 else None


def collect_class_controls(page: Any) -> tuple[tuple[ClassControlEvidence, ...], int]:
    """Read exact GoClass/GoList controls from the documented mainFrame."""
    frame = page.frame(name="mainFrame")
    if frame is None or urlsplit(frame.url).path != _CLASS_LIST_PATH:
        raise DiscoveryBlock("missing_documented_class_frame")
    controls: list[ClassControlEvidence] = []
    go_list_count = 0
    elements = frame.locator("[onclick], a[href]")
    for position in range(elements.count()):
        element = elements.nth(position)
        handler = element.get_attribute("onclick") or ""
        href = element.get_attribute("href") or ""
        if not handler and href.strip().casefold().startswith("javascript:"):
            handler = href.strip()[len("javascript:"):]
        arguments = _go_class_arguments(handler)
        if arguments is not None:
            controls.append(ClassControlEvidence(element.text_content() or "", arguments, element, frame))
        elif handler.strip().startswith("GoList(") or handler.strip().startswith("return GoList("):
            go_list_count += 1
    return tuple(controls), go_list_count


def activate_class_control(control: ClassControlEvidence) -> None:
    """Invoke the actual documented control; never reconstruct its arguments."""
    before_origin = _origin(control.surface.url)
    control.element.click()
    control.surface.wait_for_load_state("domcontentloaded")
    parsed = urlsplit(control.surface.url)
    if (
        _origin(control.surface.url) != before_origin
        or parsed.path != _CLASS_LIST_PATH
        or parsed.query
        or parsed.fragment
    ):
        raise DiscoveryBlock("unexpected_class_control_navigation")


def collect_site_links(page: Any) -> tuple[SiteLinkEvidence, ...]:
    """Collect actual anchors and visible row evidence without page actions."""
    anchors = page.locator("a[href]")
    links: list[SiteLinkEvidence] = []
    for position in range(anchors.count()):
        anchor = anchors.nth(position)
        raw_href = anchor.get_attribute("href")
        if raw_href is None:
            continue
        href = urljoin(page.url, raw_href)
        links.append(SiteLinkEvidence(href, anchor.text_content() or "", _row_fields(anchor)))
    return tuple(links)


def _same_origin_site_link(current_url: str, href: str) -> bool:
    target = urlsplit(href)
    return target.scheme in ("http", "https") and not target.username and not target.password and _origin(href) == _origin(current_url)


def _family_paths(policy: ReadOnlyRoutePolicy, family: str) -> frozenset[str]:
    return getattr(policy, family + "_paths")


def _documented_read_only_link(href: str, policy: ReadOnlyRoutePolicy, family: str) -> bool:
    parsed = urlsplit(href)
    if parsed.path not in _family_paths(policy, family):
        return False
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    keys = [key for key, _ in pairs]
    if any(key not in _ALLOWED_QUERY_KEYS[family] for key in keys):
        return False
    return len(keys) == len(set(keys)) and set(keys) == _REQUIRED_QUERY_KEYS[family]


def _navigate(page: Any, href: str, policy: ReadOnlyRoutePolicy, family: str) -> None:
    if not _same_origin_site_link(page.url, href):
        raise DiscoveryBlock("unsafe_or_cross_origin_link")
    if not _documented_read_only_link(href, policy, family):
        raise DiscoveryBlock("unsupported_or_unsafe_" + family + "_route")
    page.goto(href, wait_until="domcontentloaded")
    if page.url != href:
        raise DiscoveryBlock("unexpected_navigation_redirect")


def _route_link(
    links: tuple[SiteLinkEvidence, ...],
    family: str,
    policy: ReadOnlyRoutePolicy,
    *,
    expected: dict[str, str],
) -> SiteLinkEvidence | None:
    candidates: dict[str, SiteLinkEvidence] = {}
    for link in links:
        if urlsplit(link.href).path in _family_paths(policy, family) and not _documented_read_only_link(
            link.href, policy, family
        ):
            raise DiscoveryBlock("unsupported_or_unsafe_" + family + "_route")
        if not _documented_read_only_link(link.href, policy, family):
            continue
        if any(query_value(link.href, key) != value for key, value in expected.items()):
            continue
        candidates[link.href] = link
    if len(candidates) > 1:
        raise DiscoveryBlock("ambiguous_" + family + "_link")
    return next(iter(candidates.values())) if candidates else None


def _student_selections(class_code: str, links: tuple[SiteLinkEvidence, ...], policy: ReadOnlyRoutePolicy) -> tuple[StudentSelection, ...]:
    selections: dict[str, StudentSelection] = {}
    conflicted: set[str] = set()
    for link in links:
        if not _documented_read_only_link(link.href, policy, "student"):
            continue
        student_code = query_value(link.href, "ulID")
        student_name = " ".join(link.text.split())
        if student_code is None or not student_name:
            continue
        candidate = StudentSelection(class_code, student_name, student_code, link.href)
        existing = selections.get(student_code)
        if existing is not None and existing != candidate:
            conflicted.add(student_code)
            selections.pop(student_code, None)
        elif student_code not in conflicted:
            selections[student_code] = candidate
    return tuple(sorted(selections.values(), key=lambda item: (item.student_name.casefold(), item.student_code)))


def _history_links(
    page: Any,
    student: StudentSelection,
    link_reader: Callable[[Any], tuple[SiteLinkEvidence, ...]],
    route_policy: ReadOnlyRoutePolicy,
) -> tuple[tuple[SiteLinkEvidence, ...], int, str]:
    """Reach history only through the documented student route sequence."""
    links = link_reader(page)
    navigation_gets = 0
    for family, expected in (
        ("homework", {"ulID": student.student_code}),
        ("writing_launcher", {"bsWriterID": student.student_code}),
    ):
        route = _route_link(links, family, route_policy, expected=expected)
        if route is None:
            raise DiscoveryBlock("missing_" + family + "_link")
        _navigate(page, route.href, route_policy, family)
        navigation_gets += 1
        links = link_reader(page)
    launcher_class = query_value(route.href, "scpid")
    if launcher_class is None:
        raise DiscoveryBlock("missing_writing_class_instance")
    history = _route_link(
        links, "writing_history", route_policy,
        expected={"scpid": launcher_class, "bsWriterID": student.student_code},
    )
    if history is None:
        raise DiscoveryBlock("missing_writing_history_link")
    _navigate(page, history.href, route_policy, "writing_history")
    navigation_gets += 1
    return link_reader(page), navigation_gets, launcher_class


def discover_one_class(
    browser: Any,
    class_code: str,
    *,
    link_reader: Callable[[Any], tuple[SiteLinkEvidence, ...]] = collect_site_links,
    class_control_reader: Callable[[Any], tuple[tuple[ClassControlEvidence, ...], int]] = collect_class_controls,
    class_activator: Callable[[ClassControlEvidence], None] = activate_class_control,
    route_policy: ReadOnlyRoutePolicy = DOCUMENTED_ROUTE_POLICY,
) -> DiscoveryOutcome:
    """Use one actual GoClass control, then documented GET links; create no files."""
    pages = [page for context in browser.contexts for page in context.pages]
    issues: Counter[str] = Counter()
    class_matches: list[ClassControlEvidence] = []
    total_class_controls = 0
    go_list_controls = 0
    for page in pages:
        try:
            controls, list_count = class_control_reader(page)
        except DiscoveryBlock as error:
            issues[str(error)] += 1
            continue
        total_class_controls += len(controls)
        go_list_controls += list_count
        class_matches.extend(control for control in controls if " ".join(control.text.split()) == class_code)
    if len(class_matches) != 1:
        missing_code = "selected_class_ambiguous" if class_matches else (
            "class_list_selection_required" if go_list_controls else "class_navigation_unsupported_or_missing"
        )
        issues[missing_code] += 1
        return DiscoveryOutcome(
            DiscoveryReport(True, total_class_controls, False, 0, 0, 0, 0, 0, False, False, None, dict(issues)),
            (),
        )

    selected_control = class_matches[0]
    page = selected_control.surface
    try:
        class_activator(selected_control)
    except DiscoveryBlock as error:
        issues[str(error)] += 1
        return DiscoveryOutcome(
            DiscoveryReport(True, total_class_controls, True, 0, 0, 0, 0, 0, False, False, None, dict(issues)),
            (),
        )
    navigation_gets = 0
    students = _student_selections(class_code, link_reader(page), route_policy)
    if not students:
        issues["student_links_missing_after_class_selection"] += 1
    if len(students) > _MAX_STUDENTS:
        issues["student_limit_exceeded"] += 1
        students = students[:_MAX_STUDENTS]

    contexts: list[WritingRecordContext] = []
    students_scanned = 0
    records_seen = 0
    for student in students:
        try:
            _navigate(page, student.href, route_policy, "student")
            navigation_gets += 1
            history_links, route_gets, scpid = _history_links(page, student, link_reader, route_policy)
            navigation_gets += route_gets
            safe_details: list[SiteLinkEvidence] = []
            for link in history_links:
                if query_value(link.href, "bsPID") is None:
                    continue
                if not _documented_read_only_link(link.href, route_policy, "writing_detail"):
                    issues["unsupported_writing_detail_link"] += 1
                    continue
                if query_value(link.href, "scpid") != scpid or query_value(link.href, "bsWriterID") != student.student_code:
                    issues["writing_detail_identity_mismatch"] += 1
                    continue
                safe_details.append(link)
            context = StudentContext(class_code, scpid, student.student_name, student.student_code, student.href)
            records, record_issues = writing_record_contexts(context, tuple(safe_details))
            issues.update(issue.code for issue in record_issues)
            records_seen += len(records)
            contexts.extend(records)
            students_scanned += 1
            if len(contexts) > _MAX_RECORDS:
                issues["record_limit_exceeded"] += 1
                contexts = contexts[:_MAX_RECORDS]
                break
        except DiscoveryBlock as error:
            issues[str(error)] += 1

    # Pagination is intentionally outside this bounded implementation. The
    # false field prevents current-page discovery being reported as complete.
    issues["history_pagination_unverified"] += 1
    report = DiscoveryReport(
        attach_succeeded=True,
        class_links_discovered=total_class_controls,
        selected_class_found=True,
        students_discovered=len(students),
        students_scanned=students_scanned,
        history_records_discovered=records_seen,
        complete_contexts=len(contexts),
        navigation_gets=navigation_gets,
        pagination_scanned=False,
        scan_complete=False,
        outstanding_writing=None,
        blocker_counts=dict(sorted(issues.items())),
    )
    return DiscoveryOutcome(report, tuple(contexts))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="littlefox-one-class-dry-run",
        description="Read-only one-class metadata discovery using site-provided links; creates no files.",
    )
    result.add_argument("--class-code", required=True, help="exact current class code shown by the site")
    result.add_argument("--cdp-endpoint", default="http://127.0.0.1:9222")
    return result


def run(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        validate_cdp_endpoint(args.cdp_endpoint)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(args.cdp_endpoint)
            outcome = discover_one_class(browser, args.class_code)
    except ProbeConfigurationError:
        report = DiscoveryReport(False, 0, False, 0, 0, 0, 0, 0, False, False, None, {"invalid_local_cdp_endpoint": 1})
        print(report.sanitized_json())
        return 2
    except Exception as error:
        # Exception messages can contain URLs or student data; only the fixed
        # category and runtime type are emitted.
        report = DiscoveryReport(
            False, 0, False, 0, 0, 0, 0, 0, False, False, None,
            {"local_read_failed:" + type(error).__name__: 1},
        )
        print(report.sanitized_json())
        return 3
    print(outcome.report.sanitized_json())
    return 0 if outcome.report.complete_contexts and not outcome.report.blocker_counts else 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()


