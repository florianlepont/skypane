---
phase: quick-260923-9na
plan: 01
subsystem: testing
tags: [playwright, e2e, flaky-test, python]

# Dependency graph
requires: []
provides:
  - "Additive pre-wait (`fallback.wait_for(state=\"visible\")`) in `_with_no_script_the_fallback_save_is_the_only_way()`, decoupling the visibility leg of the fallback-Save click's actionability poll from `expect_navigation()`'s 30000ms clock"
  - "Identical additive pre-wait (`page.wait_for_selector(..., state=\"visible\")`) in the shared `_save_via_bar()` helper, pre-empting the same latent shape before its own CI report"
affects: [companion-test-browser-ux, ci-flake-floor]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lift the `visible` leg of Playwright actionability polling out of a `with page.expect_navigation():` block via a preceding `locator.wait_for(state=\"visible\")` / `page.wait_for_selector(..., state=\"visible\")` call, so it runs on its own timeout clock rather than sharing the navigation wait's budget."

key-files:
  created: []
  modified:
    - companion/test_browser_ux.py
    - companion/test_browser_ux_helpers.py

key-decisions:
  - "Applied both edits exactly as statement-for-statement specified in the plan (no timeout widened, no assertion/docstring changed, no other expect_navigation site touched) — the plan explicitly forbade re-investigating the diagnosis."
  - "Did not chase a second theory when post-fix runs kept failing, per explicit plan instruction under Task 2: reported the observation and handed the decision back rather than attempting a further fix in this quick task."

requirements-completed: [QUICK-260923-9na]

coverage:
  - id: D1
    description: "Pre-wait inserted before expect_navigation() in _with_no_script_the_fallback_save_is_the_only_way(), structurally verified (click/locator/navigation-wait unchanged, purely additive, no timeout added)"
    verification:
      - kind: unit
        ref: "AST gate (Task 1 verify block) — python -c 'import ast; ...' against companion/test_browser_ux.py"
        status: pass
      - kind: other
        ref: "git diff --numstat -- companion/test_browser_ux.py (0 deletions)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Byte-identical pre-wait inserted before expect_navigation(timeout=timeout) in the shared _save_via_bar() helper, selector structurally identical to the click's own"
    verification:
      - kind: unit
        ref: "AST gate (Task 2 verify block) — python -c 'import ast; ...' against companion/test_browser_ux_helpers.py"
        status: pass
      - kind: other
        ref: "git diff --numstat -- companion/test_browser_ux_helpers.py (0 deletions)"
        status: pass
    human_judgment: false
  - id: D3
    description: "companion/test_browser_ux_quiet_wake.py (the other consumer of _save_via_bar()) still passes in full after the helper edit"
    verification:
      - kind: e2e
        ref: "server/.venv/bin/python companion/test_browser_ux_quiet_wake.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "The fallback-Save flake is absent from four consecutive post-fix local runs of companion/test_browser_ux.py"
    verification:
      - kind: e2e
        ref: "server/.venv/bin/python companion/test_browser_ux.py, runs post1.log..post4.log"
        status: fail
    human_judgment: true
    rationale: "All four post-fix runs reproduced the fallback-Save failure (100%, not 0%) — the opposite of the plan's expected/hoped outcome. This is a genuine, surprising local measurement that a human must weigh before deciding whether further work on this check is warranted; automation cannot resolve what to do next."

duration: 114min
completed: 2026-09-23
status: complete
---

# Quick Task 260923-9na: Fallback-Save nav-budget decoupling — edits correct, local flake NOT resolved

**Both specified additive edits landed exactly as designed and pass every structural gate, but contrary to the plan's expectation, all four post-fix local runs still reproduced the fallback-Save failure — with the OTHER known signature (click-time DOM-detach/instability) rather than the one the fix targeted (navigation-clock starvation).**

## Performance

