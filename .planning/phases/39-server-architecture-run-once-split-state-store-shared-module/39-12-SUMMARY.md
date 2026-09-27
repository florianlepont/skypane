---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 12
subsystem: infra
tags: [mypy, types-requests, type-hints, ci, pyproject]

# Dependency graph
requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "device_policy.py, state_store.py, themes.py, net/safe_fetch.py and calendar_rules/{ics,match}.py, all typed at birth (39-02, 39-04, 39-05)"
provides:
  - "mypy 2.3.1 + types-requests, dev-only, hash-locked via scripts/lock-deps.sh"
  - "[tool.mypy] in pyproject.toml: global options plus a per-flag strict override on 11 pure-core modules"
  - "blocking CI 'Type check' step, right after the comment history guard"
  - "wake.py, panel_format.py, atomic_io.py, plane/runway_config.py and plane/colour_rules.py fully annotated, no behaviour change"
affects: ["39-13 (phase close, flips ARC-06 to Complete)", "poll_cycle.py's own future annotation pass, once its 80-line split lands"]

# Tech tracking
tech-stack:
  added: ["mypy==2.3.1 (dev)", "types-requests==2.33.0.20260906 (dev)"]
  patterns:
    - "mypy strictness via per-flag [[tool.mypy.overrides]] scoped to a `files` allowlist, not the global `strict` preset (which mypy only exposes globally)"
    - "typing.cast() to narrow an object-typed dict lookup back to its known runtime type (themes.py's THEMES accessors, ics.py's sort key), instead of loosening the return annotation"
    - "TYPE_CHECKING-only import of PIL.Image in panel_format.py, keeping the runtime `from PIL import Image` lazy inside new_canvas()"
    - "ModuleType | None alias for atomic_io's `fcntl = None` platform fallback"

key-files:
  created: []
  modified:
    - server/requirements-dev.in
    - server/requirements-dev.txt
    - pyproject.toml
    - .github/workflows/ci.yml
    - .gitignore
    - server/themes.py
    - server/net/safe_fetch.py
    - server/plane/calendar_rules/ics.py
    - server/wake.py
    - server/panel_format.py
    - server/atomic_io.py
    - server/plane/runway_config.py
    - server/plane/colour_rules.py

key-decisions:
  - "Task 1's pyproject [tool.mypy] `files`/override list holds only the six typed-at-birth modules; Task 2 appends the five newly-annotated modules in a second edit, matching the plan's own two-step files list rather than writing all 11 up front"
  - "wake.env_sleep_s()'s int(raw) guard: added `if raw is None: return None` ahead of the int() call and narrowed the except clause to ValueError only, since raw is now a known str at that point — identical runtime outcome to the previous `except (TypeError, ValueError)`, just typed"
  - "colour_rules.py's registry shape gets two module-level type aliases (RuleRecord, RuleRegistry) rather than repeating dict[str, dict[str, dict[str, str]]] at every call site"

requirements-completed: []  # ARC-06 stays Pending in REQUIREMENTS.md; only 39-13 flips ARC-* to Complete, per this phase's own convention

# Metrics
duration: 17min
completed: 2026-09-27
---

# Phase 39 Plan 12: mypy tooling and pure-core annotations Summary

**mypy 2.3.1 added as a dev-only dependency, configured with a strict per-flag override over 11 pure-core modules, wired into CI as a blocking step, and green — the five modules not already typed at birth (wake, panel_format, atomic_io, runway_config, colour_rules) are now fully annotated with no behaviour change.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-09-27T13:33:00Z
- **Completed:** 2026-09-27T13:49:10Z
- **Tasks:** 2 completed
- **Files modified:** 13

## Accomplishments
- `mypy==2.3.1` and `types-requests==2.33.0.20260906` pinned in `server/requirements-dev.in` with one-line comments, locked via `scripts/lock-deps.sh` (uv 0.8.17), with `server/requirements.txt` (the production lock) confirmed byte-identical before and after
- `[tool.mypy]` added to `pyproject.toml`: global options (`python_version = "3.14"`, `explicit_package_bases`, `mypy_path = "."`, `follow_imports = "silent"`, `warn_unused_configs`, `warn_redundant_casts`, `warn_unused_ignores`, `no_implicit_optional`, `check_untyped_defs`) plus one `[[tool.mypy.overrides]]` applying `disallow_untyped_defs`/`disallow_incomplete_defs`/`disallow_any_generics`/`warn_return_any` to exactly the 11-module pure-core list
- Fixed the small number of real typing gaps the six typed-at-birth modules still had: `themes.py`'s presentation accessors returning `object` from `THEMES[...]` lookups (fixed with `typing.cast`), `calendar_rules/ics.py`'s missing `dict`/`list` generics and a `current: dict[str, str] | None` re-assignment, and `net/safe_fetch.py`'s two `Any`-leakage sites (an untyped-module return and a `sockaddr[0]` union)
- Annotated `server/wake.py`, `server/panel_format.py`, `server/atomic_io.py`, `server/plane/runway_config.py` and `server/plane/colour_rules.py` end to end — `from __future__ import annotations`, explicit `dict`/`tuple`/`list` generics, a `TYPE_CHECKING`-only PIL `Image` reference in panel_format, and a `ModuleType | None` alias for atomic_io's `fcntl` platform fallback
- Added the blocking CI step "Type check (blocking; module list lives in pyproject.toml)" running `server/.venv/bin/mypy`, placed right after "Comment history guard" in `.github/workflows/ci.yml`
- `.mypy_cache/` added to `.gitignore` next to `.ruff_cache/`
- `server/.venv/bin/mypy` exits 0 checking all 11 files; full suite unchanged at 2982 passed / 139 skipped (pre-existing Chromium-shell/root-euid environment skips) both before and after Task 2; ruff and `check_comment_history.py` both clean; no test file touched by either task

