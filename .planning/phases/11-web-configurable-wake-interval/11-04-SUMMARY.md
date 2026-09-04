---
phase: 11-web-configurable-wake-interval
plan: 04
subsystem: config
tags: [python, environment-variables, systemd, companion-app, prefill]

# Dependency graph
requires:
  - phase: 11-web-configurable-wake-interval (plan 11-01)
    provides: "server/device_config.py's WAKE_INTERVAL_MIN_S/MAX_S bounds this plan's environment read is checked against"
  - phase: 11-web-configurable-wake-interval (plan 11-03)
    provides: "companion/pages/config_page.py's render() ctx['wake_interval_env_default'] fallback resolution, the sole consumer of this plan's ctx key"
provides:
  - "companion/app.py's SLEEP_ENV_VAR ('SKYPANE_SLEEP_S') constant and env_wake_interval_default() — a per-call, never-raising, bounds-checked environment reader mirroring companion/auth.py's configured_password() shape but fail-open instead of fail-closed"
  - "page_context()'s new wake_interval_env_default ctx key, documented in companion/pages/__init__.py's ctx contract"
  - "deploy/skypane.env.example's SKYPANE_SLEEP_S comment corrected to describe it as an overridable fallback, not the sole cadence source"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-open environment reader mirroring an existing fail-closed one: env_wake_interval_default() copies configured_password()'s per-call os.environ.get() shape but returns None on any failure instead of raising, because its absence has a designed empty state (a placeholder) rather than an auth boundary to guard"

key-files:
  created: []
  modified:
    - companion/app.py
    - companion/pages/__init__.py
    - companion/test_companion_app.py
    - deploy/skypane.env.example

key-decisions:
  - "env_wake_interval_default() is deliberately not imported from companion/auth.py — that module owns the password variable's name, not the sleep-interval one, and the two constants have unrelated lifecycles"
  - "The [60, 3600] range check on the environment value is a Denial-of-Service guard, not belt-and-braces: an out-of-range value rendered as a value attribute on a min/max-bounded number input would fail HTML5 constraint validation and block submission of the whole Settings form, not just the one field"

patterns-established:
  - "A fail-open sibling to an existing fail-closed environment reader: same per-call os.environ.get() shape, same never-cache-at-import-time discipline, contract difference documented explicitly in the docstring against the function a reader will naturally compare it to"

requirements-completed: []  # this plan's own frontmatter declares requirements: [] (unmapped backlog phase promoted from SEED-002, per 11-RESEARCH.md <phase_requirements>)

coverage:
  - id: D1
    description: "companion/app.py reads SKYPANE_SLEEP_S from its own process environment per-request (never cached at import time), converts and bounds-checks it without ever raising, across its whole input space including unset, empty, non-numeric, whitespace-padded, and the shipped below-floor 30"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_env_wake_interval_default_full_input_space"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#_page_context_threads_wake_interval_env_default"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Settings page pre-fills Wake interval with the deployed SKYPANE_SLEEP_S when it is in range and nothing is stored on disk; an on-disk wake_interval_s always wins over the environment value"
    verification:
      - kind: e2e
        ref: "companion/test_companion_app.py#_wake_interval_env_prefill_and_on_disk_precedence"
        status: pass
    human_judgment: false
  - id: D3
    description: "A below-floor deployed environment value (deploy/skypane.env.example's shipped SKYPANE_SLEEP_S=30) degrades to the field's placeholder empty state, never a value attribute the form could not submit"
    verification:
      - kind: e2e
        ref: "companion/test_companion_app.py#_wake_interval_below_floor_env_degrades_to_placeholder"
        status: pass
    human_judgment: false
  - id: D4
    description: "Neither systemd unit file changed, and SKYPANE_SLEEP_S's configured value is unchanged — only its documenting comment was corrected"
    verification:
      - kind: other
        ref: "git diff --quiet deploy/skypane-companion.service deploy/skypane-byos.service"
        status: pass
    human_judgment: false

# Metrics
duration: 24min
completed: 2026-09-04
status: complete
---

# Phase 11 Plan 04: Companion Environment Pre-fill Summary

**`companion/app.py` reads `SKYPANE_SLEEP_S` from its own process environment via a new fail-open `env_wake_interval_default()`, threading it into the page context as `wake_interval_env_default` so plan 11-03's Settings page pre-fills Wake interval with the real deployed cadence instead of an empty box.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-04T06:06:44Z
- **Completed:** 2026-09-04T06:30:43Z
- **Tasks:** 2 completed
- **Files modified:** 4

