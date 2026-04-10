from __future__ import annotations

import argparse
import csv
import importlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEFAULT_JSON_OUTPUT = "artifacts/gpu_report.json"
DEFAULT_MARKDOWN_OUTPUT = "artifacts/gpu_report.md"

CUDA_WORKLOADS = [
    "image_generation",
    "speech_to_text",
    "tts_generation",
]
NVENC_WORKLOAD = "video_encode_nvenc"
HWACCEL_WORKLOAD = "video_hwaccel_decode"
NVENC_ENCODER_NAMES = ["h264_nvenc", "hevc_nvenc", "av1_nvenc"]


@dataclass
class CommandResult:
    command: list[str]
    found: bool
    exit_code: int | None
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str]], CommandResult]
ModuleLoader = Callable[[str], Any]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect local GPU tooling and write a diagnostics report.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to record in the report. Defaults to the current interpreter.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_JSON_OUTPUT,
        help="Output JSON path. Defaults to artifacts/gpu_report.json.",
    )
    parser.add_argument(
        "--markdown-output",
        default=DEFAULT_MARKDOWN_OUTPUT,
        help="Output Markdown path. Defaults to artifacts/gpu_report.md.",
    )
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="Fail when CUDA-ready torch execution is not available.",
    )
    parser.add_argument(
        "--require-nvenc",
        action="store_true",
        help="Fail when FFmpeg NVENC encoders are not available.",
    )
    return parser.parse_args(argv)


