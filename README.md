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

## Testing
Run the built-in unit tests from the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub Actions also runs the same test suite on pushes to `main` and on pull requests.
