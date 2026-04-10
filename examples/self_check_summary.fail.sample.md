# Self-Check Summary

- Overall status: `FAIL`
- Overall passed: `False`
- Generated at: `2026-04-10T12:15:00+00:00`
- Repository root: `/workspace/Utube_videos`
- Python executable: `python3.11`
- Keep going: `False`
- Skip tests: `False`
- Skip report: `False`
- Selected steps: `2`
- Completed steps: `1`
- Failed steps: `1`
- Skipped steps: `1`
- Exit code: `1`
- JSON summary: `/workspace/Utube_videos/artifacts/self_check_summary.json`
- Markdown summary: `/workspace/Utube_videos/artifacts/self_check_summary.md`
- Reporting JSON: `/workspace/Utube_videos/artifacts/reporting_output.json`
- Reporting Markdown: `/workspace/Utube_videos/artifacts/reporting_summary.md`

## Steps

### `Unit tests`

- Status: `FAILED`
- Exit code: `1`
- Command: `python3.11 -m unittest discover -s tests -p test_*.py -v`

### `Strict reporting`

- Status: `SKIPPED`
- Exit code: `None`
- Command: `python3.11 reporting.py --fail-on-missing --fail-on-validation-issues --output artifacts/reporting_output.json --markdown-output artifacts/reporting_summary.md`
