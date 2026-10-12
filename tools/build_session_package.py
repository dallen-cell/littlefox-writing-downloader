"""Build the resettable Windows session distribution from explicit safe sources.

No Chrome profile, virtual environment, student data, downloaded artifacts
or private configuration are included in this archive.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_NAME = "LittleFoxWritingSession_Current.zip"

STATIC_FILES = {
    "README.md": "README.md",
    "pyproject.toml": "pyproject.toml",
    "docs/one-record-probe.md": "docs/one-record-probe.md",
    "docs/one-record-gate-b.md": "docs/one-record-gate-b.md",
    "docs/automatic-acquisition.md": "docs/automatic-acquisition.md",
    "session/README_SESSION.txt": "README_SESSION.txt",
    "session/setup_session.cmd": "setup_session.cmd",
    "session/setup_session.ps1": "setup_session.ps1",
    "session/run_one_record_probe.cmd": "run_one_record_probe.cmd",
    "session/run_one_record_review.cmd": "run_one_record_review.cmd",
    "session/run_one_class_dry_run.cmd": "run_one_class_dry_run.cmd",
}


def entries() -> dict[str, Path]:
    """Explicit source-only bundle inventory; no recursive repository packaging."""
    result = {archive_name: ROOT / path for path, archive_name in STATIC_FILES.items()}
    for path in sorted((ROOT / "src" / "littlefox_writing").rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Invalid Python source in session bundle")
        result[path.relative_to(ROOT).as_posix()] = path
    if not any(name.startswith("src/littlefox_writing/") for name in result):
        raise ValueError("Missing Writing package sources")
    for name, path in result.items():
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Required session source missing: {name}")
    return result


def build(output: Path) -> Path:
    """Build a fresh ZIP using source bytes only; refuse to overwrite existing files."""
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, mode="x", compression=ZIP_DEFLATED) as bundle:
        for archive_name, source in sorted(entries().items()):
            bundle.write(source, archive_name)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Writing session-computer distribution")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / BUNDLE_NAME)
    args = parser.parse_args()
    created = build(args.output)
    print(f"Created session distribution: {created}")


if __name__ == "__main__":
    main()
