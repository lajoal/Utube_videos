from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_JSON_OUTPUT = "artifacts/reporting_output.json"
DEFAULT_MARKDOWN_OUTPUT = "artifacts/reporting_summary.md"


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


def run_step(label: str, command: list[str], repo_root: Path) -> int:
    print(f"== {label} ==")
    print("$ " + " ".join(command))
    completed = subprocess.run(command, cwd=repo_root)
    return completed.returncode


def run_commands(
    commands: list[tuple[str, list[str]]],
    repo_root: Path,
    *,
    keep_going: bool = False,
) -> int:
    first_failure = 0

    for label, command in commands:
        exit_code = run_step(label, command, repo_root)
        if exit_code == 0:
            continue

        if first_failure == 0:
            first_failure = exit_code

        print(f"Self-check failed during: {label}")
        if not keep_going:
            return exit_code

    return first_failure


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parent
    commands = build_commands(
        args.python,
        args.output,
        args.markdown_output,
        skip_tests=args.skip_tests,
        skip_report=args.skip_report,
    )

    if not commands:
        print("No self-check steps selected.")
        return 0

    exit_code = run_commands(commands, repo_root, keep_going=args.keep_going)

    if not args.skip_report:
        print(f"JSON report: {repo_root / args.output}")
        print(f"Markdown summary: {repo_root / args.markdown_output}")

    if exit_code != 0:
        print("Self-check completed with failures.")
        return exit_code

    print("Self-check completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
