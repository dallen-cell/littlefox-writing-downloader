"""Bounded, read-only discovery of Writing contexts for one selected class.

Navigation uses only anchor hrefs read from the current same-origin page. It
does not construct site URLs, submit forms, click controls, paginate, open
record details, interpret source actors, or create student files.
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
    WritingRecordContext,
    class_contexts,
    query_value,
    student_contexts,
    writing_record_contexts,
)
from .one_record_probe import ProbeConfigurationError, validate_cdp_endpoint


_MAX_STUDENTS = 100
_MAX_RECORDS = 1000
_ROUTE_LABELS = ("Homework", "Writing")


@dataclass(frozen=True, slots=True)
class ReadOnlyRoutePolicy:
    """Exact documented GET paths for each acquisition navigation family."""

    class_paths: frozenset[str] = frozenset()
    student_paths: frozenset[str] = frozenset()
    homework_paths: frozenset[str] = frozenset()
    writing_paths: frozenset[str] = frozenset()


# The repository records identifier relationships, but not verified live route
# paths. Production therefore fails closed until those paths are added from the
# authoritative map. Tests inject synthetic documented paths.
DOCUMENTED_ROUTE_POLICY = ReadOnlyRoutePolicy()

_ALLOWED_QUERY_KEYS = {
    "class": frozenset({"scpid"}),
    "student": frozenset({"scpid", "bsWriterID"}),
    "homework": frozenset({"scpid", "bsWriterID"}),
    "writing": frozenset({"scpid", "bsWriterID"}),
}


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
    return len(keys) == len(set(keys))


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
    label: str,
    *,
    scpid: str,
    writer_id: str,
) -> SiteLinkEvidence | None:
    candidates: dict[str, SiteLinkEvidence] = {}
    for link in links:
        if " ".join(link.text.split()).casefold() != label.casefold():
            continue
        linked_class = query_value(link.href, "scpid")
        linked_writer = query_value(link.href, "bsWriterID")
        if linked_class not in (None, scpid) or linked_writer not in (None, writer_id):
            continue
        candidates[link.href] = link
    if len(candidates) > 1:
        raise DiscoveryBlock("ambiguous_" + label.casefold() + "_link")
    return next(iter(candidates.values())) if candidates else None


def _history_links(
    page: Any,
    student: Any,
    link_reader: Callable[[Any], tuple[SiteLinkEvidence, ...]],
    route_policy: ReadOnlyRoutePolicy,
) -> tuple[tuple[SiteLinkEvidence, ...], int]:
    """Reach the current Writing history page through documented link labels."""
    links = link_reader(page)
    navigation_gets = 0
    if any(query_value(link.href, "bsPID") is not None for link in links):
        return links, navigation_gets
    for label in _ROUTE_LABELS:
        route = _route_link(links, label, scpid=student.scpid, writer_id=student.student_code)
        if route is None:
            raise DiscoveryBlock("missing_" + label.casefold() + "_link")
        _navigate(page, route.href, route_policy, label.casefold())
        navigation_gets += 1
        links = link_reader(page)
        if any(query_value(link.href, "bsPID") is not None for link in links):
            return links, navigation_gets
    raise DiscoveryBlock("missing_writing_history_links")


def discover_one_class(
    browser: Any,
    class_code: str,
    *,
    link_reader: Callable[[Any], tuple[SiteLinkEvidence, ...]] = collect_site_links,
    route_policy: ReadOnlyRoutePolicy = DOCUMENTED_ROUTE_POLICY,
) -> DiscoveryOutcome:
    """Follow actual GET links for one class and return a no-file dry run."""
    pages = [page for context in browser.contexts for page in context.pages]
    issues: Counter[str] = Counter()
    class_matches: list[tuple[Any, Any]] = []
    total_class_links = 0
    for page in pages:
        links = link_reader(page)
        classes, found_issues = class_contexts(links)
        total_class_links += len(classes)
        issues.update(issue.code for issue in found_issues)
        class_matches.extend((page, item) for item in classes if item.class_code == class_code)
    if len(class_matches) != 1:
        # Known class navigation may be JavaScript-driven. Without a supported
        # documented control, absence of an anchor is acquisition failure—not
        # evidence that the class or its outstanding Writing count is zero.
        missing_code = "class_navigation_unsupported_or_missing" if not class_matches else "selected_class_ambiguous"
        issues[missing_code] += 1
        return DiscoveryOutcome(
            DiscoveryReport(True, total_class_links, False, 0, 0, 0, 0, 0, False, False, None, dict(issues)),
            (),
        )

    page, selected_class = class_matches[0]
    try:
        _navigate(page, selected_class.href, route_policy, "class")
    except DiscoveryBlock as error:
        issues[str(error)] += 1
        return DiscoveryOutcome(
            DiscoveryReport(True, total_class_links, True, 0, 0, 0, 0, 0, False, False, None, dict(issues)),
            (),
        )
    navigation_gets = 1
    students, student_issues = student_contexts(selected_class, link_reader(page))
    issues.update(issue.code for issue in student_issues)
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
            history_links, route_gets = _history_links(page, student, link_reader, route_policy)
            navigation_gets += route_gets
            records, record_issues = writing_record_contexts(student, history_links)
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
        class_links_discovered=total_class_links,
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

