# GitHub Issues Dashboard

The internal Streamlit app now includes a dedicated `Latest Issues` page under `pages/Latest_Issues.py`.

## What it does

- Connects to the GitHub Issues API
- Pulls the most recently updated issues for a repository
- Filters out pull requests from the issue list
- Writes a JSON artifact and a Markdown digest
- Lets internal users review the digest and download the artifacts from the page

## Inputs

- Repository: `owner/name`
- State filter: `open`, `all`, or `closed`
- Count limit: recent issue count to include in the digest

## Environment variables

- `UTUBE_GITHUB_REPO`: default repository shown in the page
- `UTUBE_GITHUB_TOKEN`: optional token for private repositories or higher API limits
- `GITHUB_TOKEN`: fallback token name

## Output artifacts

- `artifacts/latest_issues.json`
- `artifacts/latest_issues.md`

## Runtime flow

```text
Internal user
  -> Streamlit page (pages/Latest_Issues.py)
  -> GitHub issue backend (github_issue_digest.py)
  -> GitHub Issues API
  -> artifacts/latest_issues.json
  -> artifacts/latest_issues.md
  -> Streamlit digest preview + download
```
