---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 03
subsystem: database
tags: [sqlite, wal, history, device-health, staleness, observability]

requires:
  - phase: 19-05 / 20-02
    provides: "server/wake.py's device_staleness_thresholds() — the one definition of warn/error staleness, and the MISSED_WAKES_* multipliers with their 5/20-minute floors"
  - phase: 06-01
    provides: "history_db.ingest_caddy_battery_log() — the only path device check-ins take into device_health, and the rotation behaviour that bounds every claim made here"
  - phase: 22-06
    provides: "_paris_day_or_none() and daily_battery_averages()'s row-shape-as-contract rule, which the new reader's keys follow"
provides:
  - "history_db.check_in_gaps(conn, since=None) — observed intervals between consecutive device_health check-ins, oldest-first, with unknowable spans reported as unknown"
  - "wake.classify_check_in_gap(gap_s, wake_interval_s) — on_cadence / late / missing / unknown, derived from device_staleness_thresholds()"
  - "wake.CHECK_IN_* — the observed verdict vocabulary every caption will inherit"
  - "history_db.record_wake_epoch() and the wake_epochs table — true interval epochs accruing from ship day, read by nothing in phase 24"
affects: [24-07]

tech-stack:
  added: []
  patterns:
    - "Re-sort a device_health series by ingest id, not by ts, before taking intervals: ts is attacker-influenceable, id is the order Caddy appended the lines"
    - "A fourth CREATE TABLE IF NOT EXISTS is a migration-free schema change in this project; a new column is not"
    - "Read a reuse property off a function's compiled co_names/co_consts rather than its source text, so a docstring mention can neither pass nor fail the check"

key-files:
  created: []
  modified:
    - server/history_db.py
    - server/wake.py
    - server/poll_loop.py
    - server/test_config_history.py
    - server/test_poll_loop.py

key-decisions:
  - "The classifier landed in wake.py, not history_db.py — and NOT because of an import cycle (there is none). history_db.py's own docstring declares it stdlib-only and forbids importing device_config, which wake.py imports."
  - "The gap series is ordered by ingest id, not by ts, so a hostile timestamp cannot reorder the series around itself."
  - "An undatable or out-of-order bound makes its span unknown rather than dropping the row — dropping merges two real intervals into one false long one."
  - "wake_epochs.wake_interval_s is nullable on purpose: 'the cadence cannot be determined' is a real epoch, not a continuation of the last one."
  - "_NO_WAKE_EPOCH is a sentinel, not None, because None is a legitimate interval."

patterns-established:
  - "Verdict vocabulary as module constants beside the thresholds they use, so the Frame tile and any future grid share one function rather than two consistent copies"
  - "A reader's docstring carries what it cannot know, not only the caption drawn from it"

requirements-completed: []

duration: 62min
completed: 2026-09-14
---

# Phase 24 Plan 03: D20's data question, settled in code

**`device_health`'s observed check-in gaps are now readable with their own limits written beside them, judged by the single `device_staleness_thresholds()` the Frame tile already uses — and a migration-free `wake_epochs` table starts accruing true interval epochs that nothing in this phase reads.**

## Performance

