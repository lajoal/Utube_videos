# Utube_videos

Seed workspace for a Korean video production flow.

## Included files
- `reporting.py`
- `reporting_targets.txt`
- `config/targets.txt.example`
- `docs/reporting-workflow.md`
- `schemas/reporting_output.schema.json`
- `examples/reporting_output.sample.json`
- `examples/reporting_summary.sample.md`
- `examples/reporting_output.fail.sample.json`
- `examples/reporting_summary.fail.sample.md`
- `image_generation_prompts_ko.txt`
- `tts_script_ko.txt`
- `scene_prompts.json`
- `render_plan.json`
- `tests/test_reporting.py`
- `.github/workflows/test.yml`
- `Makefile`

## Usage
Run the reporting script from the repository root:

```bash
python reporting.py
```

This writes both `reporting_output.json` and `reporting_summary.md`.

By default, the script loads its target filenames from `reporting_targets.txt`. If that file is missing, it falls back to the built-in default list in `reporting.py`.

For automation and CI, fail the run when one or more targets are missing or when validation issues are found:

```bash
python reporting.py --fail-on-missing --fail-on-validation-issues
```

You can also load targets from another file and write the JSON report and Markdown summary to custom locations:

```bash
python reporting.py \
  --targets-file config/targets.txt \
  --output artifacts/report.json \
  --markdown-output artifacts/report.md
```

The generated outputs include the resolved target list, the `target_source` used for that run, per-file validation issues, `overall_status` / `overall_passed`, and a `cross_validation_issue_count` for file-to-file checks. The Markdown summary is meant for quick human review, while the JSON report is better suited for automation.

## Validation rules
The reporting flow validates more than file existence.
- `image_generation_prompts_ko.txt`: must be non-empty, include scene labels such as `[scene_01_intro]`, and cross-validate those labels against the `scene_id` list in `scene_prompts.json`
- `tts_script_ko.txt`: must be non-empty, use scene labels such as `[scene_01_intro]`, cross-validate label order and coverage against `scene_prompts.json`, and apply a simple narration-density heuristic based on each scene duration
- `scene_prompts.json`: checks project metadata, scene structure, positive durations, and unique `scene_id` values
- `render_plan.json`: checks render metadata, referenced asset files, timeline structure, positive durations, contiguous `start_seconds`, and cross-validates `scene_id` order and durations against `scene_prompts.json`

The scanner skips common cache and virtual environment directories by default:
- `.git`
- `.mypy_cache`
- `.pytest_cache`
- `.venv`
- `__pycache__`
- `venv`

Add more exclusions with repeated `--exclude-dir` flags.

## Convenience commands
If you use `make`, the repository includes a few shortcuts:

```bash
make report
make report-strict
make test
make check
```

`make report-strict` writes both `artifacts/reporting_output.json` and `artifacts/reporting_summary.md`.

## Docs
Detailed reporting behavior and examples live here:
- `docs/reporting-workflow.md`
- `config/targets.txt.example`
- `schemas/reporting_output.schema.json`
- `examples/reporting_output.sample.json`
- `examples/reporting_summary.sample.md`
- `examples/reporting_output.fail.sample.json`
- `examples/reporting_summary.fail.sample.md`

## Testing
Run the built-in unit tests from the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub Actions runs the test suite, performs a strict reporting smoke check, publishes the Markdown summary into the workflow summary UI, and uploads the generated `artifacts/` directory as a workflow artifact on pushes to `main` and on pull requests.
