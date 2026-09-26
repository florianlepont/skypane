---
phase: 36-state-integrity-and-device-protocol
plan: 05
subsystem: infra
tags: [ssrf, dns-rebinding, tls, http-fetch, atomic-write, calendar, notify, ical]

# Dependency graph
requires:
  - phase: 36-01
    provides: "server/atomic_io.py: atomic_write, staged_write, exclusive_lock, LockBusy"
  - phase: 36-02
    provides: "server/http_fetch.py: pinned_request, bounded_get, address_is_public, DeadlineExceeded"
provides:
  - "server/plane/calendar_rules.py: default_calendar_transport() and fetch_ics() go through http_fetch.pinned_request(), bounded by CALENDAR_FETCH_DEADLINE_S across every redirect hop"
  - "server/plane/calendar_rules.py: _calendar_registry_lock() delegates to atomic_io.exclusive_lock(); write_calendar_registry()/save_calendar_url() write through atomic_io.atomic_write()/staged_write()"
  - "server/plane/calendar_rules.py: refresh_calendar_registry() releases the registry lock during the network fetch, adds FETCH_SUPERSEDED, and derives last_synced_at from the injected now"
  - "server/notify.py: default_notify_transport() goes through http_fetch.pinned_request(), bounded by NOTIFY_DEADLINE_S; the urllib _NoRedirectHandler/_NO_REDIRECT_OPENER machinery is retired"