- **Duration:** ~62 min
- **Tasks:** 3/3
- **Files modified:** 5 (one of them, `server/wake.py`, not listed in the plan's `files_modified` — see Deviations)

## Commits

| Commit | Gate | What |
|---|---|---|
| `8985293` | RED | failing checks for the observed check-in gap reader |
| `9700220` | GREEN | `check_in_gaps()` |
| `cbb671f` | RED | failing checks for the one definition of "late" |
| `1098284` | GREEN | `wake.classify_check_in_gap()` |
| `cdb3d00` | RED | failing checks for the forward-looking epoch table |
| `005d1f0` | GREEN | `wake_epochs` + the deduped, contained poll write |

Three RED/GREEN pairs. No REFACTOR commit was needed on any task.

---

## The decision that mattered most

**Where the classifier lives — and why the plan's own stated trigger for that decision was the wrong one.**

The plan said: *"If importing `wake` into `history_db` would create a cycle, the verdict computation belongs in `wake.py`."* Measured on the tree, **there is no cycle**. `wake.py` imports `os`, `datetime` and `server.device_config`; nothing in that chain reaches back to `history_db`. `server/.venv/bin/python -c "import server.history_db, server.wake"` succeeds and still does. On the plan's literal trigger, the classifier belonged in `history_db.py`.

It went into `wake.py` anyway, on a different and stronger ground: **`history_db.py`'s own module docstring**, line 27, reads *"Stdlib-only (`sqlite3`, `json`, `os`, `datetime`). This module must not import `device_config` … it is a leaf."* `import server.wake` breaks that sentence twice — directly (it is not stdlib) and transitively (`wake` imports `device_config`, the one module `history_db` is explicitly forbidden). The absence of a cycle is not permission; the written leaf contract is the binding constraint, and no pinned check enforces it today, which is exactly why a silent breach would have gone unnoticed until something else needed it.

The placement is also the better one on its merits. `device_staleness_thresholds()` lives in `wake.py`, and so now does its one application to these intervals — so the Frame tile and any grid drawn from `check_in_gaps()` share **one function**, not two consistent copies. `history_db.py` returns raw gaps and classifies nothing; its docstring names `wake.classify_check_in_gap()` as the one place verdicts come from, which is also what satisfies the plan's `key_links` pattern (`device_staleness_thresholds` appears in `history_db.py` — as a documented link, not a duplicated import).

**Handoff consequence for 24-07:** `companion/wake.py` is a shim with an explicit re-export list. It does **not** currently re-export `classify_check_in_gap` or the `CHECK_IN_*` constants. 24-07 owns that file and must either add them to the list or import `server.wake` directly. This plan does not touch `companion/` at all.

---

## Mutations, with their quoted failure messages

Every new check was reverted and proven to fail. Staged before mutating; `git show --name-only` after each commit.

### Task 1

**M1 — add the `battery_mv IS NOT NULL` filter the battery chart legitimately uses** (the plan's named mutation). Exactly one check failed:

> FAIL check_in_gaps() reads EVERY device_health row, including one whose battery_mv is NULL — a missing X-Battery-Mv header is not a missed wake (CFG-43) - the NULL-battery check-in was filtered out of the series, merging the two 30-minute intervals into one 3600 s gap that would render as a missed wake the device never missed: `[{'ts': '2026-09-02T11:00:00+00:00', 'from_ts': '2026-09-02T10:00:00+00:00', 'gap_s': 3600, 'day': '2026-09-02'}]`

**M2 — drop the undatable row and move on** (the naive implementation). Exactly one check failed:

> FAIL check_in_gaps() reports the spans an undatable ts bounds as UNKNOWN rather than merging them into one false long interval - the undatable check-in was dropped and the spans either side of it silently merged into one 3600 s interval — a missed wake that never happened: `[{'ts': '2026-09-02T11:00:00+00:00', 'from_ts': '2026-09-02T10:00:00+00:00', 'gap_s': 3600, 'day': '2026-09-02'}]`

**M3 — trust the SQL `ts` ordering instead of re-sorting by ingest id** (not asked for; run because the ordering was my own design decision and needed to be proven load-bearing). Exactly one check failed:

> FAIL check_in_gaps() reports the spans an undatable ts bounds as UNKNOWN … `[{'ts': '2026-09-02T11:00:00+00:00', 'from_ts': '2026-09-02T10:00:00+00:00', 'gap_s': 3600, 'day': '2026-09-02'}, {'ts': 'not-a-timestamp', 'from_ts': '2026-09-02T11:00:00+00:00', 'gap_s': None, 'day': None}]`

M3 is the one that justifies the ingest-id ordering: with `ORDER BY ts`, the string `not-a-timestamp` sorts *after* every ISO timestamp, so the two real check-ins become adjacent and their 3600 s merge is reported as a genuine gap — while a meaningless trailing "span" to the hostile row is reported instead. A hostile `ts` could therefore manufacture a missed wake. `id` is assigned by `ingest_caddy_battery_log()` in the order Caddy appended the lines and is not attacker-influenceable.

### Task 2

**M4 — `gap_s >= warn_s` becomes `>`** (the plan's named mutation). Exactly one check failed, naming the boundary:

> FAIL classify_check_in_gap() is on-cadence below warn_s, late EXACTLY AT warn_s, still late below error_s and missing EXACTLY AT error_s, for a non-default 777 s cadence (CFG-43) - **at the boundary exactly AT warn_s** (warn_s=2331, error_s=9324): a 2331 s gap classified 'on_cadence', expected 'late'

**M5 — `gap_s >= error_s` becomes `>`.** Exactly one check failed, naming the other boundary:

> FAIL classify_check_in_gap() is on-cadence below warn_s … - **at the boundary exactly AT error_s** (warn_s=2331, error_s=9324): a 9324 s gap classified 'late', expected 'missing'

**M6 — re-derive the thresholds inline** (`max(3 * interval, 300)`, `max(12 * interval, 1200)`) instead of calling the shared function. Exactly one check failed:

> FAIL classify_check_in_gap()'s own source derives its thresholds from device_staleness_thresholds() … - classify_check_in_gap()'s body never calls device_staleness_thresholds() - it references `['CHECK_IN_LATE', 'CHECK_IN_MISSING', 'CHECK_IN_ON_CADENCE', 'CHECK_IN_UNKNOWN', 'bool', 'float', 'int', 'isinstance', 'max']`

**M7 — read an unknowable gap as on-cadence** (`if gap_s is None: return CHECK_IN_ON_CADENCE`). Exactly one check failed:

> FAIL classify_check_in_gap() reports an unknowable gap (None, a non-number, a bool, a negative, NaN) as unknown — never as on-cadence - gap_s=None classified 'on_cadence', expected 'unknown'

### Task 3

**M8 — remove the dedupe** (the plan's named mutation). Exactly the two dedupe checks failed, one per harness:

> FAIL three consecutive poll cycles at an unchanged effective wake interval write exactly one wake_epochs row, and a fourth at a changed interval writes a second (CFG-43 Task 3) - three cycles at an unchanged 600 s cadence wrote 3 wake_epochs rows, expected exactly 1: `[('2026-09-14T00:26:18+00:00', 600), ('2026-09-14T00:26:18+00:00', 600), ('2026-09-14T00:26:18+00:00', 600)]`

> FAIL record_wake_epoch() inserts only when the effective interval differs from the newest stored row … - expected inserts only on a change, got `[1, 1, 1, 1, 1, 1, 1]`

**M9 — move the epoch write outside `_record_history()`'s existing containment.** Two checks failed — the new one, and a pre-existing one, which is informative rather than a problem:

> FAIL a wake_epochs write raising sqlite3.Error is contained by _record_history()'s existing handler - the poll cycle completes and the panel is still written (T-24-03-B) - exception: `Error('wake_epochs write exploded')`

> FAIL a history.db failure (open_db raising) is caught and logged without failing the cycle or leaving panel.bin unwritten - exception: `OperationalError('simulated lock')`

The second failure is the pre-existing containment check catching the *extra* unguarded `open_db()` the mutation introduced. The existing guard and the new one overlap deliberately; both must hold.

**M10 — drop `IF NOT EXISTS` from the fourth table.** Two checks failed, one of them pre-existing:

> FAIL every CREATE TABLE in history_db.py is guarded by IF NOT EXISTS and there are exactly four … - 1 of history_db.py's 4 CREATE TABLE statements are not guarded by IF NOT EXISTS — an unguarded one raises on the second connection

> FAIL connect() creates history.db, sets WAL + busy_timeout, creates all three tables, and is idempotent - exception: `OperationalError('table wake_epochs already exists')`

The second is the existing idempotence check firing exactly as it should: `init_schema()` runs on every connection from both processes, so an unguarded statement is not a style question, it is a crash on connection two.

---

## Checks that failed the vacuity question, and what was done

**One did, and it was mine.** The first draft of the Task 2 reuse check read `inspect.getsource(wake.classify_check_in_gap)` and rejected the source text if it contained `MISSED_WAKES_WARN` and friends. It failed immediately against a **correct** implementation, because the function's *docstring* explains that it does not re-type those constants. A check that a correct build fails is the mirror of the vacuity problem and equally useless — and the obvious "fix" (delete the explanation from the docstring) would have paid for the check with the documentation.

Replaced with a reading off the **compiled** function:

- `classify_check_in_gap.__code__.co_names` must contain `device_staleness_thresholds` (reuse proven positively, not by absence);
- it must contain none of the four multiplier/floor names;
- `co_consts` must contain none of the four *values* (3, 12, 300, 1200), so a re-typing that inlined the literals instead of the names is caught too;
- `co_names` must contain neither `device_config` nor `load_device_config`, which is how "takes the cadence as an argument, never reads config" is pinned structurally rather than by hope.

This is strictly stronger than the text scan and immune to prose. M6 above confirms it fires.

**Two other checks are guards, not regressions, and are labelled as such** so a later reader cannot mistake one for the other:

- *"server/history_db.py still contains no ALTER TABLE and no PRAGMA user_version"* passed on the commit that introduced it, because it was already true. It exists to hold in both directions — it is the pin that stops a future plan quietly inventing this project's first migration mechanism.
- *"no file under companion/ so much as mentions wake_epochs"* likewise. Its job is to fail the day a drawing tries to read the table, which is 24-RESEARCH.md's named failure mode for Option C.

---

## A criterion that did not evaluate as predicted

**The `ALTER TABLE` / `PRAGMA user_version` / `honoured` / `punctual` greps are blunt by construction, and they fire on prose.** Recorded rather than adjusted, because the bluntness is the point.

Three times during this plan a check failed on documentation I had just written:

1. `check_in_gaps()`'s docstring originally closed with *"…which is also why no name in this codebase calls the result an honoured-wake rate"* — a sentence whose entire purpose was to forbid the word, caught by `grep -ci 'honoured'`.
2. `wake.py`'s vocabulary comment said *"there is deliberately no term meaning 'the device honoured its wake' and none meaning 'punctual'"* — same failure, same reason.
3. `init_schema()`'s new docstring said *"there is no `PRAGMA user_version` and no `ALTER TABLE` anywhere in the tree"* — the very claim the grep checks, written in the words the grep bans.

In every case the **prose** was changed, never the check. The acceptance criteria specify a bare `grep -c … outputs 0`, and a grep anyone can re-run from a terminal without reading a parser is worth more than the freedom to name the banned word while banning it. The cost is real and is recorded here so the next author knows why the comments talk around "a rate of wakes the device kept" and "in-place table alteration": those are deliberate circumlocutions, not squeamishness.

---

## Plan assumptions that turned out wrong

1. **"If importing `wake` into `history_db` would create a cycle…"** — there is no cycle, and the placement decision turned on `history_db.py`'s stdlib-only leaf contract instead. Recorded in full above. The plan anticipated the *outcome* (it describes the `wake.py` fallback in detail) but not the *reason*.
2. **`files_modified` omitted `server/wake.py`.** The plan lists `history_db.py`, `poll_loop.py` and the two harnesses; Task 2's own action text explicitly contemplates writing `wake.py`, but the frontmatter was never updated to match. `server/wake.py` is owned by no sibling in this wave (24-01 owns `companion/battery.py`, `companion/draw.py`, `companion/static/style.css`, `companion/test_companion_app.py`; 24-02 owns `companion/test_browser_ux.py`), so no ownership was violated — but the list was wrong and is recorded as such.
3. **Task 2's `<files>` says `server/history_db.py`.** Consistent with the plan's expectation that the classifier would land there; superseded by the decision above.
4. **The plan's Task 1 behaviour line says unparseable rows "are dropped".** They are not dropped here — they are kept in place and both adjacent spans are reported unknown. This satisfies the stated *outcome* ("a dropped row cannot shift the interval either side of it into a false value") more directly than dropping does, and M2/M3 prove the difference matters.

---

## Re-derived check counts (obtained by running, never by arithmetic)

| Harness | Before | After | Delta |
|---|---|---|---|
| `server/test_config_history.py` | 72 | **87** | +6 (Task 1), +5 (Task 2), +4 (Task 3) |
| `server/test_poll_loop.py` | 97 | **99** | +2 (Task 3) |

Each `EXPECTED_CHECK_COUNT` was bumped only after running the harness and reading the total off its own `N/M checks pass` line, with a ledger comment in the file's existing idiom recording what the delta bought.

Task 2's five checks all live in `server/test_config_history.py` even though the code under test is `server/wake.py`: that harness and `test_poll_loop.py` are the only two this plan owns, and `test_config_history.py` is the harness for the reader those verdicts judge. A header comment in the new section says so, so a later reader does not mistake it for misfiling.

---

## Threat model

| Threat ID | Disposition | How it landed |
|---|---|---|
| T-24-03 (SQL injection in the new readers) | mitigated | every bound in `check_in_gaps()` and `record_wake_epoch()` is a `?` placeholder; the pre-existing whole-file scan (*"every history_db.py execute() call uses ? placeholders, never %-formatting or an f-string"*) covers the new SQL without a new check being needed |
| T-24-03-B (row growth / DB error costing a poll cycle) | mitigated | the epoch write is deduped (M8) and sits inside the existing `except (sqlite3.Error, OSError)` (M9) |
| T-24-03-C (a gap read as a device fault) | mitigated | the reader's docstring carries both "cannot know" caveats; the vocabulary is observed throughout and the banned words are grep-pinned absent |
| T-24-03-D (concurrent schema creation) | accepted, unchanged | a fourth `CREATE TABLE IF NOT EXISTS` under the existing WAL + `busy_timeout`, identical to the three already there; M10 pins the guard |
| T-24-03-SC (package installs) | n/a | zero packages installed in any ecosystem |

No **Threat Flags**: nothing here opens a network endpoint, an auth path, a file-access pattern or a trust-boundary schema change beyond the register above.

---

## Known stubs

None. `wake_epochs` is deliberately unread in this phase — that is a recorded decision (24-RESEARCH.md open decision 2), pinned by a check, and explained in the schema comment beside the table, not a stub.

---

## Verification

`PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` — the failing set is **exactly the 5 baseline checks, by name**:

| # | Harness | Check |
|---|---|---|
| 1 | `server/test_manual_resolutions.py` | `add_entry()` returns ADD_FAILED … read-only parent directory (WR-11) |
| 2 | `server/test_manual_resolutions.py` | `delete_entry()` returns False … read-only mid-write (WR-11) |
| 3 | `companion/test_companion_app.py` | POST /airlines/resolve … `manual_save_failed` flash key (WR-11) |
| 4 | `companion/test_companion_app.py` | POST …/delete … `manual_delete_failed` flash key (WR-11) |
| 5 | `companion/test_status_pages.py` | `anomaly_active()` … non-existent state_dir |

All five are the container-runs-as-root artefacts (a read-only directory is writable as root); they pass in CI. No sixth failure. `server/test_config_history.py` (87/87) and `server/test_poll_loop.py` (99/99) both pass.

`ruff check .` — **All checks passed!**

Final greps:

- `grep -c 'ALTER TABLE\|PRAGMA user_version' server/history_db.py` → `0`
- `grep -ci 'honoured\|punctual' server/history_db.py server/wake.py` → `0`, `0`
- `grep -c 'MISSED_WAKES_WARN\|MISSED_WAKES_ERROR\|STALE_WARN_FLOOR_S\|STALE_ERROR_FLOOR_S' server/history_db.py` → `0`
- `grep -c 'CREATE TABLE IF NOT EXISTS' server/history_db.py` → `4` (was 3)
- `grep -rn 'wake_epochs' companion/` → nothing
- `python -c "import server.history_db, server.wake"` → succeeds

---

## Incident: a sibling agent's staged file was swept into a commit

Two sibling agents were executing in this same working tree. `git add server/history_db.py && git commit` committed **`companion/battery.py` as well**, because the sibling running 24-01 had staged that file and a bodiless `git commit` takes the whole index.

Caught immediately by the mandated `git show --name-only` after the commit. Recovered with `git reset --soft HEAD~1` (verified `HEAD` was still mine first, so no sibling commit could be orphaned) followed by `git commit --only server/history_db.py`, which commits the named paths and leaves every other staged entry in the index untouched. `companion/battery.py` was afterwards back in exactly its prior state — `M ` staged, uncommitted — and the sibling committed it itself later (`c2fed18`, `0daf7a6`).

**Every subsequent commit in this plan used `git commit --only <explicit paths>`,** never `git add` followed by a bodiless commit. In a shared working tree `git add <path>` is not sufficient isolation: the *commit* is what needs the path restriction, not the *add*.

## A second, smaller incident worth recording

The Task 2 boundary mutations were first run through a shell helper function that mutated, ran, and restored in a loop. The second iteration reported a failure message naming the **warn** boundary while the **error** boundary had been mutated — because the first iteration's restore had not landed before the second read the file, leaving both mutations active. Re-run in isolation, each mutation produced the correct, boundary-naming message (M4 and M5 above, both quoted from the isolated runs).

Batched mutation harnesses are not trustworthy without verifying the restore between iterations. The quoted messages above are all from single, isolated, verified runs.

## Self-Check: PASSED

All five modified source files exist on disk; all six task commits (`8985293`, `9700220`, `cbb671f`, `1098284`, `cdb3d00`, `005d1f0`) are present in the repository history.
