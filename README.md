# Reporting Workflow

This repository uses `reporting.py` to validate the core video-production artifacts and produce two outputs:

- A machine-friendly JSON report
- A human-friendly Markdown summary

## Default Outputs

Running the script from the repository root without extra arguments creates:

```bash
python reporting.py
```

Generated files:
- `reporting_output.json`
- `reporting_summary.md`

## Repository Self-Check

To run the repository's built-in self-check flow end to end:

```bash
python self_check.py
python self_check.py --keep-going
```

This runs:
- the unit test suite
- the strict reporting pass that writes `artifacts/reporting_output.json`
- the strict reporting Markdown summary at `artifacts/reporting_summary.md`
- a step-by-step self-check summary at `artifacts/self_check_summary.json`
- a human-readable self-check summary at `artifacts/self_check_summary.md`

By default, `self_check.py` stops on the first failing step. `--keep-going` tells it to continue into the strict reporting step even after earlier failures so the diagnostic artifacts are still produced whenever possible.

The self-check summary JSON records which steps were selected, the exact command for each step, whether it passed, failed, or was skipped, and the overall self-check status. The companion Markdown summary presents the same information in a format that is easier to scan in CI and artifacts. Both artifacts now also include workflow-level and per-step timestamps plus duration values. You can move them with `--summary-output` and `--summary-markdown-output`.

The GitHub Actions workflow and `make self-check` both use `python self_check.py --keep-going`.

If the reporting step still exits before writing artifacts, the workflow summary now falls back to `artifacts/self_check_summary.md` so the uploaded artifacts still contain a readable step-by-step failure trail.

## Strict Mode

Strict mode is intended for CI and automation.

```bash
python reporting.py --fail-on-missing --fail-on-validation-issues
```

This returns a non-zero exit code when:
- one or more target files are missing
- one or more validation issues are found

## Artifact Layout

The repository Makefile uses `artifacts/` for strict runs:

```bash
make report-strict
make self-check
```

Generated files:
- `artifacts/reporting_output.json`
- `artifacts/reporting_summary.md`
- `artifacts/self_check_summary.json`
- `artifacts/self_check_summary.md`

## Target Files

The default target list is stored in `reporting_targets.txt`.

If you want a custom manifest, start from:
- `config/targets.txt.example`

Example custom run:

```bash
python reporting.py \
  --targets-file config/targets.txt \
  --output artifacts/report.json \
  --markdown-output artifacts/report.md
```

## Output Schema

The repository documents both machine-readable artifact contracts:
- `schemas/reporting_output.schema.json`
- `schemas/self_check_summary.schema.json`

Use the reporting schema when another tool needs to validate or parse `reporting_output.json` programmatically.
Use the self-check schema when another tool needs to consume `self_check_summary.json` as a top-level pipeline status object with timing data.

## Example Outputs

Sample outputs are checked into the repository here:
- `examples/reporting_output.sample.json`
- `examples/reporting_summary.sample.md`
- `examples/reporting_output.fail.sample.json`
- `examples/reporting_summary.fail.sample.md`
- `examples/self_check_summary.sample.json`
- `examples/self_check_summary.sample.md`
- `examples/self_check_summary.fail.sample.json`
- `examples/self_check_summary.fail.sample.md`

Use the `sample` files to see clean runs and the `fail.sample` files to see how missing targets, validation issues, top-level self-check step failures, and timing data appear in the artifacts.

## What Gets Validated

`image_generation_prompts_ko.txt`
- must not be empty
- must contain scene labels such as `[scene_01_intro]`
- labels are checked against `scene_prompts.json`

`tts_script_ko.txt`
- must not be empty
- should use scene labels for each section
- section order and coverage are checked against `scene_prompts.json`
- narration density is checked against each scene duration

`scene_prompts.json`
- project metadata must exist
- scenes must have valid `scene_id`, title, duration, prompt, and narration values
- duplicate `scene_id` values are rejected

`render_plan.json`
- referenced files must exist
- timeline entries must be valid and contiguous
- scene order and durations are checked against `scene_prompts.json`

## Reading The Results

Useful top-level JSON fields:
- `overall_status`
- `overall_passed`
- `missing_targets`
- `validation_issue_count`
- `cross_validation_issue_count`
- `files_with_issues`

The reporting Markdown summary is best for artifact quality review.
The self-check Markdown summary is best for understanding which top-level verification step failed before the reporting layer completed.
The self-check JSON summary is best for machine-readable orchestration, debugging, and runtime analysis.