## Accomplishments
- `SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"` and `env_wake_interval_default()` added to `companion/app.py`, mirroring `auth.configured_password()`'s per-call `os.environ.get()` shape but fail-open (returns `None` on any failure) rather than fail-closed, with the contract difference documented in the docstring
- The reader is never-raising across its whole input space: unset, empty, non-numeric, `"1.5"`, negative, whitespace-padded (`int()` tolerates it), and every out-of-`[60, 3600]` value — verified against exactly `[None, None, 900, None, None, None, None, None, None, 60, 3600, 900]` for the plan's twelve canonical test inputs
- `page_context()` now returns `"wake_interval_env_default": env_wake_interval_default()` alongside `"device_config"`, and `companion/pages/__init__.py`'s documented `ctx` contract names the new key, its type, its source, and its sole consumer (`config_page.render()`'s pre-fill fallback)
- `deploy/skypane.env.example`'s `SKYPANE_SLEEP_S` comment now describes it as an overridable fallback the Settings page can supersede per-device, and names the companion process's own pre-fill read and its 60-3600s bounds — with no change to the shipped `30` value or either systemd unit file
- Added 4 new checks to `companion/test_companion_app.py`: a full-input-space unit check on `env_wake_interval_default()`, a `page_context()`-threading check against a minimal fake `Handler` bound to the real unbound method (proving the key is always present, never conditionally omitted), and two real-HTTP end-to-end checks over dedicated `Harness` instances proving on-disk precedence over the environment and the below-floor-degrades-to-placeholder guard — `EXPECTED_CHECK_COUNT` 125 → 129

## Task Commits

Each task was committed atomically:

1. **Task 1: Read SKYPANE_SLEEP_S from the environment into the page context** - `5c6db08` (feat)
2. **Task 2: Add environment pre-fill coverage to test_companion_app.py** - `a768052` (test)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `companion/app.py` - Adds `SLEEP_ENV_VAR`, `env_wake_interval_default()`, and the `page_context()` `wake_interval_env_default` key
- `companion/pages/__init__.py` - Documents the new `ctx` key in the page-context contract
- `companion/test_companion_app.py` - Adds `from server import device_config` import, 4 new checks (2 in Section 1/2's in-process area, 2 in Section 3's real-HTTP-harness area), bumps `EXPECTED_CHECK_COUNT` 125 → 129
- `deploy/skypane.env.example` - Corrects the `SKYPANE_SLEEP_S` comment to describe the fallback/pre-fill relationship; no value or unit-file change

## Decisions Made
- `env_wake_interval_default()` is a standalone constant/function in `companion/app.py`, not imported from or added to `companion/auth.py` — the two environment variables have unrelated lifecycles and ownership
- The `[60, 3600]` range check is load-bearing as a form-submittability guard, not merely defensive parsing: an out-of-range environment value rendered as a native `value` attribute would fail HTML5 constraint validation and block the entire Settings form's submission, not just the Wake interval field
- Task 2's `page_context()` threading check calls the real, unbound `Handler.page_context` method against a minimal hand-built stand-in object (only the four attributes that method reads), rather than mocking or reimplementing the method — this proves the actual production code path

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria (the exact twelve-case env-conversion output, both harness exit codes, ruff, every named grep, and the unchanged unit files) verified as specified.

## Issues Encountered
None.

## Known Stubs
None — every code path this plan touches is fully wired (no hardcoded empty values, no unwired data sources).

## Threat Flags
None — this plan's threat surface (the environment read, the range-checked conversion, the `ctx` key threading into `config_page.render()`'s existing consumer) is exactly what `11-04-PLAN.md`'s own `<threat_model>` already enumerates (T-11-04-01 through T-11-04-04); no new surface was introduced beyond it.

## User Setup Required
None - no external service configuration required. `deploy/skypane-companion.service`'s existing `EnvironmentFile=/opt/skypane/skypane.env` directive already delivers `SKYPANE_SLEEP_S` to this process on any already-deployed VPS with no restart-time or unit-file change needed beyond the next normal service restart picking up a corrected comment.

## Next Phase Readiness
- All three of D-07's pieces are now in place across plans 11-01/11-03/11-04: the registry field, the Settings form field, and the environment pre-fill — the end-of-phase human-verify pass (`workflow.human_verify_mode = end-of-phase`) should cover plan 11-03's deferred Task 2 `<human-check>` (real-browser visual verification) alongside this plan's own environment-pre-fill behaviour in one combined pass
- `scripts/run-all-tests.sh` shows `PASS` overall with no new regression; the pre-existing `server/test_poll_loop.py` `panel.bin` digest mismatch is the documented non-Linux/Pillow-FreeType difference (informational on Darwin, Linux/CI-authoritative), unrelated to this plan

---
*Phase: 11-web-configurable-wake-interval*
*Completed: 2026-09-04*

## Self-Check: PASSED
- FOUND: companion/app.py
- FOUND: companion/pages/__init__.py
- FOUND: companion/test_companion_app.py
- FOUND: deploy/skypane.env.example
- FOUND: .planning/phases/11-web-configurable-wake-interval/11-04-SUMMARY.md
- FOUND: 5c6db08
- FOUND: a768052
