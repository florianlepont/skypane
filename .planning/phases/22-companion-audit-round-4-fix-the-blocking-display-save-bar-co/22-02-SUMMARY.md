---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 02
subsystem: ui
tags: [python, quiet-hours, i18n, wake-scheduling, frame-state]

# Dependency graph
requires:
  - phase: 22-01
    provides: the D-02 Playwright browser harness and its dev-only CI wiring (not consumed directly by this plan, but this plan's wave depends on 22-01 having landed first)
provides:
  - "server.wake.next_wake_status(): a (next_wake_iso, effective_interval_s, hold_reason) triple, quiet-hours- and screen-off-aware, evaluated at last_checkin_ts"
  - "server.wake.HOLD_QUIET_HOURS: the one hold-reason constant"
  - "companion.frame_state: resolve_state()/headline_template()/delay_sentence_template() — the one frame-state resolution and the one delay sentence, view-free"
  - "companion/i18n_fr/frame_state.py: the French catalogue for the three new copy strings this plan introduces"
  - "the nightly-regression fixture (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris -> STATE_HELD) pinned end to end"
affects: [22-04, 22-05, 22-07, 22-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Composition over re-derivation: next_wake_status() reuses effective_wake_interval_s() and device_config.quiet_hours_status() rather than inventing new window arithmetic"
    - "hold_reason checked before any time arithmetic, so a held state can never escalate by elapsed time alone"
    - "View-free state-resolution module (companion/frame_state.py) returns state names and template-key strings only, never HTML/CSS class names — the renderer maps state to presentation"

key-files:
  created:
    - companion/frame_state.py
    - companion/i18n_fr/frame_state.py
  modified:
    - server/wake.py
    - companion/wake.py
    - companion/test_view_pages.py

key-decisions:
  - "next_wake_status() checks quiet_hours_status() at BOTH the check-in epoch and the check-in-plus-base-interval epoch (not just the check-in epoch alone) — a look-ahead beyond 22-RESEARCH.md's own Pattern 4 sketch, required to make the plan's own worked example (22:58 check-in, 900s interval, 23:00-07:00 window -> window's end, not 23:13) and the nightly-regression acceptance criterion actually pass"
  - "Two of frame_state's six English copy constants (HEADLINE_DUE/HEADLINE_LATE) and one (DELAY_UNKNOWN) are deliberately NOT redefined in companion/i18n_fr/frame_state.py's CATALOG — they already exist as live keys in i18n_fr/home.py and i18n_fr/display.py, and the auto-merge package raises ValueError on a duplicate key"

requirements-completed: []  # CFG-26 is served by three plans (22-02, 22-04, 22-07); NOT complete after this one alone.

# Metrics
duration: ~20min
completed: 2026-09-12
---

# Phase 22 Plan 02: The single next-wake truth (quiet-hours-aware, with the one frame-state resolution) Summary

**`server.wake.next_wake_status()` composes the device's own effective-interval and quiet-hours primitives into one `(next_wake_iso, effective_interval_s, hold_reason)` result, and `companion/frame_state.py` resolves due/held/late/unknown and the one delay sentence from it — the nightly false alarm (X2) is pinned dead end to end.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-12T20:47:00Z (approx.)
- **Completed:** 2026-09-12T21:07:14Z
- **Tasks:** 2 completed
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- `server/wake.py` gained `next_wake_status()` and `HOLD_QUIET_HOURS`, reproducing `stub-server/byos_server.py`'s own `quiet_hours_sleep_s(display_off_sleep_s(...))` composition, evaluated at `last_checkin_ts` — never at render time. `next_wake_at_iso()` is now a thin wrapper; every existing call site (`home_page.py:421`, `config_page.py:3109`) is untouched.
- `companion/frame_state.py` is the one place that resolves whether the frame is due, held or late, and the one place that picks the delay-sentence copy — view-free, no dot class, no status colour, matching 22-UI-SPEC.md §3.3's six binding rules by construction.
- The nightly regression (quiet hours 23:00-07:00, last check-in 22:58, clock 02:00 Europe/Paris) is pinned end to end through both new functions and resolves to `STATE_HELD`, never `STATE_LATE`.
- The existing pinned `_wake_next_wake_at_iso_contract()` fixtures (screen-on, screen-off) are asserted byte-identical.

## Task Commits

1. **Task 1: Make the next wake quiet-hours aware, evaluated at the last check-in** - `1e159e0` (feat)
2. **Task 2: One frame-state resolution and one delay sentence, in both languages** - `21648d6` (feat)
3. **Follow-up fix: match the codebase's `companion.wake` import convention** - `4bd9b65` (fix, folded into Task 2's scope)

**Plan metadata:** committed as part of this same set — no separate docs commit was needed beyond the above; STATE.md/ROADMAP.md/REQUIREMENTS.md updates land in the final bookkeeping commit below.

## Files Created/Modified
- `server/wake.py` - added `next_wake_status()` (the `(next_wake_iso, effective_interval_s, hold_reason)` triple) and `HOLD_QUIET_HOURS`; `next_wake_at_iso()` reduced to a thin wrapper
- `companion/wake.py` - re-exports `next_wake_status`/`HOLD_QUIET_HOURS` through the existing shim
- `companion/frame_state.py` - new: `STATE_DUE`/`STATE_HELD`/`STATE_LATE`/`STATE_UNKNOWN`, `resolve_state()`, `headline_template()`, `delay_sentence_template()`, and the six EN copy constants
- `companion/i18n_fr/frame_state.py` - new: French catalogue for the three genuinely-new copy strings (see the collision note below for the other three)
- `companion/test_view_pages.py` - extended `_wake_next_wake_at_iso_contract()` with the quiet-hours-active fixtures; added `_frame_state_resolve_state_contract()` and `_frame_state_view_free_and_i18n_contract()`; `EXPECTED_CHECK_COUNT` re-derived twice (114 -> 114 net-zero for Task 1, then 114 -> 116 for Task 2)

## Decisions Made

- **Look-ahead composition, not a single check-in-instant check.** 22-RESEARCH.md's Pattern 4 sketch calls `quiet_hours_status(device_cfg, parsed.timestamp())` exactly once, at the check-in epoch. Implementing literally that sketch, I verified numerically (`server/device_config.quiet_hours_status`) that a check-in at 22:58 with a 23:00-07:00 window returns `(None, None)` — the window has not started yet — so the naive result would be `22:58 + 900s = 23:13`, i.e. **exactly the naive, wrong answer the plan's own Task 1 bullet says must NOT be returned** ("returns the end of the window, not 23:13"), and would make the Task 2 nightly-regression fixture resolve to `STATE_LATE` at 02:00 — reproducing X2's bug rather than fixing it. I added a second `quiet_hours_status()` call at the check-in-plus-base-interval epoch (still entirely derived from `last_checkin_ts` and static config, never from a render-time "now") to catch a window that opens between the check-in and the naive candidate wake. Both calls reuse the same tested primitive; no new window arithmetic was written. This is documented at length in `next_wake_status()`'s own docstring.
- **Three of the six planned i18n_fr CATALOG entries are intentionally omitted from `companion/i18n_fr/frame_state.py`** because they collide with pre-existing keys in `i18n_fr/home.py` (`"Next update ≈ %s"`, `"Expected since %s"`) and `i18n_fr/display.py` (`"Applies the next time the frame wakes up."`) — the auto-merge package (`companion/i18n_fr/__init__.py`) raises `ValueError` on any duplicate key across sibling modules, which would break every test that imports `companion.i18n_fr`. See "Deviations from Plan" below for the full detail, including a real, currently-unresolved copy discrepancy (`"Attendue depuis %s"` vs. this phase's locked `"Attendu depuis %s"`) that this plan cannot fix without touching files outside its ownership.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The single check-in-instant composition sketch does not satisfy the plan's own worked example or the nightly-regression acceptance criterion**
- **Found during:** Task 1
- **Issue:** 22-RESEARCH.md's Pattern 4 sketch (and the plan's interface note citing `quiet_hours_status(device_cfg, parsed.timestamp())`) checks quiet hours only at the exact check-in instant. For the plan's own worked example (23:00-07:00 window, 22:58 check-in, 900s interval), this returns the window-INACTIVE result at 22:58, so the naive composition yields `23:13` — precisely the value the plan says must NOT be returned. Left as-is, the Task 2 nightly-regression fixture (clock at 02:00) would resolve to `STATE_LATE`, reproducing X2's exact bug this whole plan exists to fix.
- **Fix:** `next_wake_status()` additionally calls `quiet_hours_status()` at the check-in-plus-base-interval epoch (the naive candidate wake, before any extension), catching a window that opens between the check-in and that candidate. Both calls are still grounded in `last_checkin_ts` and static config, never in a render-time "now" — satisfying UI-SPEC §3.3 rule 5 — and both reuse the same tested `quiet_hours_status()` primitive with no new window arithmetic invented.
- **Files modified:** `server/wake.py`
- **Verification:** New fixture A in `_wake_next_wake_at_iso_contract()` (22:58 check-in, 900s interval, 23:00-07:00 window) asserts the result is the window's end, not 23:13; the full nightly-regression fixture in `_frame_state_resolve_state_contract()` asserts `STATE_HELD` at clock 02:00, end to end through both new functions. Both pass.
- **Committed in:** `1e159e0` (Task 1), `21648d6` (Task 2, the nightly-regression assertion)

**2. [Rule 1 - Bug] Three of the six planned French catalogue entries would have raised `ValueError` at import time via a duplicate-key collision**
- **Found during:** Task 2
- **Issue:** `"Next update ≈ %s"` and `"Expected since %s"` (two of the three headline constants) and `"Applies the next time the frame wakes up."` (one of the three delay constants) already exist as live keys in `companion/i18n_fr/home.py` and `companion/i18n_fr/display.py` respectively. `companion/i18n_fr/__init__.py`'s auto-merge `_build_catalog()` raises `ValueError`, naming the duplicate key, the moment any two sibling modules define the same English key — this is not a soft warning, it is a hard crash on import of `companion.i18n_fr` from ANY test or the app itself.
- **Fix:** Omitted these three keys from `companion/i18n_fr/frame_state.py`'s `CATALOG` entirely, documenting the omission at length in the module's own docstring. `companion.i18n.t()` still resolves them correctly today via the pre-existing entries (the merged CATALOG is one flat dict regardless of which sibling module supplied a key), so no runtime behaviour is lost. One of the three omissions surfaces a **real, currently-unresolved copy discrepancy**: `home.py`'s existing `"Expected since %s"` maps to `"Attendue depuis %s"` (feminine agreement, from that call site's own grammatical context), while 22-UI-SPEC.md's Copywriting Contract locks `"Attendu depuis %s"` (no agreement) for THIS module's held/late-headline context. I did not touch `home.py`/`display.py` to reconcile this, because (a) they are not in this plan's `files_modified`, (b) the plan's own text explicitly assigns their retirement — "in the same commit as their French entries" — to plans 22-04/22-05, and (c) no consumer reads `frame_state.py`'s constants yet in this plan, so the discrepancy has zero live user-facing effect today. Plans 22-04/22-05 must resolve it when they delete `NEXT_UPDATE_TEMPLATE`/`EXPECTED_SINCE_TEMPLATE`/`QUICK_ACTION_APPLIES_SENTENCE` and wire their own consumers to `companion/frame_state.py`.
- **Files modified:** `companion/i18n_fr/frame_state.py` (three fewer entries than a naive reading of the plan's interface table would suggest; `companion/frame_state.py`'s docstring documents the reasoning inline)
- **Verification:** `companion/test_view_pages.py`'s new `_frame_state_view_free_and_i18n_contract()` asserts all six English constants round-trip through `companion.i18n.t_lang()` correctly (the three genuinely-new ones via `frame_state.py`'s own catalogue, the three collision ones via the pre-existing `home.py`/`display.py` entries) — proving today's actual runtime resolution, not the phase's eventual target text.
- **Committed in:** `21648d6`

