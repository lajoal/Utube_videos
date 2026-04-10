from __future__ import annotations

import argparse
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON_OUTPUT = "artifacts/reporting_output.json"
DEFAULT_MARKDOWN_OUTPUT = "artifacts/reporting_summary.md"
DEFAULT_SELF_CHECK_SUMMARY_OUTPUT = "artifacts/self_check_summary.json"
DEFAULT_SELF_CHECK_SUMMARY_MARKDOWN_OUTPUT = "artifacts/self_check_summary.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the repository self-check flow end to end."
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use. Defaults to the current interpreter.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_JSON_OUTPUT,
        help="JSON reporting output path for the strict reporting step.",
    )
    parser.add_argument(
        "--markdown-output",
        default=DEFAULT_MARKDOWN_OUTPUT,
        help="Markdown summary output path for the strict reporting step.",
    )
    parser.add_argument(
        "--summary-output",
        default=DEFAULT_SELF_CHECK_SUMMARY_OUTPUT,
        help="JSON output path for the self-check step summary.",
    )
    parser.add_argument(
        "--summary-markdown-output",
        default=DEFAULT_SELF_CHECK_SUMMARY_MARKDOWN_OUTPUT,
        help="Markdown output path for the self-check step summary.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip unit test execution.",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip the strict reporting step.",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue to later self-check steps even if an earlier step fails.",
    )
    return parser.parse_args(argv)


def build_commands(
    python_executable: str,
    output_path: str,
    markdown_output_path: str,
    *,
    skip_tests: bool = False,
    skip_report: bool = False,
) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = []

    if not skip_tests:
        commands.append(
            (
                "Unit tests",
                [
                    python_executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-p",
                    "test_*.py",
                    "-v",
                ],
            )
        )

    if not skip_report:
        commands.append(
            (
                "Strict reporting",
                [
                    python_executable,
                    "reporting.py",
                    "--fail-on-missing",
                    "--fail-on-validation-issues",
                    "--output",
                    output_path,
                    "--markdown-output",
                    markdown_output_path,
                ],
            )
        )

    return commands


def resolve_output_path(repo_root: Path, output_path: str) -> Path:
    path = Path(output_path)
    if path.is_absolute():
        return path
    return repo_root / path


def elapsed_seconds(started_at: datetime, finished_at: datetime) -> float:
    return round((finished_at - started_at).total_seconds(), 6)


def run_step(label: str, command: list[str], repo_root: Path) -> int:
    print(f"== {label} ==")
    print("$ " + " ".join(command))
    completed = subprocess.run(command, cwd=repo_root)
    return completed.returncode


def build_step_result(
    label: str,
    command: list[str],
    *,
    status: str,
    exit_code: int | None,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "command": command,
        "command_display": " ".join(command),
        "status": status,
        "exit_code": exit_code,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
    }


def run_commands(
    commands: list[tuple[str, list[str]]],
    repo_root: Path,
    *,
    keep_going: bool = False,
) -> tuple[int, list[dict[str, Any]]]:
    first_failure = 0
    step_results: list[dict[str, Any]] = []

    for index, (label, command) in enumerate(commands):
        step_started_at = datetime.now(timezone.utc)
        exit_code = run_step(label, command, repo_root)
        step_finished_at = datetime.now(timezone.utc)
        status = "passed" if exit_code == 0 else "failed"
        step_results.append(
            build_step_result(
                label,
                command,
                status=status,
                exit_code=exit_code,
                started_at=step_started_at.isoformat(),
                finished_at=step_finished_at.isoformat(),
                duration_seconds=elapsed_seconds(step_started_at, step_finished_at),
            )
        )

        if exit_code == 0:
            continue

        if first_failure == 0:
            first_failure = exit_code

        print(f"Self-check failed during: {label}")
        if not keep_going:
            for skipped_label, skipped_command in commands[index + 1 :]:
                step_results.append(
                    build_step_result(
                        skipped_label,
                        skipped_command,
                        status="skipped",
                        exit_code=None,
                    )
                )
            return exit_code, step_results

    return first_failure, step_results


def format_step_labels(labels: list[str]) -> str:
    return ", ".join(labels) if labels else "None"


