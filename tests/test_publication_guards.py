from __future__ import annotations

import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
