---
quick_id: 260908-asr
status: complete
date: 2026-09-08
commits:
  - c7b5745
  - 0d7bb47
files_modified:
  - server/plane/calendar_rules.py
  - server/test_calendar_rules.py
  - server/test_poll_loop.py
  - companion/test_config_page.py
---

# 260908-asr — Enforce D-03's rolling window on every registry path (T-16-PRIV)

Closes phase 16's one open security threat, `T-16-PRIV` (medium, below the
`high` block threshold, so it shipped non-blocking).

## What was wrong

The rolling window was applied only on `refresh_calendar_registry()`'s
**success** path. On the fetch-failure path `registry["entries"]` was
re-persisted verbatim, and `load_calendar_registry()` re-validated record
*shape* but never re-applied the *window*. A feed that broke and stayed
broken therefore left the last successful fetch on disk indefinitely,
re-written every 30 minutes with no expiry — the opposite of "retention is
bounded to the current UTC day plus 48 hours".

Impact was privacy-at-rest only: a stale entry cannot produce a match (the
90-minute `CALENDAR_MATCH_TOLERANCE_S` excludes it) and the entry cap still
bounds growth. But the file holds a named person's work schedule on a VPS,
and D-03 chose a short window precisely so that schedule would not
accumulate there.

## The fix — one place owns the invariant

`_rebuild_capped_entries()` was **already** the single helper that both
`load_calendar_registry()` and `write_calendar_registry()` route every entry
list through, and `write_calendar_registry()`'s docstring already claimed
*"a caller can never persist what the loader would only drop again on the
next read"* — true for shape and the entry cap, false for the window.
Applying `select_window_entries()` there makes load and write agree by
construction, and covers both the failure-path re-persist and a file that
aged on disk.

Consequence worth naming: the failure path needs **no trim call of its
own**. Because `refresh_calendar_registry()` opens with
`load_calendar_registry(state_dir, now)`, the list it re-persists was
already windowed by that load. The whole change to that function is
threading `now` into four existing calls.

`select_window_entries()` remains the sole implementation of the window's
two edges; nothing else recomputes them.

## Two decisions the brief did not cover

- **Window drops are deliberately not folded into the drop-count warning.**
  That warning classifies an anomaly; routine expiry is the designed steady
  state, and `load_calendar_registry()` runs on every companion page render
  (`companion/app.py:1033`), so folding it in would flood the journal on
  every read of a day-old file.
- **`_resolve_retention_now()` guards the new clock seam.**
  `select_window_entries()` returns `[]` for any `now` it cannot convert, so
  an unguarded hostile or absent `now` reaching the writer would have
  **erased** the registry rather than trimmed it — turning a privacy fix
  into data loss. Reuses `_normalise_calendar_entry()`'s bool-reject +
  `math.isfinite` discipline.

`calendar_fetch_is_due()`'s docstring was rescoped: it asserted "this module
defines no clock of its own", which the new `time.time()` default makes false
at module scope.

## Verification

The check the original goal verification missed now exists: seed an entry the
realistic way, jump 10 days, drive **three consecutive failing** refresh
cycles (advancing past `CALENDAR_FETCH_INTERVAL_S` each time so the throttle
genuinely lets each attempt through — `FETCH_FAILED` is asserted per cycle),
and read the **raw** file with `json.load()` rather than through the loader,
which now windows on read and would mask the very on-disk state under test.

Three anti-drift checks alongside it: the loader windows on read without
rewriting the file; the writer refuses to persist what the loader would drop;
and a behavioural equivalence guard asserting the loader's entries are exactly
`select_window_entries(list, now)`, which goes red if a second window
implementation ever appears.

`EXPECTED_CHECK_COUNT` re-derived by running the harness: **76 → 80**. All
four confirmed **non-vacuous** by reverting the fix and watching only those
four go red (76/80).

- `scripts/run-all-tests.sh` — **PASS, 19/19 harnesses** (`calendar_rules`
  80/80, `poll-loop` 80/80, `config-page` 127/127)
- `server/.venv/bin/ruff check .` — clean
- Leaf contract intact: no `enrich` / `colour_rules` / `manual_resolutions` /
  `illustrations` import; stdlib-only (`time` added).

## Harness churn

Checks whose subject is merge/replace/cap semantics rather than retention now
pass an explicit `now` bracketing their own fixtures, rather than the window
being weakened to keep them green. `test_poll_loop.py`'s `CLOCK_BASE` is
2023-11-14, ~2.8 years behind real now, so all eight of its direct write sites
needed one too.

## Follow-up (not done here, deliberately)

`16-SECURITY.md` is **not** edited by this task — the T-16-PRIV row and its
Open Threats section still read `open`. That file is the auditor's own record;
reconciling it belongs to `/gsd-secure-phase 16`.

Branch note: this work sits on `claude/t-16-priv-retention`, branched from
`claude/seed-3-roster-highlight` (phase 16 is not on `main`).
