# Utube_videos

Seed workspace for a Korean video production flow.

## Included files
- `reporting.py`
- `gpu_report.py`
- `self_check.py`
- `reporting_targets.txt`
- `config/targets.txt.example`
- `docs/reporting-workflow.md`
- `schemas/reporting_output.schema.json`
- `schemas/gpu_report.schema.json`
- `schemas/self_check_summary.schema.json`
- `examples/README.md`
- `examples/reporting_output.sample.json`
- `examples/reporting_summary.sample.md`
- `examples/reporting_output.fail.sample.json`
- `examples/reporting_summary.fail.sample.md`
- `examples/gpu_report.sample.json`
- `examples/gpu_report.sample.md`
- `examples/self_check_summary.sample.json`
- `examples/self_check_summary.sample.md`
- `examples/self_check_summary.fail.sample.json`
- `examples/self_check_summary.fail.sample.md`
- `image_generation_prompts_ko.txt`
- `tts_script_ko.txt`
- `scene_prompts.json`
- `render_plan.json`
- `tests/test_reporting.py`
- `tests/test_reporting_examples.py`
- `tests/test_gpu_report.py`
- `tests/test_gpu_report_examples.py`
- `tests/test_self_check.py`
- `tests/test_self_check_examples.py`
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

## GPU Diagnostics

To inspect whether the local machine is ready for GPU-backed video workloads:

```bash
python gpu_report.py
python gpu_report.py --require-cuda --require-nvenc
make gpu-report
```

By default, `gpu_report.py` writes `artifacts/gpu_report.json` and `artifacts/gpu_report.md`. It checks `nvidia-smi`, `torch` CUDA readiness, FFmpeg CUDA hwaccel support, and NVENC encoders, then summarizes which workloads are ready for acceleration.

## Self-Check

To run the repository's built-in self-check flow end to end:

```bash
python self_check.py
python self_check.py --keep-going
python self_check.py --keep-going --require-cuda --require-nvenc
make self-check
make check
```

By default, `self_check.py` stops on the first failing step. Use `--keep-going` when you still want the GPU diagnostics and strict reporting steps to run after test failures so the JSON and Markdown diagnostics are produced whenever possible. Use `--require-cuda` or `--require-nvenc` when the machine must be GPU-ready for the run to count as passing.

Every self-check run also writes `artifacts/self_check_summary.json` and `artifacts/self_check_summary.md` by default. Those files record the selected steps, each command that ran, whether a step passed, failed, or was skipped, plus workflow-level and per-step timestamps and duration values. They record whether the strict reporting and GPU artifacts actually exist after the run, expose `passed_steps`, `failed_steps`, and `skipped_steps` at the top level for quick automation checks, and group generated artifact metadata under `artifacts` with path, existence, and size information. Use `--summary-output` or `--summary-markdown-output` to send those summaries to different paths.

GitHub Actions and `make self-check` use `--keep-going` so the workflow still attempts to publish diagnostic artifacts even when an earlier self-check step fails.

If the reporting step does not produce `artifacts/reporting_summary.md`, the workflow summary falls back to `artifacts/self_check_summary.md` so there is still a human-readable failure trail in the uploaded artifacts.

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
make gpu-report
make report-strict
make test
make self-check
make check
```

`make report-strict` writes both `artifacts/reporting_output.json` and `artifacts/reporting_summary.md`.

## Docs
Detailed reporting, GPU diagnostics, and self-check behavior live here:
- `docs/reporting-workflow.md`
- `config/targets.txt.example`
- `schemas/reporting_output.schema.json`
- `schemas/gpu_report.schema.json`
- `schemas/self_check_summary.schema.json`
- `examples/README.md`
- `examples/reporting_output.sample.json`
- `examples/reporting_summary.sample.md`
- `examples/reporting_output.fail.sample.json`
- `examples/reporting_summary.fail.sample.md`
- `examples/gpu_report.sample.json`
- `examples/gpu_report.sample.md`
- `examples/self_check_summary.sample.json`
- `examples/self_check_summary.sample.md`
- `examples/self_check_summary.fail.sample.json`
- `examples/self_check_summary.fail.sample.md`

## Testing
Run the built-in unit tests from the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

The test suite checks that the checked-in reporting, GPU, and self-check sample outputs stay aligned with their documented schemas and that the `self_check.py` command composition stays consistent.

GitHub Actions runs the repository self-check flow, publishes the Markdown summary into the workflow summary UI when available, and uploads the generated `artifacts/` directory as a workflow artifact on pushes to `main`, pull requests, and manual dispatches.
