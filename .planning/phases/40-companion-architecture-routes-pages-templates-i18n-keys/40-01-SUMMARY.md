---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 01
subsystem: testing
tags: [ast, pytest, companion, structural-guard, render-baseline, determinism]

# Dependency graph
requires: []
provides:
  - "test-support/companion_structure.py: ast-based production file/function line-count measurement (production_files, file_line_counts, function_code_lines, oversized_files, long_functions)"
  - "companion/test_structure_guards.py: file/function length guard with a named, measured allowlist (TRACKED_FILE_EXCEPTIONS, PENDING_OVERSIZED_FILES, PENDING_LONG_FUNCTIONS)"
  - "test-support/companion_render_snapshot.py: deterministic seed + frozen-clock capture harness (seed_snapshot_state, capture_pages, capture_unauthenticated, load_baseline/write_baseline, main --write CLI)"
  - "companion/testdata/render_baseline.json: committed pre-refactor baseline (44 rendered-page entries, 51 unauthenticated-route entries)"
  - "companion/test_render_baseline.py: byte-equality tests against the committed baseline"
affects: ["40-02", "40-03", "40-04", "40-05", "40-06", "40-07", "40-08", "40-09", "40-10", "40-11", "40-12", "40-13", "40-14", "40-15", "40-16"]

tech-stack:
  added: []
  patterns:
    - "Structural measurement lives in test-support/ (stdlib ast), never inside a companion/test_*.py module, so guard G2 (no ast/inspect/tokenize/linecache in a companion test) is structurally impossible to violate"
    - "A committed JSON render baseline plus a byte-equality test is this phase's own proof that a behaviour-preserving refactor changed nothing observable"
    - "Real time sources that leak into rendered HTML (a fallback datetime.now()/time.time() at a call site that forgot now=) are frozen at their source inside a harness; only a genuinely unfreezable value (a file's kernel-set ctime) is regex-normalised, and that exception is named in the harness's own docstring"

key-files:
  created:
    - test-support/companion_structure.py
    - companion/test_structure_guards.py
    - test-support/companion_render_snapshot.py
    - companion/test_render_baseline.py
    - companion/testdata/render_baseline.json
  modified: []

key-decisions:
  - "PENDING_OVERSIZED_FILES/PENDING_LONG_FUNCTIONS allowlists were populated from the helper's own measured output (12 functions, 5 oversized files including style.css), not from the plan's table, though the two agreed exactly"
  - "Dropped the plan's own instruction to name CMP-03/CMP-06/Phase 32-33 in the guard's module docstring: CLAUDE.md forbids phase/ticket IDs in comments and takes precedence over plan text"
  - "Froze time.time() and health_page.datetime.now() in addition to the plan-named history_db.utc_now_iso(), after discovering both are genuine pre-existing leaks (calendar_rules' registry-window filter and health_page.resolution_stats() each have a call site that never passes now=)"
  - "Normalised the four freshness pages' data-refresh-token attribute by regex instead of freezing it at the source: it folds in a file's st_ctime_ns, which no syscall (including os.utime()) can back-date, making it the one value in this harness that cannot be frozen"

requirements-completed: [CMP-03, CMP-06, CMP-01]

duration: ~55min
completed: 2026-09-27
---

# Phase 40 Plan 01: Structural guard and render-snapshot baseline Summary

Built the two measuring instruments the rest of Phase 40 is verified against: an AST-based file/function length guard with a named, measured allowlist (12 long functions, 5 oversized files), and a committed byte-level baseline of every page's rendered HTML (44 entries: 11 requests x 2 languages x 2 themes) plus every route's unauthenticated response (51 entries) — captured with a frozen clock so two independent captures are byte-identical.

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-27
- **Tasks:** 2/2 completed
- **Files created:** 5

## Accomplishments

