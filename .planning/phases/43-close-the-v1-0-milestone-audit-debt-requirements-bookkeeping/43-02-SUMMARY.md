---
phase: 43
plan: 02
status: complete
completed: 2026-09-30
---

# Code cleanup

Removed unused production preview and compatibility APIs, retired persisted
`screen_id` with tolerant read/next-save cleanup, made the history date parsers
public, and corrected stale references. Contrast helpers remain available to
tests from `test-support`, where they are actually used. The OTA malformed-header
test is green under xdist; the single prior failure was not reproducible, so no
behavioural change was made.

Validation: 484 focused tests passed; ruff, mypy, function-size and comment
history checks passed.
