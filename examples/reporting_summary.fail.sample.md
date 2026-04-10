# Reporting Summary

- Overall status: `FAIL`
- Overall passed: `False`
- Generated at: `2026-04-10T04:35:00+00:00`
- Scan root: `/workspace/Utube_videos`
- Target source: `default_manifest`
- Target filenames: `4`
- Matched files: `3`
- Missing targets: `1`
- Validation issues: `3`
- Cross validation issues: `2`
- JSON report: `/workspace/Utube_videos/reporting_output.json`
- Markdown summary: `/workspace/Utube_videos/reporting_summary.md`

## Missing Targets

- `render_plan.json`

## Files With Issues

### `image_generation_prompts_ko.txt`

- Directory: `.`
- Cross validation: image prompt label order does not match scene_prompts.json.

### `tts_script_ko.txt`

- Directory: `.`
- Cross validation: TTS labels are missing scene_ids from scene_prompts.json: scene_03, scene_04.
- Cross validation: TTS section `scene_01_intro` may be too short for its scene duration (0.9 chars/s).

## Matches By Directory

### `.`

- `image_generation_prompts_ko.txt` (text, 1 issue(s))
- `tts_script_ko.txt` (text, 2 issue(s))
- `scene_prompts.json` (json, 0 issue(s))
