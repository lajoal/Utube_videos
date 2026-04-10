# Utube_videos

Seed workspace for a Korean video production flow.

## Included files
- `reporting.py`
- `reporting_targets.txt`
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

This writes `reporting_output.json` and prints a summary of the matching files.

By default, the script loads its target filenames from `reporting_targets.txt`. If that file is missing, it falls back to the built-in default list in `reporting.py`.

For automation and CI, fail the run when one or more targets are missing:

```bash
python reporting.py --fail-on-missing
```

You can also load targets from another file and write the report to a custom location:

```bash
python reporting.py --targets-file config/targets.txt --output artifacts/report.json
```

The generated report includes both the resolved target list and the `target_source` used for that run.

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

## Testing
Run the built-in unit tests from the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub Actions runs the test suite, performs a reporting smoke check, and uploads the generated report as a workflow artifact on pushes to `main` and on pull requests.
