from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


DEFAULT_REPO = os.environ.get("UTUBE_GITHUB_REPO", os.environ.get("GITHUB_REPOSITORY", ""))
PORTAL_NAME = os.environ.get("UTUBE_PORTAL_NAME", "Utube Videos Portal")
PORTAL_URL = os.environ.get("UTUBE_PORTAL_URL", "")
PLATFORM_NAME = os.environ.get("UTUBE_PLATFORM_NAME", "Internal Platform")
PLATFORM_BRANCH = os.environ.get("UTUBE_PLATFORM_BRANCH", "codex/platform-server")
BASE_DIR = Path(os.environ.get("UTUBE_BASE_DIR", Path(__file__).resolve().parents[1])).resolve()


st.set_page_config(layout="wide", page_title="Portal Info")

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(236, 242, 233, 0.96), transparent 35%),
            linear-gradient(180deg, #f8f4eb 0%, #fcfbf7 42%, #edf4f0 100%);
    }
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .portal-card {
        background: rgba(255, 255, 255, 0.86);
        border: 1px solid rgba(37, 55, 45, 0.12);
        border-radius: 24px;
        padding: 1.35rem 1.5rem;
        box-shadow: 0 18px 45px rgba(37, 55, 45, 0.08);
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="portal-card">
      <h1 style="margin:0;color:#203228;">{PORTAL_NAME}</h1>
      <p style="margin:0.5rem 0 0 0;color:#57635d;line-height:1.6;">
        Live access and reference links for the internal operations portal.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Live address")
    if PORTAL_URL.strip():
        st.success("Portal URL is configured.")
        st.markdown(f"Open portal: [{PORTAL_URL}]({PORTAL_URL})")
        st.code(PORTAL_URL, language="bash")
    else:
        st.warning("Portal URL is not configured yet.")
        st.caption("Set UTUBE_PORTAL_URL in the platform environment so the live address appears here.")

    st.subheader("Platform")
    st.markdown(f"- Platform: `{PLATFORM_NAME}`")
    st.markdown(f"- Branch: `{PLATFORM_BRANCH}`")
    st.markdown(f"- Base directory: `{BASE_DIR}`")

with right_col:
    st.subheader("Repository links")
    if DEFAULT_REPO.strip():
        repo_url = f"https://github.com/{DEFAULT_REPO}"
        branch_url = f"{repo_url}/tree/{PLATFORM_BRANCH}"
        st.markdown(f"- Repository: [{DEFAULT_REPO}]({repo_url})")
        st.markdown(f"- Active branch: [{PLATFORM_BRANCH}]({branch_url})")
        st.markdown(f"- App entry: [{branch_url}/app.py]({branch_url}/app.py)")
    else:
        st.caption("UTUBE_GITHUB_REPO or GITHUB_REPOSITORY is not configured.")

    st.subheader("Suggested environment variables")
    st.code(
        "\n".join(
            [
                "UTUBE_PORTAL_NAME=Utube Videos Portal",
                "UTUBE_PLATFORM_NAME=Internal Platform",
                "UTUBE_PLATFORM_BRANCH=codex/platform-server",
                "UTUBE_PORTAL_URL=https://your-live-portal-url",
                "UTUBE_GITHUB_REPO=owner/name",
            ]
        ),
        language="bash",
    )
