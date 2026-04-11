from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

import github_issue_digest


BASE_DIR = Path(os.environ.get("UTUBE_BASE_DIR", github_issue_digest.repo_root_from_file())).resolve()
DEFAULT_REPO = os.environ.get("UTUBE_GITHUB_REPO", os.environ.get("GITHUB_REPOSITORY", ""))
TOKEN_CONFIGURED = bool(
    os.environ.get("UTUBE_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
)


st.set_page_config(layout="wide", page_title="Latest Issues")

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(237, 244, 230, 0.95), transparent 35%),
            linear-gradient(180deg, #f9f8f1 0%, #fcfbf6 45%, #eef4f1 100%);
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .issue-hero {
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid rgba(45, 61, 53, 0.12);
        border-radius: 24px;
        padding: 1.3rem 1.5rem;
        box-shadow: 0 18px 45px rgba(45, 61, 53, 0.08);
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="issue-hero">
      <h1 style="margin:0;color:#203228;">Latest Issues</h1>
      <p style="margin:0.5rem 0 0 0;color:#55625b;line-height:1.6;">
        Internal GitHub watch page for checking the most recently updated issues and turning them
        into a quick operational digest.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("GitHub source")
    st.code(DEFAULT_REPO or "Not set", language="bash")
    st.caption("Default repository from UTUBE_GITHUB_REPO or GITHUB_REPOSITORY")
    st.caption(f"GitHub token configured: {TOKEN_CONFIGURED}")
    if not TOKEN_CONFIGURED:
        st.info("Public repos can still work without a token, but private repos will need UTUBE_GITHUB_TOKEN or GITHUB_TOKEN.")

left_col, right_col = st.columns([1, 1.15])

with left_col:
    with st.form("latest_issues_form"):
        repo_full_name = st.text_input("Repository (owner/name)", value=DEFAULT_REPO)
        state = st.selectbox("Issue state", ["open", "all", "closed"], index=0)
        limit = st.slider("How many issues", min_value=3, max_value=25, value=10)
        submitted = st.form_submit_button("Fetch latest issues", use_container_width=True)

    if submitted:
        try:
            with st.spinner("Fetching latest issues from GitHub..."):
                st.session_state["latest_issues_result"] = github_issue_digest.run_issue_digest_job(
                    BASE_DIR,
                    repo_full_name=repo_full_name or None,
                    state=state,
                    limit=int(limit),
                )
        except Exception as exc:
            st.session_state["latest_issues_error"] = str(exc)
        else:
            st.session_state.pop("latest_issues_error", None)

    if "latest_issues_error" in st.session_state:
        st.error(st.session_state["latest_issues_error"])

    result = st.session_state.get("latest_issues_result")
    if result:
        report = result["report"]
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Status", str(result["overall_status"]).upper())
        metric_col2.metric("Issue count", int(report["issue_count"]))
        metric_col3.metric("Repo", str(report["repo_full_name"]))

        top_labels = report.get("top_labels", [])
        if top_labels:
            st.caption(
                "Top labels: "
                + ", ".join(f"{item['name']} ({item['count']})" for item in top_labels)
            )

        issues = report.get("issues", [])
        if not issues:
            st.info("No matching issues were found.")
        else:
            for issue in issues:
                with st.expander(f"#{issue['number']} {issue['title']}", expanded=False):
                    meta_col1, meta_col2 = st.columns(2)
                    meta_col1.markdown(f"State: `{issue['state']}`")
                    meta_col1.markdown(f"Author: `{issue['author']}`")
                    meta_col1.markdown(f"Comments: `{issue['comments']}`")
                    meta_col2.markdown(f"Updated: `{issue['updated_at']}`")
                    meta_col2.markdown(
                        f"Labels: `{', '.join(issue['labels']) if issue['labels'] else 'None'}`"
                    )
                    meta_col2.markdown(
                        f"Assignees: `{', '.join(issue['assignees']) if issue['assignees'] else 'None'}`"
                    )
                    st.markdown(f"Issue link: [{issue['html_url']}]({issue['html_url']})")
                    if issue.get("body_preview"):
                        st.write(issue["body_preview"])
                    else:
                        st.caption("본문 미리보기가 없습니다.")

with right_col:
    st.subheader("Latest issue digest artifact")
    markdown_path = BASE_DIR / github_issue_digest.DEFAULT_ISSUES_MARKDOWN_OUTPUT
    json_path = BASE_DIR / github_issue_digest.DEFAULT_ISSUES_OUTPUT

    if markdown_path.is_file():
        st.code(markdown_path.read_text(encoding="utf-8"), language="markdown")
    else:
        st.caption("Issue digest Markdown artifact has not been generated yet.")

    download_col1, download_col2 = st.columns(2)
    if json_path.is_file():
        download_col1.download_button(
            "Download latest_issues.json",
            data=json_path.read_bytes(),
            file_name=json_path.name,
            mime="application/json",
        )
    if markdown_path.is_file():
        download_col2.download_button(
            "Download latest_issues.md",
            data=markdown_path.read_bytes(),
            file_name=markdown_path.name,
            mime="text/markdown",
        )

    if json_path.is_file():
        st.subheader("Latest JSON artifact")
        st.json(json.loads(json_path.read_text(encoding="utf-8")))
