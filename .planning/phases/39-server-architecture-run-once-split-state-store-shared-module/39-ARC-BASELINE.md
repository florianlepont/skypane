# Phase 39 — architecture baseline (before/after record)

Single record for every before/after value this phase's ROADMAP success
criteria need: (1) no function in `server/` over 80 code lines, `run_once`
cyclomatic complexity measured before/after; (2) `server/state_store.py`
owns `poll_state.json`, the companion never imports `server.poll_loop`;
(3) `render.py`/`calendar_rules.py` split into packages, one shared
`net/safe_fetch.py`; (4) no module-global setters. Instruments first, same
rule as `38-EFF-BASELINE.md`: this file's Before section is committed
ahead of any production change ARC-01..ARC-06 makes.

Code state measured: branch `claude/phase-39` at `ece675b` (plan 39-01,
instruments only — the function-size gate and its tests — no production
file under `server/`, `companion/`, `stub-server/` or `deploy/` touched
yet).

## Measurement setup

- `git rev-parse --short HEAD` → `ece675b`
- Python: 3.11.15 (`server/.venv/bin/python`)
- Platform: `Linux-6.18.44-fc-v37-x86_64-with-glibc2.39` (`platform.platform()`)

Commands used for every number below, runnable again on any later commit
for an "After" comparison:

```
python3 scripts/check_function_size.py report --top 15 server stub-server
python3 scripts/check_function_size.py check --max 80 server stub-server
uv run --no-project --with radon==6.0.1 radon cc -s server/poll_loop.py
uv run --no-project --with radon==6.0.1 radon cc -s -n C server
server/.venv/bin/python -c "<inline typed-function counter, reproduced below>"
grep -rn "poll_loop" companion --include=*.py | grep -v "/test_"
grep -rn "poll_loop" companion --include=*.py | grep "/test_"
grep -rn "set_override_state_dir\|set_manual_registry_state_dir\|set_colour_rules_state_dir" server companion stub-server --include=*.py
./scripts/run-all-tests.sh
server/.venv/bin/ruff check .
```

## Before

Recorded 2026-09-27, against the tree after this plan's own instrument
(the function-size gate) but before any of ARC-01..ARC-06's production
changes.

### 1. Function size

`python3 scripts/check_function_size.py report --top 15 server stub-server`:

| Code lines | Location | Function |
|---|---|---|
| 335 | server/poll_loop.py:907 | `_run_once_locked` |
| 98 | server/plane/render.py:1831 | `build_parser` |
| 91 | server/plane/render.py:989 | `draw_main_text_block` |
| 87 | server/device_config.py:490 | `save_device_config` |
| 85 | server/http_fetch.py:319 | `pinned_request` |
| 84 | server/plane/render.py:1931 | `main` |
| 77 | server/plane/detect.py:717 | `poll_current_aircraft` |
| 66 | server/plane/render.py:1139 | `draw_previous_text_block` |
| 65 | server/plane/calendar_rules.py:1025 | `fetch_ics` |
| 59 | server/history_db.py:612 | `tail_caddy_battery_log` |
| 59 | server/plane/calendar_rules.py:327 | `parse_ics_events` |
| 57 | server/plane/calendar_rules.py:1342 | `match_calendar_theme` |
| 54 | stub-server/byos_server.py:753 | `Handler.do_GET` |
| 51 | server/plane/detect.py:387 | `filter_in_geofence` |
| 49 | server/plane/detect.py:897 | `build_parser` |

`python3 scripts/check_function_size.py check --max 80 server stub-server`
exits 1 and lists exactly six offenders (identical file, line and size to
the research inventory in `39-RESEARCH.md` §1):

```
server/poll_loop.py:907 _run_once_locked 335
server/plane/render.py:1831 build_parser 98
server/plane/render.py:989 draw_main_text_block 91
server/device_config.py:490 save_device_config 87
server/http_fetch.py:319 pinned_request 85
server/plane/render.py:1931 main 84
```

Total: **365 functions scanned** (non-test `.py` under `server/` and
`stub-server/`). `check --max 400` exits 0 over the same roots (`365
functions scanned, none over 400`), confirming the gate itself works and
that the offender list above is exhaustive for `--max 80`.

### 2. Cyclomatic complexity

