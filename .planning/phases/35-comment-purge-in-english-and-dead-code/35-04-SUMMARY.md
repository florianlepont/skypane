---
phase: 35-comment-purge-in-english-and-dead-code
plan: 04
subsystem: server-core
tags: [comment-hygiene, docstrings, poll-loop, device-config, history-db, wake, notify, panel-format, panel-preview, requirements]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 01
    provides: scripts/check_comment_history.py (check/ratio/same-code), scripts/comment-history-pending.txt
provides:
  - server/poll_loop.py, device_config.py, history_db.py, wake.py, notify.py,
    panel_format.py, panel_preview.py purged of plan/ticket/decision/review/quick-task
    history in comments and docstrings, code unchanged
  - server/requirements.in, requirements-dev.in, .gitignore, state/.gitignore purged
    (requirements.in and both .gitignore files needed no changes - already history-free)
affects: []

tech-stack:
  added: []
  patterns:
    - "server/poll_loop.py's module docstring is read at runtime via
      argparse.ArgumentParser(description=__doc__) in build_parser() - a runtime-__doc__
      case the phase's 35-CONTEXT.md canonical list (companion/app.py,
      deploy/backup/backup_gate.py, deploy/backup/skypane_backup.py,
      server/plane/illustrations.py) did not enumerate. same-code's keep_module_doc
      logic (scripts/check_comment_history.py) detects '__doc__' as a literal substring
      anywhere in the file text, not just in an ArgumentParser call, so any file
      containing that string keeps its module docstring in the AST comparison and needs
      --allow once the docstring's prose changes. Same handling as 35-02's
      illustrations.py: --allow used, old/new first line recorded below."

key-files:
  created: []
  modified:
    - server/poll_loop.py
    - server/device_config.py
    - server/history_db.py
    - server/wake.py
    - server/notify.py
    - server/panel_format.py
    - server/panel_preview.py
    - server/requirements-dev.in

key-decisions:
  - "poll_loop.py required --allow server/poll_loop.py for same-code, diverging from the
    plan's acceptance criteria ('exits 0 with no --allow'): its module docstring is real
    --help text via description=__doc__, a fact the phase CONTEXT.md's runtime-docstring
    list missed for this file. Handled per the CONTEXT.md's own stated policy for
    runtime docstrings (trim history, keep accurate help text) - same treatment as
    illustrations.py in 35-02. Old first line: 'The systemd-timer oneshot entrypoint:
    detect -> render -> atomic swap (PLANE-03, D-04, D-P2-02).' New first line: 'The
    systemd-timer oneshot entrypoint: detect -> render -> atomic swap.'"
  - "requirements.in, server/.gitignore, and server/state/.gitignore needed zero edits:
    check --paths reported 0 hits on all three before this plan touched them. Only
    requirements-dev.in carried one history reference (a Phase 32/TST-01/TST-03
    comment), removed."
  - "A pre-existing self-reference bug in wake.py's CHECK_IN vocabulary comment ('the
    same reason HOLD_QUIET_HOURS above is one') was corrected to 'below' while rewriting
    the comment for the purge - HOLD_QUIET_HOURS is defined later in the file, not
    earlier. A one-word accuracy fix bundled into the required rewrite, not a separate
    deviation."
  - "Second tightening pass (orchestrator review, mirroring 35-02's own second pass):
    the first pass's ID removal left docstrings/comments long relative to the ~35%
    guideline (wake.py 70.67%, notify.py 58.62%, panel_format.py 63.43%, device_config.py
    52.55%, poll_loop.py 50.55%). Compressed every docstring/comment to a summary line
    plus a compact contract, deleting who-calls-it lists, cross-module tours, and
    'deliberately'/'honest'/'never claimed' rhetoric that restated code, while keeping
    one or two sentences of real why/invariant/units. Ratios: poll_loop.py -> 34.35%,
    device_config.py -> 29.48%, history_db.py -> 28.94%, wake.py -> 37.31%, notify.py ->
    35.38%, panel_format.py -> 50.51%, panel_preview.py -> 33.33%."
  - "test_config_history.py::test_check_in_gaps_docstring_states_what_it_cannot_know
    asserts history_db.check_in_gaps.__doc__ (introspected, not source-text-scanned)
    contains specific substrings ('cannot know', 'rotat', 'unique(ts, battery_mv)', '60',
    'x-battery-mv'). The tightening pass's first compression dropped the X-Battery-Mv
    mention; the test failure caught it immediately and the docstring was restored to
    keep that phrase while staying compact."

