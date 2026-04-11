from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import github_issue_digest


DEFAULT_TEMPLATE_ANALYSIS_OUTPUT = "artifacts/template_issue_digest.json"
DEFAULT_TEMPLATE_ANALYSIS_MARKDOWN_OUTPUT = "artifacts/template_issue_digest.md"
DEFAULT_TEMPLATE_REF = "main"


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parent


def resolve_output_path(repo_root: Path, output_path: str | None, default_value: str) -> Path:
    return github_issue_digest.resolve_output_path(repo_root, output_path, default_value)


def parse_github_template_url(template_url: str) -> dict[str, str]:
    parsed = urlparse(template_url.strip())
    host = parsed.netloc.lower()
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]

    if host in {"github.com", "www.github.com"}:
        if len(path_parts) < 5 or path_parts[2] != "blob":
            raise ValueError(
                "GitHub blob URLs must look like https://github.com/owner/repo/blob/ref/path/to/file.md"
            )
        return {
            "repo_full_name": f"{path_parts[0]}/{path_parts[1]}",
            "ref": path_parts[3],
            "path": "/".join(path_parts[4:]),
            "url": template_url.strip(),
        }

    if host == "raw.githubusercontent.com":
        if len(path_parts) < 4:
            raise ValueError(
                "Raw GitHub URLs must look like https://raw.githubusercontent.com/owner/repo/ref/path/to/file.md"
            )
        return {
            "repo_full_name": f"{path_parts[0]}/{path_parts[1]}",
            "ref": path_parts[2],
            "path": "/".join(path_parts[3:]),
            "url": template_url.strip(),
        }

    raise ValueError("Template URL must be a github.com or raw.githubusercontent.com file URL.")


def resolve_template_source(
    *,
    template_url: str | None = None,
    template_repo_full_name: str | None = None,
    template_path: str | None = None,
    template_ref: str = DEFAULT_TEMPLATE_REF,
) -> dict[str, str] | None:
    if template_url and template_url.strip():
        return parse_github_template_url(template_url)

    if template_path and template_path.strip():
        return {
            "repo_full_name": github_issue_digest.resolve_repo_full_name(
                template_repo_full_name
            ),
            "ref": template_ref.strip() or DEFAULT_TEMPLATE_REF,
            "path": template_path.strip(),
            "url": "",
        }

    return None


def fetch_github_file_text(
    repo_full_name: str,
    path: str,
    *,
    ref: str = DEFAULT_TEMPLATE_REF,
    token: str | None = None,
) -> str:
    normalized_path = "/".join(quote(part, safe="") for part in path.strip("/").split("/"))
    response = github_issue_digest.github_api_get_json(
        f"{github_issue_digest.GITHUB_API_BASE_URL}/repos/{repo_full_name}/contents/{normalized_path}",
        token=token,
        params={"ref": ref},
    )
    if not isinstance(response, dict) or response.get("type") != "file":
        raise RuntimeError("Template source did not resolve to a GitHub file.")

    if response.get("encoding") != "base64" or not isinstance(response.get("content"), str):
        raise RuntimeError("Template file content could not be decoded from GitHub.")

    return base64.b64decode(response["content"]).decode("utf-8")


