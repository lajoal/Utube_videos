from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORTING_TARGETS = [
    "image_generation_prompts_ko.txt",
    "tts_script_ko.txt",
    "scene_prompts.json",
    "render_plan.json",
]

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "venv",
}

TEXT_EXTENSIONS = {".txt", ".md", ".log"}
JSON_EXTENSIONS = {".json"}


@dataclass
class FileReport:
    name: str
    path: str
    size_bytes: int
    modified_at: str
    kind: str
    line_count: int | None
    preview: str | None
    json_summary: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
            "kind": self.kind,
            "line_count": self.line_count,
            "preview": self.preview,
            "json_summary": self.json_summary,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan the repository for reporting targets and write a JSON report."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan. Defaults to the current directory.",
    )
    parser.add_argument(
        "--output",
        default="reporting_output.json",
        help="Output JSON path. Defaults to reporting_output.json.",
    )
    parser.add_argument(
        "--targets",
        nargs="*",
        help="Explicit filenames to include in the report.",
    )
    parser.add_argument(
        "--targets-file",
        help="Optional newline-delimited file of target filenames.",
    )
    parser.add_argument(
        "--exclude-dir",
        dest="exclude_dirs",
        action="append",
        help="Directory name to exclude during recursive scanning. Can be repeated.",
    )
    parser.add_argument(
        "--preview-lines",
        type=int,
        default=3,
        help="Number of preview lines to store for text files. Defaults to 3.",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Return a non-zero exit code when one or more targets are missing.",
    )
    return parser.parse_args(argv)


def iso_timestamp(path: Path) -> str:
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return modified.isoformat()


def detect_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in JSON_EXTENSIONS:
        return "json"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    return "binary"


def safe_read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return None


def load_targets_file(path: Path) -> list[str]:
    targets: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        targets.append(stripped)
    return targets


def resolve_targets(
    explicit_targets: list[str] | None, targets_file: str | None
) -> list[str]:
    targets: list[str] = []

    if explicit_targets:
        targets.extend(explicit_targets)
    if targets_file:
        targets.extend(load_targets_file(Path(targets_file)))
    if not targets:
        targets = DEFAULT_REPORTING_TARGETS.copy()

    return list(dict.fromkeys(targets))


def normalize_excluded_dirs(extra_dirs: list[str] | None) -> set[str]:
    combined = list(DEFAULT_EXCLUDED_DIRS)
    if extra_dirs:
        combined.extend(extra_dirs)
    return {item for item in combined if item}


def summarize_json(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return {
            "type": "object",
            "top_level_keys": list(data.keys())[:20],
            "top_level_key_count": len(data),
        }
    if isinstance(data, list):
        first_item_type = type(data[0]).__name__ if data else None
        return {
            "type": "array",
            "length": len(data),
            "first_item_type": first_item_type,
        }
    return {
        "type": type(data).__name__,
        "value_preview": str(data)[:200],
    }


def build_file_report(path: Path, root: Path, preview_lines: int) -> FileReport:
    kind = detect_kind(path)
    text = safe_read_text(path) if kind in {"text", "json"} else None
    line_count = len(text.splitlines()) if text is not None else None
    preview = None
    json_summary = None

    if kind == "text" and text is not None:
        preview = "\n".join(text.splitlines()[:preview_lines]).strip() or None
    elif kind == "json" and text is not None:
        try:
            json_summary = summarize_json(json.loads(text))
        except json.JSONDecodeError as exc:
            json_summary = {
                "type": "invalid_json",
                "error": str(exc),
            }

    return FileReport(
        name=path.name,
        path=str(path.relative_to(root)),
        size_bytes=path.stat().st_size,
        modified_at=iso_timestamp(path),
        kind=kind,
        line_count=line_count,
        preview=preview,
        json_summary=json_summary,
    )


def collect_reports(
    root: Path,
    targets: list[str],
    preview_lines: int,
    excluded_dirs: set[str] | None = None,
) -> dict[str, list[FileReport]]:
    target_set = set(targets)
    grouped: dict[str, list[FileReport]] = {}
    excluded = excluded_dirs or set()

    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in excluded)
        current_dir = Path(current_root)

        for filename in sorted(filenames):
            if filename not in target_set:
                continue

            path = current_dir / filename
            relative_parent = str(path.parent.relative_to(root))
            directory_key = "." if relative_parent == "." else relative_parent
            grouped.setdefault(directory_key, []).append(
                build_file_report(path, root, preview_lines)
            )

    for reports in grouped.values():
        reports.sort(key=lambda item: item.path)

    return dict(sorted(grouped.items()))


def build_output(
    root: Path,
    targets: list[str],
    grouped: dict[str, list[FileReport]],
    excluded_dirs: set[str] | None = None,
) -> dict[str, Any]:
    report_count = sum(len(files) for files in grouped.values())
    matched_names = {item.name for files in grouped.values() for item in files}
    missing_targets = sorted(target for target in targets if target not in matched_names)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_root": str(root.resolve()),
        "targets": targets,
        "excluded_directories": sorted(excluded_dirs or set()),
        "matched_file_count": report_count,
        "missing_targets": missing_targets,
        "directories": {
            directory: [item.as_dict() for item in files]
            for directory, files in grouped.items()
        },
    }


def print_summary(output: dict[str, Any]) -> None:
    print(f"Scan root: {output['scan_root']}")
    print(f"Target filenames: {len(output['targets'])}")
    print(f"Matched files: {output['matched_file_count']}")

    excluded = output["excluded_directories"]
    if excluded:
        print(f"Excluded directories: {', '.join(excluded)}")

    if output["missing_targets"]:
        print("Missing targets:")
        for target in output["missing_targets"]:
            print(f"  - {target}")

    directories = output["directories"]
    if not directories:
        print("No matching files were found.")
        return

    print("Matches by directory:")
    for directory, files in directories.items():
        print(f"  - {directory}: {len(files)}")
        for file_report in files:
            print(f"    * {file_report['path']}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    targets = resolve_targets(args.targets, args.targets_file)
    excluded_dirs = normalize_excluded_dirs(args.exclude_dirs)
    grouped = collect_reports(root, targets, args.preview_lines, excluded_dirs)
    output = build_output(root, targets, grouped, excluded_dirs)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print_summary(output)
    print(f"Report written to: {output_path}")

    if args.fail_on_missing and output["missing_targets"]:
        print("Failing because missing targets were found.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
