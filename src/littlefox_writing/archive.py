"""Safe deterministic ZIP creation for selected synthetic records."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .formatting import format_record
from .models import SyntheticRecord

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_component(value: str, fallback: str = "untitled") -> str:
    cleaned = _UNSAFE.sub("_", value).strip().rstrip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned[:100].rstrip(" .") or fallback


def archive_names(records: tuple[SyntheticRecord, ...]) -> dict[str, str]:
    """Assign stable paths that remain unique on case-insensitive Windows."""
    names: dict[str, str] = {}
    used_paths: set[str] = set()
    ordered = sorted(
        records,
        key=lambda item: (
            item.class_code.casefold(),
            item.student_code.casefold(),
            item.title.casefold(),
            item.record_id,
        ),
    )
    for record in ordered:
        if record.record_id in names:
            raise ValueError(f"Duplicate record identity: {record.record_id}")
        folder = safe_component(record.class_code, "class")
        stem = safe_component(f"{record.student_code} - {record.title}")
        suffix_number = 1
        while True:
            suffix = "" if suffix_number == 1 else f" ({suffix_number})"
            path = str(PurePosixPath(folder, f"{stem}{suffix}.txt"))
            windows_key = path.casefold()
            if windows_key not in used_paths:
                used_paths.add(windows_key)
                names[record.record_id] = path
                break
            suffix_number += 1
    return names


def write_archive(records: tuple[SyntheticRecord, ...], destination: Path) -> tuple[str, ...]:
    """Create one new ZIP atomically enough to prevent silent overwrite."""
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing export: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    paths = archive_names(records)
    archive: ZipFile | None = None
    try:
        archive = ZipFile(destination, "x", compression=ZIP_DEFLATED)
        for record in sorted(records, key=lambda item: paths[item.record_id]):
            info = ZipInfo(paths[record.record_id], date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, format_record(record).encode("utf-8"))
    except BaseException:
        if archive is not None:
            archive.close()
            destination.unlink(missing_ok=True)
        raise
    finally:
        if archive is not None:
            archive.close()
    return tuple(sorted(paths.values()))

