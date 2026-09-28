---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 07
subsystem: testing
tags: [efficiency, architecture, companion-structure, audit, re-verification]

# Dependency graph
requires:
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: EFF-01..EFF-06 remediations (compression + validators + in-memory static cache, per-page scripts, one SQLite connection per request/cycle, lazy page context + light freshness check, write-once-if-changed compact poll_state, parallel per-provider-rate-limited detection)
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: ARC-01..ARC-06 remediations (poll_cycle.py named steps over CycleContext, state_store.py as poll_state.json's sole owner, render/calendar_rules/net packages + themes.py, no module-global setters, one shared device_policy module, mypy-typed pure core)
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: CMP-01..CMP-09 remediations (route table, static allowlist, file/function size ceilings, typed PageContext, named page_shell templates, shared body-drain/cookie helpers, deduplicated tokenised stylesheet, stable-ID i18n)
provides:
  - Independent, current-code re-audit of all 6 EFF, all 6 ARC and all 9 CMP findings (41-REAUDIT-EFF-ARC-CMP.md)
  - Confirmation that Phase 39's merge and Phase 40's concurrent companion work did not undo each other's structural changes
  - A resolved status for the one Phase 40 deferred browser test (test_cfg34_live_age_ticks_at_each_converted_site[chromium-health-registry])
affects: [41-08-closing-plan]

# Tech tracking
tech-stack:
  added: []
  patterns: ["read-only re-verification against current file:line, structural gates and targeted test runs rather than trusting SUMMARY/VERIFICATION checkboxes", "re-running the phase's own measurement instrument (scripts/measure_efficiency.py) to reproduce baseline figures independently rather than citing them"]

key-files:
  created:
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-EFF-ARC-CMP.md
  modified: []

key-decisions:
  - "All 6 EFF findings (Phase 38), all 6 ARC findings (Phase 39), and all 9 CMP findings (Phase 40) verify VERIFIED-CLOSED against the current server/, stub-server/, companion/ and deploy/ trees"
  - "ARC-03 is FLAGGED-DIFFERENT on naming only: the ledger's own shorthand calls the calendar package 'calendar/'; the shipped (and always-shipped) name is server/plane/calendar_rules/. The package's ics/match/registry structure fully meets the finding's intent - a ledger-shorthand mismatch, not a code gap, carrying no open risk"
  - "CMP-02's four remaining dynamic-asset _serve_* functions (_serve_gallery_image, _serve_runway_image, _serve_illustration_image, _serve_theme_preview_image) are not a regression: they guard runtime-computed resources a static allowlist cannot hold and were never part of the original '17 static files' finding, which is fully collapsed onto one STATIC_ROUTES allowlist plus one _serve_static_route handler"
  - "ARC-05: companion/pages/home_page.py's _quiet_hours_window() (a day-band visualization helper, added after the ledger's original finding) shares one one-line enabled-check with device_policy.quiet_hours_window() but does not re-duplicate the decision logic (window-with-wraparound, countdown, pin rule, discharge curve) the finding targeted - noted, not flagged"
  - "CMP-06's shipped ceiling (80 code lines, matching ROADMAP wording) is stricter than the ledger's own '100 lines' shorthand - the stricter number is what the guard enforces today with no allowlist, a better outcome than the ledger's remediation text implied"
  - "The Phase 40 deferred-items.md test (test_cfg34_live_age_ticks_at_each_converted_site[chromium-health-registry]) now passes: its root cause (server.poll_loop losing save_poll_state) was itself the intended outcome of Phase 39's ARC-02 split onto server.state_store, and the test file has since been updated to match"

patterns-established: []

requirements-completed: []  # DOC-03 spans 4 re-audit slices (41-04..41-07) plus the 41-08 closing merge; not complete until 41-08

# Metrics
duration: 55min
completed: 2026-09-28T07:20:00Z
status: complete
---

# Phase 41 Plan 07: Closing re-audit of Phases 38-40 (EFF-01..06, ARC-01..06, CMP-01..09) Summary

**Independently re-verified all 6 efficiency findings, all 6 server-architecture findings and all 9 companion-architecture findings against the current codebase - all 21 VERIFIED-CLOSED (one FLAGGED-DIFFERENT on naming only), with the Phase 39/40 concurrent-merge risk confirmed absent.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-28T06:25:00Z (approx.)
- **Completed:** 2026-09-28T07:20:00Z
- **Tasks:** 2 (combined into one report/one commit - see Deviations)
- **Files modified:** 1 (`41-REAUDIT-EFF-ARC-CMP.md`, new)

## Accomplishments

- Ran `server/.venv/bin/mypy` (`Success: no issues found in 12 source files`, matching
  `39-VERIFICATION.md`'s own figure) and `scripts/check_function_size.py check --max 80 server
  stub-server` (`401 functions scanned, none over 80`, matching `39-ARC-BASELINE.md`'s After
  figure byte-for-byte).
- Ran the EFF/ARC targeted test set (`companion/test_static_cache.py`,
  `test_page_scripts.py`, `test_request_connections.py`, `test_freshness_token.py`,
  `test_page_context.py`: 101 passed; `server/test_poll_state_writes.py`,
  `test_state_store.py`, `test_plane_detection.py`: 91 passed) and independently re-ran
  `scripts/measure_efficiency.py --label reaudit41-07 --repeats 2`, reproducing the After
  baseline's connection counts, 304 revalidation, write-once-if-changed poll_state, and the
  disappearance of the fixed 1.1s inter-provider sleep.
- Ran the CMP targeted test set (`companion/test_route_table.py`, `test_structure_guards.py`,
  `test_stylesheet_structure.py`, `test_i18n.py`, `test_render_baseline.py`,
  `test_page_context.py`: 85 passed) and the `wc -l` top-5 companion file-size check (largest
  production file 1384 lines, all under the 1500-line ceiling; `style.css` 4820 lines is the
  one tracked exception).
- Read `server/poll_cycle.py`'s full function/class list and confirmed every ARC-01 ledger-named
  stage (`load_cycle_context`, `decide_hold`, `advance_display_queue`, `render_and_publish`,
  `record`, `persist`) exists verbatim over the `CycleContext` dataclass.
- Confirmed `server/plane/render/`, `server/plane/calendar_rules/` and `server/net/safe_fetch.py`
  are present with their expected submodules, `server/device_config.py` no longer defines
  quiet-hours/battery/theme logic itself (imports from `device_policy`/`themes`), and
  `server/notify.py` imports `server.net.safe_fetch` directly with no private
  `calendar_rules._url_is_safe` import remaining.
- Traced ARC-04's `def set_` grep to its one hit (`history_db.set_meta`, a per-connection row
  setter, not a module global) and ARC-05's three shared-logic definitions
  (`device_policy.quiet_hours_window`/`battery_critical_pin_applies`/`BATTERY_DISCHARGE_CURVE`)
  to every caller across server, byos and companion.
- Confirmed CMP-01's route table drives the one `require_session()` call site inside
  `_dispatch()`, CMP-02's static allowlist collapsed 17 per-file `_serve_*` functions to one
  `STATIC_ROUTES`-driven handler, CMP-07's shared `drain_capped_body`/`_choice_cookie_header`,
  and CMP-09's stable-ID, TypeError-enforced i18n lookup.
- Re-ran the Phase 40 deferred browser test
  (`test_cfg34_live_age_ticks_at_each_converted_site[chromium-health-registry]`) and confirmed
  it now passes (3 passed across all three parametrisations).
- Wrote 21 report rows (EFF-01..06, ARC-01..06, CMP-01..09), each with a verdict, closing
  commit(s), current file:line/test-id evidence, and a `## Flags` section.

## Task Commits

Both plan tasks (Task 1: EFF-01..06 + ARC-01..06, Task 2: CMP-01..09 + `## Flags`) target the
same single output file (`41-REAUDIT-EFF-ARC-CMP.md`); the work was done as one continuous
read-only investigation and committed as one commit, matching the precedent `41-04-SUMMARY.md`,
`41-05-SUMMARY.md` and `41-06-SUMMARY.md` all recorded for the same structural reason - an
atomic markdown-file write cannot be meaningfully split into two partial, individually-valid
commits.

1. **Tasks 1+2: Re-audit EFF-01..06, ARC-01..06 and CMP-01..09, read-only** - `ea6fcd1e` (docs)

**Plan metadata:** (this SUMMARY.md and the final metadata commit, see below)

## Files Created/Modified

- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-EFF-ARC-CMP.md` -
  21-row re-audit report (EFF-01..06, ARC-01..06, CMP-01..09), a "Gate runs" table recording
  every command/test suite used as evidence, a deferred-item follow-up section, and a
  `## Flags` section.

## Decisions Made

- Combined the plan's two tasks into a single commit (see Task Commits above) because they
  write to the same file and an intermediate partial-table commit would not be a valid
  standalone artefact - the same reasoning `41-04`/`41-05`/`41-06`-SUMMARY.md recorded.
- ARC-03 is recorded FLAGGED-DIFFERENT rather than VERIFIED-CLOSED, strictly for the ledger's
  own naming shorthand (`calendar/` vs the shipped `calendar_rules/`) - the planning-time
  context itself already flagged this discrepancy as expected, and the structural intent is
  fully met, so this is a documentation note carried forward, not a real gap for 41-08 to
  chase.
- Two Notes (EFF-01's live-VPS half, ARC-05's home_page.py day-band helper) are recorded
  against otherwise-VERIFIED-CLOSED rows rather than as flags, since neither represents open
  risk or a different remediation than what the ledger asked for - documented per the report
  format's own instruction to distinguish a flag from a note worth preserving.

## Deviations from Plan

None - plan executed exactly as written. The only adaptations were procedural (one commit
instead of two, matching the precedent of all three prior re-audit slices), documented above
under Decisions Made, not deviations under Rules 1-4 - no bug was fixed, no missing
functionality was added to the codebase, nothing blocking this plan's own progress was resolved
by touching `server/`/`stub-server/`/`companion/`/`deploy/`, and no architectural change was
made. This plan is read-only on the codebase throughout.

## Issues Encountered

None. This macOS sandbox's Playwright Chromium install was already present from a prior slice's
setup, so the one browser-dependent test this plan needed
(`test_cfg34_live_age_ticks_at_each_converted_site`) ran without additional setup.

## User Setup Required

None - no external service configuration required. This plan is read-only verification; no
code was written, and no new service was provisioned or configured.

## Next Phase Readiness

- All 6 EFF, all 6 ARC and all 9 CMP findings are provably closed on the current codebase, with
  one naming-only FLAGGED-DIFFERENT row (ARC-03) that carries no open risk for 41-08 to act on.
- No code under `server/`, `stub-server/`, `companion/`, or `deploy/` was modified by this plan;
  the only new artefact is this slice's own re-audit report and SUMMARY.
- This is the fourth and final of the four DOC-03 re-audit slices (41-04: TST/HYG, 41-05:
  firmware FW, 41-06: INT/SEC, 41-07: EFF/ARC/CMP). 41-08 (the closing plan) can now merge all
  four reports - this slice's format matches the other three (same columns, same three
  verdicts, `## Flags` section, header with audited commit/uid/tools) so it merges directly.
  The one FLAGGED-DIFFERENT row (ARC-03) and the two Notes (EFF-01, ARC-05) should carry
  forward into 41-08's closing summary as the only non-trivial items from this slice.

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-REAUDIT-EFF-ARC-CMP.md`
- FOUND: `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-07-SUMMARY.md`
- FOUND commit: `ea6fcd1e`
