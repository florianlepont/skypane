---
phase: 15-per-direction-themes-per-flight-colour-rules-and-roster-link
reviewed: 2026-09-06T16:37:49Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - server/plane/colour_rules.py
  - server/device_config.py
  - server/poll_loop.py
  - companion/pages/config_page.py
  - companion/app.py
  - companion/static/style.css
  - companion/pages/__init__.py
  - scripts/run-all-tests.sh
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 15: Per-direction themes, per-flight colour rules and roster-linked highlighting Code Review Report

**Reviewed:** 2026-09-06T16:37:49Z
**Depth:** deep
**Files Reviewed:** 8 (the phase's substantive diff, per the review's stated scope; test files read as context only)
**Status:** issues_found

## Summary

This is a careful, well-scoped implementation. I traced the D-13 resolver end to end — both call sites in `poll_loop.run_once()`, the leaf-import discipline in `server/plane/colour_rules.py`, the three key-kind normalisers, the `CLEAR_THEME_ARRIVING` sentinel's three-state contract in `server/device_config.py`, and the two new companion routes — against the locked decisions in 15-CONTEXT.md and the threat patterns named in 15-RESEARCH.md (T-15-01, T-15-02, T-15-05, and the ordering trap). I did not find a defect in the resolver itself: it never raises for a flight dict missing `hex`/`callsign`, for a non-dict `flight`/`device_cfg`, for a `state` value that is neither `"departing"` nor `"arriving"`, or for a tampered/stale cache entry — every return path re-checks membership in `device_config.THEMES` before handing a value back, closing T-15-05 at the one place that matters. The two `build_canvas()` call sites that must share one effective id do so from the same `current_flight` dict written to `poll_state["last_flight"]`, so the battery-icon-repaint invariant (D-13's stated highest-risk property) holds by construction, not just by test. The ordering trap (hoisting the resolver to the top of `run_once()`) was avoided exactly as the research warned it could not be; only the registry-cache-priming call was hoisted.

I found two WARNING-level concurrency gaps, both worth fixing but neither a data-loss or security risk on the single-operator deployment this project targets, and one INFO-level inconsistency. No BLOCKER findings.

## Warnings

### WR-01: `_handle_rule_delete()`'s existence pre-check races the locked delete, and can report a spurious failure

**File:** `companion/app.py:1654-1661`
**Issue:** The route computes `existed` from an *unlocked* `load_colour_rules()` call, then calls `delete_rule()`, which does its own independently-locked load-check-delete. If a second concurrent delete (or a repeat click) removes the same `(kind, value)` between these two reads, `existed` is `True` but `delete_rule()` correctly returns `False` (already absent) — and the handler then redirects with `FLASH_KEY_RULE_DELETE_FAILED`, telling the operator the delete failed when the entry is in fact gone, exactly as they wanted. This is the identical shape as the pre-existing `_handle_manual_resolution_delete()` (Phase 13) this route deliberately mirrors, so it is not a new class of bug this phase invented, but `colour_rules.py` in this same phase *did* solve the analogous added-vs-replaced race correctly by computing the answer inside the write lock (`add_rule()`'s `replacing` local) — the delete path didn't get the same treatment.
**Fix:** Have `delete_rule()` itself distinguish "deleted" from "was already absent" inside the lock (a three-state return, e.g. `DELETE_OK` / `DELETE_ABSENT` / `DELETE_FAILED`, mirroring the `ADD_OK_NEW`/`ADD_OK_REPLACED` split this module already established), and drop the separate unlocked `existed` pre-read in `companion/app.py`:
```python
# colour_rules.py
DELETE_OK = "deleted"
DELETE_ABSENT = "absent"
DELETE_FAILED = "failed"

def delete_rule(state_dir, kind, value):
    ...
    with _WRITE_LOCK:
        registry = load_colour_rules(state_dir)
        if normalised_value not in registry[normalised_kind]:
            return DELETE_ABSENT
        del registry[normalised_kind][normalised_value]
        ...  # write, as today
    return DELETE_OK
```
```python
# companion/app.py
result = colour_rules.delete_rule(state_dir, normalised_kind, normalised_value)
if result == colour_rules.DELETE_OK:
    return self.redirect("%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_RULE_DELETED)))
if result == colour_rules.DELETE_FAILED:
    return self.redirect("%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_RULE_DELETE_FAILED)))
return self.redirect(SETTINGS_ROUTE)  # DELETE_ABSENT: idempotent, no flash
```

### WR-02: `save_device_config()` has no write lock, and this phase adds `theme_arriving` into that same unguarded read-modify-write

**File:** `server/device_config.py:687-725`
**Issue:** `save_device_config()` reads `current = load_device_config(state_dir)`, merges in the caller's supplied fields (now including `theme_arriving`, via the `CLEAR_THEME_ARRIVING` sentinel this phase adds), and writes the merged result — with no lock around the sequence. Two concurrent `POST /settings` requests (e.g. a double-submit, or two browser tabs) can each read the same `current` snapshot before either writes; the second write silently discards whatever the first request changed — a classic lost update, exactly T-15-02's threat class. This gap pre-dates Phase 15 (every other field already shared it), so it is not a new defect this phase introduced from scratch, but the phase's own research explicitly named T-15-02 as a threat to mitigate, and the phase *did* mitigate it correctly for the sibling `colour_rules.json` store (`_WRITE_LOCK` wraps the whole load-check-mutate-write sequence in `add_rule()`/`delete_rule()`) while leaving `device_config.json`'s save path — now carrying one more field — unguarded. A lost update here would silently revert an operator's just-set `theme_arriving` (or any other field) back to its pre-request value with no error surfaced anywhere.
**Fix:** Wrap `save_device_config()`'s load-merge-write sequence in a module-level `threading.Lock()`, the same idiom `colour_rules.py` already uses:
```python
_WRITE_LOCK = threading.Lock()

def save_device_config(state_dir, theme=None, theme_arriving=None, ...):
    # ...existing validation (unchanged, stays outside the lock)...
    with _WRITE_LOCK:
        current = load_device_config(state_dir)
        # ...existing merge logic...
        os.makedirs(state_dir, exist_ok=True)
        path = device_config_path(state_dir)
        tmp = path + ".tmp"
        try:
            with open(tmp, "w") as fh:
                json.dump(new_config, fh, indent=1)
            os.replace(tmp, path)
        except Exception:
            ...
            raise
```

## Info

### IN-01: `add_rule()`/`delete_rule()` write failures are completely silent (no log line)

**File:** `server/plane/colour_rules.py:342-353, 385-396`
**Issue:** The `except Exception:` blocks in both write paths clean up the stray `.tmp` file and return a failure code, but never `print()` anything — a genuine write failure (disk full, permission denied, a redeployed `state_dir` with wrong ownership) is visible only as a generic flash message to whichever operator happened to be at the keyboard at that moment, with nothing in the service log for later diagnosis. This exactly matches `server/plane/manual_resolutions.py`'s own pre-existing silent-swallow shape (`add_entry()`/`delete_entry()`), so it is copied precedent rather than a regression, and is therefore Info rather than Warning.
**Fix:** Add a one-line `print("colour_rules: write to %s failed: %s: %s" % (path, type(exc).__name__, exc))` in the `except` clause of both `add_rule()` and `delete_rule()` (capturing `exc` by naming the exception), matching this codebase's `_save_to_gallery()`-style "log and continue" convention elsewhere in the same file tree. Consider filing the same fix against `manual_resolutions.py` at the same time so the two registries stay in step, since it is not this phase's job to fix that file on its own.

---

_Reviewed: 2026-09-06T16:37:49Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
