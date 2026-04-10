import json
import sys
import tempfile
import unittest
from pathlib import Path

import self_check


class SelfCheckScriptTests(unittest.TestCase):
    def test_parse_args_defaults(self) -> None:
        args = self_check.parse_args([])

        self.assertEqual(args.python, sys.executable)
        self.assertEqual(args.output, self_check.DEFAULT_JSON_OUTPUT)
        self.assertEqual(args.markdown_output, self_check.DEFAULT_MARKDOWN_OUTPUT)
        self.assertEqual(args.summary_output, self_check.DEFAULT_SELF_CHECK_SUMMARY_OUTPUT)
        self.assertEqual(
            args.summary_markdown_output,
            self_check.DEFAULT_SELF_CHECK_SUMMARY_MARKDOWN_OUTPUT,
        )
        self.assertFalse(args.skip_tests)
        self.assertFalse(args.skip_report)
        self.assertFalse(args.keep_going)

    def test_parse_args_supports_keep_going(self) -> None:
        args = self_check.parse_args(["--keep-going"])

        self.assertTrue(args.keep_going)

    def test_build_commands_includes_tests_and_reporting_by_default(self) -> None:
        commands = self_check.build_commands(
            "python",
            "artifacts/report.json",
            "artifacts/report.md",
        )

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][0], "Unit tests")
        self.assertIn("unittest", commands[0][1])
        self.assertEqual(commands[1][0], "Strict reporting")
        self.assertIn("reporting.py", commands[1][1])
        self.assertIn("--fail-on-missing", commands[1][1])
        self.assertIn("artifacts/report.md", commands[1][1])

    def test_build_commands_can_skip_individual_steps(self) -> None:
        self.assertEqual(
            self_check.build_commands(
                "python",
                "out.json",
                "out.md",
                skip_tests=True,
            )[0][0],
            "Strict reporting",
        )
        self.assertEqual(
            self_check.build_commands(
                "python",
                "out.json",
                "out.md",
                skip_report=True,
            )[0][0],
            "Unit tests",
        )
        self.assertEqual(
            self_check.build_commands(
                "python",
                "out.json",
                "out.md",
                skip_tests=True,
                skip_report=True,
            ),
            [],
        )

    def test_run_commands_stops_on_first_failure_without_keep_going(self) -> None:
        calls: list[str] = []
        original_run_step = self_check.run_step

        def fake_run_step(label: str, command: list[str], repo_root: Path) -> int:
            calls.append(label)
            return 3 if label == "Unit tests" else 0

        self_check.run_step = fake_run_step
        try:
            exit_code, step_results = self_check.run_commands(
                [
                    ("Unit tests", ["python", "-m", "unittest"]),
                    ("Strict reporting", ["python", "reporting.py"]),
                ],
                Path("/repo"),
            )
        finally:
            self_check.run_step = original_run_step

        self.assertEqual(exit_code, 3)
        self.assertEqual(calls, ["Unit tests"])
        self.assertEqual([item["status"] for item in step_results], ["failed", "skipped"])

    def test_run_commands_continues_when_keep_going_enabled(self) -> None:
        calls: list[str] = []
        original_run_step = self_check.run_step

        def fake_run_step(label: str, command: list[str], repo_root: Path) -> int:
            calls.append(label)
            return 5 if label == "Unit tests" else 0

        self_check.run_step = fake_run_step
        try:
            exit_code, step_results = self_check.run_commands(
                [
                    ("Unit tests", ["python", "-m", "unittest"]),
                    ("Strict reporting", ["python", "reporting.py"]),
                ],
                Path("/repo"),
                keep_going=True,
            )
        finally:
            self_check.run_step = original_run_step

        self.assertEqual(exit_code, 5)
        self.assertEqual(calls, ["Unit tests", "Strict reporting"])
        self.assertEqual([item["status"] for item in step_results], ["failed", "passed"])

    def test_build_summary_includes_step_counts_and_paths(self) -> None:
        args = self_check.parse_args(
            [
                "--keep-going",
                "--output",
                "custom/report.json",
                "--markdown-output",
                "custom/report.md",
                "--summary-output",
                "custom/self_check.json",
                "--summary-markdown-output",
                "custom/self_check.md",
            ]
        )
        step_results = [
            self_check.build_step_result(
                "Unit tests",
                ["python", "-m", "unittest"],
                status="failed",
                exit_code=1,
            ),
            self_check.build_step_result(
                "Strict reporting",
                ["python", "reporting.py"],
                status="passed",
                exit_code=0,
            ),
        ]

        summary = self_check.build_summary(Path("/repo"), args, step_results, 1)

        self.assertEqual(summary["overall_status"], "fail")
        self.assertFalse(summary["overall_passed"])
        self.assertEqual(summary["failed_step_count"], 1)
        self.assertEqual(summary["skipped_step_count"], 0)
        self.assertEqual(summary["completed_step_count"], 2)
        self.assertEqual(summary["selected_step_count"], 2)
        self.assertEqual(summary["reporting_output_path"], "/repo/custom/report.json")
        self.assertEqual(summary["reporting_markdown_output_path"], "/repo/custom/report.md")
        self.assertEqual(summary["self_check_summary_path"], "/repo/custom/self_check.json")
        self.assertEqual(summary["self_check_summary_markdown_path"], "/repo/custom/self_check.md")

    def test_build_summary_markdown_includes_step_details(self) -> None:
        summary = {
            "generated_at": "2026-04-10T12:00:00+00:00",
            "repo_root": "/repo",
            "python_executable": "python",
            "keep_going": True,
            "skip_tests": False,
            "skip_report": False,
            "reporting_output_path": "/repo/artifacts/reporting_output.json",
            "reporting_markdown_output_path": "/repo/artifacts/reporting_summary.md",
            "self_check_summary_path": "/repo/artifacts/self_check_summary.json",
            "self_check_summary_markdown_path": "/repo/artifacts/self_check_summary.md",
            "selected_step_count": 2,
            "completed_step_count": 2,
            "failed_step_count": 1,
            "skipped_step_count": 0,
            "overall_passed": False,
            "overall_status": "fail",
            "exit_code": 1,
            "steps": [
                {
                    "label": "Unit tests",
                    "command": ["python", "-m", "unittest"],
                    "command_display": "python -m unittest",
                    "status": "failed",
                    "exit_code": 1,
                },
                {
                    "label": "Strict reporting",
                    "command": ["python", "reporting.py"],
                    "command_display": "python reporting.py",
                    "status": "passed",
                    "exit_code": 0,
                },
            ],
        }

        markdown = self_check.build_summary_markdown(summary)

        self.assertIn("# Self-Check Summary", markdown)
        self.assertIn("- Overall status: `FAIL`", markdown)
        self.assertIn("### `Unit tests`", markdown)
        self.assertIn("- Status: `FAILED`", markdown)
        self.assertIn("- Command: `python -m unittest`", markdown)

    def test_write_summary_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            summary_path = Path(tempdir) / "artifacts" / "self_check_summary.json"
            summary = {
                "overall_status": "pass",
                "steps": [],
            }

            self_check.write_summary(summary_path, summary)

            self.assertTrue(summary_path.is_file())
            written = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(written["overall_status"], "pass")

    def test_write_summary_markdown_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            markdown_path = Path(tempdir) / "artifacts" / "self_check_summary.md"
            summary = {
                "generated_at": "2026-04-10T12:00:00+00:00",
                "repo_root": "/repo",
                "python_executable": "python",
                "keep_going": False,
                "skip_tests": False,
                "skip_report": False,
                "reporting_output_path": None,
                "reporting_markdown_output_path": None,
                "self_check_summary_path": "/repo/artifacts/self_check_summary.json",
                "self_check_summary_markdown_path": str(markdown_path),
                "selected_step_count": 0,
                "completed_step_count": 0,
                "failed_step_count": 0,
                "skipped_step_count": 0,
                "overall_passed": True,
                "overall_status": "pass",
                "exit_code": 0,
                "steps": [],
            }

            self_check.write_summary_markdown(markdown_path, summary)

            self.assertTrue(markdown_path.is_file())
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("# Self-Check Summary", markdown)
            self.assertIn("- Overall status: `PASS`", markdown)


if __name__ == "__main__":
    unittest.main()
