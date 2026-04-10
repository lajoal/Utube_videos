# Examples

This folder contains checked-in sample outputs from the reporting workflow, the repository self-check flow, and the GPU diagnostics flow.

Files:
- `reporting_output.sample.json`: successful reporting run in JSON form
- `reporting_summary.sample.md`: successful reporting run in Markdown form
- `reporting_output.fail.sample.json`: failing reporting run in JSON form
- `reporting_summary.fail.sample.md`: failing reporting run in Markdown form
- `gpu_report.sample.json`: successful GPU diagnostics run in JSON form
- `gpu_report.sample.md`: successful GPU diagnostics run in Markdown form
- `self_check_summary.sample.json`: successful self-check run in JSON form
- `self_check_summary.sample.md`: successful self-check run in Markdown form
- `self_check_summary.fail.sample.json`: failing self-check run in JSON form
- `self_check_summary.fail.sample.md`: failing self-check run in Markdown form

Use these files to understand how pass/fail states, GPU readiness, missing targets, validation issues, top-level self-check step results, artifact presence, and per-step timing data appear before running the scripts locally.
