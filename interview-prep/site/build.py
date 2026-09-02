#!/usr/bin/env python3
"""Build the curated interview-preparation library as a static GitHub Pages site."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlparse


SITE_ROOT = Path(__file__).resolve().parent
# This builder lives at interview-prep/site/build.py inside this standalone
# repository. Keep every input and output rooted here rather than in the
# repository from which the site was originally copied.
PROJECT_ROOT = SITE_ROOT.parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "_site"
PRIVATE_HOSTS = {
    ".".join(("mail", "google", "com")),
    ".".join(("calendar", "google", "com")),
}
PRIVATE_NOTES_HOST = "".join(("gra", "nola", ".ai"))
LINKEDIN_HOSTS = {
    ".".join(("linkedin", "com")),
    ".".join(("www", "linkedin", "com")),
}
LINKEDIN_MESSAGING_PATH = "/" + "messaging"


def is_private_source_url(href: str) -> bool:
    """Return whether a URL could expose private correspondence or notes."""

    parsed = urlparse(href)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path.lower()
    return (
        parsed.scheme.lower() == "mailto"
        or host in PRIVATE_HOSTS
        or host.endswith("." + PRIVATE_NOTES_HOST)
        or host == PRIVATE_NOTES_HOST
        or (host in LINKEDIN_HOSTS and path.startswith(LINKEDIN_MESSAGING_PATH))
    )


def safe_external_href(href: str) -> str:
    return "#" if is_private_source_url(href) else href


def validate_catalog_path(catalog_path: object) -> Path:
    """Resolve a catalog source only when it stays in a public content root."""

    if not isinstance(catalog_path, str) or not catalog_path:
        raise ValueError(f"invalid catalog path: {catalog_path!r} must be a non-empty string")

    decoded_path = catalog_path
    for _ in range(8):
        next_decoded_path = unquote(decoded_path)
        if next_decoded_path == decoded_path:
            break
        decoded_path = next_decoded_path
    else:
        raise ValueError(f"invalid catalog path: {catalog_path!r} has excessive URL encoding")

    decoded_parts = decoded_path.replace("\\", "/").split("/")
    windows_path = PureWindowsPath(decoded_path)
    if (
        Path(catalog_path).is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or "\\" in catalog_path
        or ".." in decoded_parts
    ):
        raise ValueError(f"invalid catalog path: {catalog_path!r} must be relative without traversal")

    path_parts = catalog_path.split("/")
    if not path_parts or path_parts[0] not in {"content", "code"}:
        raise ValueError(f"invalid catalog path: {catalog_path!r} must be under content/ or code/")

    project_root = PROJECT_ROOT.resolve()
    source = (project_root / catalog_path).resolve()
    allowed_root = (project_root / path_parts[0]).resolve()
    try:
        allowed_root.relative_to(project_root)
        source.relative_to(allowed_root)
    except ValueError as error:
        raise ValueError(
            f"invalid catalog path: {catalog_path!r} resolves outside {path_parts[0]}/"
        ) from error
    return source


def read_catalog() -> list[dict]:
    catalog = json.loads((SITE_ROOT / "catalog.json").read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in catalog]
    if len(ids) != len(set(ids)):
        raise ValueError("catalog IDs must be unique")

    sources = [validate_catalog_path(entry.get("path")) for entry in catalog]
    for entry, source in zip(catalog, sources, strict=True):
        if not source.is_file():
            raise FileNotFoundError(f"catalog source does not exist: {entry['path']}")
        entry.setdefault("kind", source.suffix.removeprefix(".") or "text")
    return catalog


def safe_href(href: str, source_path: str, path_to_id: dict[str, str]) -> str:
    """Resolve local markdown links into site pages; leave trusted URLs intact."""

    href = href.strip()
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https", "mailto"}:
        return safe_external_href(href)
    if href.startswith("#"):
        return href
    if parsed.scheme or href.lower().startswith("javascript:"):
        return "#"

    target = (PROJECT_ROOT / Path(source_path).parent / href.split("#", 1)[0]).resolve()
    try:
        relative = target.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return "#"

    fragment = ""
    if "#" in href:
        fragment = "#" + href.split("#", 1)[1]
    if relative in path_to_id:
        return f"{path_to_id[relative]}.html{fragment}"
    return "#"


def render_inline(text: str, source_path: str, path_to_id: dict[str, str]) -> str:
    escaped = html.escape(text, quote=False)
    tokens: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        tokens.append(f"<code>{html.escape(match.group(1), quote=False)}</code>")
        return f"\x00TOKEN{len(tokens) - 1}\x00"

    escaped = re.sub(r"`([^`]+)`", stash_code, escaped)

    def link_replacement(match: re.Match[str]) -> str:
        label = match.group(1)
        href = safe_href(html.unescape(match.group(2)), source_path, path_to_id)
        return f'<a href="{html.escape(href, quote=True)}">{label}</a>'

    escaped = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)", link_replacement, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", escaped)

    for index, token in enumerate(tokens):
        escaped = escaped.replace(f"\x00TOKEN{index}\x00", token)
    return escaped


def table_cells(line: str) -> list[str]:
    content = line.strip()
    if content.startswith("|"):
        content = content[1:]
    if content.endswith("|"):
        content = content[:-1]
    return [cell.strip() for cell in content.split("|")]


def is_table_separator(line: str) -> bool:
    cells = table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def render_markdown(markdown: str, source_path: str, path_to_id: dict[str, str]) -> str:
    lines = markdown.replace("\r\n", "\n").split("\n")
    output: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        fence = re.match(r"^\s*```\s*([\w+-]*)\s*$", line)
        if fence:
            language = fence.group(1)
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not re.match(r"^\s*```\s*$", lines[index]):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            if language.lower() == "mermaid":
                # Mermaid reads the diagram source from textContent and replaces
                # this container with an SVG in the browser. HTML-escape the
                # source so public content cannot become executable markup.
                diagram = html.escape(chr(10).join(code_lines), quote=False)
                output.append(f'<pre class="mermaid">{diagram}</pre>')
                continue
            class_name = f' class="language-{html.escape(language, quote=True)}"' if language else ""
            output.append(f"<pre><code{class_name}>{html.escape(chr(10).join(code_lines), quote=False)}</code></pre>")
            continue

        heading = re.match(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            level = len(heading.group(1))
            text = render_inline(heading.group(2), source_path, path_to_id)
            anchor = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", heading.group(2).lower())).strip("-")
            output.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            index += 1
            continue

        if stripped in {"---", "***", "___"}:
            output.append("<hr>")
            index += 1
            continue

        if line.lstrip().startswith(">"):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[index]))
                index += 1
            quote = "<br>".join(render_inline(value, source_path, path_to_id) for value in quote_lines)
            output.append(f"<blockquote>{quote}</blockquote>")
            continue

        if "|" in line and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            headers = table_cells(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(table_cells(lines[index]))
                index += 1
            head_html = "".join(f"<th>{render_inline(cell, source_path, path_to_id)}</th>" for cell in headers)
            body_html = "".join(
                "<tr>" + "".join(
                    f"<td>{render_inline(cell, source_path, path_to_id)}</td>" for cell in row
                ) + "</tr>"
                for row in rows
            )
            output.append(f"<div class=table-wrap><table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>")
            continue

        unordered = re.match(r"^\s*[-*+]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if unordered or ordered:
            tag = "ul" if unordered else "ol"
            item_pattern = r"^\s*[-*+]\s+(.+)$" if unordered else r"^\s*\d+[.)]\s+(.+)$"
            items: list[str] = []
            while index < len(lines):
                item_match = re.match(item_pattern, lines[index])
                if not item_match:
                    break
                items.append(f"<li>{render_inline(item_match.group(1), source_path, path_to_id)}</li>")
                index += 1
            output.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines) and lines[index].strip():
            candidate = lines[index]
            if (
                re.match(r"^\s*(#{1,6})\s+", candidate)
                or re.match(r"^\s*```", candidate)
                or candidate.lstrip().startswith(">")
                or re.match(r"^\s*[-*+]\s+", candidate)
                or re.match(r"^\s*\d+[.)]\s+", candidate)
            ):
                break
            paragraph_lines.append(candidate.strip())
            index += 1
        paragraph = "<br>".join(render_inline(value, source_path, path_to_id) for value in paragraph_lines)
        output.append(f"<p>{paragraph}</p>")

    return "\n".join(output)


def render_html_source(content: str) -> str:
    body = re.search(r"<body[^>]*>(.*)</body>", content, flags=re.IGNORECASE | re.DOTALL)
    if not body:
        return html.escape(content, quote=False)
    inner = body.group(1)
    inner = re.sub(r"<script\b[^>]*>.*?</script>", "", inner, flags=re.IGNORECASE | re.DOTALL)
    inner = re.sub(r"<link\b[^>]*>", "", inner, flags=re.IGNORECASE)
    inner = re.sub(
        r"\b(href|src)\s*=\s*(['\"])(.*?)\2",
        lambda match: f'{match.group(1)}={match.group(2)}{html.escape(safe_external_href(html.unescape(match.group(3))), quote=True)}{match.group(2)}',
        inner,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def wrap_plain_pre(match: re.Match[str]) -> str:
        attributes = match.group(1) or ""
        pre_body = match.group(2)
        if re.search(r"<code\b", pre_body, flags=re.IGNORECASE):
            return match.group(0)
        return f'<pre{attributes}><code class="language-text">{pre_body}</code></pre>'

    inner = re.sub(
        r"<pre(\s[^>]*)?>(.*?)</pre>",
        wrap_plain_pre,
        inner,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return inner.strip()


def render_code_source(content: str, source_path: str) -> str:
    """Render a source file as a syntax-highlightable code block."""

    language_by_suffix = {
        ".java": "java",
        ".js": "javascript",
        ".json": "json",
        ".py": "python",
        ".sql": "sql",
        ".ts": "typescript",
    }
    language = language_by_suffix.get(Path(source_path).suffix.lower(), "text")
    escaped = html.escape(content, quote=False)
    return f'<pre><code class="language-{language}">{escaped}</code></pre>'


def page_shell(title: str, body: str, catalog_entry: dict) -> str:
    tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in catalog_entry["tags"])
    mermaid_renderer = ""
    if 'class="mermaid"' in body:
        mermaid_renderer = '''
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.esm.min.mjs";
    mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
    mermaid.run({ query: ".mermaid" });
  </script>'''
    syntax_highlighter = ""
    if re.search(r"<pre\b[^>]*>\s*<code\b", body, flags=re.IGNORECASE):
        syntax_highlighter = '''
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.11.1/styles/github-dark.min.css">
  <script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.11.1/highlight.min.js" defer></script>
  <script>
    document.addEventListener("DOMContentLoaded", () => window.hljs?.highlightAll());
  </script>'''
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(catalog_entry["description"], quote=True)}">
  <title>{html.escape(title)} · Interview Prep Library</title>
  <link rel="stylesheet" href="assets/site.css">
  {syntax_highlighter}
</head>
<body>
  <header class="topbar">
    <a class="brand" href="index.html"><span class="brand-mark">IP</span><span>Interview Prep Library</span></a>
    <a class="back-link" href="index.html">← All materials</a>
  </header>
  <main class="article-wrap">
    <div class="article-meta"><span>{html.escape(catalog_entry["section"])}</span><span class="dot">•</span>{tags}</div>
    <h1 class="article-title">{html.escape(title)}</h1>
    <p class="article-dek">{html.escape(catalog_entry["description"])}</p>
    <article class="prose">{body}</article>
  </main>
  <footer class="footer"><span>Curated interview practice · no leaked or confidential material</span><a href="index.html">Back to library</a></footer>
  {mermaid_renderer}
</body>
</html>'''


def build() -> None:
    catalog = read_catalog()
    path_to_id = {entry["path"]: entry["id"] for entry in catalog}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / "assets").mkdir(parents=True)

    cards: list[str] = []
    for entry in catalog:
        source_path = entry["path"]
        source = PROJECT_ROOT / source_path
        raw = source.read_text(encoding="utf-8")
        if entry["kind"] == "html":
            body = render_html_source(raw)
        elif entry["kind"] == "code":
            body = render_code_source(raw, source_path)
        else:
            body = render_markdown(raw, source_path, path_to_id)
        (OUTPUT_ROOT / f'{entry["id"]}.html').write_text(
            page_shell(entry["title"], body, entry), encoding="utf-8"
        )
        searchable = " ".join([entry["title"], entry["section"], *entry["tags"], entry["description"]]).lower()
        tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in entry["tags"][:3])
        cards.append(
            f'''<a class="card" href="{entry["id"]}.html" data-section="{html.escape(entry["section"])}" data-search="{html.escape(searchable, quote=True)}">
  <div class="card-top"><span class="eyebrow">{html.escape(entry["section"])}</span><span class="arrow">↗</span></div>
  <h2>{html.escape(entry["title"])}</h2>
  <p>{html.escape(entry["description"])}</p>
  <div class="card-tags">{tags}</div>
</a>'''
        )

    sections = sorted({entry["section"] for entry in catalog}, key=lambda section: (section != "Start here", section))
    filter_buttons = '<button class="filter active" data-filter="all">All</button>' + "".join(
        f'<button class="filter" data-filter="{html.escape(section, quote=True)}">{html.escape(section)}</button>'
        for section in sections
    )
    catalog_json = json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/")
    index = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A searchable, curated library of system design, coding and Java interview preparation.">
  <title>Interview Prep Library</title>
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="topbar">
    <a class="brand" href="index.html"><span class="brand-mark">IP</span><span>Interview Prep Library</span></a>
    <a class="repository-pill" href="https://github.com/">Public repository</a>
  </header>
  <main class="home-wrap">
    <section class="hero">
      <div class="hero-copy">
        <p class="kicker">Curated practice library</p>
        <h1>Find the right rehearsal<br><em>before the clock starts.</em></h1>
        <p class="hero-sub">A single index for system design, coding patterns, company question signals, core Java concepts and verified solutions.</p>
      </div>
      <div class="hero-stats"><strong>{len(catalog)}</strong><span>curated materials</span><strong>{len(sections)}</strong><span>study lanes</span></div>
    </section>
    <section class="library" aria-labelledby="library-title">
      <div class="library-head"><div><p class="kicker">Library</p><h2 id="library-title">Choose a lane</h2></div><label class="search"><span aria-hidden="true">⌕</span><input id="search" type="search" placeholder="Search materials, topics or companies…" autocomplete="off"><kbd>/</kbd></label></div>
      <div class="filters" role="group" aria-label="Filter materials">{filter_buttons}</div>
      <div class="card-grid" id="cards">{''.join(cards)}</div>
      <p id="empty" class="empty" hidden>No matching material. Try a company, topic or pattern.</p>
    </section>
    <aside class="privacy-note"><span class="note-icon">✓</span><p><strong>Curated by design.</strong> This public hub contains reusable preparation material and code while excluding private correspondence, calendar details and meeting transcripts.</p></aside>
  </main>
  <footer class="footer"><span>Curated interview practice · no leaked or confidential material</span><a href="#library-title">Back to library</a></footer>
  <script>window.INTERVIEW_CATALOG = {catalog_json};</script>
  <script src="assets/app.js"></script>
</body>
</html>'''
    (OUTPUT_ROOT / "index.html").write_text(index, encoding="utf-8")
    shutil.copy2(SITE_ROOT / "site.css", OUTPUT_ROOT / "assets" / "site.css")
    shutil.copy2(SITE_ROOT / "app.js", OUTPUT_ROOT / "assets" / "app.js")
    (OUTPUT_ROOT / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    build()
