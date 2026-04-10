import json
import tempfile
import unittest
from pathlib import Path

import reporting


class ReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_file(self, relative_path: str, content: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_default_targets_match_expected_files(self) -> None:
        self.assertEqual(
            reporting.DEFAULT_REPORTING_TARGETS,
            [
                "image_generation_prompts_ko.txt",
                "tts_script_ko.txt",
                "scene_prompts.json",
                "render_plan.json",
            ],
        )

    def test_load_targets_file_ignores_comments_and_blank_lines(self) -> None:
        target_file = self.write_file(
            "targets.txt",
            "# core files\nimage_generation_prompts_ko.txt\n\n render_plan.json \n",
        )

        targets = reporting.load_targets_file(target_file)

        self.assertEqual(targets, ["image_generation_prompts_ko.txt", "render_plan.json"])

    def test_resolve_targets_uses_default_manifest_when_present(self) -> None:
        self.write_file(
            reporting.DEFAULT_TARGETS_MANIFEST,
            "tts_script_ko.txt\nrender_plan.json\n",
        )

        targets, source = reporting.resolve_targets(self.root, None, None)

        self.assertEqual(targets, ["tts_script_ko.txt", "render_plan.json"])
        self.assertEqual(source, "default_manifest")

    def test_collect_reports_groups_matches_by_directory(self) -> None:
        self.write_file(
            "image_generation_prompts_ko.txt",
            "[scene_01]\nline 1\nline 2\nline 3\n",
        )
        self.write_file(
            "nested/render_plan.json",
            json.dumps(
                {
                    "project": "demo",
                    "format": {
                        "resolution": "1920x1080",
                        "fps": 30,
                        "aspect_ratio": "16:9",
                    },
                    "audio": {
                        "voice_script_path": "tts_script_ko.txt",
                        "background_music": "calm",
                        "voice_language": "ko-KR",
                    },
                    "assets": {
                        "image_prompt_path": "image_generation_prompts_ko.txt",
                        "scene_prompt_path": "scene_prompts.json",
                    },
                    "timeline": [
                        {
                            "scene_id": "scene_01",
                            "start_seconds": 0,
                            "duration_seconds": 6,
                            "transition": "cut",
                        }
                    ],
                    "output": {
                        "video_file": "video.mp4",
                        "report_file": "reporting_output.json",
                    },
                }
            ),
        )
        self.write_file(
            "tts_script_ko.txt",
            "제목: 테스트\n두 번째 문단입니다.\n",
        )
        self.write_file(
            "scene_prompts.json",
            json.dumps(
                {
                    "project": "demo",
                    "language": "ko",
                    "scenes": [
                        {
                            "scene_id": "scene_01",
                            "title": "인트로",
                            "duration_seconds": 6,
                            "visual_prompt": "밝은 인트로",
                            "narration": "안녕하세요",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        )

        grouped = reporting.collect_reports(
            self.root,
            reporting.DEFAULT_REPORTING_TARGETS,
            preview_lines=2,
            excluded_dirs=set(),
        )

        self.assertEqual(set(grouped.keys()), {".", "nested"})
        self.assertEqual(grouped["."][0].preview, "[scene_01]\nline 1")
        self.assertEqual(grouped["nested"][0].json_summary["type"], "object")
        self.assertEqual(grouped["nested"][0].validation_issues, [])

    def test_collect_reports_ignores_excluded_directories(self) -> None:
        self.write_file(".git/render_plan.json", '{"ignored": true}')
        self.write_file("nested/render_plan.json", '{"included": true}')

        grouped = reporting.collect_reports(
            self.root,
            ["render_plan.json"],
            preview_lines=2,
            excluded_dirs={".git"},
        )

        self.assertEqual(set(grouped.keys()), {"nested"})
        self.assertEqual(grouped["nested"][0].path, "nested/render_plan.json")

    def test_build_file_report_marks_invalid_json(self) -> None:
        invalid_json = self.write_file("scene_prompts.json", "{invalid json")

        report = reporting.build_file_report(invalid_json, self.root, preview_lines=3)

        self.assertEqual(report.kind, "json")
        self.assertEqual(report.json_summary["type"], "invalid_json")
        self.assertIn("Invalid JSON:", report.validation_issues[0])

    def test_scene_prompts_validation_detects_duplicate_scene_ids(self) -> None:
        scene_prompts = self.write_file(
            "scene_prompts.json",
            json.dumps(
                {
                    "project": "demo",
                    "language": "ko",
                    "scenes": [
                        {
                            "scene_id": "scene_01",
                            "title": "인트로",
                            "duration_seconds": 6,
                            "visual_prompt": "프롬프트",
                            "narration": "내레이션",
                        },
                        {
                            "scene_id": "scene_01",
                            "title": "중복",
                            "duration_seconds": 5,
                            "visual_prompt": "프롬프트",
                            "narration": "내레이션",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
        )

        report = reporting.build_file_report(scene_prompts, self.root, preview_lines=3)

        self.assertTrue(
            any("is duplicated" in issue for issue in report.validation_issues)
        )

    def test_render_plan_validation_detects_missing_referenced_files(self) -> None:
        render_plan = self.write_file(
            "render_plan.json",
            json.dumps(
                {
                    "project": "demo",
                    "format": {
                        "resolution": "1920x1080",
                        "fps": 30,
                        "aspect_ratio": "16:9",
                    },
                    "audio": {
                        "voice_script_path": "missing_tts.txt",
                        "background_music": "calm",
                        "voice_language": "ko-KR",
                    },
                    "assets": {
                        "image_prompt_path": "missing_image.txt",
                        "scene_prompt_path": "missing_scene.json",
                    },
                    "timeline": [
                        {
                            "scene_id": "scene_01",
                            "start_seconds": 1,
                            "duration_seconds": 6,
                            "transition": "cut",
                        }
                    ],
                    "output": {
                        "video_file": "video.mp4",
                        "report_file": "reporting_output.json",
                    },
                }
            ),
        )

        report = reporting.build_file_report(render_plan, self.root, preview_lines=3)

        self.assertTrue(
            any("audio.voice_script_path references missing file" in issue for issue in report.validation_issues)
        )
        self.assertTrue(
            any("assets.image_prompt_path references missing file" in issue for issue in report.validation_issues)
        )
        self.assertTrue(
            any("start_seconds should be 0" in issue for issue in report.validation_issues)
        )

    def test_build_output_lists_missing_targets_and_validation_counts(self) -> None:
        self.write_file(
            "tts_script_ko.txt",
            "제목: 샘플\n두 번째 줄입니다.\n",
        )

        grouped = reporting.collect_reports(
            self.root,
            reporting.DEFAULT_REPORTING_TARGETS,
            preview_lines=3,
            excluded_dirs=set(),
        )
        output = reporting.build_output(
            self.root,
            reporting.DEFAULT_REPORTING_TARGETS,
            grouped,
            target_source="built_in_defaults",
            excluded_dirs={".git", "__pycache__"},
        )

        self.assertEqual(output["matched_file_count"], 1)
        self.assertEqual(output["target_source"], "built_in_defaults")
        self.assertEqual(output["validation_issue_count"], 0)
        self.assertEqual(output["files_with_issues"], [])
        self.assertIn("image_generation_prompts_ko.txt", output["missing_targets"])
        self.assertIn("scene_prompts.json", output["missing_targets"])
        self.assertIn("render_plan.json", output["missing_targets"])
        self.assertNotIn("tts_script_ko.txt", output["missing_targets"])
        self.assertEqual(
            output["excluded_directories"],
            [".git", "__pycache__"],
        )

    def test_main_returns_non_zero_when_fail_on_missing_is_enabled(self) -> None:
        self.write_file(
            "tts_script_ko.txt",
            "제목: 샘플\n두 번째 줄입니다.\n",
        )
        self.write_file(
            "config/targets.txt",
            "tts_script_ko.txt\nscene_prompts.json\n",
        )

        exit_code = reporting.main(
            [
                "--root",
                str(self.root),
                "--output",
                "artifacts/report.json",
                "--targets-file",
                "config/targets.txt",
                "--fail-on-missing",
            ]
        )

        self.assertEqual(exit_code, 1)
        output = json.loads(
            (self.root / "artifacts/report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            output["targets"],
            ["tts_script_ko.txt", "scene_prompts.json"],
        )
        self.assertEqual(output["target_source"], "targets_file")
        self.assertEqual(output["missing_targets"], ["scene_prompts.json"])

    def test_main_returns_non_zero_when_fail_on_validation_issues_is_enabled(self) -> None:
        self.write_file(
            "scene_prompts.json",
            json.dumps(
                {
                    "project": "demo",
                    "language": "ko",
                    "scenes": [
                        {
                            "scene_id": "scene_01",
                            "title": "",
                            "duration_seconds": 0,
                            "visual_prompt": "",
                            "narration": "",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        )

        exit_code = reporting.main(
            [
                "--root",
                str(self.root),
                "--output",
                "artifacts/report.json",
                "--targets",
                "scene_prompts.json",
                "--fail-on-validation-issues",
            ]
        )

        self.assertEqual(exit_code, 1)
        output = json.loads(
            (self.root / "artifacts/report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(output["target_source"], "cli")
        self.assertGreater(output["validation_issue_count"], 0)
        self.assertEqual(output["files_with_issues"], ["scene_prompts.json"])


if __name__ == "__main__":
    unittest.main()
