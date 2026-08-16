#!/usr/bin/env python3
"""Fail closed when unsafe source artifacts enter the portfolio archive."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
MAX_FILE_BYTES = 1_000_000
MAX_TRACKED_BYTES = 5_000_000

FORBIDDEN_SEGMENTS = {
    "__pycache__",
    ".venv",
    "node_modules",
    "raw",
    "source_data",
    "source_corpus",
    "evidence",
    "original_json_copies",
    "outputs",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pdf",
    ".tif",
    ".tiff",
    ".png",
    ".jpg",
    ".jpeg",
    ".zip",
    ".7z",
    ".rar",
    ".xlsx",
    ".xls",
    ".docx",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".db",
    ".sqlite",
}

CONTENT_PATTERNS = {
    "absolute Windows path": re.compile(r"\b[A-Za-z]:\\"),
    "email address": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "Chinese phone shape": re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
    "Chinese identity shape": re.compile(
        r"(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)"
    ),
    "private key header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "GitHub token shape": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "cloud access key shape": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "LLM API key shape": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
}


def repository_files() -> list[Path]:
    git_dir = ROOT / ".git"
    if git_dir.exists():
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
        return [ROOT / name for name in names]
    return sorted(path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts)


def main() -> int:
    failures: list[tuple[str, str]] = []
    files = repository_files()
    total_bytes = 0

    for path in files:
        relative = path.relative_to(ROOT)
        relative_text = relative.as_posix()
        lowered_parts = {part.lower() for part in relative.parts}
        if lowered_parts & FORBIDDEN_SEGMENTS:
            failures.append(("forbidden path segment", relative_text))
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(("forbidden file type", relative_text))
        if path.name.startswith(".env") and path.name != ".env.example":
            failures.append(("environment file", relative_text))

        size = path.stat().st_size
        total_bytes += size
        if size > MAX_FILE_BYTES:
            failures.append(("file exceeds safe size", relative_text))

        if path.resolve() == SELF:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(("non-UTF-8 or binary content", relative_text))
            continue
        for label, pattern in CONTENT_PATTERNS.items():
            if pattern.search(text):
                failures.append((label, relative_text))

    if total_bytes > MAX_TRACKED_BYTES:
        failures.append(("tracked tree exceeds safe size", "."))

    if failures:
        for label, path in sorted(set(failures)):
            print(f"{label}: {path}", file=sys.stderr)
        print("Security scan failed; matched values were intentionally withheld.", file=sys.stderr)
        return 1

    print(f"Security scan passed for {len(files)} files ({total_bytes} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
