---
phase: 36-state-integrity-and-device-protocol
plan: 04
subsystem: infra
tags: [atomic-write, fcntl, flock, lru-cache, mkstemp, concurrency]

# Dependency graph
requires:
  - phase: 36-state-integrity-and-device-protocol
    provides: "server/atomic_io.py: atomic_write, exclusive_lock, LockBusy, DEFAULT_FILE_MODE (36-01)"
provides:
  - "server/device_config.py save_device_config(): threading.Lock + atomic_io.exclusive_lock(device_config.lock) around the whole load-merge-write, write through atomic_io.atomic_write"
  - "server/plane/colour_rules.py and server/plane/manual_resolutions.py: add/delete writers on atomic_io.atomic_write instead of a pid+thread-id temp name"
  - "companion/theme_preview.py: cached_preview_bytes() writes atomically, prunes stale signatures and bounds the cache to THEME_PREVIEW_CACHE_MAX_FILES (64)"
  - "companion/illustration_normalize.py: _cached_normalized_png_bytes bounded at NORMALIZED_CACHE_MAX_ENTRIES (128)"
  - "deploy/backup/backup_gate.py: _cmd_ack() writes last-pull through a unique mkstemp temp in pulled_dir"
affects: [36-05, 36-06, 36-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Load-merge-write under threading.Lock then atomic_io.exclusive_lock(<state_dir>/<name>.lock), matching atomic_io's documented lock order"
    - "Cache-prune-after-write: atomic_io.atomic_write, then a same-directory prune pass (stale-signature regex, then an mtime-oldest-first bound), never on a cache hit"

key-files:
  created: [server/test_state_writers.py, companion/test_preview_cache.py]
  modified:
    - server/device_config.py
    - server/plane/colour_rules.py
    - server/plane/manual_resolutions.py
    - companion/theme_preview.py
    - companion/illustration_normalize.py
    - deploy/backup/backup_gate.py
    - deploy/tests/test_backup_gate.py

key-decisions:
  - "save_device_config()'s validation runs before either lock is taken (it never reads the current on-disk config), so only the load-merge-write sequence - current = load_device_config(...) through the write - is inside the locked region; this is the minimal critical section that still closes the lost-update race."
  - "_prune_preview_cache() derives its stale-signature regex from the just-written file's own basename (full-match on '<exact prefix>-[0-9a-f]{12}.png'), not from independently reconstructing the theme/event prefix, so a theme id that is a prefix of another theme's name can never cross-match - anchored fullmatch, never startswith/substring."
  - "screen_id is one of the twelve save_device_config() keywords exercised in the 12-thread no-lost-update test even though SCREEN_IDS currently has only one member (\"plane-frame\") - it cannot itself prove a lost update, but keeping all twelve keywords in one test (rather than eleven) matches the plan's literal field list and costs nothing."
  - "INT-02 stays Pending in REQUIREMENTS.md per this plan's environment notes - server/poll_loop.py's poll_state.json/panel.bin/gallery PNG and server/plane/calendar_rules.py still write through a fixed or ad hoc temp name and are owned by a later plan in this phase. INT-03 and INT-04 are marked Complete: both are fully finished end to end by this plan."

patterns-established:
  - "Pattern: lock-then-load-merge-write for a per-file JSON registry with a companion-facing HTTP writer: threading.Lock (same-process fast path) wrapping atomic_io.exclusive_lock(<state_dir>/<name>.lock) (cross-process), current state read fresh inside the lock, write via atomic_io.atomic_write."
  - "Pattern: bounded, self-pruning disk cache: atomic_io.atomic_write the new entry, then in one best-effort (never-raising) pass remove stale variants of the same logical key by an anchored full-match filename regex, then trim the whole directory to a fixed file count by oldest mtime, skipping the just-written file."

requirements-completed: [INT-03, INT-04]

# Metrics
duration: 16min
completed: 2026-09-26
---

# Phase 36 Plan 04: Config and cache writers on atomic_io Summary

**save_device_config() gets a thread lock plus a device_config.lock flock around its whole load-merge-write (no more lost settings updates across two browser tabs or processes); colour_rules.json and manual_resolutions.json drop their pid+thread-id temp names for atomic_io.atomic_write; the theme preview cache writes atomically, prunes stale signatures and is bounded to 64 files, the illustration-normalize cache is bounded to 128 entries, and the backup gate's ack marker uses a unique mkstemp temp instead of a fixed name.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-09-26T08:33:30Z (first commit after 36-03 completed)
- **Completed:** 2026-09-26T08:49:02Z
- **Tasks:** 3 (all TDD: RED then GREEN)
- **Files modified:** 6 production files, 3 new/extended test files

## Accomplishments
- `save_device_config()`'s entire load-merge-write now runs under a module `threading.Lock` plus `atomic_io.exclusive_lock(<state_dir>/device_config.lock)` (bounded 10 s wait), proven by a 12-thread x 20-save test where each thread owns one of the twelve keyword fields and the final file holds every thread's own last-written value.
- `colour_rules.add_rule`/`delete_rule` and `manual_resolutions.add_entry`/`delete_entry` write through `atomic_io.atomic_write` instead of a `%s.%d.%d.tmp` (path, pid, thread id) name, keeping every existing return-value contract (`ADD_*` constants, bool) unchanged.
- `companion/theme_preview.cached_preview_bytes()` writes a cache miss through `atomic_io.atomic_write`, then `_prune_preview_cache()` removes stale-signature files for the same theme+event (an anchored full-match regex, never a startswith/substring check) and bounds the directory to `THEME_PREVIEW_CACHE_MAX_FILES` (64) by oldest mtime; a cache hit neither writes nor prunes.
- `companion/illustration_normalize._cached_normalized_png_bytes` is now `functools.lru_cache(maxsize=128)` instead of unbounded, above the 43 vendored assets plus manual-resolution overrides.
- `deploy/backup/backup_gate.py`'s `_cmd_ack()` creates its temp via `tempfile.mkstemp(dir=pulled_dir, prefix=".last-pull.", suffix=".tmp")`, proven safe under two genuinely concurrent `ack` subprocesses (previously reproduced the old fixed-name collision as a RED failure before the fix).
- Every RED test was independently confirmed failing against the pre-migration file content (a temporary revert, captured and restored via scratch copies - no `git stash`/`git clean` used) before the corresponding GREEN commit landed.

## Task Commits

Each task was committed as a test (RED) then feat (GREEN) pair:

1. **Task 1: device_config lock + atomic registries (INT-03, INT-02)** - `fda951c` (test, RED) + `3aa48c3` (feat, GREEN)
2. **Task 2: theme preview and illustration caches (INT-04)** - `9205aa7` (test, RED) + `a6eda02` (feat, GREEN)
3. **Task 3: backup gate ack through a unique temp (INT-02)** - `58a3af9` (test, RED) + `6df60d3` (feat, GREEN)

_TDD tasks: each is a test -> feat pair (RED then GREEN); no refactor commit was needed for any task._

## Files Created/Modified
- `server/device_config.py` - `DEVICE_CONFIG_LOCK_FILENAME`, `DEVICE_CONFIG_LOCK_TIMEOUT_S`, module `_SAVE_LOCK`; `save_device_config()`'s load-merge-write moved inside `with _SAVE_LOCK: with atomic_io.exclusive_lock(...):`, write via `atomic_io.atomic_write`
- `server/plane/colour_rules.py` - `add_rule`/`delete_rule` write via `atomic_io.atomic_write`; docstrings updated
- `server/plane/manual_resolutions.py` - `add_entry`/`delete_entry` write via `atomic_io.atomic_write`; module and function docstrings updated
- `server/test_state_writers.py` (new) - no-lost-update (12 threads x 20 saves), cross-process lock wait/release, no-stray-`.tmp`-after-every-writer, forced-`atomic_write`-failure-leaves-file-intact (`add_rule`/`delete_rule`/`add_entry`/`save_device_config`), and file-mode tests
- `companion/theme_preview.py` - `THEME_PREVIEW_CACHE_MAX_FILES`, `_PREVIEW_FILENAME_RE`, new `_prune_preview_cache()`; `cached_preview_bytes()` writes via `atomic_io.atomic_write` then prunes
- `companion/illustration_normalize.py` - `NORMALIZED_CACHE_MAX_ENTRIES = 128`, `_cached_normalized_png_bytes` bounded
- `companion/test_preview_cache.py` (new) - concurrent cold preview (barrier-synchronised two threads), stale-signature pruning with unrelated files kept, cache-bound eviction (oldest first, just-written file kept), cache-hit-does-not-write-or-prune, and the lru `maxsize == 128` assertion
- `deploy/backup/backup_gate.py` - `_cmd_ack()` uses `tempfile.mkstemp` instead of the fixed `.last-pull.tmp` name
- `deploy/tests/test_backup_gate.py` - added the concurrent-ack test; swapped the single-ack test's literal-filename-absence check for a general "no `.tmp` file in `pulled_dir`" check

## Decisions Made
See `key-decisions` in the frontmatter. In brief: validation stays outside both locks in `save_device_config()` (it never touches disk); the preview-cache prune regex is derived from the just-written file's own name rather than reconstructed independently, closing the "theme `a` vs theme `a-5`" cross-match risk the plan called out; `screen_id` is kept in the 12-thread test for parity with the plan's literal field list even though it can't itself demonstrate a lost update; and INT-02 is intentionally left Pending in REQUIREMENTS.md (only INT-03/INT-04 are fully finished by this plan).

## Deviations from Plan

None - plan executed exactly as written. Every acceptance-criteria grep (`getpid`, `get_ident`, `+ "\.tmp"`, `maxsize=None`, the literal `.last-pull.tmp`, a `server` import in `backup_gate.py`) returns 0/absent as required, and `exclusive_lock` appears in `server/device_config.py`.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/atomic_io.py`'s helpers are now proven against a real lost-update race (`save_device_config`) and a real prune/bound cache (`theme_preview`), giving 36-05/36-06/36-07 a working template for `poll_loop.py`'s `poll_state.json`/`panel.bin`/gallery PNG and `calendar_rules.py`'s registry and URL secret.
- INT-02 remains open for those remaining writers; REQUIREMENTS.md reflects that (INT-02 still Pending, INT-03/INT-04 now Complete).
- No blockers for the rest of wave 2.

## Self-Check: PASSED

- FOUND: server/test_state_writers.py
- FOUND: companion/test_preview_cache.py
- FOUND: server/device_config.py (with `exclusive_lock`, `DEVICE_CONFIG_LOCK_FILENAME`)
- FOUND: companion/theme_preview.py (with `THEME_PREVIEW_CACHE_MAX_FILES`)
- FOUND commit fda951c (test RED, Task 1)
- FOUND commit 3aa48c3 (feat GREEN, Task 1)
- FOUND commit 9205aa7 (test RED, Task 2)
- FOUND commit a6eda02 (feat GREEN, Task 2)
- FOUND commit 58a3af9 (test RED, Task 3)
- FOUND commit 6df60d3 (feat GREEN, Task 3)

## TDD Gate Compliance

All three tasks show the required RED -> GREEN sequence in git log:
- Task 1: `fda951c test(36-04): ...` then `3aa48c3 feat(36-04): ...`
- Task 2: `9205aa7 test(36-04): ...` then `a6eda02 feat(36-04): ...`
- Task 3: `58a3af9 test(36-04): ...` then `6df60d3 feat(36-04): ...`

No REFACTOR commit was needed for any task. Each RED commit was independently confirmed to fail against a temporary revert of its production file(s) to their pre-migration content, before the corresponding GREEN commit landed.

---
*Phase: 36-state-integrity-and-device-protocol*
*Completed: 2026-09-26*
