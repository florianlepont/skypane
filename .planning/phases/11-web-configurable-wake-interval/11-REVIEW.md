---
phase: 11-web-configurable-wake-interval
reviewed: 2026-09-04T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .claude/skills/sketch-findings-skypane/SKILL.md
  - .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
  - companion/app.py
  - companion/pages/__init__.py
  - companion/pages/config_page.py
  - companion/test_companion_app.py
  - companion/test_config_page.py
  - deploy/skypane.env.example
  - server/device_config.py
  - server/test_config_history.py
  - stub-server/VENDOR.md
  - stub-server/byos_server.py
  - stub-server/test_poll_cycle.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-09-04T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the web-configurable wake-interval feature: the new `wake_interval_s` field in `server/device_config.py` (registry-free bounded-int field, `None`-sentinel unset state), its companion Settings-page UI (`companion/pages/config_page.py`'s `wake_interval_group()`/`handle_post()` string-to-int conversion), the `SKYPANE_SLEEP_S` environment pre-fill wiring in `companion/app.py`, and the vendored `stub-server/byos_server.py`'s read-only `read_wake_interval_s()` that feeds `quiet_hours_sleep_s()`'s existing `max(base_sleep_s, remaining)` arithmetic as its base value.

The four checks the task explicitly flagged as highest-risk were verified directly against the code and confirmed correct:

1. **bool-vs-int gotcha** — every bounded-integer check in this diff (`device_config.normalise_wake_interval_s()`, `device_config.save_device_config()`'s inline gate, `config_page.wake_interval_group()`'s `value_attr` gate, `byos_server.read_wake_interval_s()`) explicitly excludes `bool` via `isinstance(value, int) and not isinstance(value, bool)` before the range check. Confirmed by `_normalise_wake_interval_s_bounds_and_bool_gotcha` and the byos_server unit/integration checks — both pass.
2. **string-to-int conversion gate** — `config_page.handle_post()` correctly converts the submitted string to `int()` inside a `try`/`except ValueError` before ever calling `save_device_config()`, with an explicit `None`/`""` early-out for "leave unchanged." Confirmed by `_handle_post_wake_interval_string_converts_to_int_and_persists` and the rejection-path test — both pass.
3. **`None`-sentinel exception** — `wake_interval_s` is the only `device_config.py` field whose "valid" value set includes `None` (never-explicitly-set); `load_device_config()`/`save_device_config()`/`normalise_wake_interval_s()` all honor this asymmetry correctly and it is well-documented in-line.
4. **`quiet_hours_sleep_s()` untouched** — the function's body and its `max(base_sleep_s, remaining)` logic are byte-identical to the pre-Phase-11 version; the only change is what value is now passed in as `base_sleep_s` (`read_wake_interval_s(...)` instead of `self.args.sleep` directly). The `[60, 3600]` bound is confirmed to gate only the stored config field, never the value quiet-hours extension can return (verified by the "sleep_s exactly greater than base --sleep, no greater than 7200" integration check).

All three affected test suites were run directly against this worktree and pass in full: `server/test_config_history.py` (44/44), `stub-server/test_poll_cycle.py` (34/34), `companion/test_config_page.py` (79/79), `companion/test_companion_app.py` (129/129).

Two maintainability/robustness gaps remain, both worth fixing but neither incorrect today.

## Warnings

### WR-01: `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` are duplicated with no drift guard, unlike every other duplicated constant in this vendor boundary

**File:** `stub-server/byos_server.py:84-95` (and `server/device_config.py:68-69`)
**Issue:** `stub-server/byos_server.py` must never import a `server.*` module (vendor-boundary discipline), so it independently redefines `WAKE_INTERVAL_MIN_S = 60` / `WAKE_INTERVAL_MAX_S = 3600`. Every other value this vendor file duplicates from `server/device_config.py` — `_HHMM_RE` and `seconds_until_quiet_hours_end()` — is pinned byte-for-byte equal by an automated drift guard (`test_poll_cycle.py`'s `_quiet_hours_drift_guard`, confirmed present and passing). The new `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` pair is explicitly *not* covered by that guard — the file's own comment says so ("Unlike `_HHMM_RE` and `seconds_until_quiet_hours_end()`, these two are NOT covered by test_poll_cycle.py's `_quiet_hours_drift_guard`") and `stub-server/VENDOR.md`'s re-pinning instructions rely entirely on manual discipline ("These two values must stay numerically equal ... by hand, in the same commit"). If a future change adjusts the bounds in `server/device_config.py` without updating the copy here (or vice versa), the companion app could accept and persist a `wake_interval_s` that `byos_server.py`'s `read_wake_interval_s()` then silently rejects (falling back to `--sleep`) — or the reverse, where `byos_server.py` accepts a value the companion's own UI would refuse to redisplay. This is exactly the class of silent cross-process inconsistency the existing drift guard was built to prevent for the other two duplicated values, and it is confirmed absent for this one, not merely undiscovered.
**Fix:** Extend `_quiet_hours_drift_guard()` (or add a sibling check) in `stub-server/test_poll_cycle.py` to also assert `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` are numerically equal between the two files, e.g. by reading both files as plain text (matching the existing guard's own approach) and comparing the two assignment lines, or by `importlib`-loading both modules (as the harness already does for `byos_server.py`) and comparing the four integers directly:
```python
def _wake_interval_bounds_drift_guard():
    import server.device_config as device_config
    if (module.WAKE_INTERVAL_MIN_S != device_config.WAKE_INTERVAL_MIN_S
            or module.WAKE_INTERVAL_MAX_S != device_config.WAKE_INTERVAL_MAX_S):
        return False, "byos_server.py's WAKE_INTERVAL_MIN_S/MAX_S have drifted from server/device_config.py's"
    return True, ""
```

### WR-02: `handle_post()`'s wake-interval conversion only catches `ValueError`, not `TypeError`

**File:** `companion/pages/config_page.py:984-987`
**Issue:**
```python
try:
    wake_interval_s = int(submitted_wake_interval)
except ValueError:
    return FLASH_SAVE_FAILED
```
`submitted_wake_interval` is always a `str` (or `None`, already handled by the preceding branch) when this code is reached via the real HTTP path, because `Handler.read_form()` always yields string values from `parse_qs()`. However, `handle_post(form, ctx)` is a plain function taking an arbitrary `form` dict — every other field in this same function (`theme`, `tracked_runway`, the two checkbox fields) degrades safely regardless of the value's type, either via a membership test (`not in device_config.THEME_IDS`) or an equality test (`== LED_CHECKBOX_VALUE`), neither of which can raise for an arbitrary type. `int()` is different: if a future caller (a different route, a refactored form parser that preserves multi-value lists, or a test) ever passes something that isn't a string/number/None for `wake_interval_s` — e.g. a `list` from a multi-valued form field — `int(a_list)` raises `TypeError`, which is not caught here and would propagate as an unhandled 500 rather than degrading to `FLASH_SAVE_FAILED` like every other malformed-input path in this handler. This is latent, not currently reachable through `companion/app.py`'s own `do_POST` → `read_form()` path, but it breaks this function's own stated contract ("Deliberately does NOT ... silently coerced" / never-raise discipline every sibling field in this handler honors) for this one field alone.
**Fix:**
```python
try:
    wake_interval_s = int(submitted_wake_interval)
except (TypeError, ValueError):
    return FLASH_SAVE_FAILED
```

## Info

### IN-01: `int()`'s permissive grammar (underscore digit-group separators, Unicode decimal digits) is not restricted before parsing `wake_interval_s`

**File:** `companion/pages/config_page.py:984-987`
**Issue:** Python's `int(str)` accepts more than plain ASCII digits: underscore-separated digit groups (`int("1_000")` → `1000`, PEP 515) and non-ASCII Unicode decimal digits (e.g. Arabic-Indic numerals) both parse successfully. Neither is reachable from a real `<input type="number">` submission, and both are still fully bounded by `save_device_config()`'s subsequent `[60, 3600]` range check, so this is not exploitable — but it is a looser input grammar than `stub-server/byos_server.py`'s own `parse_battery_mv()` uses for its numeric header (which explicitly restricts to the literal ASCII digit set `"0123456789"` before calling `int()`, with a comment noting non-ASCII digits are why). Worth the same explicit restriction here for consistency with that established, more defensive pattern in this codebase, though this is not a security issue given the bound is still enforced.
**Fix:** Optional hardening, not required:
```python
if not all(c in "0123456789" for c in submitted_wake_interval.strip("-")):
    return FLASH_SAVE_FAILED
```
(or simply leave as-is, given the downstream range check already bounds every accepted value).

---

_Reviewed: 2026-09-04T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
