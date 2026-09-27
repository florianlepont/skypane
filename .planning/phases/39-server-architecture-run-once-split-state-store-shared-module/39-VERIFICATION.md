---
phase: 39-server-architecture-run-once-split-state-store-shared-module
verified: 2026-09-27T00:00:00Z
status: passed
score: 10/10 must-haves verified (4 ROADMAP criteria + 6 ARC requirement truths)
overrides_applied: 0
---

# Phase 39: Server architecture — run_once split, state store, shared modules — Verification Report

**Phase Goal:** The poll cycle reads as a sequence of small named steps over one context object; state has one owner; no module-global setters; no logic duplicated between server, byos and companion; the pure core is typed and checked.
**Verified:** 2026-09-27, against `HEAD` = `14ed0f1` (`Merge origin/main into claude/phase-39`, the post-merge reconciliation commit), working tree clean (`git status --short` empty).
**Status:** passed
**Re-verification:** No, this is the initial verification. Special attention was paid to whether commit `14ed0f1` (merging origin/main's Phase 38 PR #150 and Phase 40's in-progress companion work) silently regressed any of the four success criteria — every command below was re-run directly against `HEAD`, not accepted from `39-ARC-BASELINE.md`'s own (pre-merge) After section.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | No function in `server/` over 80 code lines; `run_once` complexity measured before/after | VERIFIED | `python3 scripts/check_function_size.py check --max 80 server stub-server` → `401 functions scanned, none over 80` (re-run against HEAD, matches `39-ARC-BASELINE.md`'s After figure exactly, so the merge did not reintroduce an offender). `server/poll_cycle.py` at HEAD defines `CycleContext` (`@dataclass(slots=True)`, l.691), `load_cycle_context` (l.779), `decide_hold` (l.856), `advance_display_queue` (l.1093), `render_and_publish` (l.1376), `record` (l.1391), `persist` (l.1424) — exactly the named steps ARC-01 requires, all present post-merge. |
| 2 | The companion no longer imports `server.poll_loop` | VERIFIED | `grep -rn "import server.poll_loop\|from server import poll_loop\|from server.poll_loop" companion/` → no matches (exit 1). `companion/app.py`, `companion/pages/health_page.py`, `companion/pages/airlines_page.py` import `server.poll_cycle`/`server.state_store` instead (confirmed by direct grep of those three files). `server/poll_loop.py` is 100 lines at HEAD, containing only `build_parser`/`main` — a thin systemd-entrypoint wrapper over `poll_cycle.run_once`, not the 1594-line monolith the Before baseline recorded. |
| 3 | Quiet hours, battery-critical and battery-curve logic exist once | VERIFIED | `server/device_policy.py` (stdlib-only) is the single definition of `quiet_hours_window`, `battery_critical_pin_applies`, `BATTERY_DISCHARGE_CURVE`/`battery_fraction`/`battery_percent`, `HHMM_RE`, `QUIET_HOURS_TZ`, `WAKE_INTERVAL_MIN_S/MAX_S`, `DISPLAY_OFF_SLEEP_S`, `BATTERY_CRITICAL_SLEEP_S/RECOVER_MV`. `stub-server/byos_server.py` rebinds every one of them (`= device_policy.X`, l.87-93, l.375, l.400, l.440) rather than redefining. `companion/battery.py` re-exports the same module (`from server.device_policy import (...)  # noqa: F401`, l.16) and is proven by a subprocess `sys.modules` diff test (`test_battery_module_imports_only_the_shared_device_policy_from_server`, `companion/test_companion_app_03.py:1312`) to import nothing else from `server/`. |
| 4 | mypy green in CI on the typed modules; behaviour unchanged (suite green) | VERIFIED | `server/.venv/bin/mypy` → `Success: no issues found in 12 source files`. `.github/workflows/ci.yml` runs both `server/.venv/bin/mypy` ("Type check", blocking) and `check_function_size.py check --max 80` ("Function size gate", blocking) as separate CI steps, confirmed present at HEAD. Full suite: `./scripts/run-all-tests.sh` → `3038 passed, 139 skipped, 57 warnings` (0 failed), coverage `94.29%` against the 93.0% floor ("Required test coverage of 93.0% reached"). The 139 skips are the pre-existing Chromium/root-euid skips also seen in the phase's own Before/After baselines, not new failures from the merge. |