`uv run --no-project --with radon==6.0.1 radon cc -s server/poll_loop.py`:

```
F 907:0 _run_once_locked - F (53)
F 729:0 _record_history - C (12)
F 851:0 _save_to_gallery - A (2)
F 885:0 run_once - A (2)
```

`_run_once_locked` = **CC 53** (radon grade F), `run_once` (the lock/entry
wrapper) = **CC 2** — both match the research prediction exactly. The AST
McCabe count in the research prototype (`fnsize.py`) agrees independently.

Five highest-CC functions in `server/` from
`uv run --no-project --with radon==6.0.1 radon cc -s -n C server`, **non-test
only** (the full un-filtered command also surfaces several test-file
scenario functions at CC 11-36, e.g.
`test_pipeline_e2e.py:219 test_full_pipeline_end_to_end_through_the_real_device_protocol`
at E(36); those are excluded here since they are not architecture):

| Rank | CC | Grade | Location | Function |
|---|---|---|---|---|
| 1 | 53 | F | server/poll_loop.py:907 | `_run_once_locked` |
| 2 | 48 | F | server/device_config.py:490 | `save_device_config` |
| 3 | 30 | D | server/plane/calendar_rules.py:1342 | `match_calendar_theme` |
| 4 | 28 | D | server/plane/render.py:1931 | `main` |
| 5 | 26 | D | server/plane/calendar_rules.py:327 | `parse_ics_events` |

### 3. Typed functions

Command (inline, using `scripts/check_function_size.iter_sources` for the
same scope rules as the size gate, plus `ast` to look for any parameter or
return annotation):

```
server/.venv/bin/python -c "
import ast, sys
sys.path.insert(0, 'scripts')
import check_function_size as cfs

total = 0
annotated = 0
for path in cfs.iter_sources(['server']):
    with open(path, encoding='utf-8') as fh:
        source = fh.read()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total += 1
            has_annotation = node.returns is not None
            args = node.args
            all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)
            if any(a.annotation is not None for a in all_args):
                has_annotation = True
            if has_annotation:
                annotated += 1
print('%d of %d non-test server functions have any annotation' % (annotated, total))
"
```

Output: **0 of 318 non-test server functions have any annotation** —
matches the research's "0 of about 318" exactly.

### 4. Companion imports of server.poll_loop

`grep -rn "poll_loop" companion --include=*.py | grep -v "/test_"`
(non-test files, statement-level imports only):

| File | Symbols used |
|---|---|
| `companion/app.py` | `import server.poll_loop as poll_loop`; `poll_loop._poll_state_path`, `poll_loop.now_s`, `poll_loop.run_once`, `poll_loop.PollBusy`, `poll_loop.DEFAULT_STATE_DIR` |
| `companion/pages/health_page.py` | `import server.poll_loop as poll_loop`; `poll_loop.load_poll_state` |
| `companion/pages/airlines_page.py` | `import server.poll_loop as poll_loop`; `poll_loop.load_poll_state` (×2) |
| `companion/wake.py`, `companion/battery.py`, `companion/pages/history_page.py`, `companion/pages/config_page.py` | comment-only mentions of `server/poll_loop.py`, no import |

The same grep restricted to test files (`grep -rn "poll_loop" companion
--include=*.py | grep "/test_"`) finds statement-level imports in
`test_view_pages_helpers.py`, `test_browser_ux_helpers.py`,
`test_companion_app_02.py`, `test_companion_app_05.py`,
`test_companion_app_helpers.py` and `test_status_pages_helpers.py`
(`import server.poll_loop as poll_loop`), plus one identity assertion in
`test_status_pages_05b.py:527
test_airlines_page_imports_no_history_db_or_sqlite_but_does_import_poll_loop`
that pins `airlines_page`'s module attribute to the `poll_loop` module
object — a test this phase must retarget, not merely leave passing by
accident, once `airlines_page` switches to `state_store`.

### 5. Module-global setters

The three definitions (`grep -rn
"set_override_state_dir\|set_manual_registry_state_dir\|set_colour_rules_state_dir"
server companion stub-server --include=*.py`, non-test hits only):