def run_command(command: list[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return CommandResult(
            command=command,
            found=False,
            exit_code=None,
            stdout="",
            stderr="Command not found.",
        )

    return CommandResult(
        command=command,
        found=True,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def resolve_output_path(repo_root: Path, output_path: str) -> Path:
    path = Path(output_path)
    if path.is_absolute():
        return path
    return repo_root / path


def parse_nvidia_smi_output(text: str) -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    for row in csv.reader(text.splitlines()):
        if len(row) < 4:
            continue
        index_text, name, memory_text, driver_version = [item.strip() for item in row[:4]]
        try:
            index = int(index_text)
            memory_total_mb = int(memory_text)
        except ValueError:
            continue
        gpus.append(
            {
                "index": index,
                "name": name,
                "memory_total_mb": memory_total_mb,
                "driver_version": driver_version,
            }
        )
    return gpus


def parse_ffmpeg_hwaccels(text: str) -> list[str]:
    hwaccels: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip().lower()
        if not line or line.startswith("hardware acceleration"):
            continue
        if line.startswith("ffmpeg version"):
            continue
        hwaccels.append(line)
    return hwaccels


def parse_nvenc_encoders(text: str) -> list[str]:
    encoders: list[str] = []
    for encoder in NVENC_ENCODER_NAMES:
        if encoder in text:
            encoders.append(encoder)
    return encoders


def detect_nvidia_smi(command_runner: CommandRunner = run_command) -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    result = command_runner(command)
    if not result.found:
        return {
            "available": False,
            "command_found": False,
            "command": command,
            "exit_code": None,
            "gpu_count": 0,
            "gpus": [],
            "stderr": result.stderr,
        }

    gpus = parse_nvidia_smi_output(result.stdout) if result.exit_code == 0 else []
    return {
        "available": result.exit_code == 0,
        "command_found": True,
        "command": command,
        "exit_code": result.exit_code,
        "gpu_count": len(gpus),
        "gpus": gpus,
        "stderr": result.stderr.strip(),
    }


def detect_torch(module_loader: ModuleLoader = importlib.import_module) -> dict[str, Any]:
    try:
        torch = module_loader("torch")
    except ImportError:
        return {
            "available": False,
            "version": None,
            "cuda_available": False,
            "cuda_version": None,
            "device_count": 0,
            "devices": [],
            "cudnn_available": False,
        }

    cuda = getattr(torch, "cuda", None)
    cuda_available = False
    device_count = 0
    devices: list[dict[str, Any]] = []

    if cuda is not None and hasattr(cuda, "is_available"):
        try:
            cuda_available = bool(cuda.is_available())
        except Exception:
            cuda_available = False

    if cuda_available and hasattr(cuda, "device_count"):
        try:
            device_count = int(cuda.device_count())
        except Exception:
            device_count = 0

    for index in range(device_count):
        try:
            name = str(cuda.get_device_name(index))
        except Exception:
            name = f"cuda:{index}"

        capability_value: str | None = None
        if hasattr(cuda, "get_device_capability"):
            try:
                capability = cuda.get_device_capability(index)
                capability_value = ".".join(str(part) for part in capability)
            except Exception:
                capability_value = None

        devices.append(
            {
                "index": index,
                "name": name,
                "capability": capability_value,
            }
        )

    cudnn_available = False
    backends = getattr(torch, "backends", None)
    cudnn = getattr(backends, "cudnn", None)
    if cudnn is not None and hasattr(cudnn, "is_available"):
        try:
            cudnn_available = bool(cudnn.is_available())
        except Exception:
            cudnn_available = False

    version_namespace = getattr(torch, "version", None)
    cuda_version = getattr(version_namespace, "cuda", None)

    return {
        "available": True,
        "version": getattr(torch, "__version__", None),
        "cuda_available": cuda_available,
        "cuda_version": cuda_version,
        "device_count": device_count,
        "devices": devices,
        "cudnn_available": cudnn_available,
    }


def detect_ffmpeg(command_runner: CommandRunner = run_command) -> dict[str, Any]:
    version_command = ["ffmpeg", "-version"]
    version_result = command_runner(version_command)
    if not version_result.found:
        return {
            "available": False,
            "command_found": False,
            "version_line": None,
            "cuda_hwaccel_available": False,
            "hwaccels": [],
            "nvenc_encoders": [],
            "stderr": version_result.stderr,
        }

    version_line = None
    if version_result.stdout:
        version_line = version_result.stdout.splitlines()[0].strip()

    hwaccels_result = command_runner(["ffmpeg", "-hide_banner", "-hwaccels"])
    encoders_result = command_runner(["ffmpeg", "-hide_banner", "-encoders"])

    hwaccels = []
    if hwaccels_result.found and hwaccels_result.exit_code == 0:
        hwaccels = parse_ffmpeg_hwaccels(hwaccels_result.stdout)

    nvenc_encoders = []
    if encoders_result.found and encoders_result.exit_code == 0:
        nvenc_encoders = parse_nvenc_encoders(encoders_result.stdout)

    stderr_lines = [
        item
        for item in [
            version_result.stderr.strip(),
            hwaccels_result.stderr.strip() if hwaccels_result.found else hwaccels_result.stderr,
            encoders_result.stderr.strip() if encoders_result.found else encoders_result.stderr,
        ]
        if item
    ]

    return {
        "available": version_result.exit_code == 0,
        "command_found": True,
        "version_line": version_line,
        "cuda_hwaccel_available": "cuda" in hwaccels,
        "hwaccels": hwaccels,
        "nvenc_encoders": nvenc_encoders,
        "stderr": "\n".join(stderr_lines),
    }


def collect_workloads(cuda_ready: bool, nvenc_available: bool, cuda_hwaccel_available: bool) -> tuple[list[str], list[str]]:
    available: list[str] = []
    unavailable: list[str] = []

    for workload in CUDA_WORKLOADS:
        if cuda_ready:
            available.append(workload)
        else:
            unavailable.append(workload)

    if nvenc_available:
        available.append(NVENC_WORKLOAD)
    else:
        unavailable.append(NVENC_WORKLOAD)

    if cuda_hwaccel_available:
        available.append(HWACCEL_WORKLOAD)
    else:
        unavailable.append(HWACCEL_WORKLOAD)

    return available, unavailable


def collect_gpu_report(
    repo_root: Path,
    python_executable: str,
    *,
    require_cuda: bool = False,
    require_nvenc: bool = False,
    command_runner: CommandRunner = run_command,
    module_loader: ModuleLoader = importlib.import_module,
) -> dict[str, Any]:
    nvidia_smi = detect_nvidia_smi(command_runner)
    torch_info = detect_torch(module_loader)
    ffmpeg_info = detect_ffmpeg(command_runner)

    gpu_available = bool(nvidia_smi["gpu_count"] > 0 or torch_info["device_count"] > 0)
    cuda_ready = bool(torch_info["cuda_available"])
    nvenc_available = bool(ffmpeg_info["nvenc_encoders"])
    available_workloads, unavailable_workloads = collect_workloads(
        cuda_ready,
        nvenc_available,
        bool(ffmpeg_info["cuda_hwaccel_available"]),
    )

    requirement_failures: list[str] = []
    if require_cuda and not cuda_ready:
        requirement_failures.append("CUDA-ready torch execution is not available.")
    if require_nvenc and not nvenc_available:
        requirement_failures.append("FFmpeg NVENC encoders are not available.")

    overall_status = "ready" if available_workloads else "limited"
    if requirement_failures:
        overall_status = "fail"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "python_executable": python_executable,
        "python_version": platform.python_version(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "require_cuda": require_cuda,
        "require_nvenc": require_nvenc,
        "gpu_available": gpu_available,
        "cuda_ready": cuda_ready,
        "nvenc_available": nvenc_available,
        "available_workloads": available_workloads,
        "unavailable_workloads": unavailable_workloads,
        "requirement_failures": requirement_failures,
        "overall_passed": not requirement_failures,
        "overall_status": overall_status,
        "nvidia_smi": nvidia_smi,
        "torch": torch_info,
        "ffmpeg": ffmpeg_info,
    }


def build_markdown_summary(report: dict[str, Any]) -> str:
    lines = [
        "# GPU Report Summary",
        "",
        f"- Overall status: `{report['overall_status'].upper()}`",
        f"- Overall passed: `{report['overall_passed']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- Repository root: `{report['repo_root']}`",
        f"- Python executable: `{report['python_executable']}`",
        f"- Python version: `{report['python_version']}`",
        f"- Platform: `{report['platform']['system']} {report['platform']['release']} ({report['platform']['machine']})`",
        f"- Require CUDA: `{report['require_cuda']}`",
        f"- Require NVENC: `{report['require_nvenc']}`",
        f"- GPU available: `{report['gpu_available']}`",
        f"- CUDA ready: `{report['cuda_ready']}`",
        f"- NVENC available: `{report['nvenc_available']}`",
        f"- JSON report: `{report['json_report_path']}`",
        f"- Markdown summary: `{report['markdown_summary_path']}`",
        "",
        "## Workloads",
        "",
        f"- Available workloads: `{', '.join(report['available_workloads']) if report['available_workloads'] else 'None'}`",
        f"- Unavailable workloads: `{', '.join(report['unavailable_workloads']) if report['unavailable_workloads'] else 'None'}`",
        f"- Requirement failures: `{', '.join(report['requirement_failures']) if report['requirement_failures'] else 'None'}`",
        "",
        "## NVIDIA SMI",
        "",
        f"- Command found: `{report['nvidia_smi']['command_found']}`",
        f"- Available: `{report['nvidia_smi']['available']}`",
        f"- GPU count: `{report['nvidia_smi']['gpu_count']}`",
    ]

    for gpu in report["nvidia_smi"]["gpus"]:
        lines.append(
            f"- GPU {gpu['index']}: `{gpu['name']}` with `{gpu['memory_total_mb']}` MiB on driver `{gpu['driver_version']}`"
        )
    if not report["nvidia_smi"]["gpus"]:
        lines.append("- GPU list: `None`")
    lines.extend(
        [
            f"- STDERR: `{report['nvidia_smi']['stderr'] or 'None'}`",
            "",
            "## Torch",
            "",
            f"- Available: `{report['torch']['available']}`",
            f"- Version: `{report['torch']['version']}`",
            f"- CUDA available: `{report['torch']['cuda_available']}`",
            f"- CUDA version: `{report['torch']['cuda_version']}`",
            f"- Device count: `{report['torch']['device_count']}`",
            f"- cuDNN available: `{report['torch']['cudnn_available']}`",
        ]
    )

    for device in report["torch"]["devices"]:
        lines.append(
            f"- Device {device['index']}: `{device['name']}` capability `{device['capability']}`"
        )
    if not report["torch"]["devices"]:
        lines.append("- Device list: `None`")

    lines.extend(
        [
            "",
            "## FFmpeg",
            "",
            f"- Command found: `{report['ffmpeg']['command_found']}`",
            f"- Available: `{report['ffmpeg']['available']}`",
            f"- Version line: `{report['ffmpeg']['version_line']}`",
            f"- CUDA hwaccel available: `{report['ffmpeg']['cuda_hwaccel_available']}`",
            f"- HWAccel list: `{', '.join(report['ffmpeg']['hwaccels']) if report['ffmpeg']['hwaccels'] else 'None'}`",
            f"- NVENC encoders: `{', '.join(report['ffmpeg']['nvenc_encoders']) if report['ffmpeg']['nvenc_encoders'] else 'None'}`",
            f"- STDERR: `{report['ffmpeg']['stderr'] or 'None'}`",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parent
    json_output_path = resolve_output_path(repo_root, args.output)
    markdown_output_path = resolve_output_path(repo_root, args.markdown_output)

    report = collect_gpu_report(
        repo_root,
        args.python,
        require_cuda=args.require_cuda,
        require_nvenc=args.require_nvenc,
    )
    report["json_report_path"] = str(json_output_path)
    report["markdown_summary_path"] = str(markdown_output_path)

    write_json(json_output_path, report)
    write_markdown(markdown_output_path, build_markdown_summary(report))

    print(f"GPU report status: {report['overall_status'].upper()}")
    print(f"GPU available: {report['gpu_available']}")
    print(f"CUDA ready: {report['cuda_ready']}")
    print(f"NVENC available: {report['nvenc_available']}")
    print(f"JSON report written to: {json_output_path}")
    print(f"Markdown summary written to: {markdown_output_path}")

    if report["requirement_failures"]:
        print("Failing because required GPU capabilities are missing.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
