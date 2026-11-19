---
phase: 68-console-and-companion-visual-improvements
plan: 01
subsystem: companion
tags: [housekeeping, investigation, browser-test]
requires: []
provides:
  - branch containing origin/main
  - measured cause of the Style tab preview reload
  - companion/test_browser_style_tab_previews.py (request-count harness)
affects: [68-36]
key-files:
  created: [companion/test_browser_style_tab_previews.py]
  modified: [.claude/skills/sketch-findings-skypane/SKILL.md]
requirements: [CON-01]
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 01: Wave 0 housekeeping Summary

Merged origin/main, measured why the Style tab previews appear to reload (full navigation with lazy images, not URL churn or revalidation), and confirmed the baseline is green.

## Commits

- fb44d731: merge of origin/main into the branch (planning-file auto-merge only, no conflicts)
- 01b6f4e4: browser harness for preview requests across Style tab switches
- 28cf24da: skill "as of" line

## Task 1: merge and open pull requests

- `git merge-base --is-ancestor origin/main HEAD` succeeds.
- Open pull requests (REST): none. None touches the shared companion, history, enrich, byos or pairing files.
- `git diff origin/main --stat -- companion` was empty before Task 2 (the branch had no companion changes of its own).
- Browser tooling: it was missing, so I ran `pip install -r server/requirements-dev.txt` and `python -m playwright install --only-shell chromium`. `SKYPANE_REQUIRE_BROWSER=1` is needed for every browser run: `SKYPANE_REQUIRE_BROWSER=1 pytest ...`.

## Task 2: D-07 measurement (Style tabs: /display, /display/arrivals, /display/special-looks, /display/calendar)

Result of a switch through the four tabs and back to /display, with the browser cache active:

| Visit | Preview requests | Served from cache | Lazy images |
|---|---|---|---|
| /display (first) | 9 | 0 | 10 |
| /display/arrivals | 10 | 5 | 10 |
| /display/special-looks | 5 | 5 | 5 |
| /display/calendar | 5 | 5 | 6 |
| /display (again) | 9 | 9 | 10 |

Preview responses are `200` with `cache-control: private, max-age=300`. The same preview has the same URL on every visit (no cache-busting parameter). With the cache disabled every visit hits the network (9/10/5/5/9).

Which hypothesis holds:
- URL differs per tab: not the cause (URLs are stable; only the arrivals tab has 5 URLs of its own, which are fetched once, then cached).
- Revalidation on navigation: not the cause (max-age=300 means repeat visits are served from cache with no network hit).
- Re-decode of lazily loaded images: this, together with the fact that each tab is a full document navigation (plain links, `page.goto`-style), so every `<img loading="lazy">` is rebuilt, decoded and painted again, which looks like a reload. The first visit of the arrivals-only previews is a real network fetch.

Implication for plan 36: do not change URLs or cache headers. The fix is on the page side (avoid the full re-paint, for example keep the preview strip stable across tab navigation, or set eager loading/`decoding` hints for the visible previews, or switch tabs without a document navigation) and the harness's cache-served counts are the regression signal.

Harness notes: the shared `new_context` guard installs `context.route`, which makes Chromium bypass its HTTP cache, so the cache-enabled measurement lifts the route after login (loopback server only). The cache-disabled test keeps the guard. The assertions describe today's behaviour (stable URLs, repeat visit fully cached, max-age header present, cache-off hits the network equally); plan 36 will change them to the new expected values.

## Task 3: baseline

`SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_render_baseline.py companion/test_structure_guards.py companion/test_suite_guards.py -q`: 363 passed on the merged branch. No failing pages; the baseline was not regenerated. Also green: `scripts/check_comment_history.py check`, `ruff check` on the new test. SKILL.md "as of" line now reads 2026-11-18 and says Phase 68 is changing the design system page by page and a later plan updates every reference file; no reference file was edited.

## Deviations from Plan

None in scope. Two adjustments to the harness approach (in-task): the guard-bypass described above, and tracking CDP request ids to count cache hits for previews only. No production file changed.

## Not run

Nothing was skipped. The full test suite (`./scripts/run-all-tests.sh`) was not run; only the modules named in the plan plus the new test.

## Known Stubs

None.

## Self-Check: PASSED

Files exist (test file, SKILL.md edit, this summary); commits fb44d731, 01b6f4e4, 28cf24da are in the branch.
