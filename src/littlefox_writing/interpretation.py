"""Offline interpretation of normalized synthetic Writing state chains."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .markup import MarkupBlocked, MarkupResult, interpret_html
from .models import SubmissionStatus, SyntheticRecord


class Actor(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceState:
    source_index: int | None
    actor: Actor
    source_html: str | None = None
    submitted_at: datetime | None = None
    raw_status: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedWritingTask:
    task_id: str
    class_code: str
    student_name: str
    student_code: str
    title: str
    genre: str
    states: tuple[SourceState, ...]
    chain_complete: bool = True
    chronology_reliable: bool = True
    status_evidence_supported: bool = True


class DecisionKind(StrEnum):
    CANDIDATE = "candidate"
    EXCLUDED = "excluded"
    BLOCKED = "blocked"


class ReasonCode(StrEnum):
    LATEST_STATE_TEACHER = "latest_state_teacher"
    EMPTY_CHAIN = "empty_chain"
    INCOMPLETE_CHAIN = "incomplete_chain"
    UNRELIABLE_CHRONOLOGY = "unreliable_chronology"
    UNKNOWN_STATUS = "unknown_status"
    MISSING_SOURCE_INDEX = "missing_source_index"
    INVALID_SOURCE_INDEX = "invalid_source_index"
    DUPLICATE_SOURCE_INDEX = "duplicate_source_index"
    NON_MONOTONE_SOURCE_INDEX = "non_monotone_source_index"
    UNKNOWN_ACTOR = "unknown_actor"
    CHAIN_DOES_NOT_START_WITH_STUDENT = "chain_does_not_start_with_student"
    CONSECUTIVE_STUDENT_STATES = "consecutive_student_states"
    CONSECUTIVE_TEACHER_STATES = "consecutive_teacher_states"
    MISSING_STUDENT_HTML = "missing_student_html"
    MARKUP_WITHOUT_REVIEW = "markup_without_review"
    INVALID_METADATA = "invalid_metadata"
    UNSUPPORTED_MARKUP = "unsupported_markup"


@dataclass(frozen=True, slots=True)
class InterpretationDecision:
    kind: DecisionKind
    reason: ReasonCode | None
    detail: str
    record: SyntheticRecord | None = None
    markup: MarkupResult | None = None


def _blocked(reason: ReasonCode, detail: str) -> InterpretationDecision:
    return InterpretationDecision(DecisionKind.BLOCKED, reason, detail)


def interpret_task(task: NormalizedWritingTask) -> InterpretationDecision:
    """Return an outstanding record or a structured excluded/blocked result."""
    if not task.chain_complete:
        return _blocked(ReasonCode.INCOMPLETE_CHAIN, "The normalized source chain is incomplete")
    if not task.chronology_reliable:
        return _blocked(ReasonCode.UNRELIABLE_CHRONOLOGY, "The normalized chronology is unreliable")
    if not task.status_evidence_supported:
        return _blocked(ReasonCode.UNKNOWN_STATUS, "Status evidence is unsupported or ambiguous")
    if not task.states:
        return _blocked(ReasonCode.EMPTY_CHAIN, "No source states were supplied")

    indices = [state.source_index for state in task.states]
    if any(index is None for index in indices):
        return _blocked(ReasonCode.MISSING_SOURCE_INDEX, "Every source state needs an explicit index")
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indices):
        return _blocked(ReasonCode.INVALID_SOURCE_INDEX, "Source indices must be non-negative integers")
    concrete_indices = [index for index in indices if index is not None]
    if any(index < 0 for index in concrete_indices):
        return _blocked(ReasonCode.INVALID_SOURCE_INDEX, "Source indices must be non-negative")
    if len(set(concrete_indices)) != len(concrete_indices):
        return _blocked(ReasonCode.DUPLICATE_SOURCE_INDEX, "Source indices must be unique")
    if concrete_indices != sorted(concrete_indices):
        return _blocked(ReasonCode.NON_MONOTONE_SOURCE_INDEX, "Source indices must be strictly increasing")

    if any(not isinstance(state.actor, Actor) or state.actor is Actor.UNKNOWN for state in task.states):
        return _blocked(ReasonCode.UNKNOWN_ACTOR, "Every source actor must be normalized explicitly")
    if task.states[0].actor is not Actor.STUDENT:
        return _blocked(
            ReasonCode.CHAIN_DOES_NOT_START_WITH_STUDENT,
            "A review chain cannot begin with a teacher state",
        )
    for previous, current in zip(task.states, task.states[1:]):
        if previous.actor is current.actor is Actor.STUDENT:
            return _blocked(
                ReasonCode.CONSECUTIVE_STUDENT_STATES,
                "Consecutive student states have ambiguous review pairing",
            )
        if previous.actor is current.actor is Actor.TEACHER:
            return _blocked(
                ReasonCode.CONSECUTIVE_TEACHER_STATES,
                "Consecutive teacher states have ambiguous review pairing",
            )

    latest = task.states[-1]
    if latest.actor is Actor.TEACHER:
        return InterpretationDecision(
            DecisionKind.EXCLUDED,
            ReasonCode.LATEST_STATE_TEACHER,
            "The latest student submission has a later teacher review",
        )
    if latest.source_html is None:
        return _blocked(ReasonCode.MISSING_STUDENT_HTML, "Latest student state has no source HTML")

    try:
        markup = interpret_html(latest.source_html)
    except MarkupBlocked as error:
        return _blocked(ReasonCode.UNSUPPORTED_MARKUP, f"{error.code}: {error.detail}")

    if len(task.states) == 1:
        if markup.has_recognized_markup:
            return _blocked(
                ReasonCode.MARKUP_WITHOUT_REVIEW,
                "Recognized inherited correction markup has no preceding teacher review",
            )
        status = SubmissionStatus.INITIAL
    else:
        status = (
            SubmissionStatus.REVISION_TAGGED
            if markup.has_recognized_markup
            else SubmissionStatus.REVISION_CLEAN
        )
    try:
        record = SyntheticRecord(
            record_id=f"{task.task_id}:{latest.source_index}",
            class_code=task.class_code,
            student_name=task.student_name,
            student_code=task.student_code,
            title=task.title,
            genre=task.genre,
            status=status,
            writing=markup.correction_text,
            submitted_at=latest.submitted_at,
        )
    except ValueError as error:
        return _blocked(ReasonCode.INVALID_METADATA, str(error))
    return InterpretationDecision(
        DecisionKind.CANDIDATE,
        None,
        "Latest student state is awaiting teacher review",
        record=record,
        markup=markup,
    )

