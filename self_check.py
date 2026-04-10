from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON_OUTPUT = "artifacts/reporting_output.json"
DEFAULT_MARKDOWN_OUTPUT = "artifacts/reporting_summary.md"
DEFAULT_SELF_CHECK_SUMMARY_OUTPUT = "artifacts/self_check_summary.json"


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
) -> dict[str, Any]:
    return {
        "label": label,
        "command": command,
        "command_display": " ".join(command),
        "status": status,
        "exit_code": exit_code,
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
        exit_code = run_step(label, command, repo_root)
        status = "passed" if exit_code == 0 else "failed"
        step_results.append(
            build_step_result(label, command, status=status, exit_code=exit_code)
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


def build_summary(
    repo_root: Path,
    args: argparse.Namespace,
    step_results: list[dict[str, Any]],
    exit_code: int,
) -> dict[str, Any]:
    summary_path = resolve_output_path(repo_root, args.summary_output)
    report_path = (
        None if args.skip_report else str(resolve_output_path(repo_root, args.output))
    )
    markdown_path = (
        None
        if args.skip_report
        else str(resolve_output_path(repo_root, args.markdown_output))
    )
    failed_step_count = sum(1 for item in step_results if item["status"] == "failed")
    skipped_step_count = sum(1 for item in step_results if item["status"] == "skipped")
    completed_step_count = sum(1 for item in step_results if item["status"] != "skipped")
    overall_passed = exit_code == 0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "python_executable": args.python,
        "keep_going": args.keep_going,
        "skip_tests": args.skip_tests,
        "skip_report": args.skip_report,
        "reporting_output_path": report_path,
        "reporting_markdown_output_path": markdown_path,
        "self_check_summary_path": str(summary_path),
        "selected_step_count": len(step_results),
        "completed_step_count": completed_step_count,
        "failed_step_count": failed_step_count,
        "skipped_step_count": skipped_step_count,
        "overall_passed": overall_passed,
        "overall_status": "pass" if overall_passed else "fail",
        "exit_code": exit_code,
        "steps": step_results,
    }


def write_summary(summary_path: Path, summary: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parent
    summary_path = resolve_output_path(repo_root, args.summary_output)
    commands = build_commands(
        args.python,
        args.output,
        args.markdown_output,
        skip_tests=args.skip_tests,
        skip_report=args.skip_report,
    )

    if not commands:
        summary = build_summary(repo_root, args, [], 0)
        write_summary(summary_path, summary)
        print("No self-check steps selected.")
        print(f"Self-check summary: {summary_path}")
        return 0

    exit_code, step_results = run_commands(
        commands,
        repo_root,
        keep_going=args.keep_going,
    )
    summary = build_summary(repo_root, args, step_results, exit_code)
    write_summary(summary_path, summary)

    if not args.skip_report:
        print(f"JSON report: {repo_root / args.output}")
        print(f"Markdown summary: {repo_root / args.markdown_output}")
    print(f"Self-check summary: {summary_path}")

    if exit_code != 0:
        print("Self-check completed with failures.")
        return exit_code

    print("Self-check completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
