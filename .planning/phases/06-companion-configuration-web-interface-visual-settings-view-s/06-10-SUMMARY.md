---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 10
subsystem: infra
tags: [poll-loop, sqlite, history-db, gallery, pillow, cfg-01, cfg-05, cfg-06, cfg-11, cfg-12]

requires:
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s
    provides: "06-01's device_config.py/history_db.py persistence layer, 06-02's runway-parameterised detect.py + diagnostics dict, 06-06's theme/runway/source_fault-aware render.py"
provides:
  - "run_once() reads device_config.json once per cycle and threads theme/runway/source_fault into detection and every render call site"
  - "_classify_source_fault() - the CFG-05 all-providers-failed classifier, distinct from an ordinary empty selection"
  - "a durable fault-flag transition gate (history.db meta, never poll_state.json) that re-renders once on change, never on every cycle of a persistent outage"
  - "_should_record_event()/_record_history() - CFG-06/CFG-08 history rows written only on a real hex/confirmed_state/corroborated transition, with per-cycle meta signals written every cycle"
  - "_save_to_gallery()/_prune_gallery() - CFG-11 render gallery under state/gallery/, capped at GALLERY_MAX_ENTRIES=25"
affects: [06-11, 06-12]

tech-stack:
  added: []
  patterns:
    - "render.build_canvas() + panel_format.pack_panel() replaces render.render_panel() at every poll_loop.py call site, so a hook can archive the pre-pack canvas without a second render pass"
    - "history.db's meta table (not poll_state.json) is the durable home for any per-cycle signal that isn't part of the two-deep flight history - used here for the CFG-05 fault flag specifically to avoid adding a second save_poll_state() writer path"

key-files:
  created: []
  modified:
    - server/poll_loop.py
    - server/test_poll_loop.py

key-decisions:
  - "The CFG-05 fault-transition comparison value is persisted in history.db's meta table (history_db.META_SOURCE_FAULT), not poll_state.json - the plan's own acceptance criterion (grep -c save_poll_state unchanged) rules out a second write path into poll_state.json, and history.db already has its own WAL/busy_timeout concurrency discipline"
  - "History-row insertion is gated on confirmed_state is not None (a real departing/arriving detection), not merely flight is not None - a deadband/ambiguous detection renders the Empty state and has no real transition to log"
  - "All four render call sites (the three pre-existing ones plus this plan's new fault-transition re-render) were restructured to build_canvas()+pack_panel() uniformly, so gallery archiving works consistently everywhere a panel write can occur"

patterns-established:
  - "A hook that must never fail a poll cycle (history write, gallery archive) is wrapped in its own try/except and called only after write_panel_atomic() has already succeeded - the panel is the product, an accessory failing never blocks it"

requirements-completed: [CFG-01, CFG-03, CFG-05, CFG-06, CFG-08, CFG-11, CFG-12]

coverage:
  - id: D1
    description: "run_once() reads device_config.json once per cycle and threads the saved theme/runway into detection and rendering (CFG-01/CFG-12)"
    requirement: "CFG-01"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#a saved non-default tracked runway reaches detect.select_aircraft_for_runway on the injected-snapshot branch"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#a saved non-default tracked runway reaches detect.poll_current_aircraft on the live branch"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#a default config against the FLIGHT1 fixture reproduces the pinned pre-06-10 panel.bin digest"
        status: pass
    human_judgment: false
  - id: D2
    description: "_classify_source_fault() derives the CFG-05 alert only from an all-providers-failed diagnostics report, never from an ordinary empty selection, and the D-04 no-op branch re-renders exactly once on a fault transition"
    requirement: "CFG-05"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#an all-providers-failed diagnostics report yields a true source_fault flag passed to render.build_canvas"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#providers queried successfully with nothing selected leaves the source_fault flag false"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#two consecutive cycles with an unchanged true fault flag and no new detection write panel.bin exactly once, not twice"
        status: pass
    human_judgment: false
  - id: D3
    description: "History rows (runway_events) are written only on a real hex/confirmed_state/corroborated transition; per-cycle meta signals are written every cycle regardless (CFG-03/CFG-06/CFG-08)"
    requirement: "CFG-06"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#detecting a new aircraft writes exactly one runway_events row; re-detecting it unchanged writes no further row"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#a confirmed_state flip on the same hex writes a new runway_events row"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#a corroboration flip on the same hex/confirmed_state writes a new runway_events row"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#the pipeline-run meta timestamp updates on every cycle, including one that writes no runway_events row"
        status: pass
    human_judgment: false
  - id: D4
    description: "Changed panels are archived into the CFG-11 gallery, capped at GALLERY_MAX_ENTRIES with oldest-first pruning; unchanged cycles archive nothing"
    requirement: "CFG-11"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#a panel write with changed bytes saves one image into the gallery; an unchanged-bytes cycle saves none"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#the gallery never holds more than GALLERY_MAX_ENTRIES; the oldest entries are removed first"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both new hooks (history write, gallery archive) degrade quietly on a database or filesystem failure without breaking the poll cycle or leaving the panel unwritten"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#a read-only gallery directory does not fail the cycle - run_once() still returns and panel.bin is still written"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#a history.db failure (open_db raising) is caught and logged without failing the cycle or leaving panel.bin unwritten"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-08-28
