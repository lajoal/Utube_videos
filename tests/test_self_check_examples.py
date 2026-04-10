import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
SCHEMA_PATH = REPO_ROOT / "schemas" / "self_check_summary.schema.json"

REQUIRED_SUMMARY_KEYS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "repo_root",
    "python_executable",
    "keep_going",
    "skip_tests",
    "skip_report",
    "reporting_output_path",
    "reporting_markdown_output_path",
    "reporting_output_exists",
    "reporting_markdown_output_exists",
    "self_check_summary_path",
    "self_check_summary_markdown_path",
    "selected_step_count",
    "completed_step_count",
    "failed_step_count",
    "skipped_step_count",
    "passed_steps",
    "failed_steps",
    "skipped_steps",
    "artifacts",
    "overall_passed",
    "overall_status",
    "exit_code",
    "steps",
}

REQUIRED_ARTIFACT_KEYS = {
    "reporting_json",
    "reporting_markdown",
    "self_check_json",
    "self_check_markdown",
}

REQUIRED_ARTIFACT_RECORD_KEYS = {
    "path",
    "exists",
    "size_bytes",
}

REQUIRED_STEP_KEYS = {
    "label",
    "command",
    "command_display",
    "status",
    "exit_code",
    "started_at",
    "finished_at",
    "duration_seconds",
}


class SelfCheckExampleTests(unittest.TestCase):
    def load_json(self, filename: str) -> dict:
        return json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))

    def load_text(self, filename: str) -> str:
        return (EXAMPLES_DIR / filename).read_text(encoding="utf-8")

    def assert_summary_shape(self, summary: dict) -> None:
        self.assertTrue(REQUIRED_SUMMARY_KEYS.issubset(summary.keys()))
        self.assertIn(summary["overall_status"], {"pass", "fail"})
        self.assertIsInstance(summary["overall_passed"], bool)
        self.assertIsInstance(summary["duration_seconds"], (int, float))
        self.assertTrue(REQUIRED_ARTIFACT_KEYS.issubset(summary["artifacts"].keys()))

        for artifact in summary["artifacts"].values():
            if artifact is None:
                continue
            self.assertTrue(REQUIRED_ARTIFACT_RECORD_KEYS.issubset(artifact.keys()))
            self.assertIsInstance(artifact["path"], str)
            self.assertIsInstance(artifact["exists"], bool)
            self.assertTrue(
                artifact["size_bytes"] is None or isinstance(artifact["size_bytes"], int)
            )

        self.assertIsInstance(summary["steps"], list)
        for step in summary["steps"]:
            self.assertTrue(REQUIRED_STEP_KEYS.issubset(step.keys()))
            self.assertIn(step["status"], {"passed", "failed", "skipped"})
            self.assertIsInstance(step["command"], list)
            self.assertTrue(all(isinstance(item, str) for item in step["command"]))
            if step["status"] == "skipped":
                self.assertIsNone(step["started_at"])
                self.assertIsNone(step["finished_at"])
                self.assertIsNone(step["duration_seconds"])
            else:
                self.assertIsInstance(step["duration_seconds"], (int, float))

    def test_schema_file_declares_core_self_check_fields(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["title"], "Self Check Summary")
        self.assertTrue(REQUIRED_SUMMARY_KEYS.issubset(set(schema["required"])))
        self.assertEqual(
            schema["properties"]["overall_status"]["enum"],
            ["pass", "fail"],
        )
        self.assertEqual(
            schema["$defs"]["stepResult"]["properties"]["status"]["enum"],
            ["passed", "failed", "skipped"],
        )

    def test_passing_self_check_example_matches_expected_status(self) -> None:
        summary = self.load_json("self_check_summary.sample.json")

        self.assert_summary_shape(summary)
        self.assertTrue(summary["overall_passed"])
        self.assertEqual(summary["overall_status"], "pass")
        self.assertTrue(summary["reporting_output_exists"])
        self.assertTrue(summary["reporting_markdown_output_exists"])
        self.assertEqual(summary["passed_steps"], ["Unit tests", "Strict reporting"])
        self.assertEqual(summary["failed_steps"], [])
        self.assertEqual(summary["skipped_steps"], [])
        self.assertTrue(summary["artifacts"]["reporting_json"]["exists"])
        self.assertTrue(summary["artifacts"]["reporting_markdown"]["exists"])
        self.assertTrue(summary["artifacts"]["self_check_json"]["exists"])
        self.assertTrue(summary["artifacts"]["self_check_markdown"]["exists"])
        self.assertGreater(summary["duration_seconds"], 0)
        self.assertEqual(summary["failed_step_count"], 0)
        self.assertEqual(summary["skipped_step_count"], 0)
        self.assertEqual(len(summary["steps"]), 2)
        self.assertTrue(all(step["status"] == "passed" for step in summary["steps"]))

    def test_failing_self_check_example_matches_expected_status(self) -> None:
        summary = self.load_json("self_check_summary.fail.sample.json")

        self.assert_summary_shape(summary)
        self.assertFalse(summary["overall_passed"])
        self.assertEqual(summary["overall_status"], "fail")
        self.assertFalse(summary["reporting_output_exists"])
        self.assertFalse(summary["reporting_markdown_output_exists"])
        self.assertEqual(summary["passed_steps"], [])
        self.assertEqual(summary["failed_steps"], ["Unit tests"])
        self.assertEqual(summary["skipped_steps"], ["Strict reporting"])
        self.assertFalse(summary["artifacts"]["reporting_json"]["exists"])
        self.assertFalse(summary["artifacts"]["reporting_markdown"]["exists"])
        self.assertTrue(summary["artifacts"]["self_check_json"]["exists"])
        self.assertTrue(summary["artifacts"]["self_check_markdown"]["exists"])
        self.assertGreater(summary["duration_seconds"], 0)
        self.assertEqual(summary["failed_step_count"], 1)
        self.assertEqual(summary["skipped_step_count"], 1)
        self.assertEqual(len(summary["steps"]), 2)
        self.assertEqual(summary["steps"][0]["status"], "failed")
        self.assertEqual(summary["steps"][1]["status"], "skipped")

    def test_markdown_examples_show_pass_fail_and_artifact_details(self) -> None:
        passing_summary = self.load_text("self_check_summary.sample.md")
        failing_summary = self.load_text("self_check_summary.fail.sample.md")

        self.assertIn("# Self-Check Summary", passing_summary)
        self.assertIn("Overall status: `PASS`", passing_summary)
        self.assertIn("Reporting JSON exists: `True`", passing_summary)
        self.assertIn("Passed step labels: `Unit tests, Strict reporting`", passing_summary)
        self.assertIn("## Artifacts", passing_summary)
        self.assertIn("`self_check_json`: exists=`True`, size_bytes=`4260`", passing_summary)
        self.assertIn("Duration seconds: `4.5`", passing_summary)
        self.assertIn("### `Unit tests`", passing_summary)
        self.assertIn("Overall status: `FAIL`", failing_summary)
        self.assertIn("Reporting JSON exists: `False`", failing_summary)
        self.assertIn("Failed step labels: `Unit tests`", failing_summary)
        self.assertIn("Skipped step labels: `Strict reporting`", failing_summary)
        self.assertIn("## Artifacts", failing_summary)
        self.assertIn("`reporting_json`: exists=`False`, size_bytes=`None`", failing_summary)
        self.assertIn("`self_check_markdown`: exists=`True`, size_bytes=`1710`", failing_summary)
        self.assertIn("### `Strict reporting`", failing_summary)


if __name__ == "__main__":
    unittest.main()
