import json
import os
import tempfile
import unittest
from pathlib import Path

import github_issue_digest


class GitHubIssueDigestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_resolve_repo_full_name_uses_explicit_value(self) -> None:
        self.assertEqual(
            github_issue_digest.resolve_repo_full_name("openai/openai"),
            "openai/openai",
        )

    def test_resolve_repo_full_name_uses_environment_value(self) -> None:
        original_value = os.environ.get("UTUBE_GITHUB_REPO")
        try:
            os.environ["UTUBE_GITHUB_REPO"] = "lajoal/Utube_videos"
            self.assertEqual(
                github_issue_digest.resolve_repo_full_name(None),
                "lajoal/Utube_videos",
            )
        finally:
            if original_value is None:
                os.environ.pop("UTUBE_GITHUB_REPO", None)
            else:
                os.environ["UTUBE_GITHUB_REPO"] = original_value

    def test_normalize_issue_record_keeps_expected_fields(self) -> None:
        record = github_issue_digest.normalize_issue_record(
            {
                "number": 12,
                "title": "Recent issue summary",
                "state": "open",
                "created_at": "2026-04-10T00:00:00Z",
                "updated_at": "2026-04-11T00:00:00Z",
                "html_url": "https://github.com/example/repo/issues/12",
                "user": {"login": "lajoal"},
                "labels": [{"name": "ops"}, {"name": "dashboard"}],
                "assignees": [{"login": "owner"}],
                "comments": 3,
                "body": "This issue tracks the latest internal platform improvements.",
            }
        )

        self.assertEqual(record["number"], 12)
        self.assertEqual(record["author"], "lajoal")
        self.assertEqual(record["labels"], ["ops", "dashboard"])
        self.assertEqual(record["assignees"], ["owner"])
        self.assertIn("latest internal platform", record["body_preview"])

    def test_build_issue_digest_report_counts_top_labels(self) -> None:
        report = github_issue_digest.build_issue_digest_report(
            "lajoal/Utube_videos",
            state="open",
            limit=10,
            issues=[
                {"labels": ["ops", "dashboard"]},
                {"labels": ["ops"]},
            ],
        )

        self.assertEqual(report["repo_full_name"], "lajoal/Utube_videos")
        self.assertEqual(report["issue_count"], 2)
        self.assertEqual(report["top_labels"][0], {"name": "ops", "count": 2})

    def test_run_issue_digest_job_filters_pull_requests_and_writes_outputs(self) -> None:
        original_api_get_json = github_issue_digest.github_api_get_json
        try:
            def fake_api_get_json(*_args, **_kwargs):
                return [
                    {
                        "number": 10,
                        "title": "Issue digest feature",
                        "state": "open",
                        "created_at": "2026-04-10T00:00:00Z",
                        "updated_at": "2026-04-11T01:00:00Z",
                        "html_url": "https://github.com/example/repo/issues/10",
                        "user": {"login": "owner"},
                        "labels": [{"name": "ops"}],
                        "assignees": [],
                        "comments": 1,
                        "body": "Need latest issue summaries in the internal app.",
                    },
                    {
                        "number": 11,
                        "title": "Pull request entry",
                        "state": "open",
                        "pull_request": {"url": "https://api.github.com/..."},
                    },
                ]

            github_issue_digest.github_api_get_json = fake_api_get_json
            result = github_issue_digest.run_issue_digest_job(
                self.repo_root,
                repo_full_name="lajoal/Utube_videos",
                limit=10,
                state="open",
            )
        finally:
            github_issue_digest.github_api_get_json = original_api_get_json

        self.assertEqual(result["operation"], "issue_digest")
        self.assertEqual(result["overall_status"], "ok")
        self.assertEqual(result["report"]["issue_count"], 1)
        self.assertEqual(result["report"]["issues"][0]["number"], 10)
        self.assertTrue((self.repo_root / "artifacts" / "latest_issues.json").is_file())
        self.assertTrue((self.repo_root / "artifacts" / "latest_issues.md").is_file())

        written = json.loads(
            (self.repo_root / "artifacts" / "latest_issues.json").read_text(encoding="utf-8")
        )
        self.assertEqual(written["issue_count"], 1)


if __name__ == "__main__":
    unittest.main()
