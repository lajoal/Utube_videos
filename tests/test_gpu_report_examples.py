import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
SCHEMA_PATH = REPO_ROOT / "schemas" / "gpu_report.schema.json"

REQUIRED_KEYS = {
    "generated_at",
    "repo_root",
    "python_executable",
    "python_version",
    "platform",
    "require_cuda",
    "require_nvenc",
    "gpu_available",
    "cuda_ready",
    "nvenc_available",
    "available_workloads",
    "unavailable_workloads",
    "requirement_failures",
    "overall_passed",
    "overall_status",
    "json_report_path",
    "markdown_summary_path",
    "nvidia_smi",
    "torch",
    "ffmpeg",
}


class GPUReportExampleTests(unittest.TestCase):
    def load_json(self, filename: str) -> dict:
        return json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))

    def load_text(self, filename: str) -> str:
        return (EXAMPLES_DIR / filename).read_text(encoding="utf-8")

    def test_schema_file_declares_core_gpu_report_fields(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["title"], "GPU Report")
        self.assertTrue(REQUIRED_KEYS.issubset(set(schema["required"])))
        self.assertEqual(schema["properties"]["overall_status"]["enum"], ["ready", "limited", "fail"])

    def test_sample_gpu_report_matches_expected_shape(self) -> None:
        report = self.load_json("gpu_report.sample.json")

        self.assertTrue(REQUIRED_KEYS.issubset(report.keys()))
        self.assertEqual(report["overall_status"], "ready")
        self.assertTrue(report["overall_passed"])
        self.assertTrue(report["gpu_available"])
        self.assertTrue(report["cuda_ready"])
        self.assertTrue(report["nvenc_available"])
        self.assertIn("image_generation", report["available_workloads"])
        self.assertEqual(report["nvidia_smi"]["gpu_count"], 1)
        self.assertEqual(report["torch"]["device_count"], 1)
        self.assertIn("h264_nvenc", report["ffmpeg"]["nvenc_encoders"])

    def test_sample_gpu_markdown_is_human_readable(self) -> None:
        markdown = self.load_text("gpu_report.sample.md")

        self.assertIn("# GPU Report Summary", markdown)
        self.assertIn("Overall status: `READY`", markdown)
        self.assertIn("CUDA ready: `True`", markdown)
        self.assertIn("NVENC available: `True`", markdown)
        self.assertIn("Available workloads: `image_generation, speech_to_text, tts_generation, video_encode_nvenc, video_hwaccel_decode`", markdown)
        self.assertIn("GPU 0: `NVIDIA RTX 4090`", markdown)


if __name__ == "__main__":
    unittest.main()
