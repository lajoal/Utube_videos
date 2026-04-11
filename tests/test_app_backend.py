import json
import tempfile
import unittest
from pathlib import Path

import app_backend


class AppBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_file(self, relative_path: str, content: str) -> Path:
        path = self.repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, relative_path: str, data: dict[str, object]) -> Path:
        return self.write_file(
            relative_path,
            json.dumps(data, ensure_ascii=False, indent=2),
        )

    def write_valid_reporting_assets(self) -> None:
        self.write_file(
            "image_generation_prompts_ko.txt",
            "[scene_01_intro]\n밝은 인트로 장면\n\n[scene_02_problem]\n문제 정의 장면\n",
        )
        self.write_file(
            "tts_script_ko.txt",
            "[scene_01_intro]\n이번 영상에서는 AI 기반 제작 흐름을 빠르게 살펴봅니다.\n\n"
            "[scene_02_problem]\n기획과 이미지, 편집 정보가 흩어지면 제작 속도가 느려집니다.\n",
        )
        self.write_json(
            "scene_prompts.json",
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
                    },
                    {
                        "scene_id": "scene_02",
                        "title": "문제 정의",
                        "duration_seconds": 8,
                        "visual_prompt": "문제 장면",
                        "narration": "문제를 설명합니다",
                    },
                ],
            },
        )
        self.write_json(
            "render_plan.json",
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
            },
        )

    def test_default_artifact_paths_returns_expected_locations(self) -> None:
        artifact_paths = app_backend.default_artifact_paths(self.repo_root)

        self.assertEqual(
            artifact_paths["reporting_json"],
            self.repo_root / "artifacts" / "reporting_output.json",
        )
        self.assertEqual(
            artifact_paths["self_check_markdown"],
            self.repo_root / "artifacts" / "self_check_summary.md",
        )

    def test_read_text_artifact_returns_none_for_missing_file(self) -> None:
        self.assertIsNone(app_backend.read_text_artifact(self.repo_root / "missing.md"))

    def test_run_reporting_job_writes_artifacts(self) -> None:
        self.write_valid_reporting_assets()

        result = app_backend.run_reporting_job(self.repo_root)

        self.assertEqual(result["operation"], "reporting")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["overall_passed"])
        self.assertTrue((self.repo_root / "artifacts" / "reporting_output.json").is_file())
        self.assertTrue((self.repo_root / "artifacts" / "reporting_summary.md").is_file())

    def test_run_gpu_job_writes_outputs(self) -> None:
        original_collect = app_backend.gpu_report.collect_gpu_report
        try:
            def fake_collect(
                repo_root_arg: Path,
                python_executable: str,
                **_kwargs: object,
            ) -> dict[str, object]:
                return {
                    "generated_at": "2026-04-11T00:00:00+00:00",
                    "repo_root": str(repo_root_arg),
                    "python_executable": python_executable,
                    "python_version": "3.11.9",
                    "platform": {
                        "system": "Linux",
                        "release": "6.8.0",
                        "machine": "x86_64",
                    },
                    "require_cuda": False,
                    "require_nvenc": False,
                    "gpu_available": False,
                    "cuda_ready": False,
                    "nvenc_available": False,
                    "available_workloads": [],
                    "unavailable_workloads": [
                        "image_generation",
                        "speech_to_text",
                        "tts_generation",
                        "video_encode_nvenc",
                        "video_hwaccel_decode",
                    ],
                    "requirement_failures": [],
                    "overall_passed": True,
                    "overall_status": "limited",
                    "nvidia_smi": {
                        "command_found": False,
                        "available": False,
                        "gpu_count": 0,
                        "gpus": [],
                        "stderr": "Command not found.",
                    },
                    "torch": {
                        "available": False,
                        "version": None,
                        "cuda_available": False,
                        "cuda_version": None,
                        "device_count": 0,
                        "devices": [],
                        "cudnn_available": False,
                    },
                    "ffmpeg": {
                        "command_found": True,
                        "available": True,
                        "version_line": "ffmpeg version 7.0.1",
                        "cuda_hwaccel_available": False,
                        "hwaccels": [],
                        "nvenc_encoders": [],
                        "stderr": "",
                    },
                }

            app_backend.gpu_report.collect_gpu_report = fake_collect
            result = app_backend.run_gpu_job(self.repo_root, python_executable="python3.11")
        finally:
            app_backend.gpu_report.collect_gpu_report = original_collect

        self.assertEqual(result["operation"], "gpu_report")
        self.assertEqual(result["report"]["python_executable"], "python3.11")
        self.assertTrue((self.repo_root / "artifacts" / "gpu_report.json").is_file())
        self.assertTrue((self.repo_root / "artifacts" / "gpu_report.md").is_file())

    def test_run_self_check_job_writes_summary_when_steps_fail(self) -> None:
        original_run_commands = app_backend.self_check.run_commands
        try:
            def fake_run_commands(
                commands: list[tuple[str, list[str]]],
                repo_root: Path,
                *,
                keep_going: bool = False,
            ) -> tuple[int, list[dict[str, object]]]:
                del commands, repo_root, keep_going
                return (
                    4,
                    [
                        app_backend.self_check.build_step_result(
                            "Unit tests",
                            ["python", "-m", "unittest"],
                            status="failed",
                            exit_code=4,
                            started_at="2026-04-11T00:00:00+00:00",
                            finished_at="2026-04-11T00:00:01+00:00",
                            duration_seconds=1.0,
                        )
                    ],
                )

            app_backend.self_check.run_commands = fake_run_commands
            result = app_backend.run_self_check_job(self.repo_root, python_executable="python3.11")
        finally:
            app_backend.self_check.run_commands = original_run_commands

        self.assertEqual(result["operation"], "self_check")
        self.assertEqual(result["exit_code"], 4)
        self.assertFalse(result["overall_passed"])
        self.assertTrue((self.repo_root / "artifacts" / "self_check_summary.json").is_file())
        self.assertTrue((self.repo_root / "artifacts" / "self_check_summary.md").is_file())


if __name__ == "__main__":
    unittest.main()
