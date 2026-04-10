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
DEFAULT_TARGETS_MANIFEST = "reporting_targets.txt"

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
    validation_issues: list[str]

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
            "validation_issue_count": len(self.validation_issues),
            "validation_issues": self.validation_issues,
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
    parser.add_argument(
        "--fail-on-validation-issues",
        action="store_true",
        help="Return a non-zero exit code when validation issues are found.",
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


def resolve_targets_file_path(root: Path, targets_file: str) -> Path:
    path = Path(targets_file)
    if path.is_absolute():
        return path
    return root / path


def resolve_targets(
    root: Path,
    explicit_targets: list[str] | None,
    targets_file: str | None,
) -> tuple[list[str], str]:
    targets: list[str] = []
    source_parts: list[str] = []

    if explicit_targets:
        targets.extend(explicit_targets)
        source_parts.append("cli")

    if targets_file:
        targets.extend(load_targets_file(resolve_targets_file_path(root, targets_file)))
        source_parts.append("targets_file")

    if not targets:
        manifest_path = root / DEFAULT_TARGETS_MANIFEST
        if manifest_path.is_file():
            targets = load_targets_file(manifest_path)
            source = "default_manifest"
        else:
            targets = DEFAULT_REPORTING_TARGETS.copy()
            source = "built_in_defaults"
    else:
        source = "+".join(source_parts)

    return list(dict.fromkeys(targets)), source


def normalize_excluded_dirs(extra_dirs: list[str] | None) -> set[str]:
    combined = list(DEFAULT_EXCLUDED_DIRS)
    if extra_dirs:
        combined.extend(extra_dirs)
    return {item for item in combined if item}


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_positive_number(value: Any) -> bool:
    return is_number(value) and value > 0


def is_non_negative_number(value: Any) -> bool:
    return is_number(value) and value >= 0


def numbers_equal(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(left - right) <= tolerance


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


def validate_text_target(filename: str, text: str | None) -> list[str]:
    issues: list[str] = []

    if text is None:
        return ["File could not be decoded as UTF-8 text."]

    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not non_empty_lines:
        return ["File is empty."]

    if filename == "image_generation_prompts_ko.txt":
        if not any(line.startswith("[") and line.endswith("]") for line in non_empty_lines):
            issues.append("Expected at least one scene label like [scene_01_intro].")
    elif filename == "tts_script_ko.txt":
        if len(non_empty_lines) < 2:
            issues.append("Expected at least two non-empty lines in the TTS script.")

    return issues


def validate_scene_prompts_data(data: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["scene_prompts.json must contain a JSON object."]

    if not is_non_empty_string(data.get("project")):
        issues.append("project must be a non-empty string.")
    if not is_non_empty_string(data.get("language")):
        issues.append("language must be a non-empty string.")

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        issues.append("scenes must be a non-empty array.")
        return issues

    seen_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        label = f"scenes[{index}]"
        if not isinstance(scene, dict):
            issues.append(f"{label} must be an object.")
            continue

        scene_id = scene.get("scene_id")
        if not is_non_empty_string(scene_id):
            issues.append(f"{label}.scene_id must be a non-empty string.")
        elif scene_id in seen_ids:
            issues.append(f"{label}.scene_id '{scene_id}' is duplicated.")
        else:
            seen_ids.add(scene_id)

        if not is_non_empty_string(scene.get("title")):
            issues.append(f"{label}.title must be a non-empty string.")
        if not is_positive_number(scene.get("duration_seconds")):
            issues.append(f"{label}.duration_seconds must be a positive number.")
        if not is_non_empty_string(scene.get("visual_prompt")):
            issues.append(f"{label}.visual_prompt must be a non-empty string.")
        if not is_non_empty_string(scene.get("narration")):
            issues.append(f"{label}.narration must be a non-empty string.")

    return issues


def require_existing_file_reference(
    root: Path, value: Any, field_name: str, issues: list[str]
) -> None:
    if not is_non_empty_string(value):
        issues.append(f"{field_name} must be a non-empty string.")
        return

    reference_path = root / value
    if not reference_path.is_file():
        issues.append(f"{field_name} references missing file '{value}'.")


def validate_render_plan_data(data: Any, root: Path) -> list[str]:
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["render_plan.json must contain a JSON object."]

    if not is_non_empty_string(data.get("project")):
        issues.append("project must be a non-empty string.")

    format_data = data.get("format")
    if not isinstance(format_data, dict):
        issues.append("format must be an object.")
    else:
        if not is_non_empty_string(format_data.get("resolution")):
            issues.append("format.resolution must be a non-empty string.")
        if not is_positive_number(format_data.get("fps")):
            issues.append("format.fps must be a positive number.")
        if not is_non_empty_string(format_data.get("aspect_ratio")):
            issues.append("format.aspect_ratio must be a non-empty string.")

    audio = data.get("audio")
    if not isinstance(audio, dict):
        issues.append("audio must be an object.")
    else:
        require_existing_file_reference(
            root,
            audio.get("voice_script_path"),
            "audio.voice_script_path",
            issues,
        )
        if not is_non_empty_string(audio.get("background_music")):
            issues.append("audio.background_music must be a non-empty string.")
        if not is_non_empty_string(audio.get("voice_language")):
            issues.append("audio.voice_language must be a non-empty string.")

    assets = data.get("assets")
    if not isinstance(assets, dict):
        issues.append("assets must be an object.")
    else:
        require_existing_file_reference(
            root,
            assets.get("image_prompt_path"),
            "assets.image_prompt_path",
            issues,
        )
        require_existing_file_reference(
            root,
            assets.get("scene_prompt_path"),
            "assets.scene_prompt_path",
            issues,
        )

    output = data.get("output")
    if not isinstance(output, dict):
        issues.append("output must be an object.")
    else:
        if not is_non_empty_string(output.get("video_file")):
            issues.append("output.video_file must be a non-empty string.")
        if not is_non_empty_string(output.get("report_file")):
            issues.append("output.report_file must be a non-empty string.")

    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        issues.append("timeline must be a non-empty array.")
        return issues

    expected_start = 0.0
    seen_scene_ids: set[str] = set()
    for index, entry in enumerate(timeline):
        label = f"timeline[{index}]"
        if not isinstance(entry, dict):
            issues.append(f"{label} must be an object.")
            continue

        scene_id = entry.get("scene_id")
        if not is_non_empty_string(scene_id):
            issues.append(f"{label}.scene_id must be a non-empty string.")
        elif scene_id in seen_scene_ids:
            issues.append(f"{label}.scene_id '{scene_id}' is duplicated.")
        else:
            seen_scene_ids.add(scene_id)

        start_seconds = entry.get("start_seconds")
        duration_seconds = entry.get("duration_seconds")
        if not is_non_negative_number(start_seconds):
            issues.append(f"{label}.start_seconds must be a non-negative number.")
        if not is_positive_number(duration_seconds):
            issues.append(f"{label}.duration_seconds must be a positive number.")
        if not is_non_empty_string(entry.get("transition")):
            issues.append(f"{label}.transition must be a non-empty string.")

        if is_non_negative_number(start_seconds) and is_positive_number(duration_seconds):
            start_value = float(start_seconds)
            duration_value = float(duration_seconds)
            if not numbers_equal(start_value, expected_start):
                issues.append(
                    f"{label}.start_seconds should be {expected_start:g} to keep the timeline contiguous."
                )
            expected_start = start_value + duration_value

    return issues


def validate_json_target(filename: str, data: Any, root: Path) -> list[str]:
    if filename == "scene_prompts.json":
        return validate_scene_prompts_data(data)
    if filename == "render_plan.json":
        return validate_render_plan_data(data, root)
    return []


def build_file_report(path: Path, root: Path, preview_lines: int) -> FileReport:
    kind = detect_kind(path)
    text = safe_read_text(path) if kind in {"text", "json"} else None
    line_count = len(text.splitlines()) if text is not None else None
    preview = None
    json_summary = None
    validation_issues: list[str] = []

    if kind == "text":
        if text is not None:
            preview = "\n".join(text.splitlines()[:preview_lines]).strip() or None
        validation_issues = validate_text_target(path.name, text)
    elif kind == "json":
        if text is None:
            validation_issues = ["File could not be decoded as UTF-8 JSON text."]
        else:
            try:
                parsed_json = json.loads(text)
                json_summary = summarize_json(parsed_json)
                validation_issues = validate_json_target(path.name, parsed_json, root)
            except json.JSONDecodeError as exc:
                json_summary = {
                    "type": "invalid_json",
                    "error": str(exc),
                }
                validation_issues = [f"Invalid JSON: {exc}"]

    return FileReport(
        name=path.name,
        path=str(path.relative_to(root)),
        size_bytes=path.stat().st_size,
        modified_at=iso_timestamp(path),
        kind=kind,
        line_count=line_count,
        preview=preview,
        json_summary=json_summary,
        validation_issues=validation_issues,
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
    target_source: str,
    excluded_dirs: set[str] | None = None,
) -> dict[str, Any]:
    all_reports = [item for files in grouped.values() for item in files]
    report_count = len(all_reports)
    matched_names = {item.name for item in all_reports}
    missing_targets = sorted(target for target in targets if target not in matched_names)
    files_with_issues = sorted(
        item.path for item in all_reports if item.validation_issues
    )
    validation_issue_count = sum(
        len(item.validation_issues) for item in all_reports
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_root": str(root.resolve()),
        "targets": targets,
        "target_source": target_source,
        "excluded_directories": sorted(excluded_dirs or set()),
        "matched_file_count": report_count,
        "missing_targets": missing_targets,
        "validation_issue_count": validation_issue_count,
        "files_with_issues": files_with_issues,
        "directories": {
            directory: [item.as_dict() for item in files]
            for directory, files in grouped.items()
        },
    }


def print_summary(output: dict[str, Any]) -> None:
    print(f"Scan root: {output['scan_root']}")
    print(f"Target source: {output['target_source']}")
    print(f"Target filenames: {len(output['targets'])}")
    print(f"Matched files: {output['matched_file_count']}")
    print(f"Validation issues: {output['validation_issue_count']}")

    excluded = output["excluded_directories"]
    if excluded:
        print(f"Excluded directories: {', '.join(excluded)}")

    if output["missing_targets"]:
        print("Missing targets:")
        for target in output["missing_targets"]:
            print(f"  - {target}")

    if output["files_with_issues"]:
        print("Files with validation issues:")
        for path in output["files_with_issues"]:
            print(f"  - {path}")

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
    targets, target_source = resolve_targets(root, args.targets, args.targets_file)
    excluded_dirs = normalize_excluded_dirs(args.exclude_dirs)
    grouped = collect_reports(root, targets, args.preview_lines, excluded_dirs)
    output = build_output(root, targets, grouped, target_source, excluded_dirs)

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

    if args.fail_on_validation_issues and output["validation_issue_count"]:
        print("Failing because validation issues were found.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
