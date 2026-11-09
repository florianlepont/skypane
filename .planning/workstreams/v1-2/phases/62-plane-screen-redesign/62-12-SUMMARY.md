---
phase: 62-plane-screen-redesign
plan: 12
subsystem: render-tests-docs
tags: [golden, docs, mypy]
requires: [62-07, 62-08]
provides:
  - "giant golden suite and manifest (84 cases)"
  - "docs/plane-screen-layouts.md"
  - "giant render modules in the mypy gate"
affects: [server/test_golden_giant_render.py, server/fixtures/golden/giant_render_baseline.json, docs/plane-screen-layouts.md, server/README.md, pyproject.toml, companion/test_route_table.py]
key-files:
  created: [server/test_golden_giant_render.py, server/fixtures/golden/giant_render_baseline.json, docs/plane-screen-layouts.md]
  modified: [server/README.md, pyproject.toml, companion/test_route_table.py]
decisions:
  - "Giant manifest is a sibling of the legacy one; golden_cases() in test_golden_render.py is untouched. Hash comparison skips with a message when the installed Pillow differs from the recorded version."
metrics:
  completed: 2026-11-09
---

# Phase 62 Plan 12: Giant golden manifest and layout docs Summary

A separate golden suite (84 cases, hashes recorded under Pillow 13.0.0, the production pin) locks the giant look; the classic render is proven unchanged; the layouts are documented and all giant modules are type-checked.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Giant golden suite and manifest | bfceed6 | `test_golden_giant_render.py` + `giant_render_baseline.json` |
| 2 Docs and gate | 6ca1519 | `docs/plane-screen-layouts.md`, README link, 13 giant modules in `[tool.mypy] files` |
| Fix | 544158c | owner route count 30 -> 31 in `companion/test_route_table.py` |

## Golden cases (84)

- 4 layouts (a, b, c, a_diagonal) x 5 pairings x departing/arriving (40), portrait. The band on/off is covered by a_diagonal vs a, and by the white pairing, which draws no band.
- Long, short (Pau), accented, hyphenated and airline-only names on the 4 layouts (20), blue_light pairing.
- Landscape (800x480 simulated profile) for the 4 layouts, blue_light departing and white arriving (8).
- 7 status screens x portrait/landscape (14); flat no-connection and updating (2).
- Each flight case passes `assert_giant_palette`; status cases use only the six legal indices.
- Hashes are over the index canvas bytes. Pillow: the manifest records 13.0.0 (server/.venv); the hash test skips with a clear message when Pillow differs (the system python3 here has 12.3.0). The classic suite keeps its own fail-on-mismatch convention, untouched.
- `test_classic_unchanged`: layout None and "classic" equal three legacy golden cases byte for byte. `legacy_render_baseline.json`, `test_golden_render.py` and classic fixtures are unchanged (git shows no diff).

## Deviations from Plan

**1. [Rule 1 - Bug] Owner route count.** `companion/test_route_table.py` asserted 30 owner device routes; plan 11's layout view route made it 31. Updated the count (commit 544158c). Found in the full suite.

**2. Hash test skips instead of failing** on a Pillow mismatch (per the run instructions); the classic suite still fails.

## Verification

- ruff: all checks passed. mypy: success, 44 source files (the 13 giant modules included, none excluded; no annotation fixes were needed). Function-size gate: 1065 functions, none over 80. Comment-history guard: exit 0.
- Full suite (`./scripts/run-all-tests.sh`, detached, exit code recorded): first run exit 1 with 1 failed, 10705 passed, 2599 skipped (10:22), coverage 96.12% (floor 93.0%); the single failure was the route count above. After the fix `companion/test_route_table.py` passes (89 passed). The full suite was not re-run after that one-line fix, so the combined exit-0 is not shown.
- Browser tests (Playwright) cannot run in this sandbox (no Chromium): they were skipped, not passed. The 2599 skips are mostly these plus root-permission and openssl skips.
- Not done: the real-panel check and the CI Pillow 13.0.0 regeneration is unnecessary only if CI uses 13.0.0 (the pin); otherwise regenerate.

## Known Stubs

None.

## Self-Check: PASSED

Commits bfceed6, 6ca1519, 544158c exist; the created files exist.
