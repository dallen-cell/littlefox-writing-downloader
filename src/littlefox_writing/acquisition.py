"""Source-grounded metadata acquisition from site-provided navigation evidence.

This module contains no browser selectors or URL templates. It accepts links
that were read from the current site page, preserves the documented
``scpid`` -> ``bsWriterID`` -> persistent ``bsPID`` relationship, and blocks
when visible metadata is missing or ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit

from .interpretation import NormalizedWritingTask, SourceState


@dataclass(frozen=True, slots=True)
class SiteLinkEvidence:
    """One actual anchor plus optional header/value pairs from its table row."""

    href: str
    text: str
    row_fields: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ClassContext:
    class_code: str
    scpid: str
    href: str


@dataclass(frozen=True, slots=True)
class StudentContext:
    class_code: str
    scpid: str
    student_name: str
    student_code: str
    href: str


@dataclass(frozen=True, slots=True)
class WritingRecordContext:
    class_code: str
    scpid: str
    student_name: str
    student_code: str
    title: str
    genre: str
    bspid: str
    href: str

    def normalized_task(
        self,
        states: tuple[SourceState, ...],
        *,
        chain_complete: bool = True,
        chronology_reliable: bool = True,
        status_evidence_supported: bool = True,
    ) -> NormalizedWritingTask:
        """Adapt one persistent task record and all of its source rounds."""
        return NormalizedWritingTask(
            task_id=self.bspid,
            class_code=self.class_code,
            student_name=self.student_name,
            student_code=self.student_code,
            title=self.title,
            genre=self.genre,
            states=states,
            chain_complete=chain_complete,
            chronology_reliable=chronology_reliable,
            status_evidence_supported=status_evidence_supported,
        )


@dataclass(frozen=True, slots=True)
class AcquisitionIssue:
    code: str
    scope: str


def _clean_visible(value: str) -> str | None:
    cleaned = " ".join(value.split())
    if not cleaned or any(ord(character) < 32 for character in cleaned):
        return None
    return cleaned


def query_value(href: str, name: str) -> str | None:
    """Read one unambiguous nonempty query value without constructing a URL."""
    values = [value for key, value in parse_qsl(urlsplit(href).query, keep_blank_values=True) if key == name]
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def class_contexts(links: tuple[SiteLinkEvidence, ...]) -> tuple[tuple[ClassContext, ...], tuple[AcquisitionIssue, ...]]:
    contexts: dict[str, ClassContext] = {}
    issues: list[AcquisitionIssue] = []
    for link in links:
        scpid = query_value(link.href, "scpid")
        if scpid is None or query_value(link.href, "bsWriterID") is not None or query_value(link.href, "bsPID") is not None:
            continue
        class_code = _clean_visible(link.text)
        if class_code is None:
            issues.append(AcquisitionIssue("missing_class_code", "class_link"))
            continue
        candidate = ClassContext(class_code, scpid, link.href)
        existing = contexts.get(scpid)
        if existing is not None and existing != candidate:
            issues.append(AcquisitionIssue("ambiguous_class_link", "class_link"))
            contexts.pop(scpid, None)
            continue
        contexts[scpid] = candidate
    return tuple(sorted(contexts.values(), key=lambda item: (item.class_code.casefold(), item.scpid))), tuple(issues)


def student_contexts(
    selected_class: ClassContext,
    links: tuple[SiteLinkEvidence, ...],
) -> tuple[tuple[StudentContext, ...], tuple[AcquisitionIssue, ...]]:
    contexts: dict[str, StudentContext] = {}
    issues: list[AcquisitionIssue] = []
    for link in links:
        scpid = query_value(link.href, "scpid")
        writer_id = query_value(link.href, "bsWriterID")
        if scpid != selected_class.scpid or writer_id is None or query_value(link.href, "bsPID") is not None:
            continue
        student_name = _clean_visible(link.text)
        if student_name is None:
            issues.append(AcquisitionIssue("missing_student_name", "student_link"))
            continue
        candidate = StudentContext(
            selected_class.class_code,
            selected_class.scpid,
            student_name,
            writer_id,
            link.href,
        )
        existing = contexts.get(writer_id)
        if existing is not None and existing != candidate:
            issues.append(AcquisitionIssue("ambiguous_student_link", "student_link"))
            contexts.pop(writer_id, None)
            continue
        contexts[writer_id] = candidate
    return tuple(sorted(contexts.values(), key=lambda item: (item.student_name.casefold(), item.student_code))), tuple(issues)


_TITLE_HEADERS = {"title", "writing title", "task title"}
_GENRE_HEADERS = {"type", "genre", "writing type"}


def _row_value(fields: tuple[tuple[str, str], ...], accepted_headers: set[str]) -> str | None:
    candidates = {
        cleaned_value
        for header, value in fields
        if (cleaned_header := _clean_visible(header)) is not None
        and cleaned_header.casefold() in accepted_headers
        and (cleaned_value := _clean_visible(value)) is not None
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def writing_record_contexts(
    student: StudentContext,
    links: tuple[SiteLinkEvidence, ...],
) -> tuple[tuple[WritingRecordContext, ...], tuple[AcquisitionIssue, ...]]:
    contexts: dict[str, WritingRecordContext] = {}
    issues: list[AcquisitionIssue] = []
    conflicted: set[str] = set()
    for link in links:
        bspid = query_value(link.href, "bsPID")
        if bspid is None:
            continue
        linked_writer = query_value(link.href, "bsWriterID")
        linked_class = query_value(link.href, "scpid")
        if linked_writer is not None and linked_writer != student.student_code:
            issues.append(AcquisitionIssue("record_student_mismatch", "history_link"))
            continue
        if linked_class is not None and linked_class != student.scpid:
            issues.append(AcquisitionIssue("record_class_mismatch", "history_link"))
            continue

        visible_title = _clean_visible(link.text)
        row_title = _row_value(link.row_fields, _TITLE_HEADERS)
        title = row_title or visible_title
        if title is None or (row_title is not None and visible_title is not None and row_title != visible_title):
            issues.append(AcquisitionIssue("ambiguous_writing_title", "history_row"))
            continue
        genre = _row_value(link.row_fields, _GENRE_HEADERS)
        if genre is None:
            issues.append(AcquisitionIssue("missing_or_ambiguous_writing_genre", "history_row"))
            continue

        candidate = WritingRecordContext(
            student.class_code,
            student.scpid,
            student.student_name,
            student.student_code,
            title,
            genre,
            bspid,
            link.href,
        )
        existing = contexts.get(bspid)
        if existing is not None and existing != candidate:
            conflicted.add(bspid)
            contexts.pop(bspid, None)
            issues.append(AcquisitionIssue("ambiguous_record_link", "history_row"))
            continue
        if bspid not in conflicted:
            contexts[bspid] = candidate
    return tuple(sorted(contexts.values(), key=lambda item: (item.title.casefold(), item.bspid))), tuple(issues)

