from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

import app_backend


BASE_DIR = Path(os.environ.get("UTUBE_BASE_DIR", app_backend.repo_root_from_file())).resolve()
APP_PYTHON = os.environ.get("UTUBE_PYTHON", sys.executable)


st.set_page_config(layout="wide", page_title="Operations Dashboard")

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(212, 228, 218, 0.95), transparent 35%),
            linear-gradient(180deg, #f6f3ea 0%, #faf8f2 42%, #eef3ef 100%);
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .hero-card {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(36, 55, 46, 0.12);
        border-radius: 24px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 18px 45px rgba(36, 55, 46, 0.08);
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
      <h1 style="margin:0;color:#21362b;">Utube Videos Control Room</h1>
      <p style="margin:0.55rem 0 0 0;color:#4f5d56;line-height:1.6;">
        Internal operations dashboard for reporting, GPU diagnostics, and repository self-check flows.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_markdown_preview(path: Path, label: str) -> None:
    markdown_text = app_backend.read_text_artifact(path)
    if markdown_text is None:
        st.caption(f"{label} has not been generated yet.")
        return
    st.code(markdown_text, language="markdown")


with st.sidebar:
    st.subheader("Runtime")
    st.code(str(BASE_DIR), language="bash")
    st.caption("Repository root")
    st.code(APP_PYTHON, language="bash")
    st.caption("Python executable")

reporting_tab, gpu_tab, self_check_tab, artifacts_tab = st.tabs(
    ["Reporting", "GPU Diagnostics", "Self-Check", "Artifacts"]
)

with reporting_tab:
    left_col, right_col = st.columns([1, 1.1])
    with left_col:
        with st.form("reporting_form"):
            targets_text = st.text_input("Targets (comma-separated, optional)")
            targets_file = st.text_input("Targets file (optional)")
            preview_lines = st.number_input("Preview lines", min_value=1, max_value=20, value=3)
            fail_on_missing = st.checkbox("Fail on missing targets")
            fail_on_validation_issues = st.checkbox("Fail on validation issues")
            submitted = st.form_submit_button("Run reporting", use_container_width=True)

        if submitted:
            targets = [item.strip() for item in targets_text.split(",") if item.strip()] or None
            with st.spinner("Running reporting..."):
                st.session_state["reporting_result"] = app_backend.run_reporting_job(
                    BASE_DIR,
                    targets=targets,
                    targets_file=targets_file or None,
                    preview_lines=int(preview_lines),
                    fail_on_missing=fail_on_missing,
                    fail_on_validation_issues=fail_on_validation_issues,
                )

        result = st.session_state.get("reporting_result")
        if result:
            st.metric("Reporting status", str(result["overall_status"]).upper())
            st.json(result["report"])

    with right_col:
        st.subheader("Latest reporting summary")
        render_markdown_preview(
            app_backend.default_artifact_paths(BASE_DIR)["reporting_markdown"],
            "Reporting summary",
        )

with gpu_tab:
    left_col, right_col = st.columns([1, 1.1])
    with left_col:
        with st.form("gpu_form"):
            require_cuda = st.checkbox("Require CUDA")
            require_nvenc = st.checkbox("Require NVENC")
            submitted = st.form_submit_button("Run GPU diagnostics", use_container_width=True)

        if submitted:
            with st.spinner("Collecting GPU diagnostics..."):
                st.session_state["gpu_result"] = app_backend.run_gpu_job(
                    BASE_DIR,
                    python_executable=APP_PYTHON,
                    require_cuda=require_cuda,
                    require_nvenc=require_nvenc,
                )

        result = st.session_state.get("gpu_result")
        if result:
            st.metric("GPU status", str(result["overall_status"]).upper())
            st.json(result["report"])

    with right_col:
        st.subheader("Latest GPU summary")
        render_markdown_preview(
            app_backend.default_artifact_paths(BASE_DIR)["gpu_markdown"],
            "GPU summary",
        )

with self_check_tab:
    left_col, right_col = st.columns([1, 1.1])
    with left_col:
        with st.form("self_check_form"):
            keep_going = st.checkbox("Keep going after failures", value=True)
            skip_tests = st.checkbox("Skip unit tests")
            skip_gpu = st.checkbox("Skip GPU diagnostics")
            skip_report = st.checkbox("Skip strict reporting")
            require_cuda = st.checkbox("Require CUDA")
            require_nvenc = st.checkbox("Require NVENC")
            submitted = st.form_submit_button("Run self-check", use_container_width=True)

        if submitted:
            with st.spinner("Running self-check..."):
                st.session_state["self_check_result"] = app_backend.run_self_check_job(
                    BASE_DIR,
                    python_executable=APP_PYTHON,
                    keep_going=keep_going,
                    skip_tests=skip_tests,
                    skip_gpu=skip_gpu,
                    skip_report=skip_report,
                    require_cuda=require_cuda,
                    require_nvenc=require_nvenc,
                )

        result = st.session_state.get("self_check_result")
        if result:
            st.metric("Self-check status", str(result["overall_status"]).upper())
            st.json(result["summary"])

    with right_col:
        st.subheader("Latest self-check summary")
        render_markdown_preview(
            app_backend.default_artifact_paths(BASE_DIR)["self_check_markdown"],
            "Self-check summary",
        )

with artifacts_tab:
    st.subheader("Tracked artifacts")
    artifact_paths = app_backend.default_artifact_paths(BASE_DIR)

    for label, artifact_path in artifact_paths.items():
        with st.expander(f"{label}: {artifact_path.name}", expanded=False):
            st.caption(str(artifact_path))
            if not artifact_path.is_file():
                st.warning("Artifact not generated yet.")
                continue

            if artifact_path.suffix.lower() == ".json":
                st.json(json.loads(artifact_path.read_text(encoding="utf-8")))
            else:
                st.code(artifact_path.read_text(encoding="utf-8"), language="markdown")

            st.download_button(
                label=f"Download {artifact_path.name}",
                data=artifact_path.read_bytes(),
                file_name=artifact_path.name,
                mime="application/octet-stream",
                key=f"download_{label}",
            )
