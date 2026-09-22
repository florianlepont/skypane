---
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - companion/test_browser_ux.py
  - companion/test_browser_ux_health_drawings.py
  - companion/test_browser_ux_helpers.py
  - companion/test_browser_ux_quiet_wake.py
  - companion/test_companion_app.py
  - scripts/run_all_tests.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 31: Code Review Report

**Reviewed:** 2026-09-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This phase mechanically decomposes the 96-check `companion/test_browser_ux.py` into a shared
helper module (`test_browser_ux_helpers.py`) plus two extracted standalone harnesses
(`test_browser_ux_health_drawings.py`, 11 checks; `test_browser_ux_quiet_wake.py`, 9 checks),
and wires both new harnesses into `scripts/run_all_tests.py`'s worker pool.

Verification performed, beyond reading each file:

- **Check-count arithmetic and reality.** `EXPECTED_CHECK_COUNT` history in
  `test_browser_ux.py` runs 96 → 85 (−11) → 76 (−9), and actual `check(...)` call counts in
  each of the three files (76 / 11 / 9) match their respective `EXPECTED_CHECK_COUNT`
  exactly. No check was silently dropped or duplicated by the split.
- **Byte-level verbatim-move proof.** Diffed the exact block removed from
  `test_browser_ux.py` in commit `60c51fc` (the drawings group) against the corresponding
  body of `test_browser_ux_health_drawings.py`, and the block removed in `3562290` (the
  quiet-hours/wake group) against `test_browser_ux_quiet_wake.py`. Both diffs are empty
  modulo the sed boundary used to reassemble the two-hunk removal — i.e. the moved code is
  byte-for-byte identical to what was deleted from the parent, not re-typed or edited in
  transit.
- **Import correctness.** Cross-checked every name imported from
  `companion.test_browser_ux_helpers` in all three consumer files against the helper
  module's actual top-level definitions (87 names) — no missing or misspelled imports. Also
  scanned each consumer file for any helper-shaped identifier used but not imported (a
  `NameError` risk); the only hits were plain-English mentions inside comments/docstrings
  (`SEED_BASE_TS`, `VIEWPORT_WIDTH_NARROW`, `_RING_INK_PROBE`, `_TILE_CONTENT_PROBE`,
  `_persist_once`, `_in_both_themes`), never live code.
- **Unused imports.** Every name imported from the helper module by each of the three
  consumer files is referenced at least once beyond the import statement itself — no dead
  imports introduced by the split.
- **`scripts/run_all_tests.py` wiring.** `HARNESSES` has 24 unique entries, all of which
  exist on disk; `EXPECTED_SLOWEST` has 10 unique entries, all present in `HARNESSES`;
  `_submission_order()` returns exactly 24 unique paths. The two new harnesses are present
  in both lists and both skip cleanly (exit 0) when Playwright/Chromium is unavailable, so
  their presence can't break a checkout without the dev-only browser dependency.
- **`test_companion_app.py`'s AST-based retarget.** The CFG-79 route-parity check now
  parses `test_browser_ux_helpers.py` (not `test_browser_ux.py`) for the
  `VIEW_TRANSITION_ROUTES` assignment, which is correct — 31-01 moved that assignment there
  and `test_browser_ux.py` now only imports the name. Confirmed via `git show 64ba819` that
  this was the only change in that commit, and it's exactly the fix its own commit message
  describes.
- All six files compile cleanly (`py_compile`); no duplicate top-level function
  definitions were introduced in `test_browser_ux_helpers.py`.

One quality defect was found — a stale file name in two failure messages left over from the
retarget fix. No bugs, security issues, or dropped/duplicated coverage were found.

## Warnings

### WR-01: Retargeted AST check's own failure messages still blame the wrong file

**File:** `companion/test_companion_app.py:11889-11890,11894`
**Issue:** 31-04's fix (commit `64ba819`) correctly repointed the `ast.parse()` call at
`test_browser_ux_helpers.py` (the constant's current canonical declaration site), since
`VIEW_TRANSITION_ROUTES` was relocated there by 31-01. However, the two `AssertionError`-style
failure strings this check raises on a real mismatch still say `"test_browser_ux.py"`:

```python
if view_transition_routes is None:
    return False, (
        "expected test_browser_ux.py to still declare "
        "VIEW_TRANSITION_ROUTES")
if set(site_routes) != set(view_transition_routes):
    return False, (
        "layout's own six route constants %r do not equal "
        "test_browser_ux.py's declared VIEW_TRANSITION_ROUTES "
        "membership %r" % (sorted(site_routes), sorted(view_transition_routes)))
```

If this check ever fails for real (a route added to one enumeration and not the other, or
the helper module's `VIEW_TRANSITION_ROUTES` assignment being restructured so the AST walk
can't find it), the printed diagnostic sends whoever is debugging it to edit
`test_browser_ux.py` — the file that now only imports the constant — rather than
`test_browser_ux_helpers.py`, where the assignment actually lives. This is exactly the kind
of stale-pointer message the fix's own comment (a few lines above) warns against for the
*code*; the two literal strings were missed.

**Fix:**
```python
if view_transition_routes is None:
    return False, (
        "expected test_browser_ux_helpers.py to still declare "
        "VIEW_TRANSITION_ROUTES")
if set(site_routes) != set(view_transition_routes):
    return False, (
        "layout's own six route constants %r do not equal "
        "test_browser_ux_helpers.py's declared VIEW_TRANSITION_ROUTES "
        "membership %r" % (sorted(site_routes), sorted(view_transition_routes)))
```

---

_Reviewed: 2026-09-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
