"""Bounded, read-only discovery of Writing contexts for one selected class.

Navigation uses only documented class controls and anchor hrefs read from the
current same-origin page. It does not construct site URLs, submit forms,
paginate, open record details, interpret source actors, or create files.
"""

from __future__ import annotations

import argparse
import ast
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
    "writing_history": frozenset({"scpid", "bsWriterID", "_ISmine", "baBID"}),
    "writing_detail": frozenset({"bsPID", "bsWriterID", "scpid", "qpid", "la_pid", "page"}),
}

_REQUIRED_QUERY_KEYS = {
    "class": frozenset(),
    "student": frozenset({"ulID"}),
    "homework": frozenset({"ulID"}),
    "writing_launcher": frozenset({"scpid", "bsWriterID"}),
    "writing_history": frozenset({"scpid", "bsWriterID"}),
    "writing_detail": frozenset({"bsPID", "bsWriterID", "scpid", "qpid", "la_pid", "page"}),
}


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


def _javascript_call_arguments(source: str, function_name: str, count: int) -> tuple[str, ...] | None:
    """Read one exact JavaScript call without evaluating it."""
    cleaned = source.strip()
    if cleaned.casefold().startswith("javascript:"):
        cleaned = cleaned[len("javascript:"):].strip()
    if cleaned.startswith("return "):
        cleaned = cleaned[7:].strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    prefix = function_name + "("
    if not cleaned.startswith(prefix) or not cleaned.endswith(")"):
        return None
    arguments = _split_call_arguments(cleaned[len(prefix):-1])
    return arguments if arguments is not None and len(arguments) == count else None


def _javascript_string(token: str) -> str | None:
    """Decode a quoted site-provided JavaScript argument conservatively."""
    stripped = token.strip()
    if len(stripped) < 2 or stripped[0] not in ("'", '"') or stripped[-1] != stripped[0]:
        return None
    try:
        value = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, str) or not value or any(ord(character) < 32 for character in value):
        return None
    return value


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
    if (
        parsed.scheme not in ("http", "https")
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in _family_paths(policy, family)
    ):
        return False
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    keys = [key for key, _ in pairs]
    if any(key not in _ALLOWED_QUERY_KEYS[family] for key in keys):
        return False
    return (
        len(keys) == len(set(keys))
        and _REQUIRED_QUERY_KEYS[family].issubset(keys)
    )


def _wait_for_frame_path(page: Any, name: str, path: str) -> Any:
    for _ in range(50):
        frame = page.frame(name=name)
        if frame is not None and urlsplit(frame.url).path == path:
            return frame
        page.wait_for_timeout(100)
    raise DiscoveryBlock("missing_documented_" + name.casefold())


def _open_top_menu(page: Any, label: str, expected_path: str) -> Any:
    top = page.frame(name="topFrame")
    if top is None or urlsplit(top.url).path != "/Manager/main_top.html":
        raise DiscoveryBlock("missing_documented_top_frame")
    control = top.get_by_text(label, exact=True)
    if control.count() != 1:
        raise DiscoveryBlock("missing_or_ambiguous_" + label.casefold() + "_menu")
    control.click()
    _wait_for_frame_path(page, "mainFrame", expected_path)
    _wait_for_frame_path(page, "topFrame", "/Manager/main_top.html")
    return _wait_for_frame_path(page, "mainFrame", expected_path)


def _table_columns(frame: Any, required: tuple[str, ...]) -> dict[str, int]:
    matches: list[dict[str, int]] = []
    rows = frame.locator("table tr")
    for position in range(rows.count()):
        values = [" ".join(value.split()).casefold() for value in rows.nth(position).locator("th, td").all_text_contents()]
        columns = {name: _table_heading_index(values, name) for name in required}
        if all(index is not None for index in columns.values()):
            matches.append({name: index for name, index in columns.items() if index is not None})
    if len(matches) != 1:
        raise DiscoveryBlock("missing_or_ambiguous_table_headings")
    return matches[0]


def _table_heading_index(values: list[str], name: str) -> int | None:
    """Match a heading exactly, allowing only a trailing non-text sort marker."""
    expected = name.casefold()
    candidates = []
    for index, value in enumerate(values):
        suffix = value[len(expected):] if value.startswith(expected) else ""
        if value == expected or (
            suffix.startswith(" ")
            and suffix.strip()
            and not any(char.isalnum() for char in suffix)
        ):
            candidates.append(index)
    return candidates[0] if len(candidates) == 1 else None