affects: [36-07, 39-arc-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pinned outbound HTTP for every owner-supplied URL (calendar feed, ntfy topic): default_*_transport() wrappers call http_fetch.pinned_request() instead of requests/urllib, so the socket only ever reaches an address http_fetch itself resolved and checked"
    - "Three-step refresh under a briefly-held lock, then no lock, then briefly-held lock again: record the throttle attempt before releasing, fetch outside any lock, re-check the configured URL after re-acquiring before ever writing"

key-files:
  created: []
  modified: [server/plane/calendar_rules.py, server/notify.py, server/test_calendar_rules.py, server/test_notify.py]

key-decisions:
  - "INT-14 decision from CONTEXT (pin, not just correct the docstring) applied to both remaining outbound calls in this phase: the calendar feed (already had _url_is_safe()'s DNS-based early gate) and the ntfy topic now both connect through http_fetch.pinned_request(), which resolves once, checks every answer, and connects only to a checked address - closing the TOCTOU gap where requests/urllib re-resolve at connect time."
  - "_host_is_safe()'s docstring is corrected rather than removed: it stays a real, useful early refusal (an obviously-unsafe literal address needs no network fetch to reject, and it runs before EVERY redirect hop), but the DNS-rebinding protection claim moved to where it actually lives - pinned_request() never re-resolving between its own check and its connect."
  - "refresh_calendar_registry()'s three-step restructuring keeps the outer never-raise try/except and the existing result-code contract intact; the only caller-visible addition is FETCH_SUPERSEDED, and both companion/app.py call sites already compare only against FETCH_OK, so neither needed a change."
  - "_url_is_safe() (and its DNS-based _host_is_safe()/_address_is_public() helpers) stays in calendar_rules.py, reused by notify.py, until Phase 39's ARC-03 moves the pinned-fetch primitive and this gate into a shared net/safe_fetch.py - unchanged from the 36-02 SUMMARY's own note, reconfirmed here since this plan was the last consumer of the old shape."
  - "requirements-completed lists all four from this plan's frontmatter, but only INT-12 and INT-14 are marked Complete in REQUIREMENTS.md this plan: INT-02 and INT-07 are genuine, real changes here (the calendar's writers/lock now use atomic_io; the calendar fetch and notify POST both carry a total deadline) but are only fully delivered project-wide once 36-06 (detect/enrich/adsbdb) and 36-07 (poll_loop, the unit's TimeoutStartSec proof) land their own pieces - per this plan's own environment notes, they stay Pending until then."

patterns-established:
  - "Pattern: default_*_transport(url, ...) wrappers hide http_fetch.pinned_request() behind the exact signature callers/tests already depend on (calendar_rules keeps (url, timeout); notify keeps (url, title, body, timeout)) - a caller migrating onto the pinned primitive needs zero call-site changes."
  - "Pattern: a fetch's total deadline is checked before every hop/attempt and after every chunk, with each hop's own timeout clamped to min(per_call_timeout, time_left) - first done for the calendar feed in 36-02's bounded_get()/pinned_request(), now threaded through fetch_ics()'s own redirect loop as a second, independent deadline layer."

requirements-completed: [INT-12, INT-14]

# Metrics
duration: 21min
completed: 2026-09-26
---

# Phase 36 Plan 05: Calendar and notify hardening Summary

**Both owner-supplied outbound URLs (the calendar iCal feed and the ntfy push topic) now connect through `http_fetch.pinned_request()` instead of a plain `requests.get()`/urllib opener, closing the DNS-rebinding TOCTOU gap; `fetch_ics()` carries a 10s total deadline across every redirect hop; `refresh_calendar_registry()` no longer holds the cross-process registry lock during the network fetch, and reports `FETCH_SUPERSEDED` when a companion save/disconnect lands mid-fetch; the calendar's writers and lock now go through `atomic_io`.**

## Performance

- **Duration:** ~21 min
- **Started:** 2026-09-26T08:54:00Z (approx., first read of the plan, right after 36-04 completed)
- **Completed:** 2026-09-26T09:15:30Z
- **Tasks:** 3 (all TDD)
- **Files modified:** 4 (`server/plane/calendar_rules.py`, `server/notify.py`, `server/test_calendar_rules.py`, `server/test_notify.py`; no files created)

## Accomplishments
- **Task 1 (INT-14, INT-07, INT-02 for the calendar side):** `default_calendar_transport()` now calls `http_fetch.pinned_request("GET", ...)` instead of `requests.get()`. `_address_is_public()` delegates to `http_fetch.address_is_public()`; `_host_is_safe()`'s docstring is corrected to describe itself as an early refusal only (the real DNS-rebinding protection is `pinned_request()`'s single resolve-then-connect). `fetch_ics()` gained a total wall-clock deadline (`CALENDAR_FETCH_DEADLINE_S = 10.0`, checked before every hop and after every chunk) on top of a smaller per-hop timeout (`CALENDAR_FETCH_TIMEOUT_S`, now `5.0`), each hop clamped to `min(timeout, time_left)`. `_calendar_registry_lock()` now delegates to `atomic_io.exclusive_lock()`; `write_calendar_registry()` writes through `atomic_io.atomic_write()`; `save_calendar_url()`'s set/replace branch stages the new secret through `atomic_io.staged_write(mode=0o600)`, erasing the registry inside that block and publishing only once the erase succeeds. Both replace the old pid/thread-tagged `.tmp` temp names.
- **Task 2 (INT-12):** `refresh_calendar_registry()` restructured into three steps: (a) under the lock, load, check unconfigured/throttled, and — only when due — record the attempt (`last_attempt_at = now`) before releasing; (b) fetch and parse with NO lock held; (c) under the lock again, reload and re-check the configured URL — a mismatch (changed or cleared mid-fetch) discards the stale result outright via a new `FETCH_SUPERSEDED` result code, never overwriting whatever a concurrent save/disconnect already wrote. `last_synced_at` is now `datetime.fromtimestamp(now, timezone.utc)`, never `datetime.now()`.
- **Task 3 (INT-14, INT-07 for notify):** `default_notify_transport()` now POSTs through `http_fetch.pinned_request()`; the old `_NoRedirectHandler`/`_NO_REDIRECT_OPENER` urllib machinery is gone entirely, since `pinned_request()` never follows a redirect on its own. A new `NOTIFY_DEADLINE_S = 5.0` bounds the total call.
- 31 new/rewritten tests across the two test files, all passing, none opening a real socket (fake resolver/socket/SSL-context, matching `server/test_http_fetch.py`'s own byte-at-a-time raw-reader technique for the two end-to-end "no injected transport" tests).

## Task Commits

Each task is a test → feat pair (RED then GREEN):

1. **Task 1: calendar pinned transport, total deadline, atomic writes, lock delegation** - `9cfe12b` (test) + `ff678bc` (feat)
2. **Task 2: refresh_calendar_registry without the lock across the fetch, injected clock** - `82040ca` (test) + `b9475b8` (feat)
3. **Task 3: notify through the pinned primitive** - `65a47df` (test) + `8a821a0` (feat)

_No refactor commit was needed for any task._

## Files Created/Modified
- `server/plane/calendar_rules.py` - `default_calendar_transport()`/`fetch_ics()` pinned and deadline-bounded; `_calendar_registry_lock()`/`write_calendar_registry()`/`save_calendar_url()` on `atomic_io`; `refresh_calendar_registry()` restructured around a released lock and `FETCH_SUPERSEDED`; `CALENDAR_FETCH_TIMEOUT_S` lowered to 5.0, `CALENDAR_FETCH_DEADLINE_S` (10.0) added
- `server/notify.py` - `default_notify_transport()` on `http_fetch.pinned_request()`; `NOTIFY_DEADLINE_S` (5.0) added; `_NoRedirectHandler`/`_NO_REDIRECT_OPENER`/`urllib.request` removed
- `server/test_calendar_rules.py` - one temp-file-mode spy test adjusted to `atomic_io`'s mkstemp naming convention; new tests for the pinned default-transport path, a redirect hop to a private address, mid-stream deadline exhaustion, per-hop timeout clamping, the injected-clock `last_synced_at`, the lock-not-held-across-the-fetch race (both a save and a disconnect), and the pre-fetch `last_attempt_at` recording
- `server/test_notify.py` - the two `_NO_REDIRECT_OPENER`-patching tests rewritten against the real pinned path (fake socket/SSL context); one new wiring test for `NOTIFY_DEADLINE_S`

## Decisions Made
See `key-decisions` in the frontmatter. In short: pin both remaining outbound calls per CONTEXT's INT-14 decision; keep `_host_is_safe()` as a real (if narrower-than-documented) early refusal rather than deleting it; add exactly one new result code (`FETCH_SUPERSEDED`) with no caller change needed; leave `_url_is_safe()` in `calendar_rules.py` for Phase 39 (ARC-03) to relocate; mark only INT-12/INT-14 Complete in REQUIREMENTS.md this plan, per the environment notes.

## Deviations from Plan

None - plan executed exactly as written. The temp-file-mode spy test adjustment (`test_tmp_file_mode_is_0600_at_creation_time`) is not a deviation from the plan's own instructions: the plan's Task 1 action explicitly anticipated migrating this test's file-naming assumption ("existing property, now through staged_write"), and the fix is a same-behavior re-target of the spy's path-matching predicate onto `atomic_io`'s actual temp-naming convention, not a weakening of what the test asserts (the mode is still proven to be 0600 at creation and at rename time).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/plane/calendar_rules.py` and `server/notify.py` are the last two production consumers of the pre-pinned outbound-HTTP shape; both now share the exact `http_fetch.pinned_request()` primitive 36-02 landed, ready for Phase 39's ARC-03 to fold `_url_is_safe()`/`_host_is_safe()`/`_address_is_public()` into a shared `net/safe_fetch.py` alongside `http_fetch.py`.
- 36-06 (`server/plane/enrich.py`, `server/plane/detect.py`, `server/history_db.py`) still needs its own migration onto `http_fetch.bounded_get()`/`pinned_request()` for INT-07/INT-08/INT-09/INT-10 before those requirements can close.
- 36-07 (poll cycle) still needs INT-01 (the cross-process poll lock, with its two-process reproduction test), the remaining INT-02 sites (`poll_loop.py`'s `save_poll_state`/`write_panel_atomic`/gallery PNG, `companion/app.py`'s illustration upload temps), the unit-level INT-07 proof (`TimeoutStartSec` end-to-end against every upstream at its documented worst case), INT-11 and INT-13 - only after that does REQUIREMENTS.md mark INT-02/INT-07 Complete.
- No blockers for 36-06.

## Self-Check: PASSED

- FOUND: server/plane/calendar_rules.py (modified, present)
- FOUND: server/notify.py (modified, present)
- FOUND: server/test_calendar_rules.py (modified, present)
- FOUND: server/test_notify.py (modified, present)
- FOUND commit 9cfe12b (test, Task 1)
- FOUND commit ff678bc (feat, Task 1)
- FOUND commit 82040ca (test, Task 2)
- FOUND commit b9475b8 (feat, Task 2)
- FOUND commit 65a47df (test, Task 3)
- FOUND commit 8a821a0 (feat, Task 3)
- Full suite (`./scripts/run-all-tests.sh`): 2678 passed, 133 skipped (pre-existing Playwright-Chromium/root-euid skips), coverage 93.48% (floor 93.0%), exit 0

## TDD Gate Compliance

All three tasks show the required RED -> GREEN sequence in git log:
- Task 1: `9cfe12b test(36-05): ...` then `ff678bc feat(36-05): ...`
- Task 2: `82040ca test(36-05): ...` then `b9475b8 feat(36-05): ...`
- Task 3: `65a47df test(36-05): ...` then `8a821a0 feat(36-05): ...`

No REFACTOR commit was needed for any task.

---
*Phase: 36-state-integrity-and-device-protocol*
*Completed: 2026-09-26*