- **Duration:** ~1h 54m (mostly harness run time: baseline + 4 measurement runs at ~4.5 min each, plus one quiet-wake run)
- **Started:** 2026-09-23T07:08:00+02:00 (approx, first baseline run launch)
- **Completed:** 2026-09-23T09:02:00+02:00 (approx, last measurement run finished)
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments
- Inserted `fallback.wait_for(state="visible")` immediately before `with page.expect_navigation():` in `_with_no_script_the_fallback_save_is_the_only_way()` (`companion/test_browser_ux.py`), with an explanatory comment citing the 31ms CI observation. AST gate confirms: the click, its locator, and the navigation wait are structurally unchanged; no `timeout=` argument was added anywhere.
- Applied the identical decoupling pattern to the shared `_save_via_bar()` helper (`companion/test_browser_ux_helpers.py`) — `page.wait_for_selector("[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR, state="visible")` before its own `with page.expect_navigation(timeout=timeout):` block, with the pre-wait selector proven structurally identical (via `ast.dump` comparison) to the click's own selector.
- `companion/test_browser_ux_quiet_wake.py` — the other consumer of `_save_via_bar()` — still reports **9/9 checks pass, exit 0** after the helper edit.
- Both diffs are purely additive: `git diff --numstat` reports 0 deletions in both files; `git diff --stat` across both commits touches exactly the two files the plan specified, 20 insertions, 0 deletions.
- Neither `EXPECTED_CHECK_COUNT` nor any docstring, assertion, error message, or return value was touched in either file.

## Task Commits

Each task was committed atomically:

1. **Task 1: Lift the fallback Save's visibility wait out of the navigation budget in the no-script check** - `1be1343` (fix)
2. **Task 2: Apply the same decoupling to the shared `_save_via_bar` helper, then measure the flake floor over repeated runs** - `0b1430a` (fix)

_No plan-metadata commit was made — per this quick task's explicit constraints, docs artifacts (this SUMMARY, STATE.md) are committed by the orchestrator, not this executor._

## Files Created/Modified
- `companion/test_browser_ux.py` — one added statement (+comment) inside `_with_no_script_the_fallback_save_is_the_only_way()`
- `companion/test_browser_ux_helpers.py` — one added statement (+comment) inside `_save_via_bar()`

## Decisions Made
- Followed the plan's statement-for-statement specification exactly; did not re-derive or second-guess the root-cause diagnosis, per explicit plan instruction.
- When post-fix measurement contradicted the plan's expected outcome (see below), did not pursue a second theory or additional fix within this quick task — reported the observation and left the decision to the user, per the plan's own explicit instruction under Task 2 ("do not chase a second theory in this quick task — record the observation and hand the decision back").

## Deviations from Plan

None in the code — both edits match the plan's statement-for-statement specification exactly, and every structural (AST) gate passed on the first attempt for both files. The deviation is in the **measured outcome**, not the implementation; see "Issues Encountered" below, since this is a genuine test result rather than a rule-triggered auto-fix.

## Issues Encountered — the measurement did not confirm the fix locally

**This is the most important finding in this task and must not be lost:**

The plan's success criteria called for "four consecutive `companion/test_browser_ux.py` runs with the fallback-Save check absent from every FAIL set." The actual local measurement was the opposite:

| Run | PASS | FAIL | fallback-Save FAIL? |
|-----|------|------|----------------------|
| baseline (pre-edit) | 73 | 2 | No |
| post1 (after Task 1 edit) | 72 | 3 | **Yes** |
| post2 (after Task 2 edit) | 72 | 3 | **Yes** |
| post3 | 72 | 3 | **Yes** |
| post4 | 72 | 3 | **Yes** |

All four post-fix runs failed with the identical exception, every time:

```
Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-static-save-fallback]")
    - locator resolved to <button ... data-static-save-fallback="">...</button>
  - attempting click action
    2 x waiting for element to be visible, enabled and stable
      - element is not stable
    - retrying click action
    - waiting 20ms
  - element was detached from the DOM, retrying
    - locator resolved to <button ... data-static-save-fallback="">...</button>
  - attempting click action
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
```

