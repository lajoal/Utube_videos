import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
SCHEMA_PATH = REPO_ROOT / "schemas" / "reporting_output.schema.json"

REQUIRED_REPORT_KEYS = {
    "generated_at",
    "scan_root",
    "targets",
    "target_source",
    "excluded_directories",
    "matched_file_count",
    "missing_targets",
    "validation_issue_count",
    "cross_validation_issue_count",
    "files_with_issues",
    "overall_passed",
    "overall_status",
    "directories",
}

REQUIRED_FILE_REPORT_KEYS = {
    "name",
    "path",
    "size_bytes",
    "modified_at",
    "kind",
    "line_count",
    "preview",
    "json_summary",
    "validation_issue_count",
    "validation_issues",
}


class ReportingExampleTests(unittest.TestCase):
    def load_json(self, filename: str) -> dict:
        return json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))

    def load_text(self, filename: str) -> str:
        return (EXAMPLES_DIR / filename).read_text(encoding="utf-8")

    def assert_report_shape(self, report: dict) -> None:
        self.assertTrue(REQUIRED_REPORT_KEYS.issubset(report.keys()))
        self.assertIn(report["overall_status"], {"pass", "fail"})
        self.assertIsInstance(report["overall_passed"], bool)
        self.assertIsInstance(report["directories"], dict)

        for files in report["directories"].values():
            self.assertIsInstance(files, list)
            for file_report in files:
                self.assertTrue(REQUIRED_FILE_REPORT_KEYS.issubset(file_report.keys()))
                self.assertIsInstance(file_report["validation_issues"], list)
                self.assertEqual(
                    file_report["validation_issue_count"],
                    len(file_report["validation_issues"]),
                )

    def test_schema_file_declares_core_reporting_fields(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["title"], "Reporting Output")
        self.assertTrue(REQUIRED_REPORT_KEYS.issubset(set(schema["required"])))
        self.assertEqual(
            schema["properties"]["overall_status"]["enum"],
            ["pass", "fail"],
        )

    def test_passing_example_matches_expected_status(self) -> None:
        report = self.load_json("reporting_output.sample.json")

        self.assert_report_shape(report)
        self.assertTrue(report["overall_passed"])
        self.assertEqual(report["overall_status"], "pass")
        self.assertEqual(report["missing_targets"], [])
        self.assertEqual(report["validation_issue_count"], 0)
        self.assertEqual(report["cross_validation_issue_count"], 0)
        self.assertEqual(report["files_with_issues"], [])

    def test_failing_example_matches_expected_status(self) -> None:
        report = self.load_json("reporting_output.fail.sample.json")

        self.assert_report_shape(report)
        self.assertFalse(report["overall_passed"])
        self.assertEqual(report["overall_status"], "fail")
        self.assertGreater(len(report["missing_targets"]), 0)
        self.assertGreater(report["validation_issue_count"], 0)
        self.assertGreater(report["cross_validation_issue_count"], 0)
        self.assertGreater(len(report["files_with_issues"]), 0)

    def test_markdown_examples_show_pass_and_fail_states(self) -> None:
        passing_summary = self.load_text("reporting_summary.sample.md")
        failing_summary = self.load_text("reporting_summary.fail.sample.md")

        self.assertIn("Overall status: `PASS`", passing_summary)
        self.assertIn("Overall passed: `True`", passing_summary)
        self.assertIn("Overall status: `FAIL`", failing_summary)
        self.assertIn("Overall passed: `False`", failing_summary)


if __name__ == "__main__":
    unittest.main()