**Score:** 4/4 ROADMAP criteria verified.

### Requirement-level truths (ARC-01..ARC-06)

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 5 | ARC-01: named steps over one `CycleContext` | VERIFIED | See truth 1. `radon cc -s server/poll_cycle.py` at HEAD: `run_once` A(3), highest named step `advance_display_queue` B(10) — both far below Before's `_run_once_locked` F(53), confirming the split held after the merge. |
| 6 | ARC-02: `server/state_store.py` owns `poll_state.json`; companion imports it, never `poll_loop` | VERIFIED | `server/state_store.py` exists; companion's three former `poll_loop` call sites (`app.py`, `health_page.py`, `airlines_page.py`) now import `state_store` and call `state_store.load_poll_state`/`poll_state_path`. See truth 2. |
| 7 | ARC-03: `render/`/`calendar_rules/` packages, `themes.py`, shared `net/safe_fetch.py` | VERIFIED | `server/plane/render/{__init__,cli,glyphs,hold_screens,layout,style,text}.py` and `server/plane/calendar_rules/{__init__,ics,match,registry}.py` both exist as packages at HEAD. `server/themes.py` exists. `server/net/safe_fetch.py` exists; `server/notify.py` imports it directly (`from server.net import safe_fetch`, l.32) and calls `safe_fetch.url_is_safe`/`safe_fetch.USER_AGENT` — no import of `calendar_rules._url_is_safe` remains (`grep -n "calendar_rules" server/notify.py` returns nothing). ARCHITECTURE.md's module map correctly names `poll_loop.py`/`poll_cycle.py`/`state_store.py`/`device_policy.py`/`themes.py`/`net/safe_fetch.py` and the two packages; the stale "vendored byos" framing is gone (`grep -i vendor ARCHITECTURE.md` only matches an unrelated `firmware/VENDOR.md` reference). |
| 8 | ARC-04: no module-global setters, explicit injection | VERIFIED | `grep -rn "def set_.*_state_dir"` across `server/` returns no matches — `set_override_state_dir`, `set_manual_registry_state_dir`, `set_colour_rules_state_dir` are deleted outright, not merely uncalled. Only drift-guard test assertions (`server/test_manual_resolutions.py`, `server/test_illustrations.py`, `server/test_colour_rules.py`) mention the names at all, each asserting `not hasattr(module, name)`. |
| 9 | ARC-05: quiet hours/battery-critical/battery-curve exist once, "vendored byos" rationale corrected | VERIFIED | See truth 3 and requirement 7's ARCHITECTURE.md finding. |
| 10 | ARC-06: type hints on the pure core, mypy in CI | VERIFIED | See truth 4. `server/poll_cycle.py`'s pure core (`decide_hold`, `advance_is_due`, `normalise_pending`, `enqueue_pending`, `pop_fresh_pending`, `CycleContext`) is fully annotated; mypy's global `[tool.mypy] files` list carries 12 modules and is green. |

**Score:** 6/6 ARC requirement truths verified.

**Combined score: 10/10 must-haves verified.**

### Post-merge regression check (explicit)

The task brief specifically asked whether merge commit `14ed0f1` (reconciling this branch with origin/main's Phase 38 PR #150 and Phase 40's in-progress companion work) silently regressed any of the four ROADMAP criteria. Findings, all against `HEAD` directly (not against the pre-merge `39-ARC-BASELINE.md` record):

