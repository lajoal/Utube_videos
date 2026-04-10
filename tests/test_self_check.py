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
        self.assertEqual(args.gpu_output, self_check.DEFAULT_GPU_JSON_OUTPUT)
        self.assertEqual(args.gpu_markdown_output, self_check.DEFAULT_GPU_MARKDOWN_OUTPUT)
        self.assertEqual(args.summary_output, self_check.DEFAULT_SELF_CHECK_SUMMARY_OUTPUT)
        self.assertEqual(
            args.summary_markdown_output,
            self_check.DEFAULT_SELF_CHECK_SUMMARY_MARKDOWN_OUTPUT,
        )
        self.assertFalse(args.skip_tests)
        self.assertFalse(args.skip_gpu)
        self.assertFalse(args.skip_report)
        self.assertFalse(args.keep_going)
        self.assertFalse(args.require_cuda)
        self.assertFalse(args.require_nvenc)

    def test_parse_args_supports_keep_going_and_gpu_requirements(self) -> None:
        args = self_check.parse_args(["--keep-going", "--require-cuda", "--require-nvenc"])

        self.assertTrue(args.keep_going)
        self.assertTrue(args.require_cuda)
        self.assertTrue(args.require_nvenc)

    def test_build_commands_includes_tests_gpu_and_reporting_by_default(self) -> None:
        commands = self_check.build_commands(
            "python",
            "artifacts/report.json",
            "artifacts/report.md",
            "artifacts/gpu.json",
            "artifacts/gpu.md",
        )

        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[0][0], "Unit tests")
        self.assertEqual(commands[1][0], "GPU diagnostics")
        self.assertEqual(commands[2][0], "Strict reporting")
        self.assertIn("unittest", commands[0][1])
        self.assertIn("gpu_report.py", commands[1][1])
        self.assertIn("reporting.py", commands[2][1])

    def test_build_commands_can_skip_individual_steps_and_forward_gpu_flags(self) -> None:
        self.assertEqual(
            self_check.build_commands(
                "python",
                "out.json",
                "out.md",
                "gpu.json",
                "gpu.md",
                skip_tests=True,
            )[0][0],
            "GPU diagnostics",
        )
        self.assertEqual(
            [label for label, _command in self_check.build_commands(
                "python",
                "out.json",
                "out.md",
                "gpu.json",
                "gpu.md",
                skip_gpu=True,
            )],
            ["Unit tests", "Strict reporting"],
        )
        self.assertEqual(
            [label for label, _command in self_check.build_commands(
                "python",
                "out.json",
                "out.md",
                "gpu.json",
                "gpu.md",
                skip_report=True,
            )],
            ["Unit tests", "GPU diagnostics"],
        )
        self.assertEqual(
            self_check.build_commands(
                "python",
                "out.json",
                "out.md",
                "gpu.json",
                "gpu.md",
                skip_tests=True,
                skip_gpu=True,
                skip_report=True,
            ),
            [],
        )
        gpu_command = self_check.build_commands(
            "python",
            "out.json",
            "out.md",
            "gpu.json",
            "gpu.md",
            require_cuda=True,
            require_nvenc=True,
            skip_tests=True,
            skip_report=True,
        )[0][1]
        self.assertIn("--require-cuda", gpu_command)
        self.assertIn("--require-nvenc", gpu_command)

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
                    ("GPU diagnostics", ["python", "gpu_report.py"]),
                    ("Strict reporting", ["python", "reporting.py"]),
                ],
                Path("/repo"),
            )
        finally:
            self_check.run_step = original_run_step

        self.assertEqual(exit_code, 3)
        self.assertEqual(calls, ["Unit tests"])
        self.assertEqual(
            [item["status"] for item in step_results],
            ["failed", "skipped", "skipped"],
        )
        self.assertIsNotNone(step_results[0]["started_at"])
        self.assertIsNone(step_results[1]["started_at"])
        self.assertIsNone(step_results[2]["duration_seconds"])

    def test_run_commands_continues_when_keep_going_enabled(self) -> None:
        calls: list[str] = []
        original_run_step = self_check.run_step

        def fake_run_step(label: str, command: list[str], repo_root: Path) -> int:
            calls.append(label)
            return 5 if label == "GPU diagnostics" else 0

        self_check.run_step = fake_run_step
        try:
            exit_code, step_results = self_check.run_commands(
                [
                    ("Unit tests", ["python", "-m", "unittest"]),
                    ("GPU diagnostics", ["python", "gpu_report.py"]),
                    ("Strict reporting", ["python", "reporting.py"]),
                ],
                Path("/repo"),
                keep_going=True,
            )
        finally:
            self_check.run_step = original_run_step

        self.assertEqual(exit_code, 5)
        self.assertEqual(calls, ["Unit tests", "GPU diagnostics", "Strict reporting"])
        self.assertEqual(
            [item["status"] for item in step_results],
            ["passed", "failed", "passed"],
        )
        self.assertTrue(all(item["started_at"] is not None for item in step_results))
        self.assertTrue(all(item["finished_at"] is not None for item in step_results))

    def test_build_summary_includes_gpu_artifacts_and_label_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            repo_root = Path(tempdir)
            report_json = repo_root / "custom" / "report.json"
            report_markdown = repo_root / "custom" / "report.md"
            gpu_json = repo_root / "custom" / "gpu.json"
            gpu_markdown = repo_root / "custom" / "gpu.md"
            report_json.parent.mkdir(parents=True, exist_ok=True)
            report_json.write_text("{}", encoding="utf-8")
            report_markdown.write_text("# report\n", encoding="utf-8")
            gpu_json.write_text("{}", encoding="utf-8")
            gpu_markdown.write_text("# gpu\n", encoding="utf-8")

            args = self_check.parse_args(
                [
                    "--keep-going",
                    "--output",
                    "custom/report.json",
                    "--markdown-output",
                    "custom/report.md",
                    "--gpu-output",
                    "custom/gpu.json",
                    "--gpu-markdown-output",
                    "custom/gpu.md",
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
                    status="passed",
                    exit_code=0,
                    started_at="2026-04-10T12:00:00+00:00",
                    finished_at="2026-04-10T12:00:02+00:00",
                    duration_seconds=2.0,
                ),
                self_check.build_step_result(
                    "GPU diagnostics",
                    ["python", "gpu_report.py"],
                    status="passed",
                    exit_code=0,
                    started_at="2026-04-10T12:00:02+00:00",
                    finished_at="2026-04-10T12:00:03+00:00",
                    duration_seconds=1.0,
                ),
                self_check.build_step_result(
                    "Strict reporting",
                    ["python", "reporting.py"],
                    status="passed",
                    exit_code=0,
                    started_at="2026-04-10T12:00:03+00:00",
                    finished_at="2026-04-10T12:00:04+00:00",
                    duration_seconds=1.0,
                ),
            ]

            summary = self_check.build_summary(
                repo_root,
                args,
                step_results,
                0,
                "2026-04-10T12:00:00+00:00",
                "2026-04-10T12:00:04+00:00",
                4.0,
            )

            self.assertEqual(summary["overall_status"], "pass")
            self.assertTrue(summary["overall_passed"])
            self.assertEqual(summary["selected_step_count"], 3)
            self.assertEqual(summary["completed_step_count"], 3)
            self.assertEqual(summary["failed_step_count"], 0)
            self.assertEqual(summary["skipped_step_count"], 0)
            self.assertEqual(summary["passed_steps"], ["Unit tests", "GPU diagnostics", "Strict reporting"])
            self.assertEqual(summary["failed_steps"], [])
            self.assertEqual(summary["skipped_steps"], [])
            self.assertEqual(summary["gpu_report_path"], str(gpu_json))
            self.assertEqual(summary["gpu_markdown_output_path"], str(gpu_markdown))
            self.assertTrue(summary["gpu_report_exists"])
            self.assertTrue(summary["gpu_markdown_output_exists"])
            self.assertTrue(summary["reporting_output_exists"])
            self.assertTrue(summary["reporting_markdown_output_exists"])
            self.assertEqual(
                summary["present_artifacts"],
                ["reporting_json", "reporting_markdown", "gpu_json", "gpu_markdown"],
            )
            self.assertEqual(
                summary["missing_artifacts"],
                ["self_check_json", "self_check_markdown"],
            )
            self.assertEqual(summary["present_artifact_count"], 4)
            self.assertEqual(summary["missing_artifact_count"], 2)
            self.assertGreater(summary["artifact_size_bytes_total"], 0)

    def test_build_summary_marks_outputs_absent_when_skip_gpu_and_skip_report_are_enabled(self) -> None:
        args = self_check.parse_args(["--skip-report", "--skip-gpu"])

        summary = self_check.build_summary(
            Path("/repo"),
            args,
            [],
            0,
            "2026-04-10T12:00:00+00:00",
            "2026-04-10T12:00:00+00:00",
            0.0,
        )

        self.assertIsNone(summary["reporting_output_path"])
        self.assertIsNone(summary["reporting_markdown_output_path"])
        self.assertIsNone(summary["reporting_output_exists"])
        self.assertIsNone(summary["reporting_markdown_output_exists"])
        self.assertIsNone(summary["gpu_report_path"])
        self.assertIsNone(summary["gpu_markdown_output_path"])
        self.assertIsNone(summary["gpu_report_exists"])
        self.assertIsNone(summary["gpu_markdown_output_exists"])

    def test_build_summary_markdown_includes_gpu_lines_and_artifact_section(self) -> None:
        summary = {
            "generated_at": "2026-04-10T12:00:00+00:00",
            "started_at": "2026-04-10T12:00:00+00:00",
            "finished_at": "2026-04-10T12:00:04+00:00",
            "duration_seconds": 4.0,
            "repo_root": "/repo",
            "python_executable": "python",
            "keep_going": True,
            "skip_tests": False,
            "skip_gpu": False,
            "skip_report": False,
            "require_cuda": False,
            "require_nvenc": False,
            "reporting_output_path": "/repo/artifacts/reporting_output.json",
            "reporting_markdown_output_path": "/repo/artifacts/reporting_summary.md",
            "reporting_output_exists": True,
            "reporting_markdown_output_exists": True,
            "gpu_report_path": "/repo/artifacts/gpu_report.json",
            "gpu_markdown_output_path": "/repo/artifacts/gpu_report.md",
            "gpu_report_exists": True,
            "gpu_markdown_output_exists": True,
            "self_check_summary_path": "/repo/artifacts/self_check_summary.json",
            "self_check_summary_markdown_path": "/repo/artifacts/self_check_summary.md",
            "selected_step_count": 3,
            "completed_step_count": 3,
            "failed_step_count": 0,
            "skipped_step_count": 0,
            "passed_steps": ["Unit tests", "GPU diagnostics", "Strict reporting"],
            "failed_steps": [],
            "skipped_steps": [],
            "present_artifacts": [
                "reporting_json",
                "reporting_markdown",
                "gpu_json",
                "gpu_markdown",
                "self_check_json",
                "self_check_markdown",
            ],
            "missing_artifacts": [],
            "present_artifact_count": 6,
            "missing_artifact_count": 0,
            "artifact_size_bytes_total": 16660,
            "artifacts": {
                "reporting_json": {
                    "path": "/repo/artifacts/reporting_output.json",
                    "exists": True,
                    "size_bytes": 3180,
                },
                "reporting_markdown": {
                    "path": "/repo/artifacts/reporting_summary.md",
                    "exists": True,
                    "size_bytes": 1540,
                },
                "gpu_json": {
                    "path": "/repo/artifacts/gpu_report.json",
                    "exists": True,
                    "size_bytes": 2190,
                },
                "gpu_markdown": {
                    "path": "/repo/artifacts/gpu_report.md",
                    "exists": True,
                    "size_bytes": 980,
                },
                "self_check_json": {
                    "path": "/repo/artifacts/self_check_summary.json",
                    "exists": True,
                    "size_bytes": 6120,
                },
                "self_check_markdown": {
                    "path": "/repo/artifacts/self_check_summary.md",
                    "exists": True,
                    "size_bytes": 2650,
                },
            },
            "overall_passed": True,
            "overall_status": "pass",
            "exit_code": 0,
            "steps": [
                {
                    "label": "GPU diagnostics",
                    "command": ["python", "gpu_report.py"],
                    "command_display": "python gpu_report.py",
                    "status": "passed",
                    "exit_code": 0,
                    "started_at": "2026-04-10T12:00:02+00:00",
                    "finished_at": "2026-04-10T12:00:03+00:00",
                    "duration_seconds": 1.0,
                }
            ],
        }

        markdown = self_check.build_summary_markdown(summary)

        self.assertIn("# Self-Check Summary", markdown)
        self.assertIn("- Overall status: `PASS`", markdown)
        self.assertIn("- GPU JSON exists: `True`", markdown)
        self.assertIn("- GPU Markdown exists: `True`", markdown)
        self.assertIn("- Passed step labels: `Unit tests, GPU diagnostics, Strict reporting`", markdown)
        self.assertIn("## Artifacts", markdown)
        self.assertIn("`gpu_json`: exists=`True`, size_bytes=`2190`", markdown)
        self.assertIn("### `GPU diagnostics`", markdown)
        self.assertIn("- Command: `python gpu_report.py`", markdown)

    def test_persist_summary_outputs_refreshes_self_artifact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            repo_root = Path(tempdir)
            report_json = repo_root / "artifacts" / "report.json"
            report_markdown = repo_root / "artifacts" / "report.md"
            gpu_json = repo_root / "artifacts" / "gpu.json"
            gpu_markdown = repo_root / "artifacts" / "gpu.md"
            report_json.parent.mkdir(parents=True, exist_ok=True)
            report_json.write_text("{}", encoding="utf-8")
            report_markdown.write_text("# report\n", encoding="utf-8")
            gpu_json.write_text("{}", encoding="utf-8")
            gpu_markdown.write_text("# gpu\n", encoding="utf-8")

            args = self_check.parse_args(
                [
                    "--output",
                    str(report_json),
                    "--markdown-output",
                    str(report_markdown),
                    "--gpu-output",
                    str(gpu_json),
                    "--gpu-markdown-output",
                    str(gpu_markdown),
                    "--summary-output",
                    str(repo_root / "artifacts" / "self_check_summary.json"),
                    "--summary-markdown-output",
                    str(repo_root / "artifacts" / "self_check_summary.md"),
                ]
            )
            summary = self_check.build_summary(
                repo_root,
                args,
                [],
                0,
                "2026-04-10T12:00:00+00:00",
                "2026-04-10T12:00:01+00:00",
                1.0,
            )
            summary_path = Path(summary["self_check_summary_path"])
            summary_markdown_path = Path(summary["self_check_summary_markdown_path"])

            self_check.persist_summary_outputs(summary_path, summary_markdown_path, summary)

            self.assertTrue(summary_path.is_file())
            self.assertTrue(summary_markdown_path.is_file())
            self.assertTrue(summary["artifacts"]["self_check_json"]["exists"])
            self.assertTrue(summary["artifacts"]["self_check_markdown"]["exists"])
            self.assertIsInstance(summary["artifacts"]["self_check_json"]["size_bytes"], int)
            self.assertIsInstance(summary["artifacts"]["self_check_markdown"]["size_bytes"], int)
            self.assertIn("self_check_json", summary["present_artifacts"])
            self.assertIn("self_check_markdown", summary["present_artifacts"])

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
                "started_at": "2026-04-10T12:00:00+00:00",
                "finished_at": "2026-04-10T12:00:00+00:00",
                "duration_seconds": 0.0,
                "repo_root": "/repo",
                "python_executable": "python",
                "keep_going": False,
                "skip_tests": False,
                "skip_gpu": True,
                "skip_report": True,
                "require_cuda": False,
                "require_nvenc": False,
                "reporting_output_path": None,
                "reporting_markdown_output_path": None,
                "reporting_output_exists": None,
                "reporting_markdown_output_exists": None,
                "gpu_report_path": None,
                "gpu_markdown_output_path": None,
                "gpu_report_exists": None,
                "gpu_markdown_output_exists": None,
                "self_check_summary_path": "/repo/artifacts/self_check_summary.json",
                "self_check_summary_markdown_path": str(markdown_path),
                "selected_step_count": 0,
                "completed_step_count": 0,
                "failed_step_count": 0,
                "skipped_step_count": 0,
                "passed_steps": [],
                "failed_steps": [],
                "skipped_steps": [],
                "present_artifacts": [],
                "missing_artifacts": [
                    "reporting_json",
                    "reporting_markdown",
                    "gpu_json",
                    "gpu_markdown",
                    "self_check_json",
                    "self_check_markdown",
                ],
                "present_artifact_count": 0,
                "missing_artifact_count": 6,
                "artifact_size_bytes_total": 0,
                "artifacts": {
                    "reporting_json": None,
                    "reporting_markdown": None,
                    "gpu_json": None,
                    "gpu_markdown": None,
                    "self_check_json": {
                        "path": "/repo/artifacts/self_check_summary.json",
                        "exists": False,
                        "size_bytes": None,
                    },
                    "self_check_markdown": {
                        "path": str(markdown_path),
                        "exists": False,
                        "size_bytes": None,
                    },
                },
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
            self.assertIn("## Artifacts", markdown)


if __name__ == "__main__":
    unittest.main()