def build_issue_bullets(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "- No matching issues were found."

    lines: list[str] = []
    for issue in issues:
        labels = ", ".join(issue.get("labels") or []) or "None"
        lines.append(
            f"- [#{issue['number']} {issue['title']}]({issue['html_url']}) | "
            f"updated `{issue['updated_at']}` | labels `{labels}`"
        )
    return "\n".join(lines)


def build_issue_sections(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "No matching issues were found."

    lines: list[str] = []
    for issue in issues:
        lines.append(f"### #{issue['number']} {issue['title']}")
        lines.append("")
        lines.append(f"- Link: {issue['html_url']}")
        lines.append(f"- State: {issue['state']}")
        lines.append(f"- Author: {issue['author']}")
        lines.append(f"- Updated at: {issue['updated_at']}")
        lines.append(f"- Comments: {issue['comments']}")
        labels = ", ".join(issue.get("labels") or []) or "None"
        assignees = ", ".join(issue.get("assignees") or []) or "None"
        lines.append(f"- Labels: {labels}")
        lines.append(f"- Assignees: {assignees}")
        preview = issue.get("body_preview")
        if preview:
            lines.append(f"- Summary: {preview}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_template_context(report: dict[str, Any]) -> dict[str, str]:
    top_labels = report.get("top_labels") or []
    top_labels_text = ", ".join(
        f"{item['name']} ({item['count']})" for item in top_labels
    ) or "None"

    return {
        "generated_at": str(report.get("generated_at", "")),
        "repo_full_name": str(report.get("repo_full_name", "")),
        "state": str(report.get("state", "")),
        "requested_limit": str(report.get("requested_limit", "")),
        "issue_count": str(report.get("issue_count", 0)),
        "top_labels_text": top_labels_text,
        "issue_bullets": build_issue_bullets(report.get("issues") or []),
        "issue_sections": build_issue_sections(report.get("issues") or []),
        "default_digest_markdown": github_issue_digest.build_issue_digest_markdown(report).rstrip(),
        "issues_json": json.dumps(report.get("issues") or [], indent=2, ensure_ascii=False),
    }


def render_template(template_text: str, context: dict[str, str]) -> str:
    rendered = template_text
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered.rstrip() + "\n"


def write_template_outputs(
    output_path: Path,
    markdown_output_path: Path,
    report: dict[str, Any],
    rendered_markdown: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(rendered_markdown, encoding="utf-8")


def run_template_issue_analysis_job(
    repo_root: Path,
    *,
    repo_full_name: str | None = None,
    token: str | None = None,
    state: str = "open",
    limit: int = github_issue_digest.DEFAULT_ISSUE_LIMIT,
    template_url: str | None = None,
    template_repo_full_name: str | None = None,
    template_path: str | None = None,
    template_ref: str = DEFAULT_TEMPLATE_REF,
    output: str | None = None,
    markdown_output: str | None = None,
) -> dict[str, Any]:
    resolved_repo = github_issue_digest.resolve_repo_full_name(repo_full_name)
    resolved_token = github_issue_digest.resolve_github_token(token)
    output_path = resolve_output_path(repo_root, output, DEFAULT_TEMPLATE_ANALYSIS_OUTPUT)
    markdown_output_path = resolve_output_path(
        repo_root,
        markdown_output,
        DEFAULT_TEMPLATE_ANALYSIS_MARKDOWN_OUTPUT,
    )

    issues = github_issue_digest.fetch_recent_issues(
        resolved_repo,
        token=resolved_token,
        state=state,
        limit=limit,
    )
    report = github_issue_digest.build_issue_digest_report(
        resolved_repo,
        state=state,
        limit=limit,
        issues=issues,
    )

    template_source = resolve_template_source(
        template_url=template_url,
        template_repo_full_name=template_repo_full_name,
        template_path=template_path,
        template_ref=template_ref,
    )
    context = build_template_context(report)

    if template_source is None:
        rendered_markdown = context["default_digest_markdown"] + "\n"
    else:
        template_text = fetch_github_file_text(
            template_source["repo_full_name"],
            template_source["path"],
            ref=template_source["ref"],
            token=resolved_token,
        )
        rendered_markdown = render_template(template_text, context)

    analysis_report = dict(report)
    analysis_report["template_used"] = template_source is not None
    analysis_report["template_source"] = template_source
    analysis_report["template_placeholders"] = sorted(context.keys())
    analysis_report["json_report_path"] = str(output_path)
    analysis_report["markdown_summary_path"] = str(markdown_output_path)
    write_template_outputs(output_path, markdown_output_path, analysis_report, rendered_markdown)

    return {
        "operation": "template_issue_analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": 0,
        "overall_status": "ok" if issues else "empty",
        "overall_passed": True,
        "report": analysis_report,
    }