def _select_roster_class(frame: Any, class_filter: Any, value: str) -> None:
    """Select one site-provided class and wait for its iframe GET navigation."""
    with frame.expect_navigation(wait_until="domcontentloaded"):
        class_filter.select_option(value)


def _roster_controls(frame: Any, class_code: str) -> tuple[tuple[Any, str, str], ...]:
    """Return visible site controls with class-supported name and student code."""
    class_filter = frame.locator("select[name=sClass]")
    search_form = frame.locator("form[name=search]")
    filter_source = frame.evaluate("() => typeof doListView === 'function' ? doListView.toString() : ''")
    options = class_filter.locator("option") if class_filter.count() == 1 else None
    option_matches: list[str] = []
    if options is not None:
        for position in range(options.count()):
            option = options.nth(position)
            label = " ".join(option.inner_text().split())
            if class_code in label:
                value = option.get_attribute("value")
                if value:
                    option_matches.append(value)
    action = search_form.get_attribute("action") if search_form.count() == 1 else None
    if (
        class_filter.count() != 1
        or search_form.count() != 1
        or (search_form.get_attribute("method") or "get").casefold() != "get"
        or action not in (None, "", urlsplit(frame.url).path)
        or len(option_matches) != 1
        or "document.search" not in filter_source
        or "frm.submit()" not in filter_source
        or any(value in filter_source.casefold() for value in ("window.open", "fetch", "xmlhttprequest"))
    ):
        raise DiscoveryBlock("roster_class_filter_unsupported_or_ambiguous")
    _select_roster_class(frame, class_filter, option_matches[0])
    if urlsplit(frame.url).path != "/Manager/Student/list.php":
        raise DiscoveryBlock("unexpected_roster_filter_navigation")

    controls = frame.locator("a[href*=ViewStudent]:visible")
    if not controls.count():
        button = frame.locator("button[onclick*=show_list]:visible")
        source = frame.evaluate("() => typeof show_list === 'function' ? show_list.toString() : ''")
        forbidden = ("submit", "fetch", "xmlhttprequest", "location", "window.open", ".click(")
        normalized_source = source.casefold()
        if (
            button.count() != 1
            or "style.display" not in normalized_source
            or "list_div" not in normalized_source
            or any(value in normalized_source for value in forbidden)
        ):
            raise DiscoveryBlock("roster_reveal_not_confirmed_representational")
        button.click()
        controls = frame.locator("a[href*=ViewStudent]:visible")
    if not controls.count():
        return ()
    columns = _table_columns(frame, ("Name", "ClassName"))
    found: list[tuple[Any, str, str]] = []
    for position in range(controls.count()):
        control = controls.nth(position)
        arguments = _javascript_call_arguments(control.get_attribute("href") or "", "ViewStudent", 2)
        student_code = _javascript_string(arguments[0]) if arguments else None
        row = control.locator("xpath=ancestor::tr[1]")
        cells = row.locator("th, td")
        if cells.count() <= max(columns.values()):
            continue
        observed_class = " ".join(cells.nth(columns["ClassName"]).inner_text().split())
        if observed_class != class_code or student_code is None:
            continue
        student_name = " ".join(control.inner_text().split())
        if not student_name:
            raise DiscoveryBlock("missing_student_name")
        found.append((control, student_name, student_code))
    return tuple(found)


def _validate_current_route(
    page: Any,
    policy: ReadOnlyRoutePolicy,
    family: str,
    *,
    expected_origin_url: str | None = None,
) -> None:
    if (
        not _documented_read_only_link(page.url, policy, family)
        or (expected_origin_url is not None and _origin(page.url) != _origin(expected_origin_url))
    ):
        raise DiscoveryBlock("unsupported_or_unsafe_" + family + "_route")


def _open_student_profile(manager: Any, control: Any, student_code: str, policy: ReadOnlyRoutePolicy) -> Any:
    with manager.expect_popup(timeout=5000) as popup_info:
        control.click()
    profile = popup_info.value
    profile.wait_for_load_state("domcontentloaded")
    _validate_current_route(profile, policy, "student", expected_origin_url=manager.url)
    if query_value(profile.url, "ulID") != student_code:
        profile.close()
        raise DiscoveryBlock("student_control_identity_mismatch")
    return profile


