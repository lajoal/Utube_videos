from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gpu_report
import reporting
import self_check


DEFAULT_REPORTING_OUTPUT = "artifacts/reporting_output.json"
DEFAULT_REPORTING_MARKDOWN_OUTPUT = "artifacts/reporting_summary.md"
DEFAULT_GPU_OUTPUT = "artifacts/gpu_report.json"
DEFAULT_GPU_MARKDOWN_OUTPUT = "artifacts/gpu_report.md"
DEFAULT_SELF_CHECK_OUTPUT = "artifacts/self_check_summary.json"
DEFAULT_SELF_CHECK_MARKDOWN_OUTPUT = "artifacts/self_check_summary.md"


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parent


def resolve_output_path(repo_root: Path, output_path: str | None, default_value: str) -> Path:
    raw_value = default_value if output_path is None or not str(output_path).strip() else output_path
    path = Path(raw_value)
    if not path.is_absolute():
        path = repo_root / path
    return path


def default_artifact_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "reporting_json": repo_root / DEFAULT_REPORTING_OUTPUT,
        "reporting_markdown": repo_root / DEFAULT_REPORTING_MARKDOWN_OUTPUT,
        "gpu_json": repo_root / DEFAULT_GPU_OUTPUT,
        "gpu_markdown": repo_root / DEFAULT_GPU_MARKDOWN_OUTPUT,
        "self_check_json": repo_root / DEFAULT_SELF_CHECK_OUTPUT,
        "self_check_markdown": repo_root / DEFAULT_SELF_CHECK_MARKDOWN_OUTPUT,
    }


