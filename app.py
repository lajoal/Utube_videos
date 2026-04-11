from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

import app_backend


BASE_DIR = Path(os.environ.get("UTUBE_BASE_DIR", app_backend.repo_root_from_file())).resolve()
APP_PYTHON = os.environ.get("UTUBE_PYTHON", sys.executable)


st.set_page_config(layout="wide", page_title="Utube Videos Control Room")

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
    .hero-kicker {
        color: #6b756f;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    .hero-title {
        color: #21362b;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
    }
    .hero-copy {
        color: #4f5d56;
        margin-top: 0.5rem;
        margin-bottom: 0;
        line-height: 1.6;
    }
    .status-chip {
        display: inline-block;
        border-radius: 999px;
        padding: 0.35rem 0.8rem;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .status-pass {
        background: #e7f5eb;
        color: #1f6a43;
    }
    .status-warn {
        background: #fff3dd;
        color: #8a5b12;
    }
    .status-fail {
        background: #fde8e8;
        color: #9b2c2c;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
      <div class="hero-kicker">Internal Operations</div>
      <h1 class="hero-title">Utube Videos Control Room</h1>
      <p class="hero-copy">
        Scheduler or HyperScreen style internal dashboard for running reporting, GPU diagnostics,
        and self-check flows from one place. This app is intended for you and approved users behind
        your existing platform access controls.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def status_class(status: str) -> str:
    normalized = status.lower()
    if normalized in {"pass", "ready"}:
        return "status-pass"
    if normalized in {"limited", "warn", "warning"}:
        return "status-warn"
    return "status-fail"



def render_status(operation: str, payload: dict[str, object], body_key: str) -> None:
    status_value = str(payload.get("overall_status", "unknown")).upper()
    exit_code = payload.get("exit_code")
    st.markdown(
        f'<span class="status-chip {status_class(str(payload.get("overall_status", "fail")))}">'
        f'{operation}: {status_value}</span>',
        unsafe_allow_html=True,
    )
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Exit code", exit_code)
    metric_col2.metric("Overall passed", str(payload.get("overall_passed")))
    metric_col3.metric("Generated at", str(payload.get("generated_at", "-")))
    st.json(payload[body_key])



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
    st.info("No auth layer is built into this repo. Keep it behind your existing platform access rules.")

reporting_tab, gpu_tab, self_check_tab, artifacts_tab = st.tabs(
    ["Reporting", "GPU Diagnostics", "Self-Check", "Artifacts"]
)

with reporting_tab:
    left_col, right_col = st.columns([1, 1.1])
    with left_col:
        with st.form("reporting_form"):
            st.subheader("Reporting run")
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

        if "reporting_result" in st.session_state:
            render_status("Reporting", st.session_state["reporting_result"], "report")

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
            st.subheader("GPU readiness")
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

        if "gpu_result" in st.session_state:
            render_status("GPU", st.session_state["gpu_result"], "report")

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
            st.subheader("Repository self-check")
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

        if "self_check_result" in st.session_state:
            render_status("Self-check", st.session_state["self_check_result"], "summary")

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