requirements-completed: [HYG-01, HYG-03]

duration: ~90min
completed: "2026-09-25"
---

# Phase 35 Plan 04: Comment purge, server core modules Summary

Purged plan/ticket/decision/review/quick-task-ID history from every comment and
docstring in `server/poll_loop.py` (the pacing/hold-state/notification oneshot) plus
six further server-core modules and the hash-comment `requirements-dev.in` file, then
applied a second tightening pass (per orchestrator review) compressing every
docstring/comment to a one-line summary plus a compact contract - poll_loop.py
1986 -> 1307 lines, the steepest cut in the plan - while leaving all code byte-for-byte
unchanged (`same-code --base ee2737a`, no `--allow` needed anywhere except
`poll_loop.py`'s runtime `__doc__` - see key-decisions).

## What was built

**Task 1 — `server/poll_loop.py` (1986 -> 1735 lines; 218 -> 0 history hits).**

The densest and largest file in this plan: a 43-line module docstring with `PLANE-03`/
`D-04`/`D-P2-02` IDs and a `.planning/debug/` path, ~90 inline comment blocks across
every helper and the `run_once()` cycle body, and a ~50-line `run_once()` docstring.
Rewrote each block to keep only what the task specified: ordering constraints (why the
illustration/manual-resolution/colour-rules/calendar priming block must run before
detection; why the hold-branch early return must sit before `detect.load_geofence()`;
why the calendar match has exactly one call site), failure-handling reasoning (why
every `_record_history()`/`_notify_*_transition()` call is wrapped in its own
catch-and-log, never allowed to abort a cycle), and file-format/units facts (the
battery hysteresis thresholds' raw-millivolt reasoning, the 90s/150s/5-entry pacing
constants' derivations). Dropped: every `D-NN`/`WR-NN`/`CFG-NN`/`T-NN-NN`/quick-task-id/
plan-artifact reference, the "quick task 260923-fr4" and "quick task 260827-oz9"
narration threaded through nearly every battery/pacing comment, and the
"Phase 16, plan 07" / "05-02 (DEVICE-04)" markers repeated at every touch point of the
calendar and battery-empty features. `run_once()`'s own docstring was rewritten to the
task's explicit instruction: the pacing/hold-state algorithmic contract survives, the
`D-05`/`D-06`/`D-07`/`D-13` citations do not.

**Task 2 — `device_config.py`, `history_db.py`, `wake.py`, `notify.py`,
`panel_format.py`, `panel_preview.py`, and the four hash-comment files
(169 -> 0 history hits across the six Python files combined; 1 -> 0 in
`requirements-dev.in`).**

- `device_config.py` (1154 -> 1079 lines): the module docstring, the `THEMES`/
  `RUNWAYS` registry design-rationale blocks (Phase 7/8/9 on-glass session narrative,
  quick-task ids), and every `normalise_*()`/`save_device_config()`/
  `load_device_config()` docstring were purged, keeping the validation-bound whys the
  task specified: why each field's `None` means carry-forward vs. genuine-default vs.
  never-set, why `CLEAR_THEME_ARRIVING` exists as an identity-compared sentinel, why
  `DEFAULT_DISPLAY_ENABLED=True`'s fail-open direction is a security-relevant choice,
  and `seconds_until_quiet_hours_end()`'s two load-bearing DST-correctness deviations
  from a naive implementation.
- `history_db.py` (723 -> 713 lines): the module docstring and every writer/reader
  docstring were purged of `CFG-NN`/`D-NN`/`T-06-01-NN`/plan-artifact references,
  keeping the schema, units and retention facts the task specified: the fixed-size
  `meta` table vs. per-cycle-row growth rationale, the `wake_epochs` table-not-column
  justification, `check_in_gaps()`'s "what this reader cannot know" caveats (log-range
  gaps indistinguishable from missed wakes; the `UNIQUE(ts, battery_mv)` collision
  bound), and `daily_battery_averages()`'s Europe/Paris-day-not-UTC-day bucketing facts.
- `wake.py` (442 -> 433 lines): the module docstring and every function docstring were
  purged of `D-05`/`D-13`/`D-27`/`D-03`/`CFG-26` and plan-artifact references, keeping
  the precedence-list contract (`effective_wake_interval_s()`'s five-branch fallback),
  the floor-value rationale, and `next_wake_status()`'s quiet-hours composition
  algorithm (why it calls `quiet_hours_status()` twice against check-in-derived epochs,
  never a render-time "now").
- `notify.py` (212 -> 203 lines): the module docstring's SSRF-gate-reuse and
  redirect-refusal security invariants were kept and rewritten (the exact reason
  `_NoRedirectHandler` exists, why it never re-validates a bounded chain the way
  `fetch_ics()` does, and the logging-discipline rule that a topic URL is exactly as
  secret-shaped as a calendar feed URL) while every `D-25`/`D-27`/`T-20-NN`/`CR-01`/
  `WR-04` reference was dropped.
- `panel_format.py` (145 -> 134 lines): the `PALETTE_RGB` colour-tuning history (three
  phases of on-glass calibration narrative, `D-P2-03`/`D-13`/`D-21` ids) was compressed
  to the two facts that matter for a future maintainer - the values are render-internal
  approximations that never cross the wire, and blue/green were darkened twice after
  real ink proved darker than every monitor preview.
- `panel_preview.py` (160 -> 157 lines): the module docstring's "no production caller"
  explanation and colour-accuracy caveat were kept, purged of the `CFG-10`/
  `06-RESEARCH.md`/`Plan 06-09`/quick-task-id references naming exactly which route was
  removed and when.
- `requirements-dev.in`: one comment (the pytest-migration package group) rewritten to
  drop its `Phase 32`/`TST-01`/`TST-03` references while keeping the per-package intent.
  `requirements.in`, `server/.gitignore`, and `server/state/.gitignore` needed no edits
  - `check --paths` already reported 0 hits on all three.

**Verification (both passes).** `check --paths` reports 0 hits across all eleven files
after both the purge and the tightening pass. `same-code --base ee2737a` returns 0 for
ten of the eleven files with no `--allow`; `poll_loop.py` needed
`--allow server/poll_loop.py` throughout because its module docstring is read at
runtime via `argparse.ArgumentParser(description=__doc__)` (see key-decisions).
`server/test_poll_loop.py` and `server/test_pipeline_e2e.py` (106 passed, 1
pre-existing root-euid skip) pass individually, and the full `pytest server -q -n auto`
is green after the tightening pass (717 passed, 3 pre-existing skips, 0 failed - one
transient failure during tightening, caught and fixed, see key-decisions). `ruff check`
is clean on every touched file. `git diff --stat -- server/requirements*.txt` is
empty - the compiled locks are untouched throughout.

**Tightening pass (second pass, per orchestrator review).** The first pass removed
every history ID but left docstrings and comment blocks long relative to the plan's
~35% guideline (see the ratio table below for the delta). Applied the same compression
discipline 35-02's own second pass established: every docstring cut to a one-line
summary plus a compact contract (non-obvious params, return, invariant - typically
≤8 lines, ≤~15 for a genuinely complex public function like `run_once()` or
`next_wake_status()`); comment blocks over ~10 lines cut to the essential sentence(s);
deleted who-calls-it/who-reads-it lists (e.g. wake.py's `BATTERY_CRITICAL_STATE_KEY`
comment naming every reader module), cross-module tours, and "deliberately"/
"honest"/"never claimed"-style rhetoric that restated the following code, while
keeping one or two sentences of the real why (security invariant, hardware
constraint, units, upstream quirk) per block. Re-verified `check --paths` (0 hits),
`same-code` (still 0/passes, `--allow` still scoped to `poll_loop.py` only), `ruff
check`, and the full `pytest server -q -n auto` suite after every file.

## Comment ratio, original -> after purge -> after tightening

| File | Original | After purge (1st pass) | After tightening (2nd pass) | History hits |
|------|----------|------------------------|------------------------------|---------------|
| server/poll_loop.py | 56.80% | 50.55% | **34.35%** | 218 -> 0 |
| server/device_config.py | 55.63% | 52.55% | **29.48%** | 113 -> 0 |
| server/history_db.py | 47.03% | 46.28% | **28.94%** | 28 -> 0 |
| server/wake.py | 71.27% | 70.67% | **37.31%** | 36 -> 0 |
| server/notify.py | 60.38% | 58.62% | **35.38%** | 25 -> 0 |
| server/panel_format.py | 66.21% | 63.43% | **50.51%** | 19 -> 0 |
| server/panel_preview.py | 47.50% | 46.50% | **33.33%** | 7 -> 0 |
| server/requirements-dev.in | n/a (hash-comment format, no ratio tool support) | n/a | n/a | 1 -> 0 |

Four of the seven Python files now sit at or under the ~35% guideline
(poll_loop.py, device_config.py, history_db.py, panel_preview.py). Three remain
above, each for a specific, file-scoped reason re-verified after the tightening pass
(re-read hunting for restatement, scope talk, and "who calls this" asides - none
remained to cut without also cutting a genuine invariant):

- **wake.py (37.31%, 201 lines)** is the highest-ratio file: a small module (201
  lines) whose entire content is precedence lists and staleness-threshold derivations
  shared across the server and companion web app. `next_wake_status()`'s docstring
  alone documents a genuinely non-obvious two-call composition (why
  `quiet_hours_status()` is called twice, not once) that purge_rules classify as real
  algorithmic why, not restatement - it was compressed from 17 to 9 lines but cutting
  further would drop the contract itself.
- **notify.py (35.38%, 130 lines)** sits essentially at the guideline: a small file
  whose remaining comments are almost entirely the SSRF-gate-reuse and
  redirect-refusal security invariants (why `_NoRedirectHandler` refuses every hop
  outright rather than re-validating a bounded chain) purge_rules require to survive.
- **panel_format.py (50.51%, 99 lines)** is the smallest file in the plan (99 lines)
  with the least further room to compress: its `PALETTE_RGB` data table carries
  necessarily-brief per-entry hardware-calibration annotations (interim estimate vs.
  on-glass-confirmed darkening), and `pack_panel()`'s docstring is a genuine
  bit-manipulation correctness proof (why the per-byte OR across the whole buffer
  never carries a bit between output bytes) - the same class of case 35-02's
  tightening pass accepted for `dither.py` (38.10%) and `runway_config.py` (59.02%).

## Files Created/Modified

- `server/poll_loop.py` - module docstring purged then tightened (first line changed,
  `--allow` needed for same-code - see key-decisions); ~90 inline comment blocks and
  the `run_once()` docstring purged of history then compressed; 1986 -> 1307 lines
- `server/device_config.py` - module docstring, `THEMES`/`RUNWAYS` registry comments,
  and every `normalise_*()`/`save_device_config()`/`load_device_config()` docstring
  purged then tightened; validation-bound whys and the fail-open security note kept;
  1154 -> 726 lines
- `server/history_db.py` - module docstring and every writer/reader docstring purged
  then tightened; schema, units and retention facts kept; 723 -> 539 lines
- `server/wake.py` - module docstring and every function docstring purged then
  tightened; a pre-existing "HOLD_QUIET_HOURS above" -> corrected to "below" while
  rewriting (see key-decisions); 442 -> 201 lines
- `server/notify.py` - module docstring and every function docstring purged then
  tightened; SSRF-gate and redirect-refusal security invariants kept; 212 -> 130 lines
- `server/panel_format.py` - module docstring and the `PALETTE_RGB` colour-tuning
  comment block compressed from three narrated phases to the two facts that matter,
  then tightened further; 145 -> 99 lines
- `server/panel_preview.py` - module docstring and class/function docstrings purged
  then tightened; 160 -> 126 lines
- `server/requirements-dev.in` - one comment rewritten to drop phase/prefix-id
  references

## Decisions Made

- Treated `poll_loop.py`'s `same-code --allow` requirement as a Rule 1 discovery
  (the plan's acceptance criteria assumed no `--allow` would be needed, based on
  35-CONTEXT.md's runtime-`__doc__` file list, which did not include this file) rather
  than a blocker: applied the CONTEXT.md's own stated policy for runtime docstrings
  (trim history, keep accurate `--help` text) identically to how 35-02 handled
  `illustrations.py`. Documented as key-decisions above.
- Left `requirements.in`, `server/.gitignore`, and `server/state/.gitignore`
  byte-identical, since `check --paths` reported 0 hits on all three before this plan
  touched them - no edit was needed to satisfy the plan's must_haves.
- Corrected a one-word self-reference error in `wake.py`'s CHECK_IN vocabulary comment
  (`HOLD_QUIET_HOURS above` -> `below`) while rewriting that comment for the purge,
  since `HOLD_QUIET_HOURS` is genuinely defined later in the file - not a separate
  deviation, bundled into the required rewrite.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan's own acceptance criteria] `poll_loop.py`'s module docstring
is real runtime `--help` text, missed by 35-CONTEXT.md's canonical list**
- **Found during:** Task 1, running `same-code --base ee2737a server/poll_loop.py`
  after the purge with no `--allow`.
- **Issue:** The plan's Task 1 acceptance criteria states `same-code` must exit 0
  "with no --allow". `server/poll_loop.py`'s `build_parser()` calls
  `argparse.ArgumentParser(description=__doc__)`, exactly the runtime-`__doc__` pattern
  35-CONTEXT.md's decisions section documents as `--help` text that "may be trimmed of
  history but stay accurate help text" - but that section's explicit file list
  (`companion/app.py`, `deploy/backup/backup_gate.py`,
  `deploy/backup/skypane_backup.py`, `server/plane/illustrations.py`) did not include
  this file. `check_comment_history.py`'s `same-code` command detects the pattern by
  checking whether the literal substring `__doc__` appears anywhere in the file text
  (`keep_module_doc = "__doc__" in base_text or "__doc__" in working_text`), which is
  correct for this file even though the phase's own canonical list missed it.
- **Fix:** Verified the module docstring's role by grepping for `__doc__` in the file
  (confirmed the single `argparse.ArgumentParser(description=__doc__)` use), then
  applied the CONTEXT.md's own stated runtime-docstring policy: purged history from the
  docstring while keeping it accurate as `--help` text, and used
  `same-code --allow server/poll_loop.py` for verification - the identical handling
  35-02-SUMMARY.md records for `server/plane/illustrations.py`. Confirmed `same-code`
  passes with `--allow` and that no other file's code differs.
- **Files modified:** `server/poll_loop.py`
- **Commit:** 5308c6b (Task 1)

**2. [Rule 1 - Bug] Tightening pass over-compressed `history_db.check_in_gaps()`'s
docstring, dropping a substring a behaviour test asserts on**
- **Found during:** the tightening pass, running `pytest server -q -n auto` after
  rewriting `history_db.py`.
- **Issue:** `test_config_history.py::test_check_in_gaps_docstring_states_what_it_cannot_know`
  introspects `history_db.check_in_gaps.__doc__` directly (not a source-text scan) and
  asserts it contains `"cannot know"`, `"rotat"`, `"unique(ts, battery_mv)"`, `"60"`,
  and `"x-battery-mv"` - the last substring, explaining *why* `battery_mv` is
  unfiltered, was dropped when the "No battery_mv filter" paragraph was compressed to
  one sentence.
- **Fix:** Restored the `X-Battery-Mv` header mention in that sentence while keeping
  the rest of the compression, re-ran the test (green), then the full suite.
- **Files modified:** `server/history_db.py`
- **Commit:** f3a09fa (tightening pass)

---

**Total deviations:** 2 auto-fixed (Rule 1: a gap in the phase's own canonical
runtime-docstring list; Rule 1: a test-caught over-compression, corrected within the
same pass before committing)
**Impact on plan:** No code change beyond the in-scope comment/docstring purge landed
in any commit. The `--allow` usage is scoped to exactly one file's module docstring,
matching the precedent 35-02 already set for the identical pattern. The docstring test
failure was caught and fixed before the tightening-pass commit landed, so no broken
state was ever committed.

## Issues Encountered

None beyond the one documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`server/poll_loop.py`, `device_config.py`, `history_db.py`, `wake.py`, `notify.py`,
`panel_format.py`, `panel_preview.py`, and the four hash-comment/`.gitignore` files are
fully purged (0 history hits each) and code-unchanged. Combined with 35-02's five files
and 35-03's four files, all of `server/` (excluding `server/plane/__init__.py`, trivial,
and the test files, which belong to a later plan in this group per 35-CONTEXT.md's
scope) is now purged.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `server/poll_loop.py` — FOUND
- `server/device_config.py` — FOUND
- `server/history_db.py` — FOUND
- `server/wake.py` — FOUND
- `server/notify.py` — FOUND
- `server/panel_format.py` — FOUND
- `server/panel_preview.py` — FOUND
- Commit 5308c6b (Task 1: poll_loop.py) — FOUND
- Commit e9a0acc (Task 2: server module group) — FOUND
- Commit f3a09fa (tightening pass, per orchestrator review) — FOUND