- `test-support/companion_structure.py` measures every companion production file's line count and every function's code-line count via `ast`, living outside `companion/` so guard G2 (no ast/inspect/tokenize/linecache inside a companion test module) can never be violated by it.
- `companion/test_structure_guards.py` enforces a 1500-line file ceiling and an 80-code-line function ceiling with an explicit, named allowlist for every offender that exists today; a mutation check (temporarily removing one function from the allowlist) proved it fails, naming the offender and its count.
- `test-support/companion_render_snapshot.py` seeds a deterministic state (flights within the last day, a battery-trend window ending exactly at the frozen instant, an unresolved callsign prefix, a connected calendar with a real entry and a `last_synced_at`, one colour rule, one manual resolution) against a real `companion/app.py`, with three real time sources frozen for the whole capture.
- `companion/testdata/render_baseline.json` — the committed pre-refactor baseline — and `companion/test_render_baseline.py`, which assert a fresh capture equals it byte-for-byte. Verified deterministic: passes twice in a row with a real 65-second gap between runs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Structural metrics helper and the file/function length guard** - `286e62c` (test)
   - Follow-up fix: `0475b98` (fix) — dropped phase/ticket IDs the plan's own action text had asked for in a docstring, per CLAUDE.md precedence.
2. **Task 2: Deterministic render snapshot harness and committed baseline** - `43fd8f8` (test)

_No TDD RED→GREEN split: both tasks build a measuring instrument that is correct (and passing) by construction once the allowlist/baseline reflects the helper's own measured output; the required "proves it can fail" property was instead demonstrated directly via the mutation checks below._

## Files Created/Modified

- `test-support/companion_structure.py` - AST-based production_files()/file_line_counts()/function_code_lines()/oversized_files()/long_functions()
- `companion/test_structure_guards.py` - the guard, with FILE_LINE_LIMIT=1500, FUNCTION_LINE_LIMIT=80, and the three named allowlist sets
- `test-support/companion_render_snapshot.py` - frozen_clock(), seed_snapshot_state(), capture_pages(), capture_unauthenticated(), load_baseline()/write_baseline(), capture_snapshot(), and the `--write` CLI
- `companion/test_render_baseline.py` - test_rendered_pages_match_the_baseline, test_unauthenticated_responses_match_the_baseline
- `companion/testdata/render_baseline.json` - the committed baseline (44 page entries, 51 unauthenticated-route entries)

## Decisions Made

- Measured the guard's allowlist from the helper's own live output rather than transcribing the plan's table (they agreed exactly: 12 long functions, 5 oversized files including the tracked `style.css` exception).
- Two real, pre-existing time leaks were discovered and frozen that the plan's own list of three did not name explicitly by call site: `server/plane/calendar_rules.py`'s registry-window filter falls back to `time.time()` because `companion/app.py`'s two `load_calendar_registry()` call sites never pass `now=`, and `companion/pages/health_page.py`'s `resolution_stats()` falls back to `datetime.now(timezone.utc)` for the identical reason. Both are now frozen inside the harness (see the module's own docstring for the full account); neither is fixed at its production call site — that is out of this plan's scope.
- One value could not be frozen at its source at all: the four freshness pages' `data-refresh-token` attribute folds in a file's `st_ctime_ns`, which the kernel sets on every write and no syscall can back-date. Normalised by regex (`_TOKEN_RE`) to a fixed placeholder before a page body is ever stored or compared — the sole regex-based normalisation in the harness, named in its docstring as the plan requires.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4-adjacent, CLAUDE.md precedence] Dropped phase/ticket IDs from a docstring the plan's own action text asked for**
- **Found during:** Task 1, post-commit `check_comment_history.py check` re-run
- **Issue:** The plan's Task 1 `<action>` explicitly asked for the module docstring to reference "the audit's CMP-03 scope" and "Phase 32/33 conventions". CLAUDE.md forbids plan/ticket/phase IDs in comments, enforced by `scripts/check_comment_history.py`, and per the CLAUDE.md-precedence rule this overrides plan text. The violation slipped past an earlier pre-commit check only because the file was still untracked at that point (the checker scans tracked files).
- **Fix:** Reworded the two sentences to describe the same reasoning (production-only scope, existing test-migration conventions) with no ID or phase-word literal.
- **Files modified:** `companion/test_structure_guards.py`
- **Verification:** `scripts/check_comment_history.py check` clean; guard tests still 104/104 passing; ruff clean.
- **Commit:** `0475b98`