**3. [Rule 3 - Blocking, cosmetic] Import-style mismatch with the plan's own `key_links` grep pattern**
- **Found during:** post-Task-2 self-check
- **Issue:** `companion/frame_state.py` initially imported `from companion.wake import HOLD_QUIET_HOURS`, which does not literally match the plan's `key_links` pattern (`from .wake import|import wake`) and diverges from every other companion module's own `companion.wake` import convention (`config_page.py`'s `from companion import wake`, `home_page.py`'s `import companion.wake as wake`).
- **Fix:** Switched to `from companion import wake`, referencing `wake.HOLD_QUIET_HOURS` at both call sites.
- **Files modified:** `companion/frame_state.py`
- **Verification:** `grep -c "from .wake import\|import wake" companion/frame_state.py` now returns 1; `ruff check` clean; `companion/test_view_pages.py` still 116/116.
- **Committed in:** `4bd9b65`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking/cosmetic)
**Impact on plan:** Deviations 1 and 2 were necessary for correctness — without them the plan's own stated acceptance criteria (the 22:58 worked example, the nightly regression, and a non-crashing `companion.i18n_fr` import) would not hold. No scope creep: no file outside this plan's `files_modified`/`files_owned` boundary was edited.

## Issues Encountered

**Acceptance-criterion mismatch, run literally per this plan's own constraint 5 and reported rather than silently routed around:**

