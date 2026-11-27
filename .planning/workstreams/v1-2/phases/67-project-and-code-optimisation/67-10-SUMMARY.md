---
phase: 67-project-and-code-optimisation
plan: 10
subsystem: ci
tags: [quality, function-size-gate, refactor]
requires: [67-05, 67-08]
provides: [function-size gate over server, stub-server, companion, deploy, scripts]
key-files:
  modified:
    - scripts/check_comment_history.py
    - .github/workflows/ci.yml
    - .claude/CLAUDE.md
requirements: [QUAL-01]
metrics:
  tasks: 2
  completed: 2026-11-27
---

# Phase 67 Plan 10: Function-size gate widened Summary

`_js_chunks` (89 lines) is split into string, template and regex skip helpers, and the CI function-size gate now covers companion, deploy and scripts at the unchanged cap of 80.

## Tasks

1. `8d37dda3` refactor: `_js_chunks` split into `_js_skip_string`, `_js_skip_template`, `_js_skip_regex`, `_js_slash_starts_regex`. Output identical to the old implementation over every tracked js/html/py file plus 30000 random inputs (0 mismatches); `check` output byte-identical before/after; collected test ids unchanged (496).
2. `bfa7360a` ci: gate roots `server stub-server companion deploy scripts`, `--max 80`; CLAUDE.md gate-scope text updated.

## Verification

- `check_function_size.py check --max 80 server stub-server companion deploy scripts`: 3417 functions, none over 80, exit 0
- test-support comment-history and function-size tests, deploy workflow-pinning tests: pass; ruff clean

## Deviations from Plan

None. No new test added (existing tests plus differential comparison cover it).
