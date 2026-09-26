---
status: testing
phase: 35-comment-purge-in-english-and-dead-code
source: [35-01-SUMMARY.md … 35-22-SUMMARY.md, 35-21b-SUMMARY.md]
started: 2026-09-26T07:17:32Z
updated: 2026-09-26T07:17:32Z
---

## Current Test

number: 6
name: Frame unchanged
expected: |
  A frame running firmware built from main (7cd0380 or later) wakes, polls and
  displays exactly as before (the purge changed only comments; the compiled input
  is identical, so this is optional).
awaiting: user response

## Tests

### 1. History guard rejects plan/ticket IDs everywhere
expected: `scripts/check_comment_history.py check` exits 0 on main with no pending list; a planted `# see D-06` (Python) or `/* 22-08-PLAN.md … */` (CSS) is reported.
result: pass
evidence: run on 7cd0380 — exit 0; both planted IDs reported (server/plane/dither.py d-id D-06, companion/static/style.css plan-artifact 22-08-PLAN.md); reverted.

### 2. Shipped stylesheet is smaller
expected: companion/static/style.css ≤ 150 KB raw (was 512,795 B).
result: pass
evidence: 140,426 B raw, 36,735 B gzip (was 170,819 B gzip).

### 3. English-only rule written down
expected: .claude/CLAUDE.md and CONTRIBUTING.md state the rule and name the CI guard.
result: pass
evidence: .claude/CLAUDE.md "Language and comments" section; CONTRIBUTING.md "Code language and comments".

### 4. Dead code gone
expected: no definition or call of health_severity(), anomaly_active(), usable_pairs(), label_grid() outside history docs.
result: pass
evidence: git grep finds only the live ctx["health_severity"] key and a string sample in companion/test_suite_guards.py; the design-skill references were updated with this UAT.

### 5. Companion unchanged in production
expected: After the production deploy of main (7cd0380 or later), the companion pages (Home, Health, History, Airlines, Settings, login) look and behave as before: same layout, colours, controls, save bar, charts; no console errors.
result: pass

### 6. Frame unchanged
expected: A frame running firmware built from main (7cd0380 or later) wakes, polls and displays exactly as before (the purge changed only comments; the compiled input is identical, so this is optional).
result: [pending]

## Summary

total: 6
passed: 5
issues: 0
pending: 1
skipped: 0

## Gaps

[none yet]
