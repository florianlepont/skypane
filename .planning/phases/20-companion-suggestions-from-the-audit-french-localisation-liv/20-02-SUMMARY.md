---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 02
subsystem: infra
tags: [device-config, ssrf, urllib, notifications, wake-scheduling, python]

# Dependency graph
requires:
  - phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
    provides: "the screen_id registry pattern this plan's notifications field copies (membership test on read, raise on write, additive-no-migration on disk)"
  - phase: 16-per-direction-themes-per-flight-colour-rules-and-roster-link
    provides: "server/plane/calendar_rules.py's _url_is_safe()/default_calendar_transport() SSRF-gate-plus-injectable-transport pattern, reused verbatim by server/notify.py"
provides:
  - "server/wake.py — the wake-interval/staleness-threshold arithmetic moved out of companion/, so server/poll_loop.py can import it without ever importing companion/"
  - "companion/wake.py — a 3-line re-export shim preserving every existing call site and pinned test"
  - "server/notify.py — send_notification()/default_notify_transport()/body_for_lang(), an SSRF-gated, never-raising, transport-injectable ntfy-style push sender"
  - "server/device_config.py — DEFAULT_NOTIFICATIONS/normalise_notifications(), the registry's first dict-valued field, wired into load_device_config()/save_device_config()"
affects: [20-05-poll-loop-notification-hook, 20-11-device-page-notifications-group]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "server/-side leaf module moved out of companion/ behind a re-export shim, so server/poll_loop.py never imports companion/ (D-27)"
    - "SSRF gate reuse: server/notify.py's first line calls calendar_rules._url_is_safe() verbatim rather than re-deriving a second scheme/host/private-IP check"
    - "dict-valued device_config.py field: normalise_*() degrades wholesale for a non-dict value and per-sub-key for a malformed dict, matching every scalar normaliser's own read/write split"

key-files:
  created: [server/wake.py, server/notify.py, server/test_notify.py]
  modified: [companion/wake.py, server/device_config.py, server/test_config_history.py, scripts/run_all_tests.py, companion/test_config_page.py]

key-decisions:
  - "The 'config-history' language in this plan's Task 3 threat model (T-20-12, 'history records set/cleared, never the URL') does not map to any existing history/audit-log mechanism in this codebase — confirmed by inspection of server/history_db.py, server/plane/calendar_rules.py's own write-only URL handling, and every prior phase's device_config.py field. No sibling field (theme, led_enabled, the calendar feed URL) writes to any such log. Rather than invent a new architecture absent from this plan's files_modified list (Rule 4 boundary), T-20-12 is satisfied within this file's real scope: device_config.py stays print-free by design (its own pre-existing module contract), pinned by a new source-scan check proving the notifications addition introduces no print()/logging call. The UI-side write-only rendering half of T-20-12 (no value attribute, Configured/Not configured status row) is correctly deferred to the Device-page plan that renders it."
  - "server/notify.py uses stdlib urllib.request rather than requests, per D-25's explicit stdlib preference — this module adds no new dependency to server/requirements.txt."

requirements-completed: [CFG-17]

# Metrics
duration: 55min
completed: 2026-09-11
---

# Phase 20 Plan 02: Server-side notification seams Summary

**server/wake.py (moved from companion/wake.py behind a shim), server/notify.py (SSRF-gated stdlib-urllib ntfy push sender), and a first dict-valued `notifications` field in server/device_config.py's registry**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-11T20:50:00Z (approx.)
- **Completed:** 2026-09-11T21:45:25Z
- **Tasks:** 3
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments
- Moved the wake-interval/staleness-threshold arithmetic to `server/wake.py`; `companion/wake.py` is now a 3-line re-export shim, so `server/poll_loop.py` (a later plan) can share the exact thresholds Home/Health display without the server ever importing anything under `companion/` (D-27)
- Built `server/notify.py`: an SSRF-gated (`calendar_rules._url_is_safe()`, reused verbatim), never-raising, transport-injectable ntfy-style push sender using stdlib `urllib.request` only, plus `body_for_lang()` carrying the four French transition strings from 20-UI-SPEC.md §G
- Added the `notifications` config group to `server/device_config.py` — the registry's first dict-valued field — with `DEFAULT_NOTIFICATIONS`/`normalise_notifications()` following the existing "degrade on read, raise on write" contract, wired additively into `load_device_config()`/`save_device_config()`

## Task Commits

Each task was committed atomically:

1. **Task 1: Move the wake arithmetic to server/wake.py behind a re-export shim** - `a49fa6c` (refactor)
2. **Task 2: server/notify.py — the SSRF-gated, never-raising ntfy POST, and its harness** - `8703ef0` (feat)
3. **Task 3: the notifications config group in server/device_config.py** - `3f27873` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/wake.py` - the wake-interval/staleness-threshold arithmetic, moved verbatim from `companion/wake.py`
- `companion/wake.py` - shrunk to a 3-line re-export shim over `server/wake.py`
- `server/notify.py` - `send_notification()`, `default_notify_transport()`, `body_for_lang()`, the four English/French transition body strings, the "Send a test" title/body constants
- `server/test_notify.py` - 7 checks: success/500/timeout/arbitrary-exception, the four-URL SSRF-refusal-with-call-counter check, `body_for_lang()`'s round trip, and `default_notify_transport()`'s request shape against a faked `urlopen()`
- `scripts/run_all_tests.py` - registered `server/test_notify.py` and `companion/test_i18n.py` (created by 20-01 in this wave) in the canonical harness list
- `server/device_config.py` - `DEFAULT_NOTIFICATIONS`/`normalise_notifications()`, wired into `load_device_config()`/`save_device_config(notifications=None)`
- `server/test_config_history.py` - retargeted 9 pre-existing full-config dict-equality checks; added 5 new checks; `EXPECTED_CHECK_COUNT` 64 → 69
- `companion/test_config_page.py` - one full-dict save round-trip assertion retargeted (see Deviations)

## Decisions Made
- **T-20-12 scoping (see key-decisions above):** implemented the achievable, real mitigation within `server/device_config.py`'s own scope (print-free-by-design, pinned by a source scan) rather than inventing a new "config history" audit-log subsystem the codebase has no precedent for and this plan's `files_modified` list does not include. The UI-side write-only rendering contract remains the Device-page plan's job.
- `server/notify.py` reuses `calendar_rules._url_is_safe()` by importing `server.plane.calendar_rules` directly — never a second, independently-written SSRF check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retargeted a stale full-dict equality assertion in `companion/test_config_page.py`**
- **Found during:** Task 3 (device_config.py's new `notifications` field)
- **Issue:** `load_device_config()` now always returns a `notifications` key; one pre-existing check in `companion/test_config_page.py` ("a post with a valid theme and runway writes both and returns the saved flash key") does a full-dict equality against `load_device_config()`'s output, so it started failing (180/181) — the identical class of break phases 15/16/19 each caused in this same file when they added `theme_arriving`/`calendar_theme_id`/`screen_id`.
- **Fix:** Added `"notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}` to the one expected dict literal, with a comment citing this plan, mirroring the three prior mechanical fixes already documented inline above it.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `python3 companion/test_config_page.py` → 181/181 (unchanged from baseline)
- **Committed in:** `3f27873` (Task 3 commit)

- **Boundary note:** `companion/test_config_page.py` is not in this plan's `files_modified` list and is not owned by any sibling wave-1 plan per this worktree's `project_specifics` (unlike phase 15's precedent, where the owning plan was already named and explicitly boundary-fenced). Fixed inline rather than deferred, since this plan's own `<verification>` block explicitly requires this file's count to stay unchanged, and leaving it broken would red the whole suite for anyone running it before whichever later plan touches `companion/pages/config_page.py` lands.

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — a direct, mechanical consequence of this plan's own additive registry change. No scope creep beyond the one dict literal.

## Issues Encountered
None beyond the two grep-based acceptance-criteria false positives caught and fixed during implementation (a docstring's own prose tripping the literal `str(exc)`/`companion` substring checks in `server/notify.py` and `server/wake.py` — reworded, not a logic change).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/wake.py`, `server/notify.py`, and `server/device_config.py`'s `notifications` group are all available for 20-05 (the poll-loop notification hook) and 20-11 (the Device-page Notifications group) to wire against — this plan's own scope was seams only, no page-rendering or poll-loop changes.
- `companion/test_i18n.py` is registered in `scripts/run_all_tests.py`'s canonical list but does not exist inside this plan's worktree (created by 20-01 in the same wave) — the full suite (`scripts/run-all-tests.sh`) will not go green until that sibling plan's commits land; this was a deliberate, plan-specified exclusion, not an oversight.
- No blockers for downstream plans.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-11*

## Self-Check: PASSED

All 8 claimed files found on disk; all 3 task commit hashes (`a49fa6c`, `8703ef0`, `3f27873`) found in `git log --oneline --all`.
