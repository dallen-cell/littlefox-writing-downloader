"""Offline foundation for the Little Fox Writing Downloader."""

from .models import SubmissionStatus, SyntheticRecord
from .interpretation import Actor, NormalizedWritingTask, SourceState, interpret_task

__all__ = [
    "Actor",
    "NormalizedWritingTask",
    "SourceState",
    "SubmissionStatus",
    "SyntheticRecord",
    "interpret_task",
]