def read_text_artifact(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def write_reporting_outputs(
    output_path: Path,
    markdown_output_path: Path,
    output: dict[str, Any],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(
        reporting.build_markdown_summary(output),
        encoding="utf-8",
    )


def run_reporting_job(
    repo_root: Path,
    *,
    targets: list[str] | None = None,
    targets_file: str | None = None,
    preview_lines: int = 3,
    exclude_dirs: list[str] | None = None,
    fail_on_missing: bool = False,
    fail_on_validation_issues: bool = False,
    output: str | None = None,
    markdown_output: str | None = None,
) -> dict[str, Any]:
    output_path = resolve_output_path(repo_root, output, DEFAULT_REPORTING_OUTPUT)
    markdown_output_path = resolve_output_path(
        repo_root,
        markdown_output,
        DEFAULT_REPORTING_MARKDOWN_OUTPUT,
    )

    targets_file_value = None
    if targets_file:
        targets_file_value = str(resolve_output_path(repo_root, targets_file, targets_file))
        if not Path(targets_file_value).is_file():
            raise FileNotFoundError(f"Targets file was not found: {targets_file_value}")

    resolved_targets, target_source = reporting.resolve_targets(
        repo_root,
        targets,
        targets_file_value,
    )
    normalized_exclude_dirs = reporting.normalize_excluded_dirs(exclude_dirs)
    grouped = reporting.collect_reports(
        repo_root,
        resolved_targets,
        preview_lines,
        normalized_exclude_dirs,
    )
    report = reporting.build_output(
        repo_root,
        resolved_targets,
        grouped,
        target_source,
        normalized_exclude_dirs,
    )
    report["json_report_path"] = str(output_path)
    report["markdown_summary_path"] = str(markdown_output_path)
    write_reporting_outputs(output_path, markdown_output_path, report)

    exit_code = 0
    if fail_on_missing and report["missing_targets"]:
        exit_code = 1
    if fail_on_validation_issues and report["validation_issue_count"]:
        exit_code = 1

    return {
        "operation": "reporting",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "overall_status": report["overall_status"],
        "overall_passed": report["overall_passed"],
        "report": report,
    }


def run_gpu_job(
    repo_root: Path,
    *,
    python_executable: str = sys.executable,
    require_cuda: bool = False,
    require_nvenc: bool = False,
    output: str | None = None,
    markdown_output: str | None = None,
) -> dict[str, Any]:
    output_path = resolve_output_path(repo_root, output, DEFAULT_GPU_OUTPUT)
    markdown_output_path = resolve_output_path(
        repo_root,
        markdown_output,
        DEFAULT_GPU_MARKDOWN_OUTPUT,
    )

    report = gpu_report.collect_gpu_report(
        repo_root,
        python_executable,
        require_cuda=require_cuda,
        require_nvenc=require_nvenc,
    )
    report["json_report_path"] = str(output_path)
    report["markdown_summary_path"] = str(markdown_output_path)
    gpu_report.write_json(output_path, report)
    gpu_report.write_markdown(markdown_output_path, gpu_report.build_markdown_summary(report))

    return {
        "operation": "gpu_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": 0 if report["overall_passed"] else 1,
        "overall_status": report["overall_status"],
        "overall_passed": report["overall_passed"],
        "report": report,
    }


def run_self_check_job(
    repo_root: Path,
    *,
    python_executable: str = sys.executable,
    output: str | None = None,
    markdown_output: str | None = None,
    gpu_output: str | None = None,
    gpu_markdown_output: str | None = None,
    summary_output: str | None = None,
    summary_markdown_output: str | None = None,
    skip_tests: bool = False,
    skip_gpu: bool = False,
    skip_report: bool = False,
    keep_going: bool = False,
    require_cuda: bool = False,
    require_nvenc: bool = False,
) -> dict[str, Any]:
    output_path = resolve_output_path(repo_root, output, DEFAULT_REPORTING_OUTPUT)
    markdown_output_path = resolve_output_path(
        repo_root,
        markdown_output,
        DEFAULT_REPORTING_MARKDOWN_OUTPUT,
    )
    gpu_output_path = resolve_output_path(repo_root, gpu_output, DEFAULT_GPU_OUTPUT)
    gpu_markdown_output_path = resolve_output_path(
        repo_root,
        gpu_markdown_output,
        DEFAULT_GPU_MARKDOWN_OUTPUT,
    )
    summary_output_path = resolve_output_path(
        repo_root,
        summary_output,
        DEFAULT_SELF_CHECK_OUTPUT,
    )
    summary_markdown_output_path = resolve_output_path(
        repo_root,
        summary_markdown_output,
        DEFAULT_SELF_CHECK_MARKDOWN_OUTPUT,
    )

    args = argparse.Namespace(
        python=python_executable,
        output=str(output_path),
        markdown_output=str(markdown_output_path),
        gpu_output=str(gpu_output_path),
        gpu_markdown_output=str(gpu_markdown_output_path),
        summary_output=str(summary_output_path),
        summary_markdown_output=str(summary_markdown_output_path),
        skip_tests=skip_tests,
        skip_gpu=skip_gpu,
        skip_report=skip_report,
        keep_going=keep_going,
        require_cuda=require_cuda,
        require_nvenc=require_nvenc,
    )

    commands = self_check.build_commands(
        args.python,
        args.output,
        args.markdown_output,
        args.gpu_output,
        args.gpu_markdown_output,
        skip_tests=args.skip_tests,
        skip_gpu=args.skip_gpu,
        skip_report=args.skip_report,
        require_cuda=args.require_cuda,
        require_nvenc=args.require_nvenc,
    )

    workflow_started_at = datetime.now(timezone.utc)

    if not commands:
        workflow_finished_at = datetime.now(timezone.utc)
        summary = self_check.build_summary(
            repo_root,
            args,
            [],
            0,
            workflow_started_at.isoformat(),
            workflow_finished_at.isoformat(),
            self_check.elapsed_seconds(workflow_started_at, workflow_finished_at),
        )
        self_check.persist_summary_outputs(
            summary_output_path,
            summary_markdown_output_path,
            summary,
        )
        return {
            "operation": "self_check",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "exit_code": 0,
            "overall_status": summary["overall_status"],
            "overall_passed": summary["overall_passed"],
            "summary": summary,
        }

    exit_code, step_results = self_check.run_commands(
        commands,
        repo_root,
        keep_going=args.keep_going,
    )
    workflow_finished_at = datetime.now(timezone.utc)
    summary = self_check.build_summary(
        repo_root,
        args,
        step_results,
        exit_code,
        workflow_started_at.isoformat(),
        workflow_finished_at.isoformat(),
        self_check.elapsed_seconds(workflow_started_at, workflow_finished_at),
    )
    self_check.persist_summary_outputs(
        summary_output_path,
        summary_markdown_output_path,
        summary,
    )

    return {
        "operation": "self_check",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "overall_status": summary["overall_status"],
        "overall_passed": summary["overall_passed"],
        "summary": summary,
    }
