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

    def write_json(self, relative_path: str, data: dict[str, object]) -> Path:
        return self.write_file(
            relative_path,
            json.dumps(data, ensure_ascii=False, indent=2),
        )

    def write_valid_text_assets(self) -> None:
        self.write_file(
            "image_generation_prompts_ko.txt",
            "[scene_01_intro]\n밝은 인트로 장면\n\n[scene_02_problem]\n문제 정의 장면\n",
        )
        self.write_file(
            "tts_script_ko.txt",
            "[scene_01_intro]\n이번 영상에서는 AI 기반 제작 흐름을 빠르게 살펴봅니다.\n\n[scene_02_problem]\n기획과 이미지, 편집 정보가 흩어지면 제작 속도가 느려집니다.\n",
        )

    def build_scene_prompts_data(
        self, scenes: list[dict[str, object]] | None = None, project: str = "demo"
    ) -> dict[str, object]:
        return {
            "project": project,
            "language": "ko",
            "scenes": scenes
            or [
                {
                    "scene_id": "scene_01",
                    "title": "인트로",
                    "duration_seconds": 6,
                    "visual_prompt": "밝은 인트로",
                    "narration": "안녕하세요",
                },
                {
                    "scene_id": "scene_02",
                    "title": "문제 정의",
                    "duration_seconds": 8,
                    "visual_prompt": "문제 장면",
                    "narration": "문제를 설명합니다",
                },
            ],
        }

    def build_render_plan_data(
        self,
        timeline: list[dict[str, object]] | None = None,
        project: str = "demo",
        scene_prompt_path: str = "scene_prompts.json",
        voice_script_path: str = "tts_script_ko.txt",
        image_prompt_path: str = "image_generation_prompts_ko.txt",
    ) -> dict[str, object]:
        return {
            "project": project,
            "format": {
                "resolution": "1920x1080",
                "fps": 30,
                "aspect_ratio": "16:9",
            },
            "audio": {
                "voice_script_path": voice_script_path,
                "background_music": "calm",
                "voice_language": "ko-KR",
            },
            "assets": {
                "image_prompt_path": image_prompt_path,
                "scene_prompt_path": scene_prompt_path,
            },
            "timeline": timeline
            or [
                {
                    "scene_id": "scene_01",
                    "start_seconds": 0,
                    "duration_seconds": 6,
                    "transition": "cut",
                },
                {
                    "scene_id": "scene_02",
                    "start_seconds": 6,
                    "duration_seconds": 8,
                    "transition": "fade",
                },
            ],
            "output": {
                "video_file": "video.mp4",
                "report_file": "reporting_output.json",
            },
        }

    def get_output_entry(
        self, output: dict[str, object], filename: str
    ) -> dict[str, object]:
        directories = output["directories"]
        for files in directories.values():
            for item in files:
                if item["name"] == filename:
                    return item
        raise AssertionError(f"Could not find output entry for {filename}")

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
        self.write_valid_text_assets()
        self.write_json("scene_prompts.json", self.build_scene_prompts_data())
        self.write_json(
            "nested/render_plan.json",
            self.build_render_plan_data(),
        )

        grouped = reporting.collect_reports(
            self.root,
            reporting.DEFAULT_REPORTING_TARGETS,
            preview_lines=2,
            excluded_dirs=set(),
        )

        self.assertEqual(set(grouped.keys()), {".", "nested"})
        self.assertEqual(grouped["."][0].preview, "[scene_01_intro]\n밝은 인트로 장면")
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
        scene_prompts = self.write_json(
            "scene_prompts.json",
            self.build_scene_prompts_data(
                scenes=[
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
                ]
            ),
        )

        report = reporting.build_file_report(scene_prompts, self.root, preview_lines=3)

        self.assertTrue(
            any("is duplicated" in issue for issue in report.validation_issues)
        )

    def test_render_plan_validation_detects_missing_referenced_files(self) -> None:
        render_plan = self.write_json(
            "render_plan.json",
            self.build_render_plan_data(
                timeline=[
                    {
                        "scene_id": "scene_01",
                        "start_seconds": 1,
                        "duration_seconds": 6,
                        "transition": "cut",
                    }
                ],
                scene_prompt_path="missing_scene.json",
                voice_script_path="missing_tts.txt",
                image_prompt_path="missing_image.txt",
            ),
        )

        report = reporting.build_file_report(render_plan, self.root, preview_lines=3)

        self.assertTrue(
            any(
                "audio.voice_script_path references missing file" in issue
                for issue in report.validation_issues
            )
        )
        self.assertTrue(
            any(
                "assets.image_prompt_path references missing file" in issue
                for issue in report.validation_issues
            )
        )
        self.assertTrue(
            any("start_seconds should be 0" in issue for issue in report.validation_issues)
        )

    def test_build_output_keeps_valid_cross_file_alignment_clean(self) -> None:
        self.write_valid_text_assets()
        self.write_json("scene_prompts.json", self.build_scene_prompts_data())
        self.write_json("render_plan.json", self.build_render_plan_data())

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
            excluded_dirs={".git"},
        )

        self.assertEqual(output["validation_issue_count"], 0)
        self.assertEqual(output["cross_validation_issue_count"], 0)
        self.assertEqual(output["files_with_issues"], [])

    def test_build_output_detects_render_plan_scene_alignment_issues(self) -> None:
        self.write_valid_text_assets()
        self.write_json("scene_prompts.json", self.build_scene_prompts_data())
        self.write_json(
            "render_plan.json",
            self.build_render_plan_data(
                timeline=[
                    {
                        "scene_id": "scene_02",
                        "start_seconds": 0,
                        "duration_seconds": 7,
                        "transition": "cut",
                    },
                    {
                        "scene_id": "scene_01",
                        "start_seconds": 7,
                        "duration_seconds": 6,
                        "transition": "fade",
                    },
                ]
            ),
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
            excluded_dirs=set(),
        )

        self.assertEqual(output["cross_validation_issue_count"], 2)
        self.assertEqual(output["files_with_issues"], ["render_plan.json"])
        render_plan_entry = self.get_output_entry(output, "render_plan.json")
        self.assertTrue(
            any(
                "scene order does not match" in issue
                for issue in render_plan_entry["validation_issues"]
            )
        )
        self.assertTrue(
            any(
                "duration_seconds for 'scene_02'" in issue
                for issue in render_plan_entry["validation_issues"]
            )
        )

    def test_build_output_detects_image_prompt_scene_alignment_issues(self) -> None:
        self.write_file(
            "image_generation_prompts_ko.txt",
            "[scene_02_problem]\n문제 정의 장면\n\n[scene_01_intro]\n밝은 인트로 장면\n",
        )
        self.write_file(
            "tts_script_ko.txt",
            "[scene_01_intro]\n이번 영상에서는 AI 기반 제작 흐름을 빠르게 살펴봅니다.\n\n[scene_02_problem]\n기획과 이미지, 편집 정보가 흩어지면 제작 속도가 느려집니다.\n",
        )
        self.write_json("scene_prompts.json", self.build_scene_prompts_data())
        self.write_json("render_plan.json", self.build_render_plan_data())

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
            excluded_dirs=set(),
        )

        self.assertEqual(output["cross_validation_issue_count"], 1)
        self.assertEqual(output["files_with_issues"], ["image_generation_prompts_ko.txt"])
        image_prompt_entry = self.get_output_entry(output, "image_generation_prompts_ko.txt")
        self.assertTrue(
            any(
                "image prompt label order does not match" in issue
                for issue in image_prompt_entry["validation_issues"]
            )
        )

    def test_build_output_detects_tts_scene_alignment_issues(self) -> None:
        self.write_file(
            "image_generation_prompts_ko.txt",
            "[scene_01_intro]\n밝은 인트로 장면\n\n[scene_02_problem]\n문제 정의 장면\n",
        )
        self.write_file(
            "tts_script_ko.txt",
            "[scene_02_problem]\n기획과 이미지, 편집 정보가 흩어지면 제작 속도가 느려집니다.\n\n[scene_01_intro]\n이번 영상에서는 AI 기반 제작 흐름을 빠르게 살펴봅니다.\n",
        )
        self.write_json("scene_prompts.json", self.build_scene_prompts_data())
        self.write_json("render_plan.json", self.build_render_plan_data())

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
            excluded_dirs=set(),
        )

        self.assertEqual(output["cross_validation_issue_count"], 1)
        self.assertEqual(output["files_with_issues"], ["tts_script_ko.txt"])
        tts_entry = self.get_output_entry(output, "tts_script_ko.txt")
        self.assertTrue(
            any(
                "TTS scene label order does not match" in issue
                for issue in tts_entry["validation_issues"]
            )
        )

    def test_build_output_detects_tts_density_issues(self) -> None:
        self.write_file(
            "image_generation_prompts_ko.txt",
            "[scene_01_intro]\n밝은 인트로 장면\n\n[scene_02_problem]\n문제 정의 장면\n",
        )
        self.write_file(
            "tts_script_ko.txt",
            "[scene_01_intro]\n" + ("아" * 100) + "\n\n[scene_02_problem]\n기획과 이미지 정보가 흩어집니다.\n",
        )
        self.write_json("scene_prompts.json", self.build_scene_prompts_data())
        self.write_json("render_plan.json", self.build_render_plan_data())

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
            excluded_dirs=set(),
        )

        self.assertEqual(output["cross_validation_issue_count"], 1)
        self.assertEqual(output["files_with_issues"], ["tts_script_ko.txt"])
        tts_entry = self.get_output_entry(output, "tts_script_ko.txt")
        self.assertTrue(
            any(
                "too dense" in issue
                for issue in tts_entry["validation_issues"]
            )
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
        self.write_json(
            "scene_prompts.json",
            self.build_scene_prompts_data(
                scenes=[
                    {
                        "scene_id": "scene_01",
                        "title": "",
                        "duration_seconds": 0,
                        "visual_prompt": "",
                        "narration": "",
                    }
                ]
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
