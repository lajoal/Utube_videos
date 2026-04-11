from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_ISSUES_OUTPUT = "artifacts/latest_issues.json"
DEFAULT_ISSUES_MARKDOWN_OUTPUT = "artifacts/latest_issues.md"
DEFAULT_ISSUE_LIMIT = 10
GITHUB_API_BASE_URL = "https://api.github.com"


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parent


def resolve_output_path(repo_root: Path, output_path: str | None, default_value: str) -> Path:
    raw_value = default_value if output_path is None or not str(output_path).strip() else output_path
    path = Path(raw_value)
    if not path.is_absolute():
        path = repo_root / path
    return path


def resolve_repo_full_name(repo_full_name: str | None = None) -> str:
    candidate = (
        repo_full_name
        or os.environ.get("UTUBE_GITHUB_REPO")
        or os.environ.get("GITHUB_REPOSITORY")
    )
    if not candidate:
        raise ValueError(
            "GitHub repository is not configured. Set UTUBE_GITHUB_REPO or provide owner/name in the app."
        )
    value = candidate.strip()
    if "/" not in value or value.startswith("/") or value.endswith("/"):
        raise ValueError("GitHub repository must use 'owner/name' format.")
    return value


def resolve_github_token(token: str | None = None) -> str | None:
    return token or os.environ.get("UTUBE_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")


def truncate_text(text: str | None, limit: int = 280) -> str | None:
    if text is None:
        return None
    compact = " ".join(text.split())
    if not compact:
        return None
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def github_api_get_json(
    url: str,
    *,
    token: str | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    if params:
        url = f"{url}?{urlencode(params)}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "UtubeVideosInternalDashboard",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed with {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc}") from exc


def normalize_issue_record(issue: dict[str, Any]) -> dict[str, Any]:
    labels = [
        label.get("name")
        for label in issue.get("labels", [])
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    ]
    assignees = [
        assignee.get("login")
        for assignee in issue.get("assignees", [])
        if isinstance(assignee, dict) and isinstance(assignee.get("login"), str)
    ]
    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "html_url": issue.get("html_url"),
        "author": (issue.get("user") or {}).get("login"),
        "labels": labels,
        "assignees": assignees,
        "comments": issue.get("comments", 0),
        "body_preview": truncate_text(issue.get("body")),
    }


def fetch_recent_issues(
    repo_full_name: str,
    *,
    token: str | None = None,
    state: str = "open",
    limit: int = DEFAULT_ISSUE_LIMIT,
) -> list[dict[str, Any]]:
    raw_items = github_api_get_json(
        f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/issues",
        token=token,
        params={
            "state": state,
            "sort": "updated",
            "direction": "desc",
            "per_page": min(max(limit, 1), 100),
        },
    )
    if not isinstance(raw_items, list):
        raise RuntimeError("GitHub API returned an unexpected response for issues.")

    issues: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        if "pull_request" in item:
            continue
        issues.append(normalize_issue_record(item))
        if len(issues) >= limit:
            break
    return issues


def build_issue_digest_report(
    repo_full_name: str,
    *,
    state: str,
    limit: int,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    label_counter = Counter()
    for issue in issues:
        label_counter.update(issue.get("labels", []))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_full_name": repo_full_name,
        "state": state,
        "requested_limit": limit,
        "issue_count": len(issues),
        "top_labels": [
            {"name": name, "count": count}
            for name, count in label_counter.most_common(5)
        ],
        "issues": issues,
    }


def build_issue_digest_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Latest Issues Digest",
        "",
        f"- Repository: `{report['repo_full_name']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- State filter: `{report['state']}`",
        f"- Requested limit: `{report['requested_limit']}`",
        f"- Issue count: `{report['issue_count']}`",
    ]

    top_labels = report.get("top_labels", [])
    if top_labels:
        lines.append(
            "- Top labels: `"
            + ", ".join(f"{item['name']} ({item['count']})" for item in top_labels)
            + "`"
        )
    else:
        lines.append("- Top labels: `None`")

    lines.extend(["", "## Issues", ""])

    issues = report.get("issues", [])
    if not issues:
        lines.append("- No matching issues were found.")
        return "\n".join(lines).rstrip() + "\n"

    for issue in issues:
        lines.append(f"### `#{issue['number']} {issue['title']}`")
        lines.append("")
        lines.append(f"- State: `{issue['state']}`")
        lines.append(f"- Author: `{issue['author']}`")
        lines.append(f"- Updated at: `{issue['updated_at']}`")
        lines.append(f"- Comments: `{issue['comments']}`")
        labels = issue.get("labels") or []
        assignees = issue.get("assignees") or []
        lines.append(f"- Labels: `{', '.join(labels) if labels else 'None'}`")
        lines.append(f"- Assignees: `{', '.join(assignees) if assignees else 'None'}`")
        lines.append(f"- URL: `{issue['html_url']}`")
        preview = issue.get("body_preview")
        if preview:
            lines.append(f"- Summary: {preview}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_issue_outputs(
    output_path: Path,
    markdown_output_path: Path,
    report: dict[str, Any],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(
        build_issue_digest_markdown(report),
        encoding="utf-8",
    )


def run_issue_digest_job(
    repo_root: Path,
    *,
    repo_full_name: str | None = None,
    token: str | None = None,
    state: str = "open",
    limit: int = DEFAULT_ISSUE_LIMIT,
    output: str | None = None,
    markdown_output: str | None = None,
) -> dict[str, Any]:
    resolved_repo = resolve_repo_full_name(repo_full_name)
    resolved_token = resolve_github_token(token)
    output_path = resolve_output_path(repo_root, output, DEFAULT_ISSUES_OUTPUT)
    markdown_output_path = resolve_output_path(
        repo_root,
        markdown_output,
        DEFAULT_ISSUES_MARKDOWN_OUTPUT,
    )

    issues = fetch_recent_issues(
        resolved_repo,
        token=resolved_token,
        state=state,
        limit=limit,
    )
    report = build_issue_digest_report(
        resolved_repo,
        state=state,
        limit=limit,
        issues=issues,
    )
    report["json_report_path"] = str(output_path)
    report["markdown_summary_path"] = str(markdown_output_path)
    write_issue_outputs(output_path, markdown_output_path, report)

    return {
        "operation": "issue_digest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": 0,
        "overall_status": "ok" if issues else "empty",
        "overall_passed": True,
        "report": report,
    }
