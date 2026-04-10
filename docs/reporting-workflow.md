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
```

This runs:
- the unit test suite
- the strict reporting pass that writes `artifacts/reporting_output.json`
- the strict reporting Markdown summary at `artifacts/reporting_summary.md`

The GitHub Actions workflow uses the same entrypoint, and it also supports manual runs through `workflow_dispatch`.

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
```

Generated files:
- `artifacts/reporting_output.json`
- `artifacts/reporting_summary.md`

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

The JSON report structure is documented here:
- `schemas/reporting_output.schema.json`

This schema is useful when another tool needs to validate or parse `reporting_output.json` programmatically.

## Example Outputs

Sample outputs are checked into the repository here:
- `examples/reporting_output.sample.json`
- `examples/reporting_summary.sample.md`
- `examples/reporting_output.fail.sample.json`
- `examples/reporting_summary.fail.sample.md`

Use the `sample` files to see a clean run and the `fail.sample` files to see how missing targets and validation issues appear in the reports.

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

The Markdown summary is better for quick review in pull requests, CI jobs, or workflow artifacts.