def build_artifact_record(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None

    exists = path.is_file()
    return {
        "path": str(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
    }


def refresh_summary_artifacts(summary: dict[str, Any]) -> None:
    reporting_output_path = (
        None
        if summary["reporting_output_path"] is None
        else Path(summary["reporting_output_path"])
    )
    reporting_markdown_path = (
        None
        if summary["reporting_markdown_output_path"] is None
        else Path(summary["reporting_markdown_output_path"])
    )
    self_check_summary_path = Path(summary["self_check_summary_path"])
    self_check_summary_markdown_path = Path(summary["self_check_summary_markdown_path"])

    artifacts = {
        "reporting_json": build_artifact_record(reporting_output_path),
        "reporting_markdown": build_artifact_record(reporting_markdown_path),
        "self_check_json": build_artifact_record(self_check_summary_path),
        "self_check_markdown": build_artifact_record(self_check_summary_markdown_path),
    }

    summary["artifacts"] = artifacts
    summary["reporting_output_exists"] = (
        None if artifacts["reporting_json"] is None else artifacts["reporting_json"]["exists"]
    )
    summary["reporting_markdown_output_exists"] = (
        None
        if artifacts["reporting_markdown"] is None
        else artifacts["reporting_markdown"]["exists"]
    )


def build_summary(
    repo_root: Path,
    args: argparse.Namespace,
    step_results: list[dict[str, Any]],
    exit_code: int,
    started_at: str,
    finished_at: str,
    duration_seconds: float,
) -> dict[str, Any]:
    summary_path = resolve_output_path(repo_root, args.summary_output)
    summary_markdown_path = resolve_output_path(repo_root, args.summary_markdown_output)
    report_output_path = (
        None if args.skip_report else resolve_output_path(repo_root, args.output)
    )
    report_markdown_path = (
        None
        if args.skip_report
        else resolve_output_path(repo_root, args.markdown_output)
    )
    passed_steps = [item["label"] for item in step_results if item["status"] == "passed"]
    failed_steps = [item["label"] for item in step_results if item["status"] == "failed"]
    skipped_steps = [item["label"] for item in step_results if item["status"] == "skipped"]
    failed_step_count = len(failed_steps)
    skipped_step_count = len(skipped_steps)
    completed_step_count = len(step_results) - skipped_step_count
    overall_passed = exit_code == 0

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "repo_root": str(repo_root),
        "python_executable": args.python,
        "keep_going": args.keep_going,
        "skip_tests": args.skip_tests,
        "skip_report": args.skip_report,
        "reporting_output_path": None if report_output_path is None else str(report_output_path),
        "reporting_markdown_output_path": None if report_markdown_path is None else str(report_markdown_path),
        "reporting_output_exists": None,
        "reporting_markdown_output_exists": None,
        "self_check_summary_path": str(summary_path),
        "self_check_summary_markdown_path": str(summary_markdown_path),
        "selected_step_count": len(step_results),
        "completed_step_count": completed_step_count,
        "failed_step_count": failed_step_count,
        "skipped_step_count": skipped_step_count,
        "passed_steps": passed_steps,
        "failed_steps": failed_steps,
        "skipped_steps": skipped_steps,
        "overall_passed": overall_passed,
        "overall_status": "pass" if overall_passed else "fail",
        "exit_code": exit_code,
        "steps": step_results,
    }
    refresh_summary_artifacts(summary)
    return summary


def build_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Self-Check Summary",
        "",
        f"- Overall status: `{summary['overall_status'].upper()}`",
        f"- Overall passed: `{summary['overall_passed']}`",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Started at: `{summary['started_at']}`",
        f"- Finished at: `{summary['finished_at']}`",
        f"- Duration seconds: `{summary['duration_seconds']}`",
        f"- Repository root: `{summary['repo_root']}`",
        f"- Python executable: `{summary['python_executable']}`",
        f"- Keep going: `{summary['keep_going']}`",
        f"- Skip tests: `{summary['skip_tests']}`",
        f"- Skip report: `{summary['skip_report']}`",
        f"- Selected steps: `{summary['selected_step_count']}`",
        f"- Completed steps: `{summary['completed_step_count']}`",
        f"- Failed steps: `{summary['failed_step_count']}`",
        f"- Skipped steps: `{summary['skipped_step_count']}`",
        f"- Passed step labels: `{format_step_labels(summary['passed_steps'])}`",
        f"- Failed step labels: `{format_step_labels(summary['failed_steps'])}`",
        f"- Skipped step labels: `{format_step_labels(summary['skipped_steps'])}`",
        f"- Exit code: `{summary['exit_code']}`",
        f"- JSON summary: `{summary['self_check_summary_path']}`",
        f"- Markdown summary: `{summary['self_check_summary_markdown_path']}`",
    ]

    if summary.get("reporting_output_path"):
        lines.append(f"- Reporting JSON: `{summary['reporting_output_path']}`")
        lines.append(f"- Reporting JSON exists: `{summary['reporting_output_exists']}`")
    if summary.get("reporting_markdown_output_path"):
        lines.append(
            f"- Reporting Markdown: `{summary['reporting_markdown_output_path']}`"
        )
        lines.append(
            f"- Reporting Markdown exists: `{summary['reporting_markdown_output_exists']}`"
        )

    lines.extend(["", "## Artifacts", ""])
    artifacts = summary.get("artifacts", {})
    if artifacts:
        for label, artifact in artifacts.items():
            if artifact is None:
                lines.append(f"- `{label}`: None")
                continue
            lines.append(
                f"- `{label}`: exists=`{artifact['exists']}`, size_bytes=`{artifact['size_bytes']}`, path=`{artifact['path']}`"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Steps", ""])
    if summary["steps"]:
        for step in summary["steps"]:
            lines.append(f"### `{step['label']}`")
            lines.append("")
            lines.append(f"- Status: `{step['status'].upper()}`")
            lines.append(f"- Exit code: `{step['exit_code']}`")
            lines.append(f"- Started at: `{step['started_at']}`")
            lines.append(f"- Finished at: `{step['finished_at']}`")
            lines.append(f"- Duration seconds: `{step['duration_seconds']}`")
            lines.append(f"- Command: `{step['command_display']}`")
            lines.append("")
    else:
        lines.append("- None")

    return "\n".join(lines).rstrip() + "\n"


def write_summary(summary_path: Path, summary: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_summary_markdown(summary_path: Path, summary: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        build_summary_markdown(summary),
        encoding="utf-8",
    )


def persist_summary_outputs(
    summary_path: Path,
    summary_markdown_path: Path,
    summary: dict[str, Any],
) -> None:
    previous_artifacts: dict[str, Any] | None = None

    for _ in range(5):
        write_summary(summary_path, summary)
        write_summary_markdown(summary_markdown_path, summary)
        refresh_summary_artifacts(summary)
        current_artifacts = deepcopy(summary.get("artifacts", {}))
        if current_artifacts == previous_artifacts:
            break
        previous_artifacts = current_artifacts

    write_summary(summary_path, summary)
    write_summary_markdown(summary_markdown_path, summary)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parent
    summary_path = resolve_output_path(repo_root, args.summary_output)
    summary_markdown_path = resolve_output_path(
        repo_root, args.summary_markdown_output
    )
    commands = build_commands(
        args.python,
        args.output,
        args.markdown_output,
        skip_tests=args.skip_tests,
        skip_report=args.skip_report,
    )

    workflow_started_at = datetime.now(timezone.utc)

    if not commands:
        workflow_finished_at = datetime.now(timezone.utc)
        summary = build_summary(
            repo_root,
            args,
            [],
            0,
            workflow_started_at.isoformat(),
            workflow_finished_at.isoformat(),
            elapsed_seconds(workflow_started_at, workflow_finished_at),
        )
        persist_summary_outputs(summary_path, summary_markdown_path, summary)
        print("No self-check steps selected.")
        print(f"Self-check summary: {summary_path}")
        print(f"Self-check Markdown summary: {summary_markdown_path}")
        return 0

    exit_code, step_results = run_commands(
        commands,
        repo_root,
        keep_going=args.keep_going,
    )
    workflow_finished_at = datetime.now(timezone.utc)
    summary = build_summary(
        repo_root,
        args,
        step_results,
        exit_code,
        workflow_started_at.isoformat(),
        workflow_finished_at.isoformat(),
        elapsed_seconds(workflow_started_at, workflow_finished_at),
    )
    persist_summary_outputs(summary_path, summary_markdown_path, summary)

    if not args.skip_report:
        print(f"JSON report: {repo_root / args.output}")
        print(f"Markdown summary: {repo_root / args.markdown_output}")
    print(f"Self-check summary: {summary_path}")
    print(f"Self-check Markdown summary: {summary_markdown_path}")

    if exit_code != 0:
        print("Self-check completed with failures.")
        return exit_code

    print("Self-check completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