This is **signature #1** from the plan's own root-cause diagnosis (`Locator.click: Timeout 30000ms exceeded ... element is not stable ... element was detached from the DOM`, previously attributed in `30-01-SUMMARY.md` to "an intermittent arm64-Chromium DOM-detach compositor race") — the click()-internal actionability-poll timeout — NOT **signature #2** (`TimeoutError('Timeout 31ms exceeded ... "domcontentloaded" event fired')`, the navigation-clock-starvation symptom this specific fix targets. The fix moved the *visibility* leg of the actionability poll out of `expect_navigation()`'s clock, exactly as designed and verified structurally. It does **not** touch the `stable` / `receives-events` / `enabled` legs, which `click()` still polls *inside* the `with` block — and the failure observed here is happening entirely within that remaining, unaddressed portion (the element is reported visible, enabled and stable being re-checked, then detached and re-resolved, before the 30000ms budget for `click()` itself runs out).

The plan's own "Honest limits" section anticipated exactly this possibility in the abstract ("the overlap is sharply reduced, not eliminated" — this is the correct trade, not the alternative of widening a timeout) and, under Task 2, explicitly instructed: *"If any post-fix log still carries the fallback-Save failure: report it plainly, do not widen a timeout, do not touch `EXPECTED_CHECK_COUNT`, and do not chase a second theory in this quick task — record the observation and hand the decision back."* That instruction is followed here: no further investigation, no timeout change, no additional edit was made beyond the two specified statements.

**Two unverified hypotheses, offered for context only (neither was pursued):**
1. The DOM-detach/instability race may be a genuinely separate mechanism from the navigation-clock-starvation race this fix targets — e.g. the theme-radio flip's live-preview re-render actually replacing the save button element in the DOM around the moment of `click()`, independent of any shared timeout budget.
2. The four post-fix runs ran back-to-back immediately after the baseline (five headless-Chromium runs in one session); it is possible this itself induced enough local load (thermal/memory pressure from repeated browser process spawns) to reproduce a race the single, earlier baseline run happened not to hit — which would be consistent with the plan's own framing that the failure is "CI-load-dependent."

Neither hypothesis was investigated further, per the plan's explicit scope boundary.

**Everything else about the measurement matched expectations:**
- No `SKIP` line appeared in any log — every run genuinely executed against real Playwright + Chromium.
- `EXPECTED_CHECK_COUNT` (75) was never touched; `companion/test_browser_ux.py` correctly exited 1 in all five runs (baseline + 4 post-fix), as the plan predicted two-known-failures-survive would cause.
- The deduplicated surviving-FAIL-signature set across baseline + all four post-fix runs is exactly three signatures: the leave-guard/Control+A family, the wake-interval echo check, and (now, in every post-fix run) the fallback-Save check — i.e. the flake floor measured **3 signatures both before and after**, not the hoped-for drop to 2.
- `companion/test_browser_ux_quiet_wake.py` is unaffected: 9/9, exit 0, confirming the shared-helper edit did not break its other consumer.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The two additive edits are safe to keep: they are structurally proven correct, purely additive, change no timeout, and did not regress the one hard gate that exists (`test_browser_ux_quiet_wake.py` 9/9). There is no reason to revert them.
- **The fallback-Save flake is not resolved locally.** Real confirmation was always going to be the next CI run on `main` (per the plan's own verification point 5) — that is now even more clearly the load-bearing next step, since local evidence currently points the other way (100% reproduction across 4 runs, same signature every time).
- If the next CI run still shows this failure, the likely next step is addressing the `stable`/`receives-events`/`enabled` legs of the actionability poll directly (e.g., investigating whether the theme-flip's live-preview re-render is actually replacing the save button element, which would be a Rule 1/Rule 4 question for a follow-up task, not this one) — flagged here for whoever picks this up next, not undertaken in this quick task.

---
*Phase: quick-260923-9na*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: companion/test_browser_ux.py
- FOUND: companion/test_browser_ux_helpers.py
- FOUND: .planning/quick/260923-9na-corriger-la-vraie-cause-du-test-flaky-fa/260923-9na-SUMMARY.md
- FOUND: commit 1be1343
- FOUND: commit 0b1430a
