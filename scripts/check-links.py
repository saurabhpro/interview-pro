#!/usr/bin/env python3
"""Validate local links in generated static-site HTML."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append(value)


def check_link(site_root: Path, html_file: Path, href: str) -> str | None:
    parsed = urlparse(href)
    if href.startswith("#") or parsed.scheme in {"http", "https", "mailto", "data"}:
        return None
    if parsed.scheme or parsed.netloc:
        return "uses an absolute or unsupported URL"

    path = unquote(parsed.path)
    if path.startswith("/") or path.startswith("\\"):
        return "uses an absolute path"

    target = (html_file.parent / path).resolve()
    try:
        target.relative_to(site_root)
    except ValueError:
        return "escapes the generated site"

    if not target.is_file():
        return f"points to missing file {target.relative_to(site_root)}"
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check-links.py SITE_ROOT", file=sys.stderr)
        return 2

    site_root = Path(sys.argv[1]).resolve()
    if not site_root.is_dir():
        print(f"LINKS_FAILED: site root does not exist: {site_root}", file=sys.stderr)
        return 2

    errors: list[str] = []
    for html_file in sorted(site_root.rglob("*.html")):
        collector = LinkCollector()
        collector.feed(html_file.read_text(encoding="utf-8"))
        for href in collector.links:
            problem = check_link(site_root, html_file, href)
            if problem:
                errors.append(f"{html_file.relative_to(site_root)}: {href!r} {problem}")

    if errors:
        print("LINKS_FAILED", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1

    print("LINKS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