status: complete
---

# Phase 6 Plan 10: Poll-Cycle Wiring — Config, History, Gallery, Fault Badge Summary

**`run_once()` now reads `device_config.json` once per cycle to drive theme/runway/CFG-05 fault rendering, writes `history.db` rows only on real flight transitions with per-cycle meta on every cycle, and archives changed panels into a capped, pruned gallery — closing the gap between this phase's read-side companion pages and the production poll cycle they were built to describe.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-08-28T01:52:09+02:00
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `run_once()` reads `device_config.json` exactly once per cycle (`grep -c device_config.load_device_config server/poll_loop.py` == 1) and threads the saved theme id and tracked runway id into detection (both the live `detect.poll_current_aircraft()` branch and the injected-snapshot `detect.select_aircraft_for_runway()` branch) and into every `render.build_canvas()` call site.
- `_classify_source_fault()` implements CFG-05's exact scoping rule: true only when the diagnostics dict reports at least one queried provider and every one of them failed — never when providers were queried successfully and simply selected nothing. The D-04 "nothing detected, flight already on screen" no-op branch gained exactly one new condition: a fault-flag *transition* (read from `history.db`'s durable meta table) re-renders the currently-held flight once; an unchanged fault value — even a persistent `True` across many cycles — never forces a repeat refresh.
- `_should_record_event()`/`_record_history()` write a `runway_events` row only on a real hex/confirmed_state/corroborated transition, while the pipeline-run timestamp, source-fault flag, and last-detection timestamp are written to `history.db`'s fixed-size `meta` table on every cycle regardless — the Pitfall 1 cadence-arithmetic distinction the plan called out explicitly.
- `_save_to_gallery()`/`_prune_gallery()` archive a changed panel as a colon-sanitised-timestamp PNG under `state/gallery/`, capped at `GALLERY_MAX_ENTRIES = 25` with oldest-first pruning — only ever called after `write_panel_atomic()` reports the bytes actually changed.
- Both new hooks are individually try/except-contained (`sqlite3.Error`/`OSError` for history, a broad `Exception` for the gallery's PIL/filesystem calls) and always run *after* `write_panel_atomic()` has already succeeded, so a locked database or a read-only gallery directory degrades to a logged line, never a failed cycle or an unwritten panel.
- `server/test_poll_loop.py` grew from 8 to 27 checks: the cross-module `device_config.RUNWAYS`/geofence `runways` consistency check this phase had been deferring, a pinned pre-06-10 byte-identity digest, and one check per behavior bullet from both tasks — all stubbing `enrich.default_transport` (no live network) and using their own fresh temp state directories.

## Task Commits

1. **Task 1: Read device_config each cycle and thread theme, runway and the source-fault flag through detection and rendering** - `ec024ab` (feat)
2. **Task 2: Write history rows on state change and archive changed panels into the gallery** - `4791c4e` (feat)
3. **Task 3: Extend server/test_poll_loop.py, including the cross-module runway-id consistency check** - `6c0a3f7` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `server/poll_loop.py` - `run_once()` extended additively: config read, fault classification/transition gate, history/gallery hooks; three pre-existing `render.render_panel()` call sites (plus the one new fault-transition re-render) restructured to `render.build_canvas()` + `panel_format.pack_panel()`; new module constants `GALLERY_DIRNAME`/`GALLERY_MAX_ENTRIES` and functions `_classify_source_fault()`, `_last_source_fault()`, `_should_record_event()`, `_record_history()`, `_gallery_dir()`, `_prune_gallery()`, `_save_to_gallery()`.
- `server/test_poll_loop.py` - Grew from 8 to 27 checks; two pre-existing checks widened for the new keyword arguments and the `build_canvas` call-site rename (see Deviations); `EXPECTED_CHECK_COUNT` raised to 27.

## Decisions Made

- The CFG-05 fault-transition comparison value lives in `history.db`'s meta table (`history_db.META_SOURCE_FAULT`), never `poll_state.json` — required by the plan's own acceptance criterion that `save_poll_state()`'s call-site count stay unchanged (exactly 2: the `def` and the one pre-existing call), which rules out adding a second write path into `poll_state.json` for this signal. `history.db` already carries its own WAL + busy_timeout concurrency discipline, so it is the correct durable home for a per-cycle signal that isn't part of the two-deep flight history.
- History-row insertion is gated on `confirmed_state is not None` (a real departing/arriving detection), not merely `flight is not None` — a deadband/ambiguous detection renders the Empty state and has no real transition worth logging in CFG-06's flight-history table. The last-detection meta timestamp, by contrast, updates whenever `flight is not None` regardless of confirmed state, matching the plan's literal "when a flight was detected" wording.
- All four render call sites (the three pre-existing plus this plan's new fault-transition re-render) were restructured to `build_canvas()`+`pack_panel()` uniformly, rather than restructuring only the three the plan's Task 2 text names — the fault-transition site is a genuine panel write and needed the same canvas-before-packing shape for gallery archiving to work there too.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Widened the pre-existing `render.render_panel` spy in `server/test_poll_loop.py` to accept `**kwargs`**
- **Found during:** Task 1
- **Issue:** Task 1's own additive change (threading `theme_id`/`runway_id`/`source_fault` into every render call) broke the pre-existing check "render.render_panel() is actually called with the shifted previous_flight" — the check's spy function had a fixed positional/keyword signature that didn't accept the three new keyword arguments, raising `TypeError`.
- **Fix:** Added `**kwargs` to the spy's signature and forwarded it to the wrapped original call.
- **Files modified:** server/test_poll_loop.py
- **Verification:** `server/test_poll_loop.py` returned to 8/8 passing immediately after the fix.
- **Committed in:** ec024ab (Task 1 commit)

**2. [Rule 1 - Bug] Retargeted the same spy from `render.render_panel` to `render.build_canvas`**
- **Found during:** Task 2
- **Issue:** Task 2's restructuring of poll_loop.py's render call sites from `render.render_panel()` to `render.build_canvas()` + `panel_format.pack_panel()` meant the pre-existing spy (patching `render.render_panel`) was never invoked anymore, since `run_once()` no longer calls that function at all — the check silently degraded to "spy never called, `previous_flight` stayed `None`, check fails."
- **Fix:** Retargeted the spy to `render.build_canvas` (the plan's own Task 3 action text anticipates exactly this: "Use the existing render.render_panel spy idiom, extended to spy on render.build_canvas").
- **Files modified:** server/test_poll_loop.py
- **Verification:** `server/test_poll_loop.py` returned to 8/8 (later 27/27) passing.
- **Committed in:** 4791c4e (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - the plan's own additive changes to `poll_loop.py` broke pre-existing test spies targeting the old call shape/site; both fixes are minimal and forward-compatible, no scope creep).
**Impact on plan:** Both fixes were necessary for the plan's own tasks to pass their stated `<verify>` step (`server/test_poll_loop.py` exiting 0). No behavioral change to production code from either fix.

## Issues Encountered

None beyond the two deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every one of this plan's seven listed requirements (CFG-01, CFG-03, CFG-05, CFG-06, CFG-08, CFG-11, CFG-12) was already checked off in `REQUIREMENTS.md` by earlier plans (06-02/06-07/06-08/06-09) for their read/UI side; this plan is what makes the write/wiring side genuinely real for the first time. `gsd-tools query requirements.mark-complete` confirms all seven as `already_complete` — no further action needed there.
- **Noted, not fixed (pre-existing, out of this plan's file scope):** `REQUIREMENTS.md`'s "Traceability" table (lines ~105-115) still shows "Pending (not yet planned)" for CFG-03/04/05/06/08/09/10/11 even though the requirement checkboxes above it are all `[x]` — a staleness gap left by prior plans (06-08/06-09) that only updated the checkbox list, not the prose traceability table. Doesn't block anything; worth a small doc pass whenever REQUIREMENTS.md is next touched.
- Manual, offline `--once` run against `/tmp/skypane-06-10` completed with exit 0 and the extended log line (`theme=sky tracked_runway=3 source_fault=False`), confirming the real entrypoint still works end-to-end outside the test harness.
- `scripts/run-all-tests.sh` (all 9 registered harnesses), `server/test_pipeline_e2e.py`, and `ruff check .` all pass clean.
- Ready for whichever plan in this phase is next (06-11/06-12 per ROADMAP.md) — no blockers identified.

---
*Phase: 06-companion-configuration-web-interface-visual-settings-view-s*
*Completed: 2026-08-28*

## Self-Check: PASSED

- FOUND: server/poll_loop.py
- FOUND: server/test_poll_loop.py
- FOUND: .planning/phases/06-companion-configuration-web-interface-visual-settings-view-s/06-10-SUMMARY.md
- FOUND: ec024ab (Task 1 commit)
- FOUND: 4791c4e (Task 2 commit)
- FOUND: 6c0a3f7 (Task 3 commit)
