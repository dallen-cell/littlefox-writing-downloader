"""Exact correction-text formatting."""

from .models import SyntheticRecord


def format_record(record: SyntheticRecord) -> str:
    """Format exactly the seven agreed fields without altering writing text."""
    return (
        f"Class: {record.class_code}\n"
        f"Student: {record.student_name}\n"
        f"Student Code: {record.student_code}\n"
        f"Title: {record.title}\n"
        f"Type: {record.genre}\n"
        f"Status: {record.status.value}\n"
        "\n"
        "Writing:\n"
        f"{record.writing}"
    )

