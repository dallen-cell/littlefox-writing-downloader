"""Local, read-only CDP probe for one human-opened Writing detail page.

This module deliberately does not navigate, click, fill, submit, discover
classes, interpret actors, clean live markup, or write a correction file.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
import json
import re
from typing import Any, Callable
from urllib.parse import urlsplit


_FIELD_ID = re.compile(r"^(contents|writers|regdate)_(\d+)$")
_FIELD_SELECTORS = tuple(f'[id^="{prefix}_"]' for prefix in ("contents", "writers", "regdate"))
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class ProbeConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _SourceState:
    source_index: int
    writer_evidence: str
    timestamp_evidence: str
    source_html: str


@dataclass(frozen=True, slots=True)
class ProbeReport:
    attach_succeeded: bool
    matching_pages: int
    source_state_count: int
    writer_fields_complete: bool
    timestamp_fields_complete: bool
    source_html_complete: bool
    html_element_count: int
    html_attribute_count: int
    states_with_html_elements: int
    blockers: tuple[str, ...]
    export_created: bool = False

    def sanitized_json(self) -> str:
        """Return diagnostics containing no URLs, values, HTML, or student text."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)


class _StructureCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.element_count = 0
        self.attribute_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.element_count += 1
        self.attribute_count += len(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def validate_cdp_endpoint(endpoint: str) -> str:
    """Accept an explicit local HTTP CDP endpoint and reject remote/proxied use."""
    parsed = urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
        raise ProbeConfigurationError("CDP endpoint must be an http:// loopback address")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProbeConfigurationError("CDP endpoint must not contain credentials, query, or fragment")
    if parsed.path not in ("", "/"):
        raise ProbeConfigurationError("CDP endpoint must not contain a path")
    try:
        port = parsed.port
    except ValueError as error:
        raise ProbeConfigurationError("CDP endpoint has an invalid port") from error
    if port is None:
        raise ProbeConfigurationError("CDP endpoint must include the local debugging port")
    return endpoint


def _matching_field_ids(page: Any) -> tuple[str, ...]:
    ids: list[str] = []
    for selector in _FIELD_SELECTORS:
        locator = page.locator(selector)
        for position in range(locator.count()):
            value = locator.nth(position).get_attribute("id")
            if value is not None:
                ids.append(value)
    return tuple(ids)


def _is_candidate_page(page: Any) -> bool:
    matched = {_FIELD_ID.fullmatch(value).group(1) for value in _matching_field_ids(page) if _FIELD_ID.fullmatch(value)}
    return matched == {"contents", "writers", "regdate"}


def _element_value(element: Any) -> str:
    value = element.get_attribute("value")
    if value is not None:
        return value
    return element.text_content() or ""


def _read_states(page: Any) -> tuple[tuple[_SourceState, ...], tuple[str, ...]]:
    elements: dict[tuple[str, int], Any] = {}
    blockers: list[str] = []
    seen_ids: set[str] = set()
    for selector in _FIELD_SELECTORS:
        locator = page.locator(selector)
        for position in range(locator.count()):
            element = locator.nth(position)
            element_id = element.get_attribute("id")
            match = _FIELD_ID.fullmatch(element_id or "")
            if match is None:
                blockers.append("malformed_numbered_field_id")
                continue
            if element_id in seen_ids:
                blockers.append("duplicate_numbered_field_id")
                continue
            seen_ids.add(element_id)
            elements[(match.group(1), int(match.group(2)))] = element

    index_sets = {
        prefix: {index for candidate_prefix, index in elements if candidate_prefix == prefix}
        for prefix in ("contents", "writers", "regdate")
    }
    if not index_sets["contents"]:
        blockers.append("no_numbered_source_states")
    if len({frozenset(indices) for indices in index_sets.values()}) != 1:
        blockers.append("mismatched_numbered_state_fields")
        return (), tuple(sorted(set(blockers)))

    states = tuple(
        _SourceState(
            source_index=index,
            writer_evidence=_element_value(elements[("writers", index)]),
            timestamp_evidence=_element_value(elements[("regdate", index)]),
            source_html=elements[("contents", index)].inner_html(),
        )
        for index in sorted(index_sets["contents"])
    )
    return states, tuple(sorted(set(blockers)))


def inspect_browser(browser: Any) -> ProbeReport:
    """Inspect the unique Writing detail popup without changing any page."""
    pages = [page for context in browser.contexts for page in context.pages]
    if not pages:
        return ProbeReport(True, 0, 0, False, False, False, 0, 0, 0, ("no_open_page",))

    # Little Fox opens Writing details in a separate popup. The main manager
    # window is expected to remain open: select by observed DOM structure,
    # never by tab count, tab order, URL guesses, or a clicked page.
    candidates = [page for page in pages if _is_candidate_page(page)]
    if not candidates:
        return ProbeReport(True, 0, 0, False, False, False, 0, 0, 0, ("no_matching_detail_page",))
    if len(candidates) != 1:
        return ProbeReport(
            True, len(candidates), 0, False, False, False, 0, 0, 0,
            ("multiple_matching_detail_pages",),
        )

    states, acquisition_blockers = _read_states(candidates[0])
    element_count = 0
    attribute_count = 0
    states_with_elements = 0
    for state in states:
        collector = _StructureCollector()
        collector.feed(state.source_html)
        collector.close()
        element_count += collector.element_count
        attribute_count += collector.attribute_count
        states_with_elements += collector.element_count > 0

    blockers = list(acquisition_blockers)
    writer_complete = bool(states) and all(state.writer_evidence != "" for state in states)
    timestamp_complete = bool(states) and all(state.timestamp_evidence != "" for state in states)
    html_complete = bool(states) and all(state.source_html != "" for state in states)
    if not writer_complete:
        blockers.append("writer_evidence_missing")
    if not timestamp_complete:
        blockers.append("timestamp_evidence_missing")
    if not html_complete:
        blockers.append("source_html_missing")

    # These gates intentionally remain blocked until this one-record human
    # validation establishes real values and selectors without guesswork.
    blockers.extend(
        (
            "actor_mapping_unverified",
            "required_metadata_mapping_unverified",
            "live_markup_semantics_unverified",
        )
    )
    return ProbeReport(
        attach_succeeded=True,
        matching_pages=1,
        source_state_count=len(states),
        writer_fields_complete=writer_complete,
        timestamp_fields_complete=timestamp_complete,
        source_html_complete=html_complete,
        html_element_count=element_count,
        html_attribute_count=attribute_count,
        states_with_html_elements=states_with_elements,
        blockers=tuple(sorted(set(blockers))),
    )


def run_probe(
    endpoint: str,
    *,
    playwright_factory: Callable[[], Any] | None = None,
) -> ProbeReport:
    """Attach to human-started local Chrome and inspect its existing tabs."""
    validate_cdp_endpoint(endpoint)
    if playwright_factory is None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise ProbeConfigurationError(
                'Playwright is not installed; run: python -m pip install -e ".[probe]"'
            ) from error
        playwright_factory = sync_playwright

    try:
        with playwright_factory() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint)
            return inspect_browser(browser)
    except ProbeConfigurationError:
        raise
    except Exception as error:
        # Do not echo exception text: it can contain a full page URL or local
        # profile details. The exception type is sufficient for local triage.
        return ProbeReport(
            False,
            0,
            0,
            False,
            False,
            False,
            0,
            0,
            0,
            (f"cdp_attach_or_read_failed:{type(error).__name__}",),
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="littlefox-one-record-probe",
        description="Read-only local CDP preflight for one manually opened Writing detail page.",
    )
    result.add_argument(
        "--cdp-endpoint",
        default="http://127.0.0.1:9222",
        help="loopback Chrome debugging endpoint (default: http://127.0.0.1:9222)",
    )
    return result


def run(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = run_probe(args.cdp_endpoint)
    except ProbeConfigurationError as error:
        print(json.dumps({"configuration_error": str(error)}, indent=2))
        return 2
    print(report.sanitized_json())
    return 0 if report.attach_succeeded and not report.blockers else 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

