from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def load_build_module():
    module_path = REPOSITORY_ROOT / "interview-prep" / "site" / "build.py"
    spec = importlib.util.spec_from_file_location("interview_pro_build", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CatalogPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.build = load_build_module()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temporary_root = Path(self.temporary_directory.name)
        self.project_root = self.temporary_root / "project"
        self.site_root = self.project_root / "interview-prep" / "site"
        self.site_root.mkdir(parents=True)
        (self.project_root / "content").mkdir()
        (self.project_root / "code").mkdir()
        self.build.PROJECT_ROOT = self.project_root
        self.build.SITE_ROOT = self.site_root

    def write_catalog(self, paths: list[str]) -> None:
        catalog = [{"id": f"entry-{index}", "path": path} for index, path in enumerate(paths)]
        (self.site_root / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")

    def test_rejects_invalid_paths_before_checking_source_files(self) -> None:
        invalid_paths = [
            "/tmp/source.md",
            "C:\\source.md",
            "../source.md",
            "content\\..\\source.md",
            "content/%2e%2e/source.md",
            "content/%252e%252e/source.md",
            "README.md",
        ]

        for invalid_path in invalid_paths:
            with self.subTest(path=invalid_path):
                self.write_catalog(["content/missing.md", invalid_path])
                with self.assertRaisesRegex(ValueError, "invalid catalog path"):
                    self.build.read_catalog()

    def test_rejects_source_symlink_that_resolves_outside_allowed_roots(self) -> None:
        outside_source = self.temporary_root / "outside.md"
        outside_source.write_text("outside", encoding="utf-8")
        (self.project_root / "content" / "linked.md").symlink_to(outside_source)
        self.write_catalog(["content/linked.md"])

        with self.assertRaisesRegex(ValueError, "invalid catalog path"):
            self.build.read_catalog()

    def test_rejects_allowed_root_symlink_that_resolves_outside_project(self) -> None:
        outside_content = self.temporary_root / "outside-content"
        outside_content.mkdir()
        (outside_content / "source.md").write_text("outside", encoding="utf-8")
        (self.project_root / "content").rmdir()
        (self.project_root / "content").symlink_to(outside_content, target_is_directory=True)
        self.write_catalog(["content/source.md"])

        with self.assertRaisesRegex(ValueError, "invalid catalog path"):
            self.build.read_catalog()


class PublicSafetyScopeTests(unittest.TestCase):
    def test_scans_tracked_review_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            review_directory = project_root / ".review"
            review_directory.mkdir()
            marker = "/" + "Users" + "/example/private.txt"
            (review_directory / "tracked.txt").write_text(marker, encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(project_root)], check=True)
            subprocess.run(
                ["git", "-C", str(project_root), "add", ".review/tracked.txt"],
                check=True,
            )

            result = subprocess.run(
                [sys.executable, str(REPOSITORY_ROOT / "scripts" / "check-public-safe.py"), str(project_root)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(".review/tracked.txt", result.stdout)
        self.assertIn("PUBLIC_UNSAFE", result.stdout)


class MermaidRenderingTests(unittest.TestCase):
    def test_mermaid_fence_becomes_renderable_diagram_container(self) -> None:
        build = load_build_module()

        rendered = build.render_markdown(
            "```mermaid\nflowchart LR\n    A --> B\n```",
            "content/diagram.md",
            {},
        )

        self.assertIn('<pre class="mermaid">', rendered)
        self.assertIn("flowchart LR", rendered)
        self.assertNotIn("language-mermaid", rendered)

    def test_pages_with_diagrams_load_mermaid_renderer(self) -> None:
        build = load_build_module()
        entry = {
            "title": "Diagram",
            "description": "A diagram",
            "section": "System design",
            "tags": ["diagram"],
        }

        rendered = build.page_shell("Diagram", '<pre class="mermaid">flowchart LR</pre>', entry)

        self.assertIn("mermaid.esm.min.mjs", rendered)
        self.assertIn("for (const diagram of diagrams)", rendered)
        self.assertIn("await mermaid.run({ nodes: [diagram] })", rendered)

    def test_mermaid_renderer_detects_single_quoted_class_attributes(self) -> None:
        build = load_build_module()
        entry = {
            "title": "Diagram",
            "description": "A diagram",
            "section": "System design",
            "tags": ["diagram"],
        }

        rendered = build.page_shell("Diagram", "<pre class='mermaid'>flowchart LR</pre>", entry)

        self.assertIn("mermaid.esm.min.mjs", rendered)


class HeadingAnchorTests(unittest.TestCase):
    def test_markdown_headings_have_stable_fragment_links(self) -> None:
        build = load_build_module()

        rendered = build.render_markdown(
            "# System context\n\n## 5. System context\n\n### System context",
            "content/diagram.md",
            {},
        )

        self.assertIn('id="system-context"', rendered)
        self.assertIn('href="#system-context"', rendered)
        self.assertIn('id="5-system-context"', rendered)
        self.assertIn('href="#5-system-context"', rendered)
        self.assertIn('id="system-context-2"', rendered)

    def test_raw_html_headings_get_ids_without_losing_existing_ids(self) -> None:
        build = load_build_module()

        rendered = build.render_html_source(
            '<html><body><h2>5. System context</h2><h3 id="already-there">Existing</h3></body></html>'
        )

        self.assertIn('<h2 id="5-system-context">', rendered)
        self.assertIn('href="#5-system-context"', rendered)
        self.assertIn('<h3 id="already-there">', rendered)
        self.assertIn('href="#already-there"', rendered)


class JpmorganAnswerDeckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (
            REPOSITORY_ROOT / "content" / "company" / "jpmorgan-backend-question-bank.md"
        ).read_text(encoding="utf-8")

    def section(self, number: int) -> str:
        start = self.source.index(f"## {number}.")
        next_heading = f"## {number + 1}."
        end = self.source.find(next_heading, start)
        return self.source[start:] if end == -1 else self.source[start:end]

    def test_first_five_sections_answer_every_numbered_question(self) -> None:
        expected_counts = {1: 14, 2: 10, 3: 7, 4: 11, 5: 7}

        for section_number, expected_count in expected_counts.items():
            with self.subTest(section=section_number):
                section = self.section(section_number)
                answers = re.findall(r"^### " + str(section_number) + r"\.\d+ .+$", section, re.MULTILINE)
                self.assertEqual(expected_count, len(answers))
                self.assertEqual(expected_count, section.count("**Answer.**"))

    def test_every_coding_question_has_java_complexity_and_tests(self) -> None:
        coding = self.section(1)

        self.assertEqual(14, coding.count("```java"))
        self.assertEqual(14, coding.count("**Complexity.**"))
        self.assertEqual(14, coding.count("**Tests.**"))

    def test_system_design_questions_remain_questions_only(self) -> None:
        system_design = self.section(6)

        self.assertNotIn("**Answer.**", system_design)


class SiteInteractionTests(unittest.TestCase):
    def test_filter_click_hides_cards_outside_selected_lane(self) -> None:
        script = (REPOSITORY_ROOT / "interview-prep" / "site" / "app.js").read_text(encoding="utf-8")
        harness = f"""
const assert = require('node:assert/strict');
const vm = require('node:vm');

class ClassList {{
  constructor() {{ this.values = new Set(); }}
  toggle(value, enabled) {{
    if (enabled) this.values.add(value); else this.values.delete(value);
  }}
}}

class Element {{
  constructor(section, filter) {{
    this.dataset = {{ section, filter, search: section.toLowerCase() }};
    this.hidden = false;
    this.classList = new ClassList();
    this.listeners = {{}};
    this.value = '';
  }}
  addEventListener(name, callback) {{ this.listeners[name] = callback; }}
  setAttribute() {{}}
}}

const search = new Element('', '');
const cards = [new Element('System design', ''), new Element('Core concepts', '')];
const filters = [new Element('', 'all'), new Element('', 'System design')];
const document = {{
  activeElement: null,
  querySelector(selector) {{ return selector === '#search' ? search : null; }},
  querySelectorAll(selector) {{
    if (selector === '.card') return cards;
    if (selector === '.filter') return filters;
    return [];
  }},
  addEventListener() {{}}
}};

vm.runInNewContext({json.dumps(script)}, {{ document }});
filters[1].listeners.click();
assert.equal(cards[0].hidden, false);
assert.equal(cards[1].hidden, true);
assert.equal(cards[1].classList.values.has('is-filtered-out'), true);
"""
        result = subprocess.run(["node", "-e", harness], check=False, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_article_shell_loads_syntax_highlighter_for_code_blocks(self) -> None:
        build = load_build_module()
        entry = {
            "title": "Code",
            "description": "A code sample",
            "section": "Code solutions",
            "tags": ["java"],
        }

        rendered = build.page_shell("Code", '<pre><code class="language-java">class Demo {}</code></pre>', entry)

        self.assertIn("highlight.min.js", rendered)
        self.assertIn("github-dark.min.css", rendered)
        self.assertIn("highlightAll", rendered)

    def test_article_shell_cache_busts_local_assets(self) -> None:
        build = load_build_module()
        build.build()
        rendered = (REPOSITORY_ROOT / "_site" / "index.html").read_text(encoding="utf-8")

        self.assertRegex(rendered, r'href="assets/site\.css\?v=[0-9a-f]{12}"')
        self.assertRegex(rendered, r'src="assets/app\.js\?v=[0-9a-f]{12}"')

    def test_raw_html_pre_is_wrapped_as_a_code_block(self) -> None:
        build = load_build_module()

        rendered = build.render_html_source("<html><body><main><pre>queue -&gt; worker</pre></main></body></html>")

        self.assertIn('<pre><code class="language-text">queue -&gt; worker</code></pre>', rendered)


if __name__ == "__main__":
    unittest.main()
