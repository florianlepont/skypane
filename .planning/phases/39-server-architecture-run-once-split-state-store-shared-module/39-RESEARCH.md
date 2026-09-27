# Phase 39: Server architecture (run_once split, state store, shared modules): Research

**Researched:** 2026-09-27
**Domain:** Behaviour-preserving Python refactor (server/, stub-server/, minimal companion import switches)
**Confidence:** HIGH. Almost everything here comes from the code on `claude/phase-39` (base `f83bf04`). The only external facts are the mypy and types-requests versions, which were checked against PyPI and slopcheck.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (verbatim)
- **ARC-01:** the poll cycle reads as named steps — `load_cycle_context` / `decide_hold` / `advance_display_queue` / `render_and_publish` / `persist` / `record` (names may be refined, the shape may not) — over one `CycleContext` dataclass. The render → pack → write → gallery sequence exists once. Success criterion: no function in `server/` over 80 code lines (code lines = non-blank, non-comment, non-docstring); `run_once` cyclomatic complexity measured before and after and recorded in a committed `39-ARC-BASELINE.md` (same pattern as `38-EFF-BASELINE.md`).
- **ARC-02:** `server/state_store.py` owns `poll_state.json` (path, load, serialise, save, persist-if-changed). The companion imports `state_store`, never `server.poll_loop`.
- **ARC-03:** split `server/plane/render.py` into a `render/` package (`layout`, `text`, `hold_screens`, `cli` — refine as the code dictates), `server/plane/calendar_rules.py` into a package (`ics`, `registry`, `match`), move theme logic out of `device_config.py` into `themes.py`, and one shared `net/safe_fetch.py` holding the URL-safety check so `notify.py` stops importing the private `calendar_rules._url_is_safe`.
- **ARC-04:** no module-global setters. State dirs (and any other per-cycle input) are passed explicitly.
- **ARC-05:** quiet hours, battery-critical hysteresis and the battery discharge curve exist **once**, in one shared module used by `server/`, `stub-server/byos_server.py` and `companion/`. The "vendored byos" rationale in `ARCHITECTURE.md` is corrected.
- **ARC-06:** type hints on the pure core; mypy added to `server/requirements-dev.in` (lock regenerated through `scripts/lock-deps.sh`, never by hand) and run in CI (`.github/workflows/ci.yml`) on the typed modules; green.
- Behaviour unchanged: no test assertion is weakened or deleted to get green. Tests may be **retargeted** (import path / monkeypatch target moved to where the code now lives) — that is the expected cost of a move, and each retarget keeps the same assertion.
- No new runtime dependency (production stays stdlib + Pillow + requests; mypy is dev-only). Code, comments and docs in English; no phase/plan/requirement IDs in comments (`scripts/check_comment_history.py`). Ruff and coverage gate stay green.

### Claude's Discretion (verbatim)
- **D-1: The poll cycle becomes a library module.** `run_once` and its steps, `PollBusy` and `poll_cycle_lock` move out of the entrypoint into a library module (e.g. `server/poll_cycle.py`, or a `server/cycle/` package if 80-line functions need several files). `server/poll_loop.py` stays the systemd entrypoint (`build_parser`/`main`) so `deploy/skypane-poll.service` does not change. The companion's `/poll-now` imports the library module. This is what "the companion no longer imports `server.poll_loop`" requires.
- **D-2: Keep public import paths stable where cheap.** When `render.py` / `calendar_rules.py` become packages, `server.plane.render` / `server.plane.calendar_rules` stay importable (package `__init__` re-exports the public API), so companion files owned by Phase 40 need no edits for ARC-03. A package must not be named `calendar` if that could shadow the stdlib module on any `sys.path` configuration.
- **D-3: byos imports the shared module via the same repo-root `sys.path` bootstrap the companion and poll loop use.** The deployed layout (`/opt/skypane/current/{server,stub-server,companion}`) already ships `server/` next to `stub-server/`; the byos unit's sandbox must still allow reading it (check `deploy/skypane-byos.service`). The shared module is stdlib-only so byos gains no dependency.
- Exact module names, the `CycleContext` field list, and the mypy strictness (`--strict` on the pure core vs. `disallow_untyped_defs` per module) are the planner's call, documented in the plans.

