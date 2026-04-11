# Platform Workflow

This repository is now arranged for an internal platform workflow similar to your scheduler or HyperScreen setup.

## Brief workflow

1. Internal user opens the Streamlit app at `app.py`.
2. The app exposes three actions: `Reporting`, `GPU Diagnostics`, and `Self-Check`.
3. When a user clicks a run button, `app.py` calls the matching helper in `app_backend.py`.
4. `app_backend.py` runs the existing repository logic without replacing it:
   - `reporting.py`
   - `gpu_report.py`
   - `self_check.py`
5. Each run writes artifacts into `artifacts/`.
6. The Streamlit app immediately reads the latest JSON and Markdown artifacts and shows them in the UI.
7. Approved users can review results and download artifacts directly from the dashboard.

## Runtime flow

```text
Internal user
  -> Streamlit app (app.py)
  -> backend helper (app_backend.py)
  -> existing job script
     -> reporting.py
     -> gpu_report.py
     -> self_check.py
  -> artifacts/*.json, artifacts/*.md
  -> Streamlit dashboard preview + download
```

## Current operating model

- Access model: private internal use behind your platform access control
- App entrypoint: `streamlit run app.py`
- Platform entrypoint: `Procfile`
- Python runtime: `runtime.txt`
- Streamlit defaults: `.streamlit/config.toml`

## Default artifacts

- `artifacts/reporting_output.json`
- `artifacts/reporting_summary.md`
- `artifacts/gpu_report.json`
- `artifacts/gpu_report.md`
- `artifacts/self_check_summary.json`
- `artifacts/self_check_summary.md`
