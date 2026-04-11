# GitHub Template Analysis

This page lets you analyze GitHub issues using a template file stored on GitHub.

## Why this matters

The template file does not need to exist on the local machine running the app. If the file is stored in a GitHub repository and the app can access that repository, the app can fetch the template and render the analysis from it.

## Supported template sources

- GitHub file URL such as `https://github.com/owner/repo/blob/main/path/to/template.md`
- Raw GitHub URL such as `https://raw.githubusercontent.com/owner/repo/main/path/to/template.md`
- Direct repository selection with:
  - template repository
  - template path
  - template ref

## Current placeholders

- `{{generated_at}}`
- `{{repo_full_name}}`
- `{{state}}`
- `{{requested_limit}}`
- `{{issue_count}}`
- `{{top_labels_text}}`
- `{{issue_bullets}}`
- `{{issue_sections}}`
- `{{default_digest_markdown}}`
- `{{issues_json}}`

## Output artifacts

- `artifacts/template_issue_digest.json`
- `artifacts/template_issue_digest.md`

## Example flow

```text
Internal user
  -> Streamlit page (pages/GitHub_Template_Analysis.py)
  -> GitHub template analysis backend (github_template_analysis.py)
  -> GitHub Issues API + GitHub template file
  -> artifacts/template_issue_digest.json
  -> artifacts/template_issue_digest.md
  -> Streamlit preview + download
```
