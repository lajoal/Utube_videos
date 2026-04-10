import sys
import unittest
from pathlib import Path

import self_check


class SelfCheckScriptTests(unittest.TestCase):
    def test_parse_args_defaults(self) -> None:
        args = self_check.parse_args([])

        self.assertEqual(args.python, sys.executable)
        self.assertEqual(args.output, self_check.DEFAULT_JSON_OUTPUT)
        self.assertEqual(args.markdown_output, self_check.DEFAULT_MARKDOWN_OUTPUT)
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
            exit_code = self_check.run_commands(
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

    def test_run_commands_continues_when_keep_going_enabled(self) -> None:
        calls: list[str] = []
        original_run_step = self_check.run_step

        def fake_run_step(label: str, command: list[str], repo_root: Path) -> int:
            calls.append(label)
            return 5 if label == "Unit tests" else 0

        self_check.run_step = fake_run_step
        try:
            exit_code = self_check.run_commands(
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


if __name__ == "__main__":
    unittest.main()
