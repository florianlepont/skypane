---
phase: 15-per-direction-themes-per-flight-colour-rules-and-roster-link
plan: 02
subsystem: server-config
tags: [config, theme, sentinel, tdd-adjacent]
status: complete
dependency-graph:
  requires: []
  provides:
    - server/device_config.py:CLEAR_THEME_ARRIVING
    - server/device_config.py:normalise_theme_arriving
    - "device_config.json theme_arriving key"
    - "save_device_config(theme_arriving=...) three-state contract"
  affects:
    - companion/pages/config_page.py (plan 15-04, not yet wired)
    - server/plane/colour_rules.py (plan 15-01, reads theme_arriving via .get())
    - server/poll_loop.py (plan 15-03, not yet wired)
tech-stack:
  added: []
  patterns:
    - "module-level object() sentinel to widen a keyword-argument's meaning beyond None, mirroring companion/pages/health_page.py's _DB_UNAVAILABLE idiom"
key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py
decisions:
  - "CLEAR_THEME_ARRIVING = object() distinguishes 'clear the override' from None's existing 'not supplied, carry forward' meaning, compared strictly by identity (is / is not) in both the validation and write branches - never by equality, so no crafted value can collide with it (D-04, D-05)."
  - "normalise_theme_arriving() degrades every hostile/unregistered value to None, deliberately not DEFAULT_THEME_ID - None here means 'no override, same as theme', not 'degraded to the documented default' (D-04)."
  - "load_device_config() reads theme_arriving with .get() so a device_config.json written before this phase resolves to None with zero migration and zero rewrite of the file on disk."
metrics:
  duration: "~35 min"
  completed: 2026-09-06
---

# Phase 15 Plan 02: theme_arriving config field with a clearable sentinel Summary

Added `theme_arriving`, the optional per-direction theme override (D-04), to `server/device_config.py` — including the phase's hardest design point: a `CLEAR_THEME_ARRIVING` sentinel that lets `save_device_config()` genuinely clear a previously-set override, something `None`'s existing "carry forward" meaning cannot express.

## What was built

**`server/device_config.py`:**
- `CLEAR_THEME_ARRIVING = object()` — a module-level sentinel distinct from `None`, mirroring `companion/pages/health_page.py`'s `_DB_UNAVAILABLE` idiom. Exists only in the write path; `load_device_config()` never sees it.
- `normalise_theme_arriving(value)` — returns `value` unchanged only when it is a string member of `THEMES`, else `None`. Deliberately degrades to `None`, never `DEFAULT_THEME_ID` — the divergence from `normalise_theme_id()`'s shape that the plan flagged as the field's real risk.
- `load_device_config()` now always returns `theme_arriving`, read via `.get()` so a pre-Phase-14 file with no such key resolves to `None` with no migration and no rewrite.
- `save_device_config(..., theme_arriving=None, ...)` — a new keyword with a three-state contract: `None` carries forward (matching every other field), `CLEAR_THEME_ARRIVING` clears to `None`, any other value must be a `THEMES` member or `ValueError` is raised before anything is written. Both the validation and write branches use identity comparison (`is` / `is not`) against the sentinel, never equality.

**`server/test_config_history.py`:** extended with 5 new checks covering the degrade proof (hostile on-disk values → `None`, never `DEFAULT_THEME_ID`), the sentinel's distinctness, the no-migration proof (a pre-Phase-14 file round-trips unchanged and is never rewritten), and the full three-state write contract (set → carry-forward-on-omission → `CLEAR_THEME_ARRIVING` clears → non-member value rejects, file byte-identical after rejection). `EXPECTED_CHECK_COUNT` moved 49 → 54, re-derived by running the harness. The decrement-and-confirm-failure guard-liveness check was run manually and the value restored.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 9 pre-existing `test_config_history.py` dict-equality assertions to include the new additive `theme_arriving: None` key**
- **Found during:** Task 1's own acceptance criterion — "`server/test_config_history.py` exits 0 with its `EXPECTED_CHECK_COUNT` still at its pre-edit value, proving this task broke no existing device-config behaviour."
- **Issue:** `load_device_config()` now unconditionally returns a 9th key. Every pre-existing check that asserted full-dict equality against an 8-key literal (missing/malformed-file defaults, hostile-value degradation, save/load round-trips for `theme`, `tracked_runway`, `led_enabled`, `quiet_hours_*`, `wake_interval_s`, `display_enabled`) failed with a spurious extra-key mismatch, even though none of those fields' own behaviour changed.
- **Fix:** Inserted `"theme_arriving": None, ` into each of the 9 affected dict literals via a single scoped `sed` substitution keyed on the exact `"theme": "(white|black)", "tracked_runway"` pattern — none of these pre-existing tests set `theme_arriving`, so `None` is the only correct expected value in every case.
- **Files modified:** `server/test_config_history.py`
- **Commit:** `447dcf4`

### Known Cross-Plan Test Regression (not fixed — out of this plan's scope)

**`companion/test_config_page.py` line ~1555** ("a post with a valid theme and runway writes both and returns the saved flash key") does a full-dict equality against `load_device_config()`'s output without the new `theme_arriving` key, so it now fails (`scripts/run-all-tests.sh` reports this single harness as FAILED; every other of the 17 harnesses passes, including `server/test_config_history.py` at 54/54 and `server/test_render.py`'s unedited D-07 gate at 134/134).

This is the same class of break Task 1 fixed in `server/test_config_history.py`, but `companion/pages/config_page.py` and its test file are explicitly owned by sibling plan 15-04 (see this plan's own `<verification>`: `git diff -- server/poll_loop.py companion/` must be empty for 15-02's commits, and the artifacts table lists `config_page.py`'s `theme_arriving`-related symbols as "produced by sibling plans ... do not create here"). Modifying `companion/` here would violate that explicit boundary. Plan 15-04 will need the identical one-line fix (`"theme_arriving": None,` added to the expected dict literal at that assertion) when it wires up the arrivals-theme-override checkbox — flagging this explicitly so it isn't mistaken for new work when 15-04 lands.

No auth gates encountered.

## Self-Check: PASSED

- FOUND: `server/device_config.py` (modified, exists)
- FOUND: `server/test_config_history.py` (modified, exists)
- FOUND: commit `447dcf4` (git log)
- FOUND: commit `b74f8cd` (git log)
- `server/.venv/bin/python3 server/test_config_history.py` → 54/54 checks pass
- `server/.venv/bin/python3 server/test_render.py` → 134/134 checks pass, `EXPECTED_CHECK_COUNT` unedited
- `git diff --stat -- server/plane/render.py` → empty
- `git diff -- server/requirements.txt server/requirements-dev.txt` → empty
- `git diff --stat -- server/poll_loop.py companion/` → empty for this plan's commits