| Setter | Defined at | Only production caller |
|---|---|---|
| `set_override_state_dir` | `server/plane/illustrations.py:551` | `server/poll_loop.py:945` |
| `set_manual_registry_state_dir` | `server/plane/manual_resolutions.py:374` | `server/poll_loop.py:946` |
| `set_colour_rules_state_dir` | `server/plane/colour_rules.py:301` | `server/poll_loop.py:950` |

No companion file calls any of the three. Test files with direct calls
(for retarget scope, not reproduced line-by-line here):
`server/test_poll_loop.py`, `server/test_enrich.py`,
`server/test_manual_resolutions.py`, `server/test_illustrations.py`,
`server/test_colour_rules.py`.

### 6. Duplicated device policy

Re-verified file:line for every row of the research §6 table:

| Logic | Copy 1 | Copy 2 | Identical? |
|---|---|---|---|
| `seconds_until_quiet_hours_end` | `server/device_config.py:620` | `stub-server/byos_server.py:386` | Yes, byte-for-byte (byos's own comment at :80-83 says so; a drift guard test pins it) |
| `_HHMM_RE` | `server/device_config.py:78` | `stub-server/byos_server.py:72` | Yes |
| `QUIET_HOURS_TZ` (`Europe/Paris`) | `server/device_config.py:82` | `stub-server/byos_server.py:76` | Yes |
| `DISPLAY_OFF_SLEEP_S` (300) | `server/device_config.py:59` | `stub-server/byos_server.py:88` | Yes |
| `BATTERY_CRITICAL_SLEEP_S` (3600) | `server/device_config.py:64` | `stub-server/byos_server.py:94` | Yes |
| `WAKE_INTERVAL_MIN_S`/`MAX_S` (60/3600) | `server/device_config.py:53-54` | `stub-server/byos_server.py:82-83` | Yes |
| `BATTERY_CRITICAL_RECOVER_MV` (3700) | `server/poll_loop.py:242` | `stub-server/byos_server.py:95` | Yes |
| battery-critical latch reader | `server/wake.py:49 read_battery_critical` | `stub-server/byos_server.py:336 read_battery_critical` | Yes (fail-open, `is True`) |
| discharge curve + percent estimate | `server/poll_loop.py:359-405 _NOTIFY_BATTERY_DISCHARGE_CURVE`/`_battery_percent_estimate` | `companion/battery.py:19-77 BATTERY_DISCHARGE_CURVE`/`battery_fraction` | Yes (same 14-knot table, same guards) |
| **Quiet-hours invalid-time fallback** | `server/device_config.py:434 normalise_quiet_hours_time` (called from `:656 quiet_hours_status`) | `stub-server/byos_server.py:422 read_quiet_hours` | **NO — different.** With `quiet_hours_enabled: true` and an invalid stored `quiet_hours_start`/`end`, the server substitutes the defaults `23:00`/`07:00` (`DEFAULT_QUIET_HOURS_START`/`END`, `device_config.py:42-43`) and a hold is drawn; byos's `read_quiet_hours` returns `None` outright on the same invalid input, so quiet hours are treated as off (no sleep extension). Developer decision D-4 (39-CONTEXT.md): unify onto the server's fallback (23:00-07:00 + hold); byos adopts it. This is the one deliberate, intentional behaviour change of this phase — the reachable (valid-config) behaviour is unchanged. |

### 7. Suite

`./scripts/run-all-tests.sh` (local venv, Python 3.11.15):

```
2915 passed, 139 skipped, 57 warnings in 79.74s (0:01:19)
```

139 skips are the Chromium-dependent browser tests (not installed in this
container; CI installs Chromium and runs them) plus one root-euid skip.
2915 = the research's own baseline of 2901 plus the 14 new detector tests
this plan's Task 1 added (`test-support/test_check_function_size.py`).

Coverage (`--cov --cov-report=term-missing:skip-covered`):

```
TOTAL   10569    627    94%
Required test coverage of 93.0% reached. Total coverage: 94.07%
```

Identical to the research's own cross-check figure (94.07%), since no
production file changed between research and this baseline.

`server/.venv/bin/ruff check .`: **All checks passed!**

`server/.venv/bin/python scripts/check_comment_history.py check`: no
output, exit 0 (clean).

## After

Recorded by the final plan of this phase with the same commands.