- `companion/app.py` at HEAD (which took main's routes/structure in the merge) still imports `server.poll_cycle`/`server.state_store` and never `server.poll_loop` (confirmed by direct grep of the file, not just the repo-wide grep).
- `server/poll_loop.py` at HEAD is still 100 lines, `build_parser`/`main` only — the merge did not reintroduce cycle logic into the entrypoint.
- The function-size gate (`check --max 80`) and `mypy` both pass at HEAD with the exact same "zero offenders" / "12 source files" results the phase's own After baseline recorded pre-merge — the merge did not reintroduce an over-80-line function or an untyped regression in the 12 mypy-tracked files.
- Full suite green post-merge: 3038 passed (up from the pre-merge After baseline's 2995 — the extra tests come from Phase 38/40 work merged in), 0 failed, coverage 94.29% (above the pre-merge 94.27% and the 93% floor).
- ruff and `check_comment_history.py` both clean post-merge.

No regression found.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/poll_cycle.py` | Named steps + `CycleContext`, run_once entrypoint | VERIFIED | 1579 lines; contains `CycleContext`, `load_cycle_context`, `decide_hold`, `advance_display_queue`, `render_and_publish`, `record`, `persist`, `run_once`; mypy-tracked. |
| `server/poll_loop.py` | Thin systemd entrypoint only | VERIFIED | 100 lines, `build_parser`/`main` only, imported by `deploy/skypane-poll.service` unchanged. |
| `server/state_store.py` | Owns `poll_state.json` | VERIFIED | `load_poll_state`/`save_poll_state`/`serialize_poll_state`/`persist_poll_state_if_changed`/`poll_state_path`/`DEFAULT_STATE_DIR`/`read_battery_critical` all present; imported by companion and by `byos_server.py` (`read_battery_critical` rebind). |
| `server/device_policy.py` | Single quiet-hours/battery-critical/battery-curve definition, stdlib-only | VERIFIED | Present, imported by `byos_server.py` and `companion/battery.py`; subprocess isolation test confirms stdlib-only. |
| `server/plane/render/` package | `layout`, `text`, `hold_screens`, `cli`, etc. | VERIFIED | 7 submodules present. |
| `server/plane/calendar_rules/` package | `ics`, `registry`, `match` | VERIFIED | 4 submodules present (`__init__`, `ics`, `match`, `registry`). |
| `server/themes.py` | Theme logic out of `device_config.py` | VERIFIED | Present. |
| `server/net/safe_fetch.py` | Shared URL-safety check | VERIFIED | Present; `notify.py` imports it directly. |
| `39-ARC-BASELINE.md` | Before/After measurement record | VERIFIED | Committed, both sections present, criteria table marks all four "Met"; independently re-run against HEAD in this verification with matching numbers. |
| `.github/workflows/ci.yml` | Blocking mypy + function-size steps | VERIFIED | Both steps present at HEAD (l.100-104). |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `companion/app.py` | `server.poll_cycle.run_once` | `import server.poll_cycle as poll_cycle` + `poll_cycle.run_once(...)` (l.2299) | WIRED |
| `companion/app.py`, `health_page.py`, `airlines_page.py` | `server.state_store` | `import server.state_store as state_store` + `state_store.load_poll_state`/`poll_state_path` | WIRED |
| `companion/battery.py` | `server.device_policy` | `from server.device_policy import (...)` | WIRED |
| `stub-server/byos_server.py` | `server.device_policy` | module-level rebinds (`_HHMM_RE = device_policy.HHMM_RE`, etc., l.87-93) and function calls (`device_policy.quiet_hours_window`, `device_policy.battery_critical_pin_applies`) | WIRED |
| `stub-server/byos_server.py` | `server.state_store` | `read_battery_critical = state_store.read_battery_critical` | WIRED |
| `server/notify.py` | `server.net.safe_fetch` | `from server.net import safe_fetch` + `safe_fetch.url_is_safe`/`safe_fetch.USER_AGENT` | WIRED |
| `server/poll_loop.py` (`main`) | `server/poll_cycle.py` (`run_once`) | entrypoint dispatch, `deploy/skypane-poll.service` unchanged | WIRED |
| `.github/workflows/ci.yml` | `mypy` / `check_function_size.py` | two dedicated blocking steps | WIRED |

### Behavioral Spot-Checks / Direct Command Re-Runs

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Function-size gate | `python3 scripts/check_function_size.py check --max 80 server stub-server` | `401 functions scanned, none over 80` | PASS |
| No companion→poll_loop import | `grep -rn "import server.poll_loop\|from server import poll_loop\|from server.poll_loop" companion/` | no matches (exit 1) | PASS |
| No module-global setters | `grep -rn "def set_.*_state_dir" server/` | no matches (exit 1) | PASS |
| mypy | `server/.venv/bin/mypy` | `Success: no issues found in 12 source files` | PASS |
| Full suite + coverage | `./scripts/run-all-tests.sh` | `3038 passed, 139 skipped, 57 warnings`; `TOTAL 10764 615 94%`; `Required test coverage of 93.0% reached. Total coverage: 94.29%` | PASS |
| Lint | `server/.venv/bin/ruff check .` | `All checks passed!` | PASS |
| Comment-history guard | `server/.venv/bin/python scripts/check_comment_history.py check` | exit 0, no output | PASS |

### Probe Execution

Step 7c: SKIPPED. This phase declares no `probe-*.sh` scripts; its own instrument is `39-ARC-BASELINE.md`'s documented command set, all of which were independently re-run above against HEAD.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| ARC-01 | 39-04, 39-05, 39-10, 39-11 | SATISFIED | Truths 1, 5 |
| ARC-02 | 39-02, 39-10 | SATISFIED | Truths 2, 6 |
| ARC-03 | 39-04, 39-05, 39-08 | SATISFIED | Truth 7 |
| ARC-04 | 39-03 | SATISFIED | Truth 8 |
| ARC-05 | 39-02, 39-06, 39-13 | SATISFIED | Truths 3, 9 |
| ARC-06 | 39-02, 39-12, 39-13 | SATISFIED | Truths 4, 10 |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps only ARC-01..06 to Phase 39, and both the checklist and summary-table rows are marked Complete; all six are claimed by at least one plan above.

### Anti-Patterns Found

None. `grep -n -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` returns no matches in `server/poll_cycle.py`, `server/poll_loop.py`, `server/state_store.py`, `server/device_policy.py`, `server/themes.py`, or `server/net/safe_fetch.py`. The one logged deferral (`.planning/phases/39-server-architecture-run-once-split-state-store-shared-module/deferred-items.md`, 39-10 Task 2) is stale docstring/comment prose in six companion files that still says "poll_loop" descriptively — none of the six import or call the moved module (verified: the actual import grep is empty), and the deferral was an explicit, logged scope decision to avoid a needless merge conflict with the parallel Phase 40 session, not a functional gap.

### Intentional behaviour changes (developer-approved, re-confirmed present at HEAD)

- **D-4** — the quiet-hours invalid-stored-time fallback is unified onto the server's 23:00–07:00 + hold behaviour on both the server and byos sides, through the shared `device_policy.quiet_hours_window()`. Pinned by `server/test_device_policy.py::test_quiet_hours_invalid_stored_time_falls_back_to_default_window` and `stub-server/test_poll_cycle.py::test_read_quiet_hours_invalid_time_falls_back_to_default_window`, both present and passing in the full-suite run above.
- **D-5** — the companion theme preview is now vendored-only (no in-process `/poll-now` override visibility), a direct consequence of deleting `illustrations.set_override_state_dir`. Pinned by `server/test_illustrations.py::test_select_illustration_state_dir_override_vs_no_state_dir`.

### Human Verification Required

None. Every ROADMAP criterion and every ARC requirement is verifiable by direct command against the codebase (function-size gate, grep, mypy, full suite, ruff, comment-history check) — no UI, no live-deploy, no external-service dependency in this phase's scope.

### Gaps Summary

None. All four ROADMAP success criteria and all six ARC-01..ARC-06 requirement truths verified directly against `HEAD` (`14ed0f1`, the post-merge reconciliation commit), independent of `39-ARC-BASELINE.md`'s own (pre-merge) After section and independent of every SUMMARY.md's narrative claims. The post-merge regression check specifically requested in this verification's brief found no regression: companion still never imports `server.poll_loop`, `server/poll_loop.py` is still a 100-line entrypoint, and the function-size/mypy/test-suite/coverage gates are all green at HEAD with figures matching or exceeding the phase's own pre-merge baseline.

---

_Verified: 2026-09-27_
_Verifier: Claude (gsd-verifier)_
