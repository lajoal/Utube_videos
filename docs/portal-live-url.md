# Portal Live URL

The internal app now includes a `Portal Info` page that can show the actual live portal address once the platform environment is configured.

## Why this helps

A GitHub branch URL is not the same thing as the real portal address. After deployment, the app needs a stable place where approved users can see the actual live URL and related links.

## Environment variables

Set these in the platform environment:

- `UTUBE_PORTAL_NAME`: display name for the portal
- `UTUBE_PLATFORM_NAME`: platform display name
- `UTUBE_PLATFORM_BRANCH`: deployed branch name
- `UTUBE_PORTAL_URL`: actual live address for the deployed app
- `UTUBE_GITHUB_REPO`: repository name in `owner/name` format

## Result

The `Portal Info` page will show:

- the actual live portal address
- the active GitHub repository link
- the active branch link
- a quick environment summary

## Important note

If `UTUBE_PORTAL_URL` is not set, the app cannot invent the real live address. It will show a warning until the platform provides that value.
