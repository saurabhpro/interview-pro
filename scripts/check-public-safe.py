#!/usr/bin/env python3
"""Reject private links and identifiers from public repository text files."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SKIPPED_DIRECTORIES = {".git", "_site"}


def _joined(*parts: str) -> str:
    return "".join(parts)


PATTERNS = (
    ("private webmail link", re.compile(r"mail[.]google[.]com", re.IGNORECASE)),
    ("private calendar link", re.compile(r"calendar[.]google[.]com", re.IGNORECASE)),
    ("private professional-network message", re.compile(r"linkedin[.]com/messaging", re.IGNORECASE)),
    ("private meeting-note reference", re.compile(_joined("gra", "nola"), re.IGNORECASE)),
    ("absolute macOS user path", re.compile(_joined("/", "Users", "/"), re.IGNORECASE)),
    ("daily preparation path", re.compile(_joined("interview-prep", "/daily"), re.IGNORECASE)),
    ("personal email address", re.compile(r"@gmail[.]com", re.IGNORECASE)),
    ("JPMorgan email address", re.compile(r"@jpmchase[.]com", re.IGNORECASE)),
    ("Wise email address", re.compile(r"@wise[.]com", re.IGNORECASE)),
    ("Plum email address", re.compile(r"@withplum[.]com", re.IGNORECASE)),
    ("Zuba email address", re.compile(r"@zuba[.]com", re.IGNORECASE)),
    (
        "UK mobile number",
        re.compile(r"(?<![\w+])(?:[+]44[\s().-]*(?:0[\s().-]*)?7|07)(?:[\s().-]*\d){9}\b", re.IGNORECASE),
    ),
    ("raw plugin link", re.compile(_joined("plugin", "://"), re.IGNORECASE)),
)


def text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIPPED_DIRECTORIES for part in path.parts):
            continue
        try:
            raw = path.read_bytes()
        except OSError as error:
            yield path, None, error
            continue
        if b"\0" in raw:
            continue
        try:
            yield path, raw.decode("utf-8"), None
        except UnicodeDecodeError:
            continue


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    violations = 0
    for path, content, error in text_files(root):
        display_path = path.relative_to(root)
        if error is not None:
            print(f"{display_path}: unable to scan: {error}")
            violations += 1
            continue
        assert content is not None
        for line_number, line in enumerate(content.splitlines(), start=1):
            for label, pattern in PATTERNS:
                for match in pattern.finditer(line):
                    print(f"{display_path}:{line_number}:{match.start() + 1}: {label}")
                    violations += 1

    if violations:
        print(f"PUBLIC_UNSAFE: {violations} violation(s)")
        return 1

    print("PUBLIC_SAFE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
