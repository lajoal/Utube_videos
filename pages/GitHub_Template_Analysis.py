from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

import github_template_analysis


BASE_DIR = Path(os.environ.get("UTUBE_BASE_DIR", github_template_analysis.repo_root_from_file())).resolve()
DEFAULT_REPO = os.environ.get("UTUBE_GITHUB_REPO", os.environ.get("GITHUB_REPOSITORY", ""))
DEFAULT_TEMPLATE_REPO = DEFAULT_REPO
DEFAULT_TEMPLATE_PATH = "templates/issue_digest_template.md"
DEFAULT_TEMPLATE_REF = os.environ.get("UTUBE_TEMPLATE_REF", "main")
TOKEN_CONFIGURED = bool(
    os.environ.get("UTUBE_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
)


st.set_page_config(layout="wide", page_title="GitHub Template Analysis")

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(230, 240, 229, 0.95), transparent 35%),
            linear-gradient(180deg, #f7f4ec 0%, #fbfaf5 45%, #eef5f1 100%);
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .template-hero {
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid rgba(36, 56, 46, 0.12);
        border-radius: 24px;
        padding: 1.3rem 1.5rem;
        box-shadow: 0 18px 45px rgba(36, 56, 46, 0.08);
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="template-hero">
      <h1 style="margin:0;color:#203228;">GitHub Template Analysis</h1>
      <p style="margin:0.5rem 0 0 0;color:#55625b;line-height:1.6;">
        Analyze GitHub issues using a template file that lives on GitHub. The template does not need
        to exist on this computer as long as it is accessible in a GitHub repository.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("GitHub integration")
    st.code(DEFAULT_REPO or "Not set", language="bash")
    st.caption("Default issue repository")
    st.caption(f"GitHub token configured: {TOKEN_CONFIGURED}")
    st.caption("If your template or issue repo is private, set UTUBE_GITHUB_TOKEN or GITHUB_TOKEN.")

left_col, right_col = st.columns([1, 1.15])

with left_col:
    with st.form("github_template_analysis_form"):
        st.subheader("Issue source")
        repo_full_name = st.text_input("Repository (owner/name)", value=DEFAULT_REPO)
        state = st.selectbox("Issue state", ["open", "all", "closed"], index=0)
        limit = st.slider("How many issues", min_value=3, max_value=25, value=10)

        st.subheader("Template source on GitHub")
        template_url = st.text_input("Template GitHub URL (optional)")
        template_repo_full_name = st.text_input(
            "Template repository (optional)",
            value=DEFAULT_TEMPLATE_REPO,
        )
        template_path = st.text_input(
            "Template path (optional)",
            value=DEFAULT_TEMPLATE_PATH,
        )
        template_ref = st.text_input("Template ref", value=DEFAULT_TEMPLATE_REF)
        st.caption(
            "If Template GitHub URL is filled, it wins. Otherwise repo/path/ref will be used."
        )
        st.caption(
            "Default sample template: templates/issue_digest_template.md"
        )

        submitted = st.form_submit_button(
            "Run GitHub template analysis",
            use_container_width=True,
        )

    if submitted:
        try:
            with st.spinner("Fetching GitHub issues and remote template..."):
                st.session_state["github_template_analysis_result"] = (
                    github_template_analysis.run_template_issue_analysis_job(
                        BASE_DIR,
                        repo_full_name=repo_full_name or None,
                        state=state,
                        limit=int(limit),
                        template_url=template_url or None,
                        template_repo_full_name=template_repo_full_name or None,
                        template_path=template_path or None,
                        template_ref=template_ref or github_template_analysis.DEFAULT_TEMPLATE_REF,
                    )
                )
        except Exception as exc:
            st.session_state["github_template_analysis_error"] = str(exc)
        else:
            st.session_state.pop("github_template_analysis_error", None)

    if "github_template_analysis_error" in st.session_state:
        st.error(st.session_state["github_template_analysis_error"])

    result = st.session_state.get("github_template_analysis_result")
    if result:
        report = result["report"]
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Status", str(result["overall_status"]).upper())
        metric_col2.metric("Issue count", int(report["issue_count"]))
        metric_col3.metric("Template used", str(report["template_used"]))

        template_source = report.get("template_source")
        if template_source:
            st.caption(
                f"Template source: {template_source['repo_full_name']} @ {template_source['ref']} / {template_source['path']}"
            )
        else:
            st.caption("No GitHub template was provided. Default digest format was used.")

        st.subheader("Analysis report")
        st.json(report)

with right_col:
    st.subheader("Rendered Markdown")
    markdown_path = BASE_DIR / github_template_analysis.DEFAULT_TEMPLATE_ANALYSIS_MARKDOWN_OUTPUT
    json_path = BASE_DIR / github_template_analysis.DEFAULT_TEMPLATE_ANALYSIS_OUTPUT

    if markdown_path.is_file():
        st.code(markdown_path.read_text(encoding="utf-8"), language="markdown")
    else:
        st.caption("Template-based Markdown artifact has not been generated yet.")

    download_col1, download_col2 = st.columns(2)
    if json_path.is_file():
        download_col1.download_button(
            "Download template_issue_digest.json",
            data=json_path.read_bytes(),
            file_name=json_path.name,
            mime="application/json",
        )
    if markdown_path.is_file():
        download_col2.download_button(
            "Download template_issue_digest.md",
            data=markdown_path.read_bytes(),
            file_name=markdown_path.name,
            mime="text/markdown",
        )

    if json_path.is_file():
        st.subheader("Latest JSON artifact")
        st.json(json.loads(json_path.read_text(encoding="utf-8")))