## Task Commits

1. **Task 1: mypy tooling — dev pins, regenerated lock, [tool.mypy], CI step, green on the six typed-at-birth modules** - `050cf87` (feat)
2. **Task 2: annotate wake, panel_format, atomic_io, runway_config and colour_rules, add them to the typed set** - `1d9af36` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `server/requirements-dev.in` - added mypy/types-requests pins with rationale comments
- `server/requirements-dev.txt` - regenerated hash lock (mypy, types-requests and their transitive deps: pathspec, mypy-extensions, ast-serialize, librt)
- `pyproject.toml` - new `[tool.mypy]` table plus `[[tool.mypy.overrides]]`, `files`/`module` lists grown from 6 to 11 across the two tasks
- `.github/workflows/ci.yml` - blocking "Type check" step after the comment history guard
- `.gitignore` - `.mypy_cache/`
- `server/themes.py` - `typing.cast()` on every `THEMES[...]` accessor return
- `server/net/safe_fetch.py` - `bool(...)` wrap and `str(...)` wrap to close two Any-leak sites
- `server/plane/calendar_rules/ics.py` - `list[str]`/`dict[str, str]`/`dict[str, object]` generics, a typed `current` re-assignment guard, `cast(float, ...)` on the sort key
- `server/wake.py` - full annotations; `env_sleep_s()`'s explicit `raw is None` guard
- `server/panel_format.py` - full annotations; `TYPE_CHECKING` import of `PIL.Image`
- `server/atomic_io.py` - full annotations; `ModuleType | None` for the `fcntl` fallback
- `server/plane/runway_config.py` - full annotations (both functions typed `object` in/out, matching their genuinely untyped "any state" contract)
- `server/plane/colour_rules.py` - full annotations; `RuleRecord`/`RuleRegistry` type aliases

## Decisions Made
- Task 1's `files`/override list intentionally holds only the six typed-at-birth modules, not all 11 — matches the plan's own two-step `files` list (Task 2 appends), and keeps each commit's mypy-checked-file-count assertion (6, then 11) meaningful rather than vacuous
- `wake.env_sleep_s()`'s new `if raw is None: return None` guard is a typing fix, not a behaviour change: `int(None)` already raised `TypeError`, which the old `except (TypeError, ValueError)` already caught and returned `None` for; narrowing the except clause to `ValueError` only is safe because `raw` is provably `str` past the new guard
- `colour_rules.py` gained two small type aliases (`RuleRecord = dict[str, str]`, `RuleRegistry = dict[str, dict[str, RuleRecord]]`) rather than spelling the nested dict shape out at every one of the module's six call sites

## Deviations from Plan

None - plan executed exactly as written. The research's own mypy-trial error counts (wake 8, atomic_io+panel_format+runway_config 13, colour_rules 17) were for a different, `--strict`-flavoured trial run against the pre-refactor `device_config.py`-adjacent code; the actual five modules in this repo's current tree (post 39-02..39-09) needed only annotations, no logic changes, to satisfy the plan's own narrower per-flag override.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required. mypy and types-requests are dev-only; `deploy/deploy.sh` still installs only `server/requirements.txt`, confirmed unchanged by this plan.

## Next Phase Readiness
- ARC-06 is functionally complete (mypy green in CI on the 11-module pure core) but stays **Pending** in REQUIREMENTS.md per this phase's convention — only 39-13 (the closing plan) flips ARC-01..06 to Complete.
- `server/poll_cycle.py`'s pure helpers are still outside the mypy `files` list (the research's own recommendation deferred them to "after its 80-line split lands," which is 39-11's job, not this plan's) — a natural next module to add to `[tool.mypy]`'s `files` list once that split is final, but out of scope here.
- No blockers for 39-13.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

## Self-Check: PASSED

All files claimed created/modified were verified present on disk; both task commit hashes (`050cf87`, `1d9af36`) were verified present in `git log --oneline --all`.
