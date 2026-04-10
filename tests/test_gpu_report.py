import json
import tempfile
import unittest
from pathlib import Path

import gpu_report


class FakeCuda:
    def is_available(self) -> bool:
        return True

    def device_count(self) -> int:
        return 1

    def get_device_name(self, index: int) -> str:
        return "NVIDIA RTX 4090"

    def get_device_capability(self, index: int) -> tuple[int, int]:
        return (8, 9)


class FakeCudnn:
    def is_available(self) -> bool:
        return True


class FakeTorch:
    __version__ = "2.6.0"
    cuda = FakeCuda()
    version = type("VersionNamespace", (), {"cuda": "12.4"})
    backends = type("Backends", (), {"cudnn": FakeCudnn()})


class GPUReportTests(unittest.TestCase):
    def test_parse_args_defaults(self) -> None:
        args = gpu_report.parse_args([])

        self.assertEqual(args.python, gpu_report.sys.executable)
        self.assertEqual(args.output, gpu_report.DEFAULT_JSON_OUTPUT)
        self.assertEqual(args.markdown_output, gpu_report.DEFAULT_MARKDOWN_OUTPUT)
        self.assertFalse(args.require_cuda)
        self.assertFalse(args.require_nvenc)

    def test_parse_nvidia_smi_output_returns_gpu_rows(self) -> None:
        rows = gpu_report.parse_nvidia_smi_output(
            "0, NVIDIA RTX 4090, 24564, 555.42\n1, NVIDIA RTX 4080, 16376, 555.42\n"
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["index"], 0)
        self.assertEqual(rows[0]["name"], "NVIDIA RTX 4090")
        self.assertEqual(rows[0]["memory_total_mb"], 24564)
        self.assertEqual(rows[1]["driver_version"], "555.42")

    def test_collect_gpu_report_marks_ready_when_cuda_and_nvenc_are_available(self) -> None:
        def fake_command_runner(command: list[str]) -> gpu_report.CommandResult:
            if command[0] == "nvidia-smi":
                return gpu_report.CommandResult(
                    command,
                    True,
                    0,
                    "0, NVIDIA RTX 4090, 24564, 555.42\n",
                    "",
                )
            if command[:3] == ["ffmpeg", "-hide_banner", "-hwaccels"]:
                return gpu_report.CommandResult(
                    command,
                    True,
                    0,
                    "Hardware acceleration methods:\ncuda\n",
                    "",
                )
            if command[:3] == ["ffmpeg", "-hide_banner", "-encoders"]:
                return gpu_report.CommandResult(
                    command,
                    True,
                    0,
                    " V....D h264_nvenc\n V....D hevc_nvenc\n V....D av1_nvenc\n",
                    "",
                )
            if command[:2] == ["ffmpeg", "-version"]:
                return gpu_report.CommandResult(
                    command,
                    True,
                    0,
                    "ffmpeg version 7.0.1\n",
                    "",
                )
            raise AssertionError(f"Unexpected command: {command}")

        report = gpu_report.collect_gpu_report(
            Path("/repo"),
            "python3.11",
            command_runner=fake_command_runner,
            module_loader=lambda name: FakeTorch,
        )

        self.assertTrue(report["gpu_available"])
        self.assertTrue(report["cuda_ready"])
        self.assertTrue(report["nvenc_available"])
        self.assertEqual(report["overall_status"], "ready")
        self.assertEqual(report["requirement_failures"], [])
        self.assertEqual(
            report["available_workloads"],
            [
                "image_generation",
                "speech_to_text",
                "tts_generation",
                "video_encode_nvenc",
                "video_hwaccel_decode",
            ],
        )
        self.assertEqual(report["torch"]["devices"][0]["capability"], "8.9")

    def test_collect_gpu_report_fails_requirements_when_cuda_and_nvenc_are_missing(self) -> None:
        def fake_command_runner(command: list[str]) -> gpu_report.CommandResult:
            if command[0] == "nvidia-smi":
                return gpu_report.CommandResult(command, False, None, "", "Command not found.")
            if command[:2] == ["ffmpeg", "-version"]:
                return gpu_report.CommandResult(command, True, 0, "ffmpeg version 7.0.1\n", "")
            if command[:3] == ["ffmpeg", "-hide_banner", "-hwaccels"]:
                return gpu_report.CommandResult(command, True, 0, "Hardware acceleration methods:\n", "")
            if command[:3] == ["ffmpeg", "-hide_banner", "-encoders"]:
                return gpu_report.CommandResult(command, True, 0, "", "")
            raise AssertionError(f"Unexpected command: {command}")

        def missing_torch(name: str):
            raise ImportError(name)

        report = gpu_report.collect_gpu_report(
            Path("/repo"),
            "python3.11",
            require_cuda=True,
            require_nvenc=True,
            command_runner=fake_command_runner,
            module_loader=missing_torch,
        )

        self.assertFalse(report["gpu_available"])
        self.assertFalse(report["cuda_ready"])
        self.assertFalse(report["nvenc_available"])
        self.assertEqual(report["overall_status"], "fail")
        self.assertEqual(
            report["requirement_failures"],
            [
                "CUDA-ready torch execution is not available.",
                "FFmpeg NVENC encoders are not available.",
            ],
        )
        self.assertEqual(report["unavailable_workloads"], [
            "image_generation",
            "speech_to_text",
            "tts_generation",
            "video_encode_nvenc",
            "video_hwaccel_decode",
        ])

    def test_build_markdown_summary_lists_gpu_details(self) -> None:
        report = {
            "generated_at": "2026-04-10T12:30:00+00:00",
            "repo_root": "/repo",
            "python_executable": "python3.11",
            "python_version": "3.11.9",
            "platform": {
                "system": "Linux",
                "release": "6.8.0",
                "machine": "x86_64",
            },
            "require_cuda": False,
            "require_nvenc": False,
            "gpu_available": True,
            "cuda_ready": True,
            "nvenc_available": True,
            "available_workloads": [
                "image_generation",
                "speech_to_text",
                "tts_generation",
                "video_encode_nvenc",
                "video_hwaccel_decode",
            ],
            "unavailable_workloads": [],
            "requirement_failures": [],
            "overall_passed": True,
            "overall_status": "ready",
            "json_report_path": "/repo/artifacts/gpu_report.json",
            "markdown_summary_path": "/repo/artifacts/gpu_report.md",
            "nvidia_smi": {
                "command_found": True,
                "available": True,
                "gpu_count": 1,
                "gpus": [
                    {
                        "index": 0,
                        "name": "NVIDIA RTX 4090",
                        "memory_total_mb": 24564,
                        "driver_version": "555.42",
                    }
                ],
                "stderr": "",
            },
            "torch": {
                "available": True,
                "version": "2.6.0",
                "cuda_available": True,
                "cuda_version": "12.4",
                "device_count": 1,
                "devices": [
                    {
                        "index": 0,
                        "name": "NVIDIA RTX 4090",
                        "capability": "8.9",
                    }
                ],
                "cudnn_available": True,
            },
            "ffmpeg": {
                "command_found": True,
                "available": True,
                "version_line": "ffmpeg version 7.0.1",
                "cuda_hwaccel_available": True,
                "hwaccels": ["cuda"],
                "nvenc_encoders": ["h264_nvenc", "hevc_nvenc"],
                "stderr": "",
            },
        }

        markdown = gpu_report.build_markdown_summary(report)

        self.assertIn("# GPU Report Summary", markdown)
        self.assertIn("- Overall status: `READY`", markdown)
        self.assertIn("- GPU available: `True`", markdown)
        self.assertIn("- Available workloads: `image_generation, speech_to_text, tts_generation, video_encode_nvenc, video_hwaccel_decode`", markdown)
        self.assertIn("- GPU 0: `NVIDIA RTX 4090`", markdown)
        self.assertIn("- Device 0: `NVIDIA RTX 4090` capability `8.9`", markdown)
        self.assertIn("- NVENC encoders: `h264_nvenc, hevc_nvenc`", markdown)

    def test_main_writes_json_and_markdown_outputs(self) -> None:
        original_collect = gpu_report.collect_gpu_report
        try:
            with tempfile.TemporaryDirectory() as tempdir:
                repo_root = Path(tempdir)
                output_path = repo_root / "artifacts" / "gpu_report.json"
                markdown_path = repo_root / "artifacts" / "gpu_report.md"

                def fake_collect(repo_root_arg: Path, python_executable: str, **kwargs):
                    return {
                        "generated_at": "2026-04-10T12:30:00+00:00",
                        "repo_root": str(repo_root_arg),
                        "python_executable": python_executable,
                        "python_version": "3.11.9",
                        "platform": {
                            "system": "Linux",
                            "release": "6.8.0",
                            "machine": "x86_64",
                        },
                        "require_cuda": kwargs.get("require_cuda", False),
                        "require_nvenc": kwargs.get("require_nvenc", False),
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

                gpu_report.collect_gpu_report = fake_collect
                original_file = gpu_report.__file__
                gpu_report.__file__ = str(repo_root / "gpu_report.py")
                try:
                    exit_code = gpu_report.main(
                        [
                            "--python",
                            "python3.11",
                            "--output",
                            str(output_path),
                            "--markdown-output",
                            str(markdown_path),
                        ]
                    )
                finally:
                    gpu_report.__file__ = original_file

                self.assertEqual(exit_code, 0)
                self.assertTrue(output_path.is_file())
                self.assertTrue(markdown_path.is_file())
                written = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(written["overall_status"], "limited")
                self.assertEqual(written["json_report_path"], str(output_path))
        finally:
            gpu_report.collect_gpu_report = original_collect


if __name__ == "__main__":
    unittest.main()