`companion/test_i18n.py` — required green by this plan's `<verification>` section and by acceptance criterion "the new catalogue has no orphaned key, because its English source constants ship in the same commit" — **fails** its `D-08 Check 2` (no dead translations) after this plan, with exactly this line:

```
FAIL D-08 Check 2: every companion.i18n_fr.CATALOG key is produced by the D-05 module scan,
server/notify.py's own bodies, or a documented exception - 3 companion.i18n_fr.CATALOG key(s)
are never produced by the D-05 module scan and are not in a documented exception list:
['Applies at the next wake, around %s.', 'Applies when quiet hours end, around %s.',
'Next wake around %s · quiet hours']
```
(`companion/test_i18n.py: 21/22 checks pass`, exit 1.)

**Why the criterion's premise does not hold, and why I did not route around it:** the check's "produced" set comes from an AST scan (`_scan_all_d05_modules()`) of a fixed file list (`_SCAN_RELATIVE_PATHS`) looking for literal `companion.i18n.t(...)` **call sites** — it does not see a bare module-level string constant. `companion/frame_state.py` defines these three constants but calls `i18n.t()` on none of them (that is the consuming page's job, in a later plan), and it is explicitly NOT in `_SCAN_RELATIVE_PATHS` today — the plan's own read_first note says so explicitly: *"`frame_state.py` is NOT in the scan list today; plan 22-08 widens that list, so do not add it here."* So "ship the English source constants in the same commit," as the acceptance criterion states, does **not** by itself make the scanner see them; three FAIL-worthy orphans are the mechanical, reproducible result, and this is not something a code fix inside this plan's scope can resolve:
- Adding `frame_state.py` to `_SCAN_RELATIVE_PATHS` is explicitly forbidden by this plan's own read_first note.
- Adding a fourth documented exception-list entry (mirroring `_APP_PY_OWNED_STRINGS`/`_FLASH_AWAITING_TRANSLATION_WIRING`) would require editing `companion/test_i18n.py`, which is **not** in this plan's `files_modified` and is instead the sole property of **plan 22-08** in this phase's wave/ownership split (verified: no other plan in 22-03..22-16 lists `companion/test_i18n.py` in its own `files_modified` except 22-08).
- The orphan is expected to self-resolve without any test-file edit once plans 22-04/22-05 wire a real page-module consumer that calls `i18n.t()` with these three constants from inside a scanned module (`layout.py`, `config_page.py`, `health_page.py` are all in `_SCAN_RELATIVE_PATHS`) — at that point the AST scan will see the call sites directly.

Per this plan's critical constraint 5 ("If a criterion's command returns something other than what the plan states, STOP and record it in the SUMMARY rather than adjusting code to match a bad criterion or silently editing the criterion"), I ran the criterion literally, confirmed the exact mismatch, and am reporting it here rather than editing `companion/test_i18n.py` or weakening `companion/frame_state.py`'s design to dodge it. `PYTHON=.../python bash scripts/run-all-tests.sh` (run at plan close) shows exactly 4 failing harnesses: the three pre-existing, documented-since-Phase-18 root-sandbox read-only/anomaly failures (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — all failing on the exact named read-only-directory/anomaly cases, confirmed by grepping each harness's own FAIL lines) plus this one new, explained `companion/test_i18n.py` failure. No other harness regressed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `server.wake.next_wake_status()` and `companion.frame_state` are ready for plans 22-04 (the Frame strip / Health tile), 22-05 (settings delay captions) and 22-07 (Home) to wire as consumers.
- **Action item for 22-04/22-05:** when deleting `layout.py`'s `NEXT_UPDATE_TEMPLATE`/`EXPECTED_SINCE_TEMPLATE`/`QUICK_ACTION_APPLIES_SENTENCE` and their `i18n_fr/home.py`/`i18n_fr/display.py` entries (per this phase's own "delete them there, in the same commit as their French entries" instruction), also add the three now-unblocked keys to `companion/i18n_fr/frame_state.py`'s `CATALOG` — including reconciling `"Expected since %s"`'s French value to the locked `"Attendu depuis %s"` (see Deviation 2 above) — and wire the actual `i18n.t()` call sites so `companion/test_i18n.py`'s D-08 Check 2 goes green again without any exception-list addition.
- **Action item for 22-08:** once `frame_state.py` is added to `_SCAN_RELATIVE_PATHS`, re-verify the orphan/dead-translation checks still pass for whatever state the CATALOG is in by then.
- No blockers for those downstream plans; the computation itself is complete, tested (including the exact nightly-false-alarm scenario), and matches every acceptance criterion except the one documented `test_i18n.py` mismatch above.

---
*Phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co*
*Completed: 2026-09-12*

## Self-Check: PASSED

All created/modified files present on disk (`server/wake.py`, `companion/wake.py`,
`companion/frame_state.py`, `companion/i18n_fr/frame_state.py`,
`companion/test_view_pages.py`, this SUMMARY.md); all three task commits
(`1e159e0`, `21648d6`, `4bd9b65`) found in `git log`.
