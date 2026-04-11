# Platform App

This repository now supports an internal operations dashboard in the same spirit as your scheduler or HyperScreen setup.

## What it is

- `app.py`: Streamlit dashboard for internal users
- `app_backend.py`: testable backend helpers that call the existing reporting, GPU, and self-check flows
- `Procfile`: platform start command
- `.streamlit/config.toml`: Streamlit defaults for internal hosting

This is intended for you and approved users behind your existing platform access controls. The repository itself does not add an authentication layer.

## Install

```bash
pip install -r requirements.txt
```

## Run locally or on your internal platform

```bash
streamlit run app.py
```

If your platform injects a `PORT` environment variable, the included `Procfile` already uses it.

## Environment variables

- `UTUBE_BASE_DIR`: override the repository root if needed
- `UTUBE_PYTHON`: override the Python executable used for GPU and self-check runs

## What the dashboard can do

- Run the reporting flow and show the latest Markdown summary
- Run GPU diagnostics and show the latest Markdown summary
- Run the repository self-check with optional skip flags and GPU requirements
- View and download the generated artifacts from `artifacts/`

## Artifact defaults

- `artifacts/reporting_output.json`
- `artifacts/reporting_summary.md`
- `artifacts/gpu_report.json`
- `artifacts/gpu_report.md`
- `artifacts/self_check_summary.json`
- `artifacts/self_check_summary.md`