def _open_writing_history(profile: Any, student_code: str, policy: ReadOnlyRoutePolicy) -> tuple[Any, str, int]:
    site_origin_url = profile.url
    homework = profile.locator("a[href*=StHomework]")
    if homework.count() != 1:
        raise DiscoveryBlock("missing_or_ambiguous_homework_control")
    homework.click()
    profile.wait_for_url("**/Manager/Student/Student_homework2.php?*")
    _validate_current_route(profile, policy, "homework", expected_origin_url=site_origin_url)
    if query_value(profile.url, "ulID") != student_code:
        raise DiscoveryBlock("homework_identity_mismatch")

    candidates = profile.locator("[onclick*=new_win], a[href*=new_win]")
    launchers: list[Any] = []
    for position in range(candidates.count()):
        candidate = candidates.nth(position)
        source = candidate.get_attribute("onclick") or candidate.get_attribute("href") or ""
        arguments = _javascript_call_arguments(source, "new_win", 5)
        destination = _javascript_string(arguments[0]) if arguments else None
        if destination is None:
            continue
        href = urljoin(profile.url, destination)
        if urlsplit(href).path == next(iter(policy.writing_launcher_paths)):
            if not _documented_read_only_link(href, policy, "writing_launcher"):
                raise DiscoveryBlock("unsupported_or_unsafe_writing_launcher_route")
            if query_value(href, "bsWriterID") != student_code:
                raise DiscoveryBlock("writing_launcher_identity_mismatch")
            launchers.append(candidate)
    if len(launchers) != 1:
        raise DiscoveryBlock("missing_or_ambiguous_writing_launcher")
    with profile.expect_popup(timeout=5000) as popup_info:
        launchers[0].click()
    history = popup_info.value
    history.wait_for_url("**/Manager/Homework/writing/list.php?*")
    _validate_current_route(history, policy, "writing_history", expected_origin_url=profile.url)
    if query_value(history.url, "bsWriterID") != student_code:
        raise DiscoveryBlock("writing_history_identity_mismatch")
    scpid = query_value(history.url, "scpid")
    if scpid is None:
        raise DiscoveryBlock("missing_writing_class_instance")
    return history, scpid, 3


def _history_record_links(
    history: Any,
    student: StudentContext,
    policy: ReadOnlyRoutePolicy,
) -> tuple[tuple[SiteLinkEvidence, ...], int]:
    columns = _table_columns(history, ("Title", "Type"))
    initial_controls = history.locator("a[href*=doView]:visible")
    record_count = initial_controls.count()
    links: list[SiteLinkEvidence] = []
    history_origin_url = history.url
    for position in range(record_count):
        controls = history.locator("a[href*=doView]:visible")
        if controls.count() != record_count:
            raise DiscoveryBlock("history_changed_during_scan")
        control = controls.nth(position)
        arguments = _javascript_call_arguments(control.get_attribute("href") or "", "doView", 12)
        expected_bspid = _javascript_string(arguments[0]) if arguments else None
        expected_writer = _javascript_string(arguments[4]) if arguments else None
        expected_scpid = _javascript_string(arguments[8]) if arguments else None
        if expected_bspid is None or expected_writer != student.student_code or expected_scpid != student.scpid:
            raise DiscoveryBlock("writing_detail_control_identity_mismatch")
        row = control.locator("xpath=ancestor::tr[1]")
        cells = row.locator("th, td")
        if cells.count() <= max(columns.values()):
            raise DiscoveryBlock("unsupported_writing_history_row")
        title = " ".join(cells.nth(columns["Title"]).inner_text().split())
        genre = " ".join(cells.nth(columns["Type"]).inner_text().split())
        control.click()
        history.wait_for_url("**/Manager/Homework/writing/view_editor.php?*")
        _validate_current_route(history, policy, "writing_detail", expected_origin_url=history_origin_url)
        if (
            query_value(history.url, "bsPID") != expected_bspid
            or query_value(history.url, "bsWriterID") != student.student_code
            or query_value(history.url, "scpid") != student.scpid
        ):
            raise DiscoveryBlock("writing_detail_identity_mismatch")
        links.append(SiteLinkEvidence(history.url, title, (("Title", title), ("Type", genre))))
        history.go_back(wait_until="domcontentloaded")
        history.wait_for_url("**/Manager/Homework/writing/list.php?*")
        _validate_current_route(history, policy, "writing_history", expected_origin_url=history_origin_url)
    return tuple(links), record_count * 2


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