**2. [Rule 2 - missing critical functionality] Froze two additional real time leaks beyond the plan's named one**
- **Found during:** Task 2, while tracing every render-time clock read to build `frozen_clock()`
- **Issue:** The plan named `history_db.utc_now_iso()` as the one clock to freeze. Reading `companion/app.py`'s and `companion/pages/health_page.py`'s actual call sites turned up two more real leaks: `calendar_rules.load_calendar_registry()`'s window filter defaults to `time.time()` (never passed `now=` from `companion/app.py`), and `health_page.resolution_stats()` defaults to `datetime.now(timezone.utc)` (never passed `now=` from its one caller). Left unfrozen, either would have made the Display and Health page bodies depend on real wall-clock time, breaking the "two captures at different wall-clock times are byte-identical" requirement.
- **Fix:** `frozen_clock()` patches `time.time` and `companion.pages.health_page.datetime` (a frozen `datetime` subclass) alongside `history_db.utc_now_iso`, all three restored on exit.
- **Files modified:** `test-support/companion_render_snapshot.py`
- **Verification:** `test_render_baseline.py` passes twice in a row with a real 65-second gap between runs (see below).
- **Commit:** `43fd8f8`

**3. [Rule 1 - bug in the harness under construction, fixed before first commit] data-refresh-token broke determinism via an unfreezable file ctime**
- **Found during:** Task 2, first `--write` + pytest verification pass
- **Issue:** `/display?flash=saved` (and every other freshness-tracked page) failed byte-equality on the very first re-run: `_page_freshness_token()` folds each stamped file's `st_ctime_ns` into its hash, and ctime is set by the kernel on every write with no syscall (including `os.utime()`) able to back-date it — so two independent temporary state directories, however identically seeded, always produce a different token.
- **Fix:** Added `_TOKEN_RE`, a regex that normalises the `data-refresh-token="..."` attribute to a fixed placeholder in every captured page body, before it is stored in the baseline or compared against it. Documented in the harness's own module docstring as the plan requires ("Normalising output with a regex is allowed only for a value that cannot be frozen").
- **Files modified:** `test-support/companion_render_snapshot.py`
- **Verification:** baseline regenerated; `test_render_baseline.py` passes; mutation checks (below) confirm the test still catches a real content regression.
- **Commit:** `43fd8f8` (this fix landed before the task's own first commit — no separate commit)

---

**Total deviations:** 3 (1 CLAUDE.md-precedence fix, 1 Rule 2 addition, 1 Rule 1 fix within the harness under construction)
**Impact on plan:** All three were necessary for the guard/harness to be correct and to honour the plan's own determinism and no-phase-ID requirements. No scope creep — no production file under test was touched.

## Issues Encountered

None beyond the deviations above.

## Mutation Checks (acceptance criteria)

- **Structural guard:** removing `companion/pages/history_page.py::_history_cards_html` from `PENDING_LONG_FUNCTIONS` made `test_no_production_function_exceeds_the_code_line_ceiling` fail, naming the function and its line count (95). Reverted before commit.
- **Render baseline (page):** editing one character of the Home page's `<title>` in the committed JSON made `test_rendered_pages_match_the_baseline` fail with a unified diff naming `'/|en|light'`. Baseline regenerated clean before commit.
- **Render baseline (unauthenticated, T-40-01 route-gate scenario):** flipping `GET /health`'s recorded status from 303 to 200 in the committed JSON made `test_unauthenticated_responses_match_the_baseline` fail with a diff naming `'GET /health'` — the exact route-loosening regression the threat register's T-40-01 mitigation exists to catch. Baseline regenerated clean before commit.
- **Determinism:** `companion/test_render_baseline.py` was run twice with a real 65-second gap between invocations; both passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both measuring instruments are in place and green on the unmodified codebase:

- Every subsequent Phase 40 plan that splits a file or a function should shrink `PENDING_OVERSIZED_FILES`/`PENDING_LONG_FUNCTIONS` in `companion/test_structure_guards.py` as it goes (the guard fails on any file/function that goes over the ceiling and is not already named there), with the phase's closing plan expected to empty both sets.
- Every subsequent Phase 40 plan that touches `companion/`'s rendering path should run `companion/test_render_baseline.py` and expect it to still pass unchanged — a failure there is the "no rendered-output change" contract breaking, except for the three deliberate CFG-34(a)-(c) live-age changes a later plan introduces on purpose (at which point the baseline is expected to be regenerated for exactly those entries, and the harness's `--write` CLI is the sanctioned way to do it).
- No blockers.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 5 created files confirmed present on disk; all 3 task commit hashes (`286e62c`, `0475b98`, `43fd8f8`) confirmed present in git history.
