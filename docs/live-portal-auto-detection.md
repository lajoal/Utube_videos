# Live Portal Auto Detection

The internal app now includes a `Live Portal` page that behaves more like a scheduler or HyperScreen entry page.

## What changed

Instead of only relying on a manually configured environment variable, the page first tries to detect the current app URL from the running Streamlit session.

## Detection order

1. Current Streamlit session URL
2. `UTUBE_PORTAL_URL` fallback
3. Warning message when neither is available

## Why this is closer to your existing pattern

In a deployed internal app, approved users should be able to open the portal and immediately see the actual live address and navigation links without manually looking up a GitHub branch.

## Important note

Automatic URL detection depends on Streamlit session context support in the deployed runtime. If the runtime does not expose that information, `UTUBE_PORTAL_URL` still works as a fallback.
