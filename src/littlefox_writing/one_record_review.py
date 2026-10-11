"""One manually selected Writing record: local, human-verified read-only review.

Reads only the already-open Writing detail popup through loopback CDP.
Does not navigate, infer unknown actors/metadata, grade, or scan students.
Raw field values and writing appear only on the local operator's screen.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from .formatting import format_record
from .interpretation import Actor, DecisionKind, NormalizedWritingTask, SourceState, interpret_task
from .one_record_probe import (
    ProbeConfigurationError, _is_candidate_page, _read_states, validate_cdp_endpoint,
)


class LocalBlock(Exception):
    """Deliberate fail-closed condition without source-bearing text."""


def _require_yes(ask: Callable[[str], str], prompt: str) -> bool:
    return ask(prompt).strip() == "YES"


def _field(ask: Callable[[str], str], label: str) -> str:
    value = ask(label + ": ")
    if not value.strip() or any(ord(c) < 32 or c in "\u2028\u2029" for c in value):
        raise LocalBlock("invalid_manual_metadata")
    return value


def _snapshot(browser: Any) -> tuple[Any, tuple[Any, ...]]:
    pages = [page for context in browser.contexts for page in context.pages]
    matches = [page for page in pages if _is_candidate_page(page)]
    if len(matches) != 1:
        raise LocalBlock("no_matching_detail_page" if not matches else "multiple_matching_detail_pages")
    states, blockers = _read_states(matches[0])
    if blockers or not states:
        raise LocalBlock("numbered_source_fields_incomplete")
    if any(not s.writer_evidence or not s.timestamp_evidence or not s.source_html for s in states):
        raise LocalBlock("required_source_evidence_missing")
    return matches[0], states


def _source_signature(states: tuple[Any, ...]) -> tuple[tuple[Any, ...], ...]:
    """Comparison remains in memory; no hashes or student data are logged."""
    return tuple(
        (s.source_index, s.writer_evidence, s.timestamp_evidence, s.source_html)
        for s in states
    )


def review_browser(
    browser: Any,
    *,
    ask: Callable[[str], str] = input,
    emit: Callable[[str], None] = print,
    output: Path | None = None,
) -> dict[str, Any]:
    """Safely handle one current popup with local, explicit human verification."""
    page, states = _snapshot(browser)
    original = _source_signature(states)
    emit("LOCAL ONLY: writer/timestamp evidence and later preview may identify a student.")
    emit("Do not copy the private review display into chat, GitHub, or logs.")
    emit("Compare each state with the site's normal Writing view; do not infer roles from order.")
    for s in states:
        emit("Source index " + str(s.source_index))
        emit("  writers_N: " + json.dumps(s.writer_evidence, ensure_ascii=False))
        emit("  regdate_N: " + json.dumps(s.timestamp_evidence, ensure_ascii=False))
    if not _require_yes(
        ask, "Have you independently confirmed the source indexes, actors and chronology in the site UI? Type YES: "
    ):
        raise LocalBlock("actor_or_chronology_not_verified")

    normalized = []
    for s in states:
        choice = ask("Source index " + str(s.source_index) + " actor shown by the site (S=student, T=teacher): ").strip().upper()
        if choice not in ("S", "T"):
            raise LocalBlock("actor_mapping_unverified")
        normalized.append(
            SourceState(
                source_index=s.source_index,
                actor=Actor.STUDENT if choice == "S" else Actor.TEACHER,
                source_html=s.source_html,
            )
        )
    if not _require_yes(
        ask, "Is that entire actor chain correctly matched to the actual site display? Type YES: "
    ):
        raise LocalBlock("actor_mapping_unverified")
    if normalized[-1].actor is Actor.TEACHER:
        return {"outcome": "excluded", "reason": "latest_state_teacher", "export_created": False}

    if not _require_yes(
        ask, "Does the site show this latest STUDENT submission is still awaiting a teacher review? Type YES: "
    ):
        raise LocalBlock("outstanding_status_unverified")

    emit("For THIS SAME record, read the class/student fields from site-provided navigation")
    emit("and the exact Title/Type from its Writing HISTORY row; do not guess or use generic 'Writing'.")
    class_code = _field(ask, "Class")
    student_name = _field(ask, "Student display name")
    student_code = _field(ask, "Student code")
    title = _field(ask, "Writing history title")
    genre = _field(ask, "Writing history genre/type")
    if not _require_yes(
        ask, "Have you compared ALL FIVE fields above with this record's actual site pages? Type YES: "
    ):
        raise LocalBlock("required_metadata_mapping_unverified")

    task = NormalizedWritingTask(
        task_id="one-manually-selected-record",
        class_code=class_code,
        student_name=student_name,
        student_code=student_code,
        title=title,
        genre=genre,
        states=tuple(normalized),
        chain_complete=True,
        chronology_reliable=True,  # Explicitly attested above, never inferred from the page.
        status_evidence_supported=True,  # Explicitly attested above.
    )
    result = interpret_task(task)
    if result.kind is not DecisionKind.CANDIDATE or result.record is None:
        # Never emit parser detail: unknown tag/attribute values may be personal.
        return {
            "outcome": result.kind.value,
            "reason": result.reason.value if result.reason else "unknown",
            "export_created": False,
        }

    emit("LOCAL CORRECTION PREVIEW (private, not written yet):")
    emit(format_record(result.record))
    if not _require_yes(
        ask, "Does the full preview EXACTLY match this student's current Writing, including punctuation and breaks, with no missing words or retained correction marks? Type YES: "
    ):
        raise LocalBlock("text_not_human_verified")
    if output is None:
        destination = ask("Optional: enter a NEW local .txt path to export, or press Enter for preview only: ").strip()
        if not destination:
            return {"outcome": "preview_verified_no_file", "export_created": False}
        output = Path(destination)
    if output.suffix.lower() != ".txt":
        raise LocalBlock("output_must_be_txt")

    if ask("Write ONE local .txt file at your chosen location? Type EXPORT: ").strip() != "EXPORT":
        raise LocalBlock("export_not_confirmed")
    # The final source read happens AFTER confirmation, just before writing.
    latest_page, latest_states = _snapshot(browser)
    if latest_page is not page or _source_signature(latest_states) != original:
        raise LocalBlock("source_changed_since_review")
    # Exclusive creation: never overwrite; user controls destination.
    try:
        with output.open("x", encoding="utf-8", newline="\n") as file:
            file.write(format_record(result.record))
    except FileExistsError:
        raise LocalBlock("output_already_exists") from None
    except OSError:
        raise LocalBlock("output_write_failed") from None
    return {"outcome": "one_record_exported", "export_created": True}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="littlefox-one-record-review",
        description="Human-verified, read-only one-record Writing preview; no site actions.",
    )
    p.add_argument("--cdp-endpoint", default="http://127.0.0.1:9222")
    p.add_argument("--output", type=Path, help="optional user-selected new .txt path; never overwrite")
    return p


def run(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        validate_cdp_endpoint(args.cdp_endpoint)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(args.cdp_endpoint)
            outcome = review_browser(browser, output=args.output)
    except LocalBlock as error:
        outcome = {"outcome": "blocked", "reason": str(error), "export_created": False}
    except (EOFError, KeyboardInterrupt):
        outcome = {"outcome": "blocked", "reason": "operator_cancelled", "export_created": False}
    except ProbeConfigurationError:
        outcome = {"outcome": "blocked", "reason": "invalid_local_cdp_endpoint", "export_created": False}
    except Exception as error:
        # Never print exception messages; they may contain page URLs or content.
        outcome = {"outcome": "blocked", "reason": "local_read_failed:" + type(error).__name__, "export_created": False}
    print("SANITIZED SUMMARY (safe to share):")
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["export_created"] else 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
