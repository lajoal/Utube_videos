from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


DEFAULT_REPO = os.environ.get("UTUBE_GITHUB_REPO", os.environ.get("GITHUB_REPOSITORY", ""))
PORTAL_NAME = os.environ.get("UTUBE_PORTAL_NAME", "Utube Videos Portal")
PORTAL_URL_FALLBACK = os.environ.get("UTUBE_PORTAL_URL", "")
PLATFORM_NAME = os.environ.get("UTUBE_PLATFORM_NAME", "Internal Platform")
PLATFORM_BRANCH = os.environ.get("UTUBE_PLATFORM_BRANCH", "codex/platform-server")
BASE_DIR = Path(os.environ.get("UTUBE_BASE_DIR", Path(__file__).resolve().parents[1])).resolve()


st.set_page_config(layout="wide", page_title="Live Portal")

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


def detect_live_url() -> tuple[str, str]:
    context = getattr(st, "context", None)
    current_url = getattr(context, "url", "") if context is not None else ""
    if isinstance(current_url, str) and current_url.strip():
        return current_url.strip(), "auto"
    if PORTAL_URL_FALLBACK.strip():
        return PORTAL_URL_FALLBACK.strip(), "env"
    return "", "missing"


live_url, source = detect_live_url()

st.markdown(
    f"""
    <div class="portal-card">
      <h1 style="margin:0;color:#203228;">{PORTAL_NAME}</h1>
      <p style="margin:0.5rem 0 0 0;color:#57635d;line-height:1.6;">
        Scheduler or HyperScreen style live portal landing page. When deployed, this page can show the
        current app address automatically and link internal users to the active operational pages.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Live portal address")
    if live_url:
        if source == "auto":
            st.success("Detected current portal address from the running Streamlit session.")
        else:
            st.info("Using UTUBE_PORTAL_URL fallback from the environment.")
        st.markdown(f"Open portal: [{live_url}]({live_url})")
        st.code(live_url, language="bash")
    else:
        st.warning("Live portal address is not available yet.")
        st.caption(
            "After deployment, this page can read the current address automatically when Streamlit session context is available."
        )
        st.caption(
            "If your platform does not expose session URL data, set UTUBE_PORTAL_URL as a fallback."
        )

    st.subheader("Platform")
    st.markdown(f"- Platform: `{PLATFORM_NAME}`")
    st.markdown(f"- Branch: `{PLATFORM_BRANCH}`")
    st.markdown(f"- Base directory: `{BASE_DIR}`")

with right_col:
    st.subheader("Quick navigation")
    st.page_link("app.py", label="Operations Dashboard")
    st.page_link("pages/Latest_Issues.py", label="Latest Issues")
    st.page_link("pages/GitHub_Template_Analysis.py", label="GitHub Template Analysis")
    st.page_link("pages/Portal_Info.py", label="Portal Info")

    st.subheader("Repository links")
    if DEFAULT_REPO.strip():
        repo_url = f"https://github.com/{DEFAULT_REPO}"
        branch_url = f"{repo_url}/tree/{PLATFORM_BRANCH}"
        st.markdown(f"- Repository: [{DEFAULT_REPO}]({repo_url})")
        st.markdown(f"- Active branch: [{PLATFORM_BRANCH}]({branch_url})")
    else:
        st.caption("UTUBE_GITHUB_REPO or GITHUB_REPOSITORY is not configured.")

    st.subheader("Environment summary")
    st.code(
        "\n".join(
            [
                f"UTUBE_PLATFORM_NAME={PLATFORM_NAME}",
                f"UTUBE_PLATFORM_BRANCH={PLATFORM_BRANCH}",
                f"UTUBE_GITHUB_REPO={DEFAULT_REPO or 'owner/name'}",
                f"UTUBE_PORTAL_URL={PORTAL_URL_FALLBACK or 'https://your-live-portal-url'}",
            ]
        ),
        language="bash",
    )
