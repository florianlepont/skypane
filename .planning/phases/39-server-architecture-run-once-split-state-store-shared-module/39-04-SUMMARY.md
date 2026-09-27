---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 04
subsystem: server
tags: [ssrf, http, refactor, package-split, calendar, notify]

requires:
  - phase: 39-01
    provides: "scripts/check_function_size.py (the ≤80-code-line gate used to verify pinned_request's split and the whole calendar_rules package)"
provides:
  - "server/net/safe_fetch.py: the one SSRF gate (url_is_safe/host_is_safe/USER_AGENT), shared by calendar_rules and notify"
  - "server/plane/calendar_rules/ package: ics.py, registry.py, match.py plus an __init__.py that keeps the orchestration and re-exports the full historical surface"
  - "server/http_fetch.py: pinned_request split into _resolve_pinned_target/_open_pinned_connection/_send_pinned_request, each ≤80 code lines"
affects: [40, notify, calendar_rules, http_fetch]

tech-stack:
  added: []
  patterns:
    - "Alias-not-copy re-export: a moved function/constant is assigned to its old name (USER_AGENT = safe_fetch.USER_AGENT) so identity tests can prove one gate exists, not two"
    - "Package split via git mv to __init__.py first, then carve submodules out - preserves the file's history on the file git ends up treating as the continuation"
    - "One-directional submodule imports inside a package (registry imports ics; match imports both; neither imports the package __init__) to avoid import cycles"

