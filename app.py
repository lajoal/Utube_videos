from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


PORTAL_NAME = os.environ.get("UTUBE_PORTAL_NAME", "Utube Videos Portal")
PLATFORM_NAME = os.environ.get("UTUBE_PLATFORM_NAME", "Internal Platform")
PLATFORM_BRANCH = os.environ.get("UTUBE_PLATFORM_BRANCH", "codex/portal-root")
DEFAULT_REPO = os.environ.get("UTUBE_GITHUB_REPO", os.environ.get("GITHUB_REPOSITORY", ""))
PORTAL_URL_FALLBACK = os.environ.get("UTUBE_PORTAL_URL", "")
BASE_DIR = Path(os.environ.get("UTUBE_BASE_DIR", Path(__file__).resolve().parent)).resolve()


st.set_page_config(layout="wide", page_title=PORTAL_NAME)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(235, 243, 233, 0.96), transparent 35%),
            linear-gradient(180deg, #f7f3e9 0%, #fbfaf6 44%, #edf4f0 100%);
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .hero-card {
        background: rgba(255, 255, 255, 0.86);
        border: 1px solid rgba(34, 53, 44, 0.12);
        border-radius: 28px;
        padding: 1.5rem 1.7rem;
        box-shadow: 0 18px 45px rgba(34, 53, 44, 0.08);
        margin-bottom: 1rem;
    }
    .kicker {
        color: #6d756f;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .hero-title {
        color: #203228;
        font-size: 2.25rem;
        font-weight: 800;
        margin: 0;
    }
    .hero-copy {
        color: #58655d;
        margin-top: 0.55rem;
        margin-bottom: 0;
        line-height: 1.65;
    }
    .feature-card {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(34, 53, 44, 0.10);
        border-radius: 22px;
        padding: 1rem 1.1rem;
        min-height: 180px;
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
    <div class="hero-card">
      <div class="kicker">Portal Home</div>
      <h1 class="hero-title">{PORTAL_NAME}</h1>
      <p class="hero-copy">
        Scheduler or HyperScreen style root portal. Approved users arrive here first, then move into
        the operations dashboard, latest issue watch page, and GitHub template-based analysis tools.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

status_col1, status_col2, status_col3 = st.columns(3)
status_col1.metric("Platform", PLATFORM_NAME)
status_col2.metric("Branch", PLATFORM_BRANCH)
status_col3.metric("Repository", DEFAULT_REPO or "Not set")

left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Live portal address")
    if live_url:
        if source == "auto":
            st.success("The live address was detected from the running Streamlit session.")
        else:
            st.info("Using UTUBE_PORTAL_URL from the environment as the portal address.")
        st.markdown(f"Open portal: [{live_url}]({live_url})")
        st.code(live_url, language="bash")
    else:
        st.warning("The live portal address is not available yet.")
        st.caption(
            "Once deployed, this root page can usually detect the current address automatically."
        )
        st.caption(
            "If your platform does not expose the current URL, set UTUBE_PORTAL_URL as a fallback."
        )

    st.subheader("Portal navigation")
    st.page_link("pages/Operations_Dashboard.py", label="Operations Dashboard")
    st.page_link("pages/Latest_Issues.py", label="Latest Issues")
    st.page_link("pages/GitHub_Template_Analysis.py", label="GitHub Template Analysis")

with right_col:
    st.subheader("Runtime")
    st.code(str(BASE_DIR), language="bash")
    st.caption("Repository root")

    if DEFAULT_REPO.strip():
        repo_url = f"https://github.com/{DEFAULT_REPO}"
        branch_url = f"{repo_url}/tree/{PLATFORM_BRANCH}"
        st.markdown(f"Repository: [{DEFAULT_REPO}]({repo_url})")
        st.markdown(f"Branch: [{PLATFORM_BRANCH}]({branch_url})")
    else:
        st.caption("Set UTUBE_GITHUB_REPO or GITHUB_REPOSITORY to show repository links.")

feature_col1, feature_col2, feature_col3 = st.columns(3)
with feature_col1:
    st.markdown(
        """
        <div class="feature-card">
          <h3>Operations</h3>
          <p>Run reporting, GPU diagnostics, and self-check jobs from the same internal workspace.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with feature_col2:
    st.markdown(
        """
        <div class="feature-card">
          <h3>Issue Watch</h3>
          <p>Pull the latest GitHub issues, summarize them, and save digest artifacts for the team.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with feature_col3:
    st.markdown(
        """
        <div class="feature-card">
          <h3>Template Analysis</h3>
          <p>Use a template stored on GitHub to render issue analysis even when the file is not on this machine.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.info("This app is intended for you and approved users behind your existing internal platform access controls.")
