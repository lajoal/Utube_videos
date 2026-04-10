# Self-Check Summary

- Overall status: `PASS`
- Overall passed: `True`
- Generated at: `2026-04-10T12:10:05.300000+00:00`
- Started at: `2026-04-10T12:10:00+00:00`
- Finished at: `2026-04-10T12:10:05.300000+00:00`
- Duration seconds: `5.3`
- Repository root: `/workspace/Utube_videos`
- Python executable: `python3.11`
- Keep going: `True`
- Skip tests: `False`
- Skip GPU: `False`
- Skip report: `False`
- Require CUDA: `False`
- Require NVENC: `False`
- Selected steps: `3`
- Completed steps: `3`
- Failed steps: `0`
- Skipped steps: `0`
- Passed step labels: `Unit tests, GPU diagnostics, Strict reporting`
- Failed step labels: `None`
- Skipped step labels: `None`
- Present artifacts: `reporting_json, reporting_markdown, gpu_json, gpu_markdown, self_check_json, self_check_markdown`
- Missing artifacts: `None`
- Present artifact count: `6`
- Missing artifact count: `0`
- Artifact size total: `16660`
- Exit code: `0`
- JSON summary: `/workspace/Utube_videos/artifacts/self_check_summary.json`
- Markdown summary: `/workspace/Utube_videos/artifacts/self_check_summary.md`
- GPU JSON: `/workspace/Utube_videos/artifacts/gpu_report.json`
- GPU JSON exists: `True`
- GPU Markdown: `/workspace/Utube_videos/artifacts/gpu_report.md`
- GPU Markdown exists: `True`
- Reporting JSON: `/workspace/Utube_videos/artifacts/reporting_output.json`
- Reporting JSON exists: `True`
- Reporting Markdown: `/workspace/Utube_videos/artifacts/reporting_summary.md`
- Reporting Markdown exists: `True`

## Artifacts

- `reporting_json`: exists=`True`, size_bytes=`3180`, path=`/workspace/Utube_videos/artifacts/reporting_output.json`
- `reporting_markdown`: exists=`True`, size_bytes=`1540`, path=`/workspace/Utube_videos/artifacts/reporting_summary.md`
- `gpu_json`: exists=`True`, size_bytes=`2190`, path=`/workspace/Utube_videos/artifacts/gpu_report.json`
- `gpu_markdown`: exists=`True`, size_bytes=`980`, path=`/workspace/Utube_videos/artifacts/gpu_report.md`
- `self_check_json`: exists=`True`, size_bytes=`6120`, path=`/workspace/Utube_videos/artifacts/self_check_summary.json`
- `self_check_markdown`: exists=`True`, size_bytes=`2650`, path=`/workspace/Utube_videos/artifacts/self_check_summary.md`

## Steps

### `Unit tests`

- Status: `PASSED`
- Exit code: `0`
- Started at: `2026-04-10T12:10:00+00:00`
- Finished at: `2026-04-10T12:10:03+00:00`
- Duration seconds: `3.0`
- Command: `python3.11 -m unittest discover -s tests -p test_*.py -v`

### `GPU diagnostics`

- Status: `PASSED`
- Exit code: `0`
- Started at: `2026-04-10T12:10:03+00:00`
- Finished at: `2026-04-10T12:10:04.100000+00:00`
- Duration seconds: `1.1`
- Command: `python3.11 gpu_report.py --output artifacts/gpu_report.json --markdown-output artifacts/gpu_report.md`

### `Strict reporting`

- Status: `PASSED`
- Exit code: `0`
- Started at: `2026-04-10T12:10:04.100000+00:00`
- Finished at: `2026-04-10T12:10:05.300000+00:00`
- Duration seconds: `1.2`
- Command: `python3.11 reporting.py --fail-on-missing --fail-on-validation-issues --output artifacts/reporting_output.json --markdown-output artifacts/reporting_summary.md`