def discover_one_class_live(
    browser: Any,
    class_code: str,
    *,
    route_policy: ReadOnlyRoutePolicy = DOCUMENTED_ROUTE_POLICY,
    menu_opener: Callable[[Any, str, str], Any] = _open_top_menu,
    class_control_reader: Callable[[Any], tuple[tuple[ClassControlEvidence, ...], int]] = collect_class_controls,
    roster_reader: Callable[[Any, str], tuple[tuple[Any, str, str], ...]] = _roster_controls,
    profile_opener: Callable[[Any, Any, str, ReadOnlyRoutePolicy], Any] = _open_student_profile,
    history_opener: Callable[[Any, str, ReadOnlyRoutePolicy], tuple[Any, str, int]] = _open_writing_history,
    record_reader: Callable[[Any, StudentContext, ReadOnlyRoutePolicy], tuple[tuple[SiteLinkEvidence, ...], int]] = _history_record_links,
) -> DiscoveryOutcome:
    """Discover one current class through the verified live manager controls."""
    pages = [page for context in browser.contexts for page in context.pages]
    issues: Counter[str] = Counter()
    managers = [page for page in pages if urlsplit(page.url).path == "/Manager/index.html"]
    if len(managers) != 1:
        issues["missing_or_ambiguous_manager_page"] += 1
        return DiscoveryOutcome(
            DiscoveryReport(True, 0, False, 0, 0, 0, 0, 0, False, False, None, dict(issues)),
            (),
        )
    manager = managers[0]
    navigation_gets = 0
    contexts: list[WritingRecordContext] = []
    students_scanned = 0
    records_seen = 0
    class_count = 0
    selected_class_found = False
    roster_controls: tuple[tuple[Any, str, str], ...] = ()
    try:
        menu_opener(manager, "Classes", _CLASS_LIST_PATH)
        controls, _ = class_control_reader(manager)
        class_matches = [control for control in controls if " ".join(control.text.split()) == class_code]
        if len(class_matches) != 1:
            code = "selected_class_ambiguous" if class_matches else "selected_class_missing"
            raise DiscoveryBlock(code)
        selected_class_found = True
        class_count = len(controls)

        roster = menu_opener(manager, "Students", "/Manager/Student/list.php")
        roster_controls = roster_reader(roster, class_code)
        if not roster_controls:
            raise DiscoveryBlock("selected_class_roster_missing")
        if len(roster_controls) > _MAX_STUDENTS:
            issues["student_limit_exceeded"] += 1
            roster_controls = roster_controls[:_MAX_STUDENTS]

        for control, student_name, student_code in roster_controls:
            profile = None
            history = None
            try:
                profile = profile_opener(manager, control, student_code, route_policy)
                navigation_gets += 1
                student_href = profile.url
                history, scpid, route_gets = history_opener(profile, student_code, route_policy)
                navigation_gets += route_gets
                student = StudentContext(class_code, scpid, student_name, student_code, student_href)
                links, detail_gets = record_reader(history, student, route_policy)
                navigation_gets += detail_gets
                records, record_issues = writing_record_contexts(student, links)
                issues.update(issue.code for issue in record_issues)
                records_seen += len(links)
                contexts.extend(records)
                students_scanned += 1
                if len(contexts) > _MAX_RECORDS:
                    issues["record_limit_exceeded"] += 1
                    contexts = contexts[:_MAX_RECORDS]
                    break
            except DiscoveryBlock as error:
                issues[str(error)] += 1
            finally:
                if history is not None and not history.is_closed():
                    history.close()
                if profile is not None and not profile.is_closed():
                    profile.close()
    except DiscoveryBlock as error:
        issues[str(error)] += 1

    issues["history_pagination_unverified"] += 1
    report = DiscoveryReport(
        attach_succeeded=True,
        class_links_discovered=class_count,
        selected_class_found=selected_class_found,
        students_discovered=len(roster_controls),
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
            outcome = discover_one_class_live(browser, args.class_code)
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