key-files:
  created:
    - server/net/__init__.py
    - server/net/safe_fetch.py
    - server/test_safe_fetch.py
    - server/plane/calendar_rules/ics.py
    - server/plane/calendar_rules/registry.py
    - server/plane/calendar_rules/match.py
  modified:
    - server/plane/calendar_rules.py (git mv'd to server/plane/calendar_rules/__init__.py, then reduced to orchestration + re-exports)
    - server/notify.py
    - server/http_fetch.py
    - server/test_notify.py
    - server/test_calendar_rules.py

key-decisions:
  - "CALENDAR_MAX_RAW_EXAMINED lives in ics.py (bounds VEVENT collection during parsing) and registry.py imports it from ics, rather than duplicating it, to keep the one-directional registry-imports-ics rule intact."
  - "CALENDAR_FETCH_INTERVAL_S lives in registry.py (calendar_fetch_is_due's own default), not in __init__.py alongside the other CALENDAR_FETCH_* constants, because __init__ cannot be imported back into registry without creating a cycle."
  - "_normalise_calendar_url stays in registry.py (calendar-specific webcal handling, grouped with the other secret/registry helpers), not in __init__.py or safe_fetch, matching the plan's own module-content list."
  - "ics.py and match.py were typed (parameter/return annotations, 3.11-compatible syntax) in a small follow-up commit after the initial split commit, once it was noticed 'typed from birth' per the plan applied to both, not only to safe_fetch.py."

requirements-completed: [ARC-01, ARC-03]

duration: 26min
completed: 2026-09-27
---

# Phase 39 Plan 04: Shared SSRF gate and calendar_rules package split Summary

**One `server/net/safe_fetch.url_is_safe()` now backs both the calendar feed fetch and the ntfy push (notify.py no longer imports calendar_rules at all), `server/plane/calendar_rules.py` (1433 lines) is a package of `ics`/`registry`/`match` submodules behind an unchanged public import path, and `http_fetch.pinned_request` is split under the 80-code-line gate with identical behaviour.**

## Performance

- **Duration:** ~26 min
- **Tasks:** 2/2 completed
- **Files modified/created:** 11 (6 created, 5 modified; 1 of the modified files, `calendar_rules.py`, was git-mv'd into the new package's `__init__.py`)

## Accomplishments

- `server/net/safe_fetch.py` (typed, `from __future__ import annotations`) holds `USER_AGENT`, `_address_is_public`, `host_is_safe` and `url_is_safe`, moved verbatim from `calendar_rules`'s old SSRF section. `calendar_rules`'s own `USER_AGENT`/`_address_is_public`/`_host_is_safe`/`_url_is_safe` are now identity aliases of these, and `fetch_ics()`'s redirect-hop check calls `safe_fetch.url_is_safe` directly.
- `notify.py` no longer imports `server.plane.calendar_rules` at all (`grep -n "calendar_rules" server/notify.py` returns nothing) — it imports `server.net.safe_fetch` for both the gate and `USER_AGENT`, with its module docstring and the `test_notify.py` comment naming the old `_host_is_safe()` location updated to point at `server/net/safe_fetch.py`.
- `http_fetch.pinned_request` (85 code lines, over the plan's 80-line gate) is split into `_resolve_pinned_target` / `_open_pinned_connection` / `_send_pinned_request`; the public signature, every exception type raised, deadline handling and pinning order are unchanged, and all of `test_http_fetch.py`'s existing tests pass unmodified.
- `server/plane/calendar_rules.py` became a package: `ics.py` (RFC 5545 parsing — `unfold_ics_lines`/`split_property`/`parse_ics_datetime`/`_build_entry`/`parse_ics_events` plus the shared IATA/UTC allowlists and `CALENDAR_MAX_RAW_EXAMINED`), `registry.py` (the `calendar_rules.json`/`calendar_url.secret` file contract, the cross-process lock, load/write/save, retention windowing/capping, the throttle predicate, secret-mode checks and `_normalise_calendar_url`), `match.py` (`match_calendar_theme` and its IATA/far-end/reference-time helpers, typed). `__init__.py` keeps `default_calendar_transport`/`fetch_ics`/`refresh_calendar_registry` (the once-per-cycle entry point) plus the Task 1 SSRF aliases, and re-exports every name this codebase's callers and tests read off `calendar_rules` today.
- Import direction is acyclic by construction: `registry` imports `ics` (for the shared allowlists and the raw-examination bound); `match` imports both `ics` and `registry`; neither submodule imports the package `__init__`.
- A new surface test in `server/test_calendar_rules.py` (`test_package_exposes_every_name_callers_and_tests_use`) asserts `hasattr()` over a literal, grep-derived list of every name any caller or test in `server/` or `companion/` reads off `calendar_rules` today, including the required privates `_url_is_safe`, `_normalise_calendar_url`, `_normalise_calendar_entry`, `_build_entry` and `os`. Two more tests prove `cr.default_calendar_transport` assignment is still honoured by `fetch_ics()` (the companion's `stubbed_calendar_transport` contract relies on this bare-name lookup inside `__init__.py`'s own module globals) and that `cr.os is os` by identity (so the existing `os.open`/`os.replace`/`os.chmod`/`os.remove`/`os.fdopen` monkeypatches in this test file keep reaching `registry.py`'s real file operations). A fourth test proves neither `server/plane/calendar/` nor `server/plane/calendar.py` exists, since either would shadow the stdlib `calendar` module.
- No file under `companion/` was touched by either task (`git diff --name-only` across both commits lists none) — the package keeps the stable `server.plane.calendar_rules` import path per CONTEXT decision D-2, so Phase 40's parallel companion work needs no edits for this plan.

## Task Commits

1. **Task 1: server/net/safe_fetch.py owns the URL gate; notify switches; pinned_request split** - `28c4c75` (test, RED) / `526364b` (feat, GREEN)
2. **Task 2: server/plane/calendar_rules becomes a package (ics, registry, match, orchestration in __init__)** - `8fe92d8` (feat) / `ce55396` (feat, follow-up typing fix)

## Files Created/Modified

- `server/net/__init__.py` - package docstring only
- `server/net/safe_fetch.py` - `USER_AGENT`, `_address_is_public`, `host_is_safe`, `url_is_safe`; typed
- `server/test_safe_fetch.py` - the gate's own behaviour tests plus the identity/decoupling proofs (calendar_rules aliases, notify has no `calendar_rules` attribute)
- `server/plane/calendar_rules/__init__.py` - orchestration (`default_calendar_transport`, `fetch_ics`, `refresh_calendar_registry`) + explicit re-exports of the full historical surface
- `server/plane/calendar_rules/ics.py` - RFC 5545 subset parser; typed
- `server/plane/calendar_rules/registry.py` - registry/secret file contract, lock, throttle, window
- `server/plane/calendar_rules/match.py` - `match_calendar_theme`; typed
- `server/notify.py` - imports `server.net.safe_fetch` instead of `server.plane.calendar_rules`
- `server/http_fetch.py` - `pinned_request` split into three private helpers, module docstring pointer updated
- `server/test_notify.py` - comment naming the old `_host_is_safe()` location updated
- `server/test_calendar_rules.py` - four new tests: full-surface `hasattr`, `default_calendar_transport` assignment contract, `cr.os` identity, no plain-`calendar` name

## Decisions Made

See `key-decisions` in the frontmatter above: `CALENDAR_MAX_RAW_EXAMINED` placed in `ics.py` (registry imports it) rather than duplicated; `CALENDAR_FETCH_INTERVAL_S` placed in `registry.py` (its only caller, `calendar_fetch_is_due`) rather than alongside the other fetch-bound constants in `__init__.py`, since `registry` cannot import `__init__` without a cycle; `_normalise_calendar_url` stays in `registry.py`; `ics.py`/`match.py` typed in a small follow-up commit after noticing the plan's "typed from birth" instruction named both modules, not only `safe_fetch.py`.

## Deviations from Plan

None - plan executed exactly as written. The follow-up typing commit (`ce55396`) is not a deviation from the plan's requirements (both files needed type hints per the plan's own conventions section); it is recorded as a separate commit because the split commit was already complete and green, and adding hints afterward kept each commit's diff reviewable and its own verification unambiguous.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None — the SSRF gate (T-39-07), the `pinned_request` split (T-39-08) and the exception-type-only logging (T-39-09) were all moved/split verbatim per the plan's own threat register; no new network endpoint, auth path, file-access pattern or schema change was introduced. Both existing SSRF test suites (`test_calendar_rules.py`'s address-gate tests, `test_notify.py`'s SSRF-refusal test) pass unchanged, and `test_safe_fetch.py` adds direct coverage of the shared gate itself.

## Next Phase Readiness

- ARC-03's calendar-package/`net/safe_fetch`/notify-decoupling clauses and ARC-01's `pinned_request` size clause are functionally complete; per this phase's own convention (39-02's premature tick was reverted), REQUIREMENTS.md is left untouched here — only the phase's close-out plan (39-13) flips ARC-* to Complete.
- `server/plane/render.py` splitting and `device_config.py`'s theme-logic extraction (the rest of ARC-03) are not started by this plan and remain open for a later plan in this phase.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: server/net/__init__.py
- FOUND: server/net/safe_fetch.py
- FOUND: server/test_safe_fetch.py
- FOUND: server/plane/calendar_rules/__init__.py
- FOUND: server/plane/calendar_rules/ics.py
- FOUND: server/plane/calendar_rules/registry.py
- FOUND: server/plane/calendar_rules/match.py
- FOUND commit: 28c4c75
- FOUND commit: 526364b
- FOUND commit: 8fe92d8
- FOUND commit: ce55396
