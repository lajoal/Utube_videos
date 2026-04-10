# Utube_videos

Seed workspace for a Korean video production flow.

## Included files
- `reporting.py`
- `image_generation_prompts_ko.txt`
- `tts_script_ko.txt`
- `scene_prompts.json`
- `render_plan.json`
- `tests/test_reporting.py`
- `.github/workflows/test.yml`

## Usage
Run the reporting script from the repository root:

```bash
python reporting.py
```

This writes `reporting_output.json` and prints a summary of the matching files.

For automation and CI, fail the run when one or more targets are missing:

```bash
python reporting.py --fail-on-missing
```

You can also load targets from a file and write the report to a custom location:

```bash
python reporting.py --targets-file targets.txt --output artifacts/report.json
```

The scanner skips common cache and virtual environment directories by default:
- `.git`
- `.mypy_cache`
- `.pytest_cache`
- `.venv`
- `__pycache__`
- `venv`

Add more exclusions with repeated `--exclude-dir` flags.

## Testing
Run the built-in unit tests from the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub Actions runs the test suite and a reporting smoke check on pushes to `main` and on pull requests.
