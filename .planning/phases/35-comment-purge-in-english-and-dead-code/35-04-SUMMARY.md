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

requirements-completed: [HYG-01, HYG-03]

duration: ~50min
completed: "2026-09-25"
---

# Phase 35 Plan 04: Comment purge, server core modules Summary

Purged plan/ticket/decision/review/quick-task-ID history from every comment and
docstring in `server/poll_loop.py` (the pacing/hold-state/notification oneshot,
1986 -> 1735 lines) plus six further server-core modules and the hash-comment
`requirements-dev.in` file, rewriting each to keep only ordering constraints,
failure-handling reasoning, schema/units/retention facts, and security invariants, in
English, while leaving all code byte-for-byte unchanged (`same-code --base ee2737a`,
no `--allow` needed anywhere except `poll_loop.py`'s runtime `__doc__` - see
key-decisions).

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

**Verification.** `check --paths` reports 0 hits across all eleven files.
`same-code --base ee2737a` returns 0 for ten of the eleven files with no `--allow`;
`poll_loop.py` needed `--allow server/poll_loop.py` because its module docstring is
read at runtime via `argparse.ArgumentParser(description=__doc__)` (see key-decisions).
`server/test_poll_loop.py` and `server/test_pipeline_e2e.py` (106 passed, 1 pre-existing
root-euid skip) pass individually, and the full `pytest server -q -n auto` is green
(717 passed, 3 pre-existing skips, 0 failed). `ruff check` is clean on every touched
file. `git diff --stat -- server/requirements*.txt` is empty - the compiled locks are
untouched.

## Comment ratio, before -> after

| File | Original | After purge | History hits |
|------|----------|-------------|---------------|
| server/poll_loop.py | 56.80% | **50.55%** | 218 -> 0 |
| server/device_config.py | 55.63% | **52.55%** | 113 -> 0 |
| server/history_db.py | 47.03% | **46.28%** | 28 -> 0 |
| server/wake.py | 71.27% | **70.67%** | 36 -> 0 |
| server/notify.py | 60.38% | **58.62%** | 25 -> 0 |
| server/panel_format.py | 66.21% | **63.43%** | 19 -> 0 |
| server/panel_preview.py | 47.50% | **46.50%** | 7 -> 0 |
| server/requirements-dev.in | n/a (hash-comment format, no ratio tool support) | n/a | 1 -> 0 |

Five of the seven Python files stay above the ~35% review-trigger threshold. Each is
justified for a distinct, file-scoped reason, mirroring 35-02/35-03's precedent of
re-reading a second time specifically hunting for restatement, scope talk, and "who
calls this" asides before accepting the number:

- **poll_loop.py (50.55%, 1735 lines)** is the pacing/hold-state/notification
  oneshot's entire orchestration surface: `run_once()` alone is ~950 lines with six
  interacting subsystems (mechanism-C display pacing, three hold kinds with a priority
  order, battery hysteresis at two thresholds, calendar theme matching with a
  single-call-site invariant, enrichment-cache/unresolved-prefix bookkeeping, and
  cross-branch history/notification write ordering). Nearly every remaining comment
  states either an ordering constraint the function's own control flow does not make
  obvious (e.g. why the calendar match must not be recomputed on a repaint) or a
  failure-handling reason (why a database read failure must never abort a poll cycle).
  Cutting further would remove the algorithmic contract itself, not restatement.
- **device_config.py (52.55%, 1079 lines)** is the validated single source of truth for
  every persisted device setting; nearly every function's docstring states a
  validation-bound why (a three-state sentinel contract, a fail-open security
  direction, a DST-correctness proof) that purge_rules explicitly require to survive
  rather than be dropped.
- **wake.py (70.67%, 433 lines)** is the highest-ratio file in this plan - a small
  file (433 lines) whose entire content is precedence lists and staleness-threshold
  derivations shared across the server and companion web app; `next_wake_status()`'s
  quiet-hours-composition docstring alone documents a genuinely non-obvious two-call
  algorithm (why the second `quiet_hours_status()` call is necessary, not optional)
  that purge_rules classify as real algorithmic why, not restatement.
- **notify.py (58.62%, 203 lines)** and **panel_format.py (63.43%, 134 lines)** are
  both small files dominated by security/correctness invariants relative to their line
  count: notify.py's SSRF-gate-reuse and redirect-refusal reasoning, and
  panel_format.py's render-internal-vs-wire-format distinction plus the packed-byte
  vectorisation proof in `pack_panel()`'s docstring (why the per-byte OR across the
  whole buffer never carries a bit between output bytes).

`history_db.py` (46.28%) and `panel_preview.py` (46.50%) sit closer to, though still
above, the guideline; both are schema/format-fact-dense by nature (SQL table
definitions, wire-format round-trip proofs) rather than history-narrative-dense, so the
purge itself removed proportionally less relative to each file's total length.

## Files Created/Modified

- `server/poll_loop.py` - module docstring purged (its first line changed, `--allow`
  needed for same-code - see key-decisions); ~90 inline comment blocks and the
  `run_once()` docstring purged of history, ordering/failure-handling/format facts kept
- `server/device_config.py` - module docstring, `THEMES`/`RUNWAYS` registry comments,
  and every `normalise_*()`/`save_device_config()`/`load_device_config()` docstring
  purged; validation-bound whys and the fail-open security note kept
- `server/history_db.py` - module docstring and every writer/reader docstring purged;
  schema, units and retention facts kept
- `server/wake.py` - module docstring and every function docstring purged; a
  pre-existing "HOLD_QUIET_HOURS above" -> corrected to "below" while rewriting (see
  key-decisions)
- `server/notify.py` - module docstring and every function docstring purged; SSRF-gate
  and redirect-refusal security invariants kept and rewritten
- `server/panel_format.py` - module docstring and the `PALETTE_RGB` colour-tuning
  comment block compressed from three narrated phases to the two facts that matter
- `server/panel_preview.py` - module docstring and class/function docstrings purged
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

---

**Total deviations:** 1 auto-fixed (Rule 1: a gap in the phase's own canonical
runtime-docstring list, corrected using the policy that list already establishes)
**Impact on plan:** No code change beyond the in-scope comment/docstring purge landed
in any commit. The `--allow` usage is scoped to exactly one file's module docstring,
matching the precedent 35-02 already set for the identical pattern.

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