### Coordination
- This phase owns `server/`, `stub-server/` and the new shared modules. Phase 40 owns `companion/` and runs in parallel. Companion edits here are limited to the minimal import switches ARC-02/ARC-05 need (`companion/app.py`, `companion/pages/health_page.py`, `companion/pages/airlines_page.py`, `companion/battery.py`, `companion/wake.py` as needed) and their test retargets, each in its **own small commit**. Merge `main` often.
- Phase 42 (OTA) later touches `server/poll_loop.py`; do not pre-empt it.
- Base branch: `claude/plan-phase-38` (PR #150).

### Deferred Ideas (OUT OF SCOPE)
- Companion architecture (routes, pages, templates, i18n keys): Phase 40.
- OTA: Phase 42.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARC-01 | Named cycle steps over a `CycleContext`; the render/publish sequence exists once; no function in server/ over 80 code lines; run_once CC recorded before and after | §1 function inventory (6 offenders), §2 anatomy (4 publish copies, locals → fields, step proposal) |
| ARC-02 | `server/state_store.py` owns poll_state.json; companion imports it | §5 inventory of every poll_state.json reader and writer, plus the companion call-site map |
| ARC-03 | render / calendar_rules packages, `themes.py`, `net/safe_fetch.py` | §7 outlines, re-export surface, the `calendar` shadowing proof, CLI invocation |
| ARC-04 | Explicit injection, no module-global setters | §4 (three setters, their callers, consumers, and one latent companion leak) |
| ARC-05 | One shared module used by server, byos and companion | §6 (copies compared; **one semantic difference in quiet hours**; one companion test conflict) |
| ARC-06 | Typed pure core; mypy in CI, green | §8 (mypy trial error counts, config, lock regeneration verified) |
</phase_requirements>

## Summary

The refactor is feasible and the safety net is strong: **2901 passed / 139 skipped in 87 s** (`./scripts/run-all-tests.sh`, local venv on Python 3.11.15; 105 of the skips are Chromium browser tests, which CI runs). Coverage is **94.07 %** against a floor of **93 %**. Ruff and the comment-history guard are clean. `_run_once_locked` is **335 code lines with McCabe CC 53** (radon grade F, confirmed by an independent AST count). The render → pack → write → gallery sequence **still appears 4 times** after Phase 38. Five other server functions are over 80 code lines, and each needs a split for criterion 1 to hold. stub-server has none.

Test coupling decides how the code can move. Tests reach poll_loop internals mainly by **reading attributes** (≈400 references: `run_once` 168, `load_poll_state` 45, `MIN_ADVANCE_INTERVAL_S` 40, …). Only **5 monkeypatches rebind a poll_loop module-global** (`now_s`, `advance_is_due`, `_notify_silence_transition` ×2, `POLL_LOCK_WAIT_S`, `run_once`). Every other patch rebinds attributes of shared module objects (`poll_loop.detect.*`, `poll_loop.render.build_canvas`, `poll_loop.history_db.*`, `poll_loop.notify.*`), so it survives the move as long as the new cycle module calls those functions through the module attribute (`render.build_canvas(...)`, never `from … import build_canvas`). There is one hidden hazard of the same kind in the calendar split: a companion test helper patches `calendar_rules.default_calendar_transport` on the package object, and that patch only reaches code that looks the name up in that namespace.

ARC-05 is not purely mechanical. The battery curve, the battery-critical reader and the constants are semantically identical across their copies. The **quiet-hours validation differs**. The server path (via `load_device_config`'s normalisers) replaces an invalid stored `quiet_hours_start`/`end` with the defaults 23:00/07:00, so a hold happens. byos treats the same file as "quiet hours off", so there is no sleep extension. Only the arithmetic `seconds_until_quiet_hours_end` is byte-identical. Also, `companion/test_companion_app_03.py` currently asserts that `companion.battery` imports **nothing from `server`**, which directly contradicts "one shared module used by companion" unless the shared module lives outside `server/` or that assertion is retargeted.

**Primary recommendation:** order the work as follows.
1. Tooling and baseline.
2. `server/state_store.py` plus a stdlib-only `server/device_policy.py`, wired into server and byos.
3. Explicit injection.
4. Move the cycle to `server/poll_cycle.py`.
5. Split render, calendar_rules/net and themes in parallel, since they touch disjoint files.
6. Add mypy and CI.
7. Switch the companion imports, one commit per file group, then close.

Tests are retargeted mechanically, and there is **no re-export facade in poll_loop**: a facade makes monkeypatches silently miss.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Poll cycle orchestration (`run_once`, steps, `CycleContext`) | Backend library `server/poll_cycle.py` | Entrypoint `server/poll_loop.py` (argparse/main only) | Shared by the systemd oneshot and the companion's `/poll-now` |
| poll_state.json persistence | `server/state_store.py` (Database/Storage) | — | Single owner; read by the companion, wake and byos |
| Battery and quiet-hours policy (constants, hysteresis, curve, window arithmetic) | `server/device_policy.py` (stdlib-only, pure) | device_config, wake, byos and companion re-export or import it | Must be importable by byos (stdlib-only) and companion.battery |
| Theme registry | `server/themes.py` | `device_config` re-exports | Presentation data, separate from persistence |
| Outbound URL safety (SSRF gate) | `server/net/safe_fetch.py` | `http_fetch` (pinned transport) | Shared by calendar fetch and notify |
| Rendering | `server/plane/render/` package | companion theme preview, firmware generator | Pure image composition |
| Device protocol sleep_s composition | `stub-server/byos_server.py` | uses device_policy | Keeps its own fail-open file readers |

## Standard Stack

No new runtime dependency. Dev-only additions:

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| mypy | 2.3.1 | Type check the pure core in CI | [VERIFIED: PyPI via `pip download`, slopcheck OK] |
| types-requests | 2.33.0.20260906 | Stubs for `requests` (detect, http_fetch, enrich) | [VERIFIED: PyPI, slopcheck OK]. Pulls `urllib3`, already transitively locked |
| Pillow 12.3.0 (existing) | ships `py.typed` | no stub package needed | [VERIFIED: `PIL/py.typed` exists in 12.3.0] |
| radon | 6.0.1 | CC measurement for the baseline doc only | [VERIFIED: slopcheck OK]. **Do not add to the lock**; run ad hoc: `uv run --no-project --with radon==6.0.1 radon cc -s server/poll_loop.py` |

Installation: add `mypy==2.3.1` and `types-requests==2.33.0.20260906` to `server/requirements-dev.in`, then run `scripts/lock-deps.sh` (uv 0.8.17 is on PATH here and PyPI is reachable through the proxy; verified by the `uv run --with mypy` trials).

## Package Legitimacy Audit

| Package | Registry | Source Repo | slopcheck | Disposition |
|---------|----------|-------------|-----------|-------------|
| mypy | PyPI | github.com/python/mypy | [OK] | Approved (dev-only) |
| types-requests | PyPI | github.com/python/typeshed | [OK] | Approved (dev-only) |
| radon | PyPI | github.com/rubik/radon | [OK] | Approved, ad-hoc measurement only, not locked |

Packages removed: none. Flagged: none.

---

## 1. Function-size inventory (criterion 1)

The measuring script is at `/tmp/claude-0/-home-user-skypane/8e8fad4c-428d-5d59-a5f5-520b5fff40f0/scratchpad/fnsize.py`. **Recommendation:** promote it to `scripts/check_function_size.py`: stdlib-only (ast + tokenize), with a `check` subcommand, `--max 80`, and roots `server stub-server`. Add a detector test `test-support/test_check_function_size.py` modelled on `test-support/test_check_comment_history.py`, and a CI step next to "Comment history guard". Definition used:

- **Code line**: a physical line holding at least one token other than COMMENT, NL, NEWLINE, INDENT or DEDENT, minus every line of a module, class or function docstring.
- **Function size**: code lines within `def … end_lineno`, *inclusive of nested defs* (stricter).
- **Scope**: non-test `.py` under the roots, excluding `.venv`, `test_*.py` and `conftest.py`.

**Criterion scope recommendation:** non-test source only. Test functions are not "architecture", and `test_poll_loop.py` has many long scenario tests. Include `stub-server/`: it costs nothing, because its largest function is `Handler.do_GET` at 54. companion/ has 13 functions over 80 (for example `_dispatch_get` at 93, `battery_sparkline_svg` at 120). That is Phase 40's scope, so do **not** gate companion here.

Current offenders (365 functions scanned):

| Code lines | CC (AST / radon) | Location | Plan owner |
|---|---|---|---|
| **335** | 53 / F(53) | `server/poll_loop.py:907 _run_once_locked` | run_once split |
| 98 | 1 | `server/plane/render.py:1831 build_parser` | render split (group argparse sections into helpers) |
| 91 | 17 / C | `server/plane/render.py:989 draw_main_text_block` | render split |
| 87 | 48 / F(48) | `server/device_config.py:490 save_device_config` | themes/device_config plan |
| 85 | 20 / C | `server/http_fetch.py:319 pinned_request` | net plan |
| 84 | 28 / D | `server/plane/render.py:1931 main` | render split |

These are close to the line and must not cross it after a split: `detect.poll_current_aircraft` 77, `render.draw_previous_text_block` 66, `calendar_rules.fetch_ics` 65.

`run_once` itself is CC 2 (the wrapper). **The number to record is `_run_once_locked` = 53**, measured both ways:
- `uv run --no-project --with radon==6.0.1 radon cc -s server/poll_loop.py` → `F 907:0 _run_once_locked - F (53)`.
- The AST McCabe count gives the same result: +1 per if/for/while/except/IfExp/assert/comprehension(+ifs)/match_case, + (n-1) per BoolOp.

After the split, record the max CC over the new `run_once` and its step functions, plus the per-step table. Typed-function baseline for ARC-06: **0 of 318** non-test server functions have any annotation.

## 2. `_run_once_locked` anatomy (server/poll_loop.py:907-1538)

| Lines | Segment | Reads | Produces / mutates |
|---|---|---|---|
| 907-935 | docstring | | |
| 936-950 | makedirs + **3 global setters** | state_dir | illustration/manual/colour caches (ARC-04) |
| 952-956 | calendar refresh (may open a socket; never raises) | state_dir, `now_s()` | `calendar_registry` |
| 958-1000 | context load | state_dir | `device_cfg, theme_id, poll_state, poll_state_baseline (write-once snapshot), battery_mv, battery_critical` (written into poll_state[`battery_critical_active`]), `effective_wake_interval_s, effective_theme_id=theme_id, tracked_runway_id, quiet_remaining, quiet_until (now_s()), display_enabled` |
| 1001-1010 | **decide_hold**: battery_empty > display_off > quiet_hours | | `hold_kind` |
| 1012-1123 | **hold branch** (early return) | | `was_hold, legacy_present`; battery-low block (1024-1029, notify); `source_fault=_last_source_fault()`; `hold_state` + legacy key delete; `now_iso`; render-on-entry or battery_empty boundary → **publish copy #1 (1047-1063)**; `_record_history(None…)`; silence notify; **one** `_persist_poll_state`; log; result dict |
| 1125-1147 | detection | geofence, snapshot | `geofence_data, diagnostics, provider_last_calls` (live path only; `detect.poll_current_aircraft` runs providers in parallel via ThreadPoolExecutor inside detect.py:816), `flight` |
| 1149-1156 | fault + clock | | `source_fault, previous_source_fault, now_iso` |
| 1158-1186 | hold-exit + slot load | poll_state | `hold_exited` (clears hold_state and legacy key), `current_flight/confirmed_state/route/calendar_theme_id` (THEMES membership check), `previous_*`, `pending`, `last_advance_at`, `now=now_s()`, `unknown_prefix=None`, `event_recorded=False` |
| 1188-1194 | battery-low (same block as 1024-1029) | battery_mv | `battery_low, battery_changed`, notify |
| 1196-1247 | **advance_display_queue** | | `promoted, refreshed, dropped, queue_dirty, prior_confirmed_state`; shifts previous_* and current_flight; `last_advance_at=now` |
| 1249-1364 | promoted/refreshed branch | | runway inference, `state_source`; either the empty render or enrichment (`enrich.resolve_route(now=now_s())`, cache trims, unresolved prefixes, `_should_record_event`, last_recorded_*), **calendar match (only site)**, colour resolve; **publish copy #2 (1342-1345)**; 9 slot writes; `_record_history(current_flight…, provider_last_calls)` |
| 1365-1436 | held branch | | repaint on `source_fault != previous or battery_changed or hold_exited`, reusing persisted calendar id; **publish copy #3 (1414-1417)**; queue writes if queue_dirty; `_record_history(None…, detected=flight is not None)` |
| 1437-1462 | empty branch | | **publish copy #4 (1448-1451)**; `_record_history(None…)` |
| 1464-1493 | persist: **persist → silence notify → persist-again-if-notify-changed** | | |
| 1495-1538 | log line + result dict | | |

**Publish duplication after Phase 38: 4 copies.** Each is `pack_panel(canvas)` → `write_panel_atomic` → `if changed: _save_to_gallery(canvas, now_iso)`. Replace them with one `publish_canvas(ctx, canvas) -> bool`.

**history_db flow (Phase 38):** `run_once` opens `history_db.connection_scope(state_dir)` inside `poll_cycle_lock`. Every `open_db` in the cycle shares that one connection. `_record_history` does the caddy tail read *before* `write_batch(conn)`; one outer batch holds the core writes plus two SAVEPOINT-isolated accessory writes (`_run_isolated_write`). `_load_provider_last_calls` and `_last_source_fault` are plain SELECTs. Keep `_record_history` as is. It is 60 code lines and can move unchanged into the cycle module or a `server/cycle_history.py`.

**Write-once poll_state:** `poll_state_baseline` is taken right after load. The hold path persists **once, after** the silence notify. The live path persists **before** the notify (a crash-safety invariant for `last_recorded_*`, documented at 1464-1474) and then again only if the notify changed something. **These two orders differ on purpose and must be kept exactly.** `test_poll_state_writes.py` and the efficiency-probe write counts guard them.

**Ordering constraints to keep:**
- The calendar refresh runs even during a hold.
- The battery-low notify fires *after* ADS-B detection on the live path, but before the render.
- The `hold_exited` mutation happens after detection.
- `_should_record_event` runs before the last_recorded_* overwrite.
- The log prefix stays `"poll_loop: "`: tests parse stdout lines starting with it (e.g. `test_manual_resolution_reaches_route_source_end_to_end`), journald greps rely on it, and so does the `PollBusy` message text.
- Keep the separate `now_s()` call sites (calendar refresh, quiet hours, pacing, enrich, calendar match) rather than collapsing them into one timestamp. The fake-clock tests cannot tell the difference, but strict preservation is free.

### Proposed step functions (each ≤ ~60 code lines)

```
run_once(snapshot, state_dir, geofence, caddy_log, lock_timeout_s)    # lock + connection_scope
  ctx = load_cycle_context(...)           # 936-1000 (+ explicit registries, ARC-04)
  hold = decide_hold(ctx)                 # 1001-1010, pure: (battery_critical, display_enabled, quiet_remaining)
  if hold: return run_hold_cycle(ctx, hold)   # 1012-1123 (uses publish_canvas, record_cycle, finish_hold)
  detect_flight(ctx)                       # 1125-1156
  load_display_slots(ctx)                  # 1158-1186 (incl. hold-exit clear)
  update_battery_low(ctx)                  # shared with the hold path
  advance_display_queue(ctx)               # 1196-1247
  render_and_publish(ctx)                  # dispatch: _render_promoted / _render_held / _render_empty → publish_canvas once
  record(ctx)                              # one _record_history call, args derived from ctx.branch
  persist(ctx)                             # 1464-1493 (persist → silence notify → persist)
  log_cycle(ctx); return ctx.result()
```

**CycleContext fields** (dataclass, `slots=True` is fine on 3.11 and 3.14):
- inputs: `state_dir, snapshot, geofence, caddy_log`
- config: `device_cfg, theme_id, tracked_runway_id, display_enabled, effective_wake_interval_s, quiet_remaining, quiet_until, calendar_registry`
- registries (ARC-04): `colour_rules, manual_registry`
- state: `poll_state, poll_state_baseline, battery_mv, battery_critical, battery_low, battery_changed, hold_kind, was_hold`
- detection: `diagnostics, provider_last_calls, flight, source_fault, previous_source_fault, now_iso, now, hold_exited`
- slots: `current_flight, current_confirmed_state, current_route, current_calendar_theme_id, previous_flight, previous_confirmed_state, previous_route, pending, last_advance_at`
- pacing: `promoted, refreshed, dropped, queue_dirty, prior_confirmed_state`
- outcome: `branch ("promoted"|"held"|"empty"), confirmed_state, render_state, state_source, route_source, route, calendar_theme_id, effective_theme_id, unknown_prefix, event_recorded, panel_changed`

Keep `decide_hold`, `advance_is_due`, `normalise_pending`, `enqueue_pending` and `pop_fresh_pending` pure, because they are the typed pure core.

**Module layout:** one `server/poll_cycle.py` holding `run_once`, `PollBusy`, `poll_cycle_lock`, `POLL_LOCK_*`, `now_s`, pacing constants and helpers, `CycleContext`, the steps, the notify hooks and `_record_history`. Optionally put gallery and publish in `server/panel_publish.py`. **Do not scatter the seams** (`now_s`, `advance_is_due`, `_notify_silence_transition`, `POLL_LOCK_WAIT_S`) across a package: a monkeypatch only reaches lookups in the module it patches. `poll_loop.py` keeps its docstring, `build_parser` and `main`, plus `from server.poll_cycle import run_once, PollBusy`. It must bind these names as module globals so that `monkeypatch.setattr(poll_loop, "run_once", _raise)` (the main() test) keeps working. `DEFAULT_STATE_DIR` moves to state_store, and poll_loop imports it for `--state-dir`. `deploy/skypane-poll.service` and `activate.sh`'s `poll_loop.py --help` smoke check stay unchanged.

## 3. Test coupling inventory

### poll_loop (all test files; counts are references)
Module-global patches, which **must be retargeted** to the defining module:

| Symbol | Where | Count |
|---|---|---|
| `now_s` | `server/test_poll_loop.py:172` (the shared `clock` fixture) | 1 |
| `advance_is_due` | test_poll_loop.py | 1 |
| `_notify_silence_transition` | test_poll_loop.py | 2 |
| `POLL_LOCK_WAIT_S` | test_poll_loop.py | 1 |
| `run_once` | test_poll_loop.py (main() test) | 1, stays valid if poll_loop binds `run_once` globally |

Patches on shared module objects accessed through poll_loop keep working if the cycle module keeps `import server.plane.detect as detect` etc. and calls through the attribute:
- `poll_loop.detect.{poll_current_aircraft ×7, load_geofence ×3, select_aircraft_for_runway ×2}`
- `poll_loop.render.build_canvas ×4`
- `poll_loop.history_db.{utc_now_iso ×2, set_meta ×4, record_wake_epoch, read_caddy_battery_log, open_db, apply_caddy_battery_log}`
- `poll_loop.notify.send_notification ×4`
- `poll_loop.atomic_io.atomic_write`

When retargeting, rewrite `poll_loop.detect` as `detect` (import the module directly) or as `poll_cycle.detect`.

Attribute reads (all files): `run_once` 168, `load_poll_state` 45, `MIN_ADVANCE_INTERVAL_S` 40, `save_poll_state` 17, `now_s` 13, `_notify_silence_transition` 13, `load_battery_state` 11, `_notify_battery_transition` 9, `_battery_percent_estimate` 6, `normalise_pending` 4, `MAX_PENDING_FLIGHTS` 4, `apply_battery_hysteresis` 3, `MAX_STALENESS_S` 3, and ≤2 each for `poll_cycle_lock, main, _poll_state_path, _as_timestamp, _NOTIFY_BATTERY_*, PollBusy, GALLERY_*, BATTERY_LOW_THRESHOLD_MV, write_panel_atomic, apply_battery_critical_hysteresis, advance_is_due, _save_to_gallery, _parse_iso_epoch, _load_provider_last_calls, POLL_LOCK_FILENAME, POLL_INTERVAL_S, DEFAULT_STATE_DIR`.

Files: `server/test_poll_loop.py` (418 lines mention poll_loop), `test_provider_rate.py` 15, `test_pipeline_e2e.py` 13, `test_poll_efficiency.py` 7, `test_poll_state_writes.py` 7, `test_poll_lock.py` 6, `test-support/efficiency_probe.py` (`run_once`), `test-support/test_efficiency_probe.py` (`save_poll_state`). Companion tests: `test_browser_ux_helpers.py` (`save_poll_state`, `_save_to_gallery`), `test_companion_app_02.py` (battery threshold and curve parity), `test_companion_app_05.py` (`load_poll_state`), `test_companion_app_helpers.py`, `test_status_pages_helpers.py`, `test_view_pages_helpers.py` (`save_poll_state`), `test_status_pages_05b.py` (**asserts airlines_page imports poll_loop**).

**Strategy:** retarget mechanically with a sed map (`poll_loop.load_poll_state` → `state_store.load_poll_state`, `poll_loop.run_once` → `poll_cycle.run_once`, …) plus the 5 seam patches. Keep `import server.poll_loop as poll_loop` only in tests of `main`/`build_parser`. Do **not** add a re-export facade in poll_loop: `monkeypatch.setattr(poll_loop, "now_s", …)` on a re-exported name is a silent no-op, and tests would pass while no longer controlling the clock.

### Tests pinned to cross-file source text (must become identity checks, not deletions)
- `stub-server/test_poll_cycle.py:305` (`seconds_until_quiet_hours_end` and `_HHMM_RE` byte-identical), `:~565` (`DISPLAY_OFF_SLEEP_S`) and `:705` (`BATTERY_CRITICAL_SLEEP_S`, `BATTERY_CRITICAL_RECOVER_MV`) all read `server/device_config.py` and `server/poll_loop.py` **as text**. After unification they fail (the constant lines move). Retarget each to `byos_module.X is device_policy.X` or `==`. That is strictly stronger, not weaker.
- `companion/test_companion_app_02.py:1070` compares the curve to `poll_loop._NOTIFY_BATTERY_DISCHARGE_CURVE` and `_battery_percent_estimate`. Retarget to `device_policy`, or turn it into an identity assertion.
- `server/test_render.py:979` reads `server/plane/render.py` as text (no `stroke_width`/`stroke_fill`). Retarget it to scan every `.py` in `server/plane/render/`.

### render (server/test_render.py plus others)
About 90 distinct names are reached through `render.`, including these privates: `_flight_line1_text` 13, `_TYPE_DISPLAY_LABELS` 11, `_tracked_text_width` 7, `_font` 7, `_flight_line2_text` 7, `_role_font` 6, `_build_no_connection_canvas` 5 (+ `firmware/tools/gen_fault_screen.py`), `_PREVIEW_ROUTE` 5, `_build_hold_canvas` 4, `_build_dimmed_hold_canvas` 4, `_resize_illustration` 3, `_opaque_bbox` 3, `_top_for_centered_content` 2, `_tracked_text_bbox`, `_threshold_alpha`, `_draw_tracked_text`, `_BAND_TOP_LABEL_DIRECTION`. Module attributes are also used: `render.device_config` (45), `render.ImageDraw` (a class-level spy on `ImageDraw.ImageDraw.text/rectangle/textbbox`) and `render.illustrations` (a spy on `select_illustration`). There are **no monkeypatches of render-namespace functions**. All patches hit shared objects (PIL classes, the illustrations module), so a split is safe for patches.

**Strategy:** `render/__init__.py` explicitly re-exports every public name *and* every private name listed above, plus the modules `device_config`, `illustrations`, `ImageDraw` and `Image`. Tests stay unchanged except the source-text test. Retargeting privates to submodules is optional polish.

### calendar_rules (server/test_calendar_rules.py as `cr`, plus companion)
- Privates reached: `_url_is_safe` (18 + 3 elsewhere), `_normalise_calendar_url` 6, `_normalise_calendar_entry` 6, `_build_entry` 2.
- `cr.os.{open,replace,chmod,remove,fdopen}` patches hit the global `os` module, which is fine if `__init__` exposes `os`.
- **Hazard:** `companion/test_companion_app_helpers.py:79-84` (`stubbed_calendar_transport`) assigns `calendar_rules.default_calendar_transport = fake` and relies on `fetch_ics` reading the bare name in its own module (`calendar_rules.py:1067`). `companion/test_companion_app_05.py:1250` likewise assigns `calendar_rules.refresh_calendar_registry` (the call from companion/app.py goes through the package attribute, so that one is fine).
- **Resolution (pick one):** (a) keep `default_calendar_transport`, `fetch_ics` and `refresh_calendar_registry` in `calendar_rules/__init__.py`, as the package's orchestration layer; or (b) move them to `calendar_rules/fetch.py` and retarget the helper to `server.plane.calendar_rules.fetch` in a separate small companion commit.
- **Recommend (a).** It needs zero companion edits (D-2) and still meets `ics`/`registry`/`match`. If (a) is not taken, a missed retarget fails loudly (pytest-socket blocks the real fetch), not silently.

### Setters (ARC-04) called directly by tests
`set_colour_rules_state_dir`: test_colour_rules 12, test_poll_loop 17 (mostly `finally:` resets). `set_manual_registry_state_dir`: test_enrich 11 (+ an autouse reset fixture at :73), test_manual_resolutions 4, test_poll_loop 4. `set_override_state_dir`: test_illustrations 10. `c._cached_rules[...]` is mutated directly in test_colour_rules.py:386.

## 4. Module-global setters (ARC-04)

| Setter | Global | Consumer (reads global) | Callers |
|---|---|---|---|
| `illustrations.set_override_state_dir` (illustrations.py:551) | `_override_state_dir` | `override_dir_for_state_dir(state_dir=None)` fallback, then `select_illustration` from `render._build_active_canvas` (render.py:1693, 1705; no state_dir passed) | poll_loop.py:945 only |
| `manual_resolutions.set_manual_registry_state_dir` (:374) | `_cached_registry` | `airline_name_for_prefix` ← `enrich.airline_source_from_callsign` (:603) ← `resolve_route` | poll_loop.py:946 only |
| `colour_rules.set_colour_rules_state_dir` (:301) | `_cached_rules` | `resolve_effective_theme_id` (:330) | poll_loop.py:950 only |

The companion calls none of the setters. It already uses explicit forms (`illustrations.resolved_illustration_path(key, state_dir)`, `load_colour_rules(state_dir)`, `load_manual_resolutions(state_dir)`).

**Injection design (minimal churn):**
- `resolve_effective_theme_id(state, flight, device_cfg, calendar_theme_id=None, rules=None)`, where `rules=None` means an empty registry (today's "setter never called" behaviour).
- `enrich.resolve_route(..., manual_registry=None)` → `airline_source_from_callsign(callsign, manual_registry=None)` → `manual_resolutions.airline_name_for_prefix(prefix, registry)`.
- `render.build_canvas(..., state_dir=None)` → `_build_active_canvas` → `select_illustration(..., state_dir=state_dir)`.
- The cycle loads `colour_rules.load_colour_rules(state_dir)` and `manual_resolutions.load_manual_resolutions(state_dir)` once in `load_cycle_context`, which keeps the "one registry per cycle" snapshot semantics, and passes `state_dir` to every `build_canvas`.
- Delete the three setters and globals.

**Latent behaviour change to flag (LOW impact, decision needed):** today `companion/theme_preview.py` calls `render.build_canvas` without a state_dir, so the override fallback is whatever the global holds. That is `None` in a fresh companion process, and the state dir **after an in-process `/poll-now`**. Previews therefore show vendored art until someone presses "poll now" and overrides afterwards. Explicit injection makes previews vendored-only, matching the fresh-process behaviour. The preview cache signature (`preview_signature`) ignores override files anyway, so the current post-poll behaviour is already a cache-staleness bug. Recommend: accept vendored-only, and document it in the plan and SUMMARY.

**Test rewrite needed:** `server/test_poll_loop.py:2011 test_manual_registry_loaded_once_per_cycle_from_its_own_state_dir` asserts via the global (`enrich.airline_from_callsign("ZZZ1234")` after a cycle). Retarget it to observable cycle output: run cycles with a `ZZZ…` callsign on the seeded dir, then on the empty dir, and assert `route_source`/`last_route.airline_name` as the sibling test at :2044 does. The invariant stays the same ("registry reloaded from THIS cycle's state_dir"), but the assertion text changes, so call it out in the plan.

Other module-level mutable state: `render._font_cache`, `render._illustration_cache` (keyed on path+mtime+size, bounded), `dither._STATE_BACKGROUND_CACHE`, `history_db._SCHEMA_READY`, `history_db._SCOPE` (thread-local). All are content-keyed memos or connection plumbing, not per-cycle configuration, so they are **out of scope**.

## 5. state_store (ARC-02)

poll_state.json touch points today:

| Location | Kind |
|---|---|
| `server/poll_loop.py:272 _poll_state_path`, `:276 load_poll_state`, `:541 _serialize_poll_state`, `:552 save_poll_state`, `:566 _persist_poll_state`, `:289 _HOLD_KINDS`, `:292 _hold_state` | owner |
| `server/poll_loop.py:304 load_battery_state` | reads `battery_state.json` (byos-owned). Recommend moving it to state_store too, as the state-file reader home |
| `server/wake.py:50 read_battery_critical` | opens poll_state.json directly; key `BATTERY_CRITICAL_STATE_KEY` |
| `stub-server/byos_server.py:336 read_battery_critical` | opens it directly; identical semantics (fail-open False) |
| `companion/app.py:644` | `poll_loop._poll_state_path(state_dir)` (freshness stamp) |
| `companion/pages/health_page.py:1802`, `companion/pages/airlines_page.py:656, 901` | `poll_loop.load_poll_state` |
| `deploy/backup/skypane_backup.py:43`, `test-support/efficiency_probe.py:40` | filename literal |

`server/state_store.py` API: `DEFAULT_STATE_DIR` (moved from poll_loop; `os.path.join(server/, "state")`), `POLL_STATE_FILENAME`, `poll_state_path(state_dir)`, `load_poll_state`, `serialize_poll_state`, `save_poll_state`, `persist_poll_state_if_changed(state_dir, state, baseline) -> None`, `HOLD_KINDS`, `hold_state(poll_state)`, `load_battery_state`, and `read_battery_critical(state_dir)` implemented as `load_poll_state(state_dir).get(KEY) is True`. That is semantically identical to both copies, because load returns `{}` on OSError, ValueError or non-dict. Imports: stdlib + `server.atomic_io` only, which keeps it byos-importable.

Companion non-test map:

| Today | New home |
|---|---|
| app.py `poll_loop.run_once`, `poll_loop.PollBusy` (2534-2537) | `poll_cycle.run_once/PollBusy` |
| app.py `poll_loop.now_s()` (2172, 2495) | `poll_cycle.now_s()` (app imports poll_cycle anyway) |
| app.py `poll_loop.DEFAULT_STATE_DIR` (2811) | `state_store.DEFAULT_STATE_DIR` |
| app.py `poll_loop._poll_state_path` (644) | `state_store.poll_state_path` |
| app.py (docs/comments 12, 526, 529, 2837) | text update |
| health_page.py:36, 1802 | `import server.state_store as state_store`; `state_store.load_poll_state` |
| airlines_page.py:28, 656, 901 (+ comment 24) | same |

`companion/pages/config_page.py:444` and `history_page.py:60` mention poll_loop only in comments. `poll_cycle` must never import `poll_loop`: the entrypoint imports the library, never the reverse.

## 6. ARC-05 duplications, compared

| Logic | Copies | Semantically identical? |
|---|---|---|
| `seconds_until_quiet_hours_end` | device_config.py:620, byos_server.py:386 | **Yes**, byte-identical (a drift test pins it) |
| `_HHMM_RE`, `QUIET_HOURS_TZ` | device_config.py:78/82, byos:72/76 | Yes |
| **Quiet-hours validation** | `device_config.quiet_hours_status` (via `normalise_quiet_hours_time` in `load_device_config`) vs `byos.read_quiet_hours` | **NO: DIFFERENT.** With `quiet_hours_enabled: true` and an invalid `quiet_hours_start`/`end` on disk, the server substitutes the defaults 23:00/07:00 (hold screen drawn, `wake.next_wake_status` extends), while byos returns `None` (no quiet-hours sleep extension). Reachable only through a hand-edited or corrupted file; `save_device_config` validates. **Behaviour decision:** recommend sharing only the arithmetic plus constants and keeping both validation policies exactly as they are (this phase is behaviour-preserving). Add one test per side pinning the current outcome for an invalid time, so the difference becomes documented instead of accidental. Unify later only as an explicit behaviour change. |
| `DISPLAY_OFF_SLEEP_S` 300, `BATTERY_CRITICAL_SLEEP_S` 3600, `WAKE_INTERVAL_MIN_S/MAX_S` 60/3600 | device_config.py:53-64, byos:82-94 | Yes |
| `BATTERY_CRITICAL_RECOVER_MV` 3700 | poll_loop.py:242, byos:95 | Yes |
| battery-critical latch reader | wake.py:50, byos:336 | Yes (fail-open, `is True`) |
| battery-critical hysteresis | poll_loop.py:336 only; byos uses only `fresh_mv >= RECOVER_MV` (an anticipation rule, not a copy) | n/a (one copy + one derived rule) |
| battery-low hysteresis 3500/3600 | poll_loop.py:233-234, :323 only | single copy; move it with the critical one |
| discharge curve + percent | poll_loop.py:359-405 (`_NOTIFY_BATTERY_*`, `_battery_percent_estimate`), companion/battery.py:19-114 | **Yes.** Both are `int(round(fraction*100))` over the same 14-knot table with the same None/NaN/≤0 guards |
| wake_interval / display / led field readers | byos `read_wake_interval_s`, `read_display_enabled`, `read_led_enabled` vs device_config normalisers | Same bounds and defaults (byos returns the CLI default instead of None for wake). Optional to share; not required by the ledger |
| byos `_atomic_write` vs `server/atomic_io` | | Not in ARC-05; leave it (byos keeps its own mode handling) |

**Shared module:** `server/device_policy.py`. It must be stdlib-only, **import nothing from `server`**, and must not be named after a stdlib module. It holds the battery constants and both hysteresis functions, `BATTERY_CRITICAL_STATE_KEY`, the curve plus `battery_fraction`/`battery_percent`, `HHMM_RE`, `QUIET_HOURS_TZ`, `seconds_until_quiet_hours_end`, `DISPLAY_OFF_SLEEP_S`, `BATTERY_CRITICAL_SLEEP_S`, `WAKE_INTERVAL_MIN_S/MAX_S`, and a pure `battery_critical_pin_applies(latched, fresh_mv)`. device_config, wake, poll_cycle and byos import from it. device_config re-exports the names callers already use (`device_config.DISPLAY_OFF_SLEEP_S` etc.). `companion/battery.py` re-exports `BATTERY_DISCHARGE_CURVE`, `BATTERY_FULL_MV`, `BATTERY_EMPTY_MV`, `battery_fraction` and `battery_percent` from it, and keeps the companion-only `LOW_BATTERY_DISPLAY_*`, `_curve_mv_at_percent` and life estimate. That follows the `companion/wake.py` shim pattern.

**Companion test conflict (flag):** `companion/test_companion_app_03.py:1312 test_battery_module_imports_neither_a_page_module_nor_the_server_package` asserts that no `server*` module is in sys.modules after `import companion.battery`. Two options:
- (a) Retarget the assertion to "pulls in no module outside {`server`, `server.device_policy`} and no third-party package (PIL, requests)". Its stated purpose, "stdlib-only on purpose", is preserved. Recommended; do it in its own companion commit.
- (b) Put the shared module outside `server/` (for example a top-level `skypane_policy/`). That forces `deploy/deploy.sh:40`'s `git archive` path list, `deploy/tests/test_deploy.py:100`'s expected list and mypy paths to change, and contradicts D-3's "server/ already ships next to stub-server/".

**byos wiring:** add the same bootstrap as poll_loop.py:40-44 (`_REPO_ROOT = dirname(dirname(abspath(__file__)))`; insert if absent), then `from server import device_policy, state_store`. It works:
- **Deployed:** runs as `/opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/byos_server.py`, `WorkingDirectory=/opt/skypane`, `ProtectSystem=strict` (the whole FS read-only, `/opt` readable), `ReadWritePaths=/opt/skypane/state`, no `ReadOnlyPaths`/`InaccessiblePaths`. `/opt/skypane/current/server` is readable. `activate.sh:163` byte-compiles the release and `:166-168` smoke-runs `byos_server.py --help`, which exercises the import.
- **Tests:** `test_byos_hardening.py:61` and `test_byos_bind_secret.py:34` load it with `spec_from_file_location` (pytest `pythonpath=["."]` puts the repo root on sys.path already). Subprocess launches from `test_poll_cycle.py`, `test_byos_hardening.py:182` and `test_pipeline_e2e.py` rely on the bootstrap. `stub-server/devices_cli.py:31` inserts `stub-server/` and imports `byos_server`, which then bootstraps the repo root. Fine.

Docs to correct:
- `ARCHITECTURE.md:327` ("vendored from `flightportrait/frame` — unchanged in logic") and `:357` ("a fail-open reader proven behaviour-identical to `server/wake.py`'s own copy").
- `stub-server/VENDOR.md:120, 165, 256` (stdlib-only, "never import server", drift guard).
- byos comments at `byos_server.py:8` (the docstring "Stdlib only." stays true: shared modules are stdlib), `:59, 78, 132, 342-344, 380-385`.
- The `device_config.py:57, 62, 630` "kept in step with byos" comments.

## 7. ARC-03 splits

**`calendar` shadowing is real.** Running a module directly puts its directory at `sys.path[0]`: `python server/plane/render.py` puts `server/plane/`, and `python server/poll_loop.py` puts `server/`. render imports enrich → requests → `http.cookiejar`, which imports stdlib `calendar`. A `server/plane/calendar/` package would therefore shadow stdlib `calendar` whenever any `server/plane/*.py` script runs directly (render, detect and illustrations all have `__main__` blocks). **Keep the package name `calendar_rules/`.** The same rule applies to every new top-level module in `server/` and `server/plane/`: avoid stdlib names (`types`, `select`, `queue`, `token`, `http`, `json`, `io`, `secrets`, `calendar`, `time`, …). The proposed names (`poll_cycle`, `state_store`, `device_policy`, `themes`, `net`, `render/{layout,text,hold_screens,glyphs,cli}`) are all clear.

**render.py (2049) → `server/plane/render/`:**

| Submodule | Lines today | Content |
|---|---|---|
| `constants.py` (or `style.py`) | 43-349 | spacing, fonts, state colours, headline texts, dimmed/frame/band/battery geometry, `state_*_index`, `runway_tag_text`, `empty_heading_text` |
| `text.py` | 351-476, 845-956, 974-1233 | `_font`, `fit_text_size`, tracked text, role fonts, wrap, `_flight_line1/2_text`, `_TYPE_DISPLAY_LABELS`, `display_airline_name`, `draw_main_text_block` (**split to ≤80**), `draw_previous_text_block` |
| `layout.py` | 294-333, 478-844, 1619-1812 | band, frame, source-fault badge, battery icon, top labels, illustration load/resize/cache/placement, `_assert_legal_palette`, `_build_active_canvas`, `build_canvas`, `render_panel` |
| `hold_screens.py` | 1234-1343, 1498-1574 | empty, quiet, display-off, battery-empty and no-connection canvases, `_build_hold_canvas`, `_build_dimmed_hold_canvas` |
| `glyphs.py` | 1344-1497, 1575-1618 | power, moon, empty-battery, alert, runway icons |
| `cli.py` + `__main__.py` | 1813-2049 | `_PREVIEW_*`, `build_parser` (**98 → split**), `main` (**84 → split**) |

`build_canvas` dispatches into both layout and hold_screens: put it in `layout.py` (hold_screens must not import layout) or in `__init__`. Keep `_illustration_cache` and `_font_cache` in exactly one module each.

CLI: today it is invoked as `server/.venv/bin/python3 server/plane/render.py …` (docstring usage; `server/README.md`; historical `hardware/BRINGUP-LOG.md`, leave as is). No deploy script, systemd unit or CI step runs it. Tests call `render.main([...])` in-process (test_render.py:2018-2081). After the split, document `python3 -m server.plane.render …` (the `__main__.py`, run from the repo root); `cli.py` keeps the sys.path bootstrap if direct execution should still work. `firmware/tools/gen_fault_screen.py:76,100,244` imports `server.plane.render` and calls `_build_no_connection_canvas`, so it keeps working through the re-export. Its generated header text contains the literal `server/plane/render.py _build_no_connection_canvas(flat=True)`, and `server/test_fault_screen_mask.py` compares the generator output byte-for-byte with `firmware/main/fault_screen_mask.h`. If that provenance string is changed, **regenerate the header in the same commit**; otherwise leave it.

**calendar_rules.py (1433) → `server/plane/calendar_rules/`:**

| Submodule | Lines | Content |
|---|---|---|
| `ics.py` | 181-427 | allowlist regexes, `unfold_ics_lines`, `split_property`, `parse_ics_datetime`, `_build_entry`, `parse_ics_events` |
| `registry.py` | 30-180, 428-894 | constants, FETCH_* statuses, lock, paths, secret, `_normalise_calendar_entry`, retention/cap, load/write registry, `save_calendar_url`, mode checks, throttle and window |
| `match.py` | 1261-1433 | `DEPARTING_STATE`/`ARRIVING_STATE`, IATA helpers, `match_calendar_theme` |
| `__init__.py` | 998-1260 + re-exports | `default_calendar_transport`, `fetch_ics`, `refresh_calendar_registry` (see the hazard in §3), plus explicit re-exports incl. `_url_is_safe`, `_normalise_calendar_url`, `_normalise_calendar_entry`, `_build_entry`, `os` |

`notify.py` also uses `calendar_rules.USER_AGENT` (:101): move `USER_AGENT` to `net/safe_fetch.py` too, or have notify import it from there.

**net/safe_fetch.py:** move `_address_is_public` (a thin wrapper over `http_fetch.address_is_public`), `_host_is_safe`, `_url_is_safe` → `url_is_safe` and, optionally, `_normalise_calendar_url` (calendar-specific: webcal → https; keep it in calendar_rules). `http_fetch.py:32-33` already anticipates absorbing it into `net/safe_fetch.py`. Two options:
- (a) Create `server/net/__init__.py` + `server/net/safe_fetch.py` holding only the URL gate, leave `server/http_fetch.py` where it is, and have safe_fetch import `address_is_public` from it. Minimal, and it needs no retargeting of test_http_fetch (700 lines, which patches `http_fetch._default_ssl_context` and `requests.get`) or test_notify (which patches `http_fetch.pinned_request` and `_default_ssl_context`).
- (b) Move http_fetch into `server/net/`, which requires retargeting those patches.

**Recommend (a)** and split `pinned_request` (85) into helpers in place. `notify.py:115` switches to `safe_fetch.url_is_safe`. No other duplicate SSRF logic exists: enrich and detect go through `http_fetch.bounded_get` to fixed hosts.

**themes.py:** move `THEMES` (device_config.py:84-265), `THEME_IDS`, `DEFAULT_THEME_ID` and the presentation accessors (:676-735: `theme_background_index`, `theme_ink_index`, `theme_label`, `theme_dithered`, `theme_weight`, `theme_is_band`, `theme_band_index`, `theme_band_dithered`). Choose whether the runway accessors (:737-746) go too; the ledger names only themes. `device_config` re-exports all of them (usage: `THEME_IDS` 74, `THEMES` 59, `DEFAULT_THEME_ID` 35, `theme_label` 12, …), so no caller changes. `themes.py` imports only `server.panel_format`'s IDX constants (panel_format imports PIL lazily). Split `save_device_config` (87 lines, CC 48) into per-field validate/merge helpers. `companion/test_config_page_02.py:1924` patches `device_config.save_device_config`, so the name must stay a device_config global.

## 8. ARC-06 mypy

No mypy config exists today. Config files present: `pyproject.toml` only (ruff, pytest, coverage). **Recommend `[tool.mypy]` in pyproject.toml.**

Trial with mypy 2.3.1, `--python 3.14`, `disallow_untyped_defs`, `check_untyped_defs`, `warn_return_any`, `explicit_package_bases`, `mypy_path="."`, `follow_imports="silent"`:

| Module | Errors | Nature |
|---|---|---|
| server/wake.py | 8 | 7 no-untyped-def; 1 real: `int(raw)` with `raw: str | None` (:41) needs an `if raw is None: return None` guard (same behaviour: TypeError is caught today) |
| atomic_io + panel_format + runway_config | 13 | 11 untyped defs; `fcntl = None` fallback (:50) needs `# type: ignore[assignment]` or an Optional module alias; PIL resolves once run inside server/.venv |
| device_config.py | 27 | all no-untyped-def |
| colour_rules.py | 17 | 14 untyped defs + 3 var-annotated (`_cached_rules`, which goes away under ARC-04) |
| (`--strict`, for reference) | wake 14, colour_rules 42, device_config 46, detect 53, poll_loop 161 | |

**Pure core to type (recommended list):**
- `server/device_policy.py`, `server/state_store.py` and `server/themes.py` (all new)
- `server/wake.py`, `server/panel_format.py`, `server/atomic_io.py`
- `server/plane/runway_config.py`, `server/plane/colour_rules.py`
- `server/plane/calendar_rules/{ics,match}.py`, `server/net/safe_fetch.py`
- `server/poll_cycle.py`: its pure helpers (`decide_hold`, pacing) plus `CycleContext`, and the step signatures, which cost little to annotate while they are being written

Leave out render, detect, enrich, http_fetch, history_db, notify and byos for now.

**Config shape:** global `python_version = "3.14"`, `explicit_package_bases = true` (server/ has no `__init__.py`; it is a namespace package), `mypy_path = "."`, `follow_imports = "silent"`, `warn_unused_configs`, `warn_redundant_casts`, `warn_unused_ignores`, `no_implicit_optional`, `check_untyped_defs`, and `files = [ …typed list… ]`. Then `[[tool.mypy.overrides]]` for the typed modules with `disallow_untyped_defs`, `disallow_incomplete_defs`, `disallow_any_generics`, `warn_return_any`. `strict` is global-only in mypy config, so use the per-flag overrides. Pillow is typed (py.typed). requests needs `types-requests`, which detect, http_fetch and enrich import transitively; with `follow_imports=silent` they are analysed for types but their errors are suppressed.

**Runtime compatibility:** the local venv is **Python 3.11.15** and production/CI is 3.14. Annotations must run on both. Use `X | None` and `from __future__ import annotations` where needed; avoid PEP 695 `type` aliases and `class C[T]` generics (3.12+).

**CI step** (ci.yml, after "Comment history guard"): `server/.venv/bin/mypy`. It reads the `files` list from pyproject and runs inside the venv, so Pillow and requests stubs resolve. Lock: edit `server/requirements-dev.in`, then run `scripts/lock-deps.sh` (uv 0.8.17 present; it compiles for `--python-version 3.14 --python-platform x86_64-manylinux_2_28`). Commit both `requirements-dev.txt` and any `requirements.txt` churn (there should be none). Locally, `server/.venv` must be reinstalled (`pip install --require-hashes -r server/requirements-dev.txt`) before `server/.venv/bin/mypy` exists.

## 9. Tooling / CI facts

- Whole suite: `./scripts/run-all-tests.sh` (`pytest -n auto --cov`, gate from pyproject). Here: **2901 passed, 139 skipped, 87 s wall**; 105 skips are Chromium (not installed locally; CI sets `SKYPANE_REQUIRE_BROWSER=1`) and 1 is root-euid.
- Subset: `./scripts/run-all-tests.sh -- server/test_poll_loop.py` (the gate is disabled when extra args are given).
- Coverage: **94.07 %**, `fail_under = 93` in `pyproject.toml [tool.coverage.report]`; `source = ["server","stub-server","companion","deploy/backup"]`, test files omitted. Moving code preserves executed lines. The watch-outs are new modules with only-import-covered defensive branches and the render CLI's uncovered lines (render.py:1986-2049), which move with it. poll_loop.py is at 95 % (33 missed lines).
- Ruff: `select = E4,E7,E9,F`, `ignore = E402` (the sys.path bootstraps). The pyproject comment enumerates the E402 sites (poll_loop 4, render 3, enrich 1). Update the comment when bootstraps move or byos gains one.
- `scripts/check_comment_history.py check` (CI): new comments must not contain `ARC-0x`, `D-1`, `Phase 39`, `.planning/`, or plan IDs like `39-04`. This includes the new baseline-gate script's help text if it ends up in a tracked `.py` file.
- `deploy/activate.sh:166-168` smoke-runs `companion/app.py`, `server/poll_loop.py`, `stub-server/byos_server.py` and `deploy/backup/skypane_backup.py` with `--help`. That is a free import check for every entrypoint after the moves.
- Phase-38 instruments: `scripts/measure_efficiency.py` and `test-support/efficiency_probe.py` import `server.poll_loop.run_once` → retarget to `poll_cycle`. They count `atomic_io.atomic_write` calls on poll_state.json, a strong guard for the write-once flow during the split.

## 10. Plan decomposition proposal

| Plan | Wave | Content | Files (ownership) | Depends |
|---|---|---|---|---|
| 39-01 | 1 | `scripts/check_function_size.py` + detector tests; `39-ARC-BASELINE.md` "Before" section (inventory above, radon CC, 0/318 typed, companion import sites, duplicate table incl. the quiet-hours difference) | scripts/, test-support/, .planning | — |
| 39-02 | 2 | `server/state_store.py` + `server/device_policy.py`; poll_loop/wake/device_config use them (re-exports); byos bootstrap + imports; stub-server drift tests → identity checks; pin tests for the quiet-hours validation difference; ARCHITECTURE/VENDOR text | server/{state_store,device_policy,poll_loop,wake,device_config}.py, stub-server/*, ARCHITECTURE.md | 01 |
| 39-03 | 3 | ARC-04 injection (colour_rules, manual_resolutions, enrich, illustrations, `render.build_canvas(state_dir=)`); delete setters; retarget setter tests; rewrite the global-assertion test (§4) | server/plane/{colour_rules,manual_resolutions,enrich,illustrations,render}.py, poll_loop.py, their tests | 02 |
| 39-04 | 4 | **run_once split** → `server/poll_cycle.py` (`CycleContext`, steps, single `publish_canvas`); poll_loop slimmed to entrypoint; retarget server tests + efficiency_probe; record "After" CC | server/poll_cycle.py, poll_loop.py, server/test_poll_*.py, test_pipeline_e2e, test_provider_rate, test-support/efficiency_probe.py | 03 |
| 39-05 | 4 ∥ | render package split + the 3 oversized render functions; source-text test retarget | server/plane/render/**, server/test_render.py (+ gen_fault_screen/header only if touched) | 03 |
| 39-06 | 4 ∥ | calendar_rules package + `server/net/safe_fetch.py`; notify switch; `pinned_request` split | server/plane/calendar_rules/**, server/net/**, notify.py, http_fetch.py, their tests | 02 |
| 39-07 | 4 ∥ | `server/themes.py`; `save_device_config` split | server/{themes,device_config}.py, test_config_history/test_runway_config | 02 |
| 39-08 | 5 | mypy: annotations on the pure core, `[tool.mypy]`, dev lock via lock-deps.sh, CI step; function-size gate made blocking in CI and a tree-wide test | pyproject.toml, server/requirements-dev.*, ci.yml, typed modules | 04-07 |
| 39-09 | 5 ∥ | Companion import switches, **one commit per group**: (a) app.py → poll_cycle/state_store; (b) health_page/airlines_page → state_store; (c) battery.py → device_policy re-export; (d) test retargets (helpers, 05b airlines-import assertion, 03 battery isolation allowlist, 02 parity); plus a `server/test_import_boundaries.py` guard | companion/app.py, pages/health_page.py, pages/airlines_page.py, battery.py, listed tests | 02, 04 |
| 39-10 | 6 | Close: baseline "After", ARCHITECTURE.md poll-cycle and module map, README usage lines, full suite + coverage + ruff + comment guard + mypy + size gate | docs | all |

Parallel safety: 04, 05, 06 and 07 touch disjoint production files. The shared files to watch are `pyproject.toml` (only 08 edits it) and `server/poll_loop.py`: 02 and 03 edit it before 04, and 05, 06 and 07 must not edit it. They rely on the stable import paths through the package `__init__`s.

**Riskiest steps:**
1. **39-04:** ordering of persist/notify between the hold and live paths, the 5 seam patches, the `"poll_loop: "` log prefix, and `render.build_canvas` being patched through the module attribute.
2. **39-06:** the `default_calendar_transport` lookup namespace, and preserving the SSRF gate unchanged.
3. **39-02:** the quiet-hours semantic difference and the byos bootstrap in deploy and subprocess tests.
4. **39-03:** the theme-preview override leak.

## Architecture Patterns

- **Seam discipline:** any name a test monkeypatches must be looked up at call time in the module the test patches. Call through module attributes (`render.build_canvas`, `detect.poll_current_aircraft`, `calendar_rules.default_calendar_transport`), never `from X import fn`, inside the cycle.
- **Re-export for stable paths, never for patch targets:** package `__init__` re-exports are fine for read access (render, calendar_rules, device_config ← themes/device_policy). They are wrong for anything tests rebind.
- **Existing shim precedent:** `companion/wake.py` re-exports `server.wake`; `companion/battery.py` follows the same pattern for the curve.

### Anti-Patterns to Avoid
- A re-export facade in `poll_loop.py` for tests (silent no-op patches).
- A package named `calendar` or any new module named after the stdlib.
- `device_policy` importing `server.device_config` (that pulls panel_format into byos and companion.battery).
- Collapsing the hold and live persist orders into one `persist()` path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| CC measurement | a new McCabe counter in the repo | radon 6.0.1 ad hoc (the AST count in the scratchpad script agrees; keep it only as a cross-check) |
| Import-boundary checks | source-text greps (forbidden in companion tests by `test_suite_guards.py` G2/G3) | subprocess `import X` + `sys.modules` inspection (the established pattern: `companion/test_companion_app_02.py:1149`, `_03.py:1312`) |
| Dependency locking | hand edits | `scripts/lock-deps.sh` |

## Runtime State Inventory

| Category | Items Found | Action |
|---|---|---|
| Stored data | poll_state.json keys (`hold_state`, legacy `quiet_hours_active`, `battery_critical_active`, `battery_low_active`, `notifications`, `last_*`, `previous_*`, `pending_flights`, `enrichment_cache`, `unresolved_prefixes`, `last_recorded_*`, `last_calendar_theme_id`); history.db meta keys (`META_PROVIDER_LAST_CALL_PREFIX+name` etc.) | None: key names and file names are unchanged (verified: the refactor moves code, not formats). Keep the compact serialisation exactly (`separators=(",",":")`), because persist-if-changed diffs strings |
| Live service config | systemd units reference `server/poll_loop.py`, `stub-server/byos_server.py`, `companion/app.py` | None: entrypoints keep their paths (D-1) |
| OS-registered state | skypane-poll.timer/service, skypane-byos.service, skypane-companion.service | None |
| Secrets/env vars | `SKYPANE_SLEEP_S` (read by `wake.env_sleep_s`), `SKYPANE_CADDY_ACCESS_LOG`, `SKYPANE_STATE_DIR` | None: names unchanged |
| Build artifacts | `activate.sh` byte-compiles each release fresh; a stale `server/plane/render.py` would coexist with `render/` only in a dirty checkout | Delete `render.py` and `calendar_rules.py` in the same commit that adds the packages (`git mv` then split); remove stray `__pycache__/render.*.pyc` locally if imports behave oddly |

## Common Pitfalls

### Pitfall 1: silent monkeypatch no-ops after a move
**What goes wrong:** a test patches `poll_loop.now_s`, but the cycle reads `poll_cycle.now_s`. The test passes against the real clock or flakes.
**How to avoid:** retarget the 5 seam patches (§3) and add no facade.
**Warning signs:** pacing tests that become time-dependent; `test_now_s_clock_reaches_adsbdb_cache_stamp` fails.

### Pitfall 2: reordering side effects while extracting steps
**What goes wrong:** the notify, persist and record order changes, and poll_state write counts or crash-safety change.
**How to avoid:** keep the hold path as record → notify → persist and the live path as publish → record → persist → notify → persist. `server/test_poll_state_writes.py` and `server/test_poll_efficiency.py` are the guards.

### Pitfall 3: the calendar transport patch namespace
See §3; decide (a) or (b) before starting 39-06.

### Pitfall 4: byos loses "fail-open" on import failure
**What goes wrong:** a bootstrap mistake means `import server.device_policy` raises, and byos crashes at start (the always-on device endpoint goes down).
**How to avoid:** `activate.sh`'s `--help` smoke check blocks a bad release, and the subprocess tests cover it. Keep the shared modules free of third-party imports.

### Pitfall 5: stdlib shadowing
See §7. Direct script runs put `server/` or `server/plane/` on `sys.path[0]`.

### Pitfall 6: 3.11 vs 3.14 syntax
The local venv is 3.11. Do not use 3.12+ syntax in annotations.

## Code Examples

Import-boundary guard (behavioural; lives in `server/test_import_boundaries.py`, outside companion ownership, and follows the existing subprocess pattern):
```python
# Pattern source: companion/test_companion_app_03.py:1312
script = (
    "import json, sys\n"
    "import companion.app\n"             # imports every page module
    "print(json.dumps(sorted(m for m in sys.modules if m == 'server.poll_loop')))\n"
)
result = subprocess.run([sys.executable, "-c", script], cwd=REPO_ROOT, env=child_env(),
                        capture_output=True, text=True, timeout=60)
assert json.loads(result.stdout.strip().splitlines()[-1]) == []
```
Add a second assertion that `server.poll_cycle` imports no `server.poll_loop`. A third, byos side: after loading byos, `byos.seconds_until_quiet_hours_end is device_policy.seconds_until_quiet_hours_end`.

Function-size core (from the scratchpad script):
```python
def code_lines(src):  # tokens other than COMMENT/NL/NEWLINE/INDENT/DEDENT/ENDMARKER
    ...
size = len(set(range(fn.lineno, fn.end_lineno + 1)) & (code_lines(src) - docstring_lines(tree)))
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Theme previews becoming vendored-only (no overrides) is acceptable | §4 | Low: a visible preview difference after /poll-now; needs the developer's nod |
| A2 | The quiet-hours validation difference should be preserved (not unified) this phase | §6 | Medium: unifying either way is a behaviour change on corrupted configs |
| A3 | Retargeting `test_companion_app_03`'s "no server import" assertion to an allowlist is an acceptable retarget, not a weakening | §6 | Medium: otherwise the shared module must live outside `server/` (deploy changes) |
| A4 | Changing `test_status_pages_05b.py:527`'s "airlines_page imports poll_loop" to "imports state_store" is required by ARC-02 itself | §3/§5 | Low |

## Open Questions

1. **Quiet-hours invalid-time policy (A2).** Recommendation: preserve both, pin each with a test, and log a follow-up.
2. **Where `default_calendar_transport` lives (§3).** Recommendation: the `calendar_rules/__init__.py` orchestration layer (no companion edit).
3. **Whether to also unify byos's field readers (`read_wake_interval_s`, `read_display_enabled`, `read_led_enabled`) through device_policy normalisers.** They are identical today, and it is optional; recommend yes if cheap, done in 39-02.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| server/.venv python | tests | ✓ | 3.11.15 (CI and prod 3.14) | `PYTHON=` override |
| uv | lock-deps.sh, radon/mypy trials | ✓ | 0.8.17 | — |
| PyPI via proxy | lock regeneration | ✓ | — | — |
| Python 3.14 (uv-managed) | mypy `python_version` trial | ✓ | 3.14.0rc2 | — |
| Chromium headless shell | browser tests | ✗ locally | — | CI runs them; 105 skips locally |
| radon | baseline CC | ✓ via `uv run --with` | 6.0.1 | AST script |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + xdist + pytest-cov + pytest-socket (pyproject `[tool.pytest.ini_options]`) |
| Quick run | `./scripts/run-all-tests.sh -- server/test_poll_loop.py server/test_poll_state_writes.py -x` |
| Full suite | `./scripts/run-all-tests.sh` (≈90 s here) |
| Extra gates | `server/.venv/bin/ruff check .`, `server/.venv/bin/python scripts/check_comment_history.py check`, `server/.venv/bin/mypy` (after 39-08), `python3 scripts/check_function_size.py check --max 80 server stub-server` (new) |

### Phase Requirements → Test Map
| Req | Behaviour | Guards (existing) | New |
|---|---|---|---|
| ARC-01 | cycle behaviour identical | `server/test_poll_loop.py`, `test_poll_state_writes.py`, `test_poll_efficiency.py`, `test_provider_rate.py`, `test_pipeline_e2e.py`, `test_poll_lock.py`, `stub-server/test_poll_cycle.py`, `companion/test_poll_now_lock.py`, `test_request_connections.py`, `test_freshness_token.py` | `test-support/test_check_function_size.py` (detector samples + tree has no function > 80 in server/, stub-server/); unit tests for `decide_hold` and `publish_canvas` |
| ARC-02 | poll_state read/write | `test_poll_state_writes.py`, `test_poll_lock.py`, companion status and airlines tests | `server/test_import_boundaries.py`: a subprocess `import companion.app` never loads `server.poll_loop`; `server/test_state_store.py` (load/serialise/persist-if-changed round trips, `read_battery_critical` parity) |
| ARC-03 | render, calendar, notify, themes behaviour | `test_render.py`, `test_fault_screen_mask.py`, `test_calendar_rules.py`, `test_notify.py`, `test_http_fetch.py`, `test_config_history.py`, companion calendar tests | a render-package source-text test over all files; `import server.plane.render`/`calendar_rules` public-surface smoke |
| ARC-04 | registries per cycle, no globals | `test_colour_rules.py`, `test_enrich.py`, `test_illustrations.py`, `test_manual_resolutions.py`, test_poll_loop manual/colour tests | assert the modules no longer define `set_*_state_dir` (hasattr check, behavioural) |
| ARC-05 | one copy | stub-server drift tests (retargeted to `is`), companion parity test (retargeted) | byos `is` identity checks; quiet-hours invalid-time pin tests (server and byos); battery isolation allowlist test |
| ARC-06 | mypy green | — | CI step `server/.venv/bin/mypy` |

### Sampling Rate
- Per task commit: the quick run over the files touched, plus ruff.
- Per wave merge: the full suite plus the comment guard (plus mypy and the size gate once they exist).
- Phase gate: full suite green at ≥ 93 % coverage, mypy green, size gate green, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `scripts/check_function_size.py` + `test-support/test_check_function_size.py`
- [ ] `server/test_import_boundaries.py` (subprocess + sys.modules; not in companion/, so `test_suite_guards` G2 does not apply and Phase 40 ownership is respected)
- [ ] `server/test_state_store.py`, `server/test_device_policy.py`
- [ ] mypy + types-requests in the dev lock (39-08)

## Security Domain

| ASVS Category | Applies | Control |
|---------------|---------|---------|
| V5 Input Validation | yes | Existing normalisers (`normalise_*`, `_HHMM_RE` anchored with `\Z`) move unchanged; byos keeps its own fail-open readers |
| V12/V13 SSRF (outbound fetch) | yes | `url_is_safe` moves verbatim to `net/safe_fetch.py`: https-only, resolve-then-check-every-address, redirect hops re-checked, `pinned_request` still pins. `test_calendar_rules.py` and `test_notify.py` SSRF tests must stay green unchanged |
| V14 Config | yes | The byos sys.path bootstrap inserts `/opt/skypane/current`, which is root-owned and read-only under `ProtectSystem=strict`; no user-writable path goes on sys.path |
| V2/V3/V4/V6 | no | Not touched (auth, sessions and crypto unchanged) |

| Threat | STRIDE | Mitigation |
|---|---|---|
| SSRF gate weakened during the move | Tampering / Info disclosure | move verbatim; existing SSRF tests; notify imports the public `url_is_safe` |
| Import hijack through a new sys.path entry | Elevation | only the repo root of the release (root-owned); no cwd-relative insert |
| Log leaking secrets | Info disclosure | keep the "log exception type only" rule in fetch paths (calendar URL tokens) |

## Sources

### Primary (HIGH confidence)
- The codebase at `claude/phase-39` (`f83bf04`): every file and line cited above, read directly.
- Tool runs: the full suite (2901 passed / 139 skipped / 87 s / 94.07 %), `radon cc` (6.0.1), `mypy` 2.3.1 trials, `slopcheck` (mypy, types-requests, radon: OK), `pip download` (versions), `uv` 0.8.17.

### Secondary
- None needed; this phase is codebase archaeology.

## Metadata
**Confidence breakdown:** stack HIGH (verified versions); architecture HIGH (derived from code); pitfalls HIGH (each tied to a concrete test or line).
**Research date:** 2026-09-27. **Valid until:** Phase 40 merges into main. Re-check the companion call sites (§5) and helper patches (§3) after each `main` merge.
