import json
import tempfile
import unittest
from pathlib import Path

import github_template_analysis


class GitHubTemplateAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_parse_github_template_url_supports_blob_urls(self) -> None:
        parsed = github_template_analysis.parse_github_template_url(
            "https://github.com/lajoal/Utube_videos/blob/main/templates/issue_digest_template.md"
        )

        self.assertEqual(parsed["repo_full_name"], "lajoal/Utube_videos")
        self.assertEqual(parsed["ref"], "main")
        self.assertEqual(parsed["path"], "templates/issue_digest_template.md")

    def test_parse_github_template_url_supports_raw_urls(self) -> None:
        parsed = github_template_analysis.parse_github_template_url(
            "https://raw.githubusercontent.com/lajoal/Utube_videos/main/templates/issue_digest_template.md"
        )

        self.assertEqual(parsed["repo_full_name"], "lajoal/Utube_videos")
        self.assertEqual(parsed["ref"], "main")
        self.assertEqual(parsed["path"], "templates/issue_digest_template.md")

    def test_render_template_replaces_placeholders(self) -> None:
        rendered = github_template_analysis.render_template(
            "Repo: {{repo_full_name}}\nCount: {{issue_count}}",
            {"repo_full_name": "lajoal/Utube_videos", "issue_count": "3"},
        )

        self.assertIn("Repo: lajoal/Utube_videos", rendered)
        self.assertIn("Count: 3", rendered)

    def test_run_template_issue_analysis_job_uses_github_template_and_writes_outputs(self) -> None:
        original_fetch_recent_issues = github_template_analysis.github_issue_digest.fetch_recent_issues
        original_fetch_template = github_template_analysis.fetch_github_file_text
        try:
            def fake_fetch_recent_issues(*_args, **_kwargs):
                return [
                    {
                        "number": 21,
                        "title": "Need internal issue formatting",
                        "state": "open",
                        "created_at": "2026-04-10T00:00:00Z",
                        "updated_at": "2026-04-11T02:00:00Z",
                        "html_url": "https://github.com/lajoal/Utube_videos/issues/21",
                        "author": "lajoal",
                        "labels": ["ops", "format"],
                        "assignees": ["lajoal"],
                        "comments": 2,
                        "body_preview": "Use the uploaded GitHub template for issue analysis.",
                    }
                ]

            def fake_fetch_template(*_args, **_kwargs):
                return "# Custom Digest\nRepo: {{repo_full_name}}\n\n{{issue_bullets}}\n"

            github_template_analysis.github_issue_digest.fetch_recent_issues = fake_fetch_recent_issues
            github_template_analysis.fetch_github_file_text = fake_fetch_template

            result = github_template_analysis.run_template_issue_analysis_job(
                self.repo_root,
                repo_full_name="lajoal/Utube_videos",
                template_repo_full_name="lajoal/Utube_videos",
                template_path="templates/issue_digest_template.md",
                template_ref="main",
            )
        finally:
            github_template_analysis.github_issue_digest.fetch_recent_issues = original_fetch_recent_issues
            github_template_analysis.fetch_github_file_text = original_fetch_template

        self.assertEqual(result["operation"], "template_issue_analysis")
        self.assertEqual(result["overall_status"], "ok")
        self.assertTrue(result["report"]["template_used"])
        self.assertTrue(
            (self.repo_root / "artifacts" / "template_issue_digest.json").is_file()
        )
        self.assertTrue(
            (self.repo_root / "artifacts" / "template_issue_digest.md").is_file()
        )

        markdown = (
            self.repo_root / "artifacts" / "template_issue_digest.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# Custom Digest", markdown)
        self.assertIn("Repo: lajoal/Utube_videos", markdown)
        self.assertIn("#21 Need internal issue formatting", markdown)

        written = json.loads(
            (self.repo_root / "artifacts" / "template_issue_digest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(written["issue_count"], 1)
        self.assertTrue(written["template_used"])


if __name__ == "__main__":
    unittest.main()
