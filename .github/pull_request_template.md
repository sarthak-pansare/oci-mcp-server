<!-- Thanks for contributing! Please fill in the sections below. -->

## What does this change?

<!-- One or two sentences. Link any related issue: closes #123 -->

## Why?

<!-- The motivation. -->

## How was it tested?

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` passes
- [ ] Manually verified against a live OCI tenancy (describe how)

## Checklist

- [ ] Tool docstrings are one line
- [ ] List tools default to `limit=50` and accept a `page` token
- [ ] List tools return compact summaries by default (no full SDK objects)
- [ ] Null-stripping is applied to responses (`strip_nulls`)
- [ ] No OCI credentials, OCIDs of real production resources, or private keys committed
- [ ] CHANGELOG.md updated under `## [Unreleased]`
