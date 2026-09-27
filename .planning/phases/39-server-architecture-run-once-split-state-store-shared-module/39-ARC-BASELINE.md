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

Recorded 2026-09-27 (same day as Before), by this phase's closing plan,
against commit `9a1f444` (this plan's own Task 1 commit — the size gate
made permanent in CI and `server/poll_cycle.py` added to the mypy file
list — the last production-adjacent change before this record), with the
exact same commands listed under Measurement setup above. Python and
platform unchanged from Before (`server/.venv/bin/python` 3.11.15,
`Linux-6.18.44-fc-v37-x86_64-with-glibc2.39`).

### 1. Function size

`python3 scripts/check_function_size.py report --top 15 server stub-server`:

| Code lines | Location | Function |
|---|---|---|
| 77 | server/plane/detect.py:717 | `poll_current_aircraft` |
| 66 | server/plane/render/text.py:441 | `draw_previous_text_block` |
| 65 | server/plane/calendar_rules/__init__.py:177 | `fetch_ics` |
| 62 | server/plane/calendar_rules/ics.py:182 | `parse_ics_events` |
| 59 | server/history_db.py:612 | `tail_caddy_battery_log` |
| 59 | server/plane/calendar_rules/match.py:93 | `match_calendar_theme` |
| 57 | server/poll_cycle.py:890 | `run_hold_cycle` |
| 54 | stub-server/byos_server.py:709 | `Handler.do_GET` |
| 51 | server/plane/detect.py:387 | `filter_in_geofence` |
| 49 | server/plane/detect.py:897 | `build_parser` |
| 49 | server/plane/render/cli.py:70 | `_add_route_shaping_arguments` |
| 48 | server/plane/render/text.py:338 | `_draw_main_block_band` |
| 47 | server/plane/colour_rules.py:148 | `load_colour_rules` |
| 47 | server/plane/render/layout.py:334 | `_build_active_canvas` |
| 47 | stub-server/byos_server.py:796 | `main` |

`python3 scripts/check_function_size.py check --max 80 server stub-server`:

```
401 functions scanned, none over 80
```

**Zero offenders** — all six Before offenders are gone: `poll_loop.py`'s
`_run_once_locked` (335 lines) was split into `poll_cycle.py`'s named
steps (39-10/39-11); `render.py`'s `build_parser` (98) and `main` (84)
were split in the render-package plan (39-08); `device_config.py`'s
`save_device_config` (87) was split in 39-05; `http_fetch.py`'s
`pinned_request` (85) was split in 39-04. The scanned function count grew
from 365 to **401** (+36) — the size-gate splits and the ARC-03 package
carve-ups (`render/`, `calendar_rules/`) each add small named helpers in
place of one large one; `check --max 400` is no longer needed as a
sanity check, since `--max 80` itself now reports zero offenders directly.

### 2. Cyclomatic complexity

`uv run --no-project --with radon==6.0.1 radon cc -s server/poll_cycle.py`
(the module `poll_loop.py`'s cycle body became), the named steps and
`run_once` itself:

```
F 890:0 run_hold_cycle - B (6)
F 1093:0 advance_display_queue - B (10)
F 1052:0 load_display_slots - A (5)
F 856:0 decide_hold - A (4)
F 1376:0 render_and_publish - A (4)
F 779:0 load_cycle_context - A (2)
F 871:0 publish_canvas - A (2)
F 992:0 update_battery_low - A (2)
F 1008:0 detect_flight - A (2)
F 1391:0 record - A (3)
F 1424:0 persist - A (2)
F 1462:0 log_cycle - B (9)
F 1499:0 cycle_result - A (1)
F 1520:0 run_once - A (3)
```

`run_once` (the lock/entry wrapper, dispatching to `run_hold_cycle` or the
eight live steps) = **CC 3** (up from Before's 2, one extra branch for the
hold/live dispatch that `_run_once_locked` used to make inline); the
highest CC among `run_once` and every one of its own named steps is
**`advance_display_queue` at CC 10** (grade B — the pacing/queue-eviction
logic `_run_once_locked` used to inline). Both numbers are far below
Before's **`_run_once_locked` = CC 53** (grade F) — an 81% drop from the
worst single function to the worst single step. `_record_history` (a
pre-existing accessory helper this phase's split calls but did not touch)
remains the module's own ceiling at CC 12, matching 39-11's own
handoff note and still nowhere near Before's 53.

Five highest-CC **non-test** functions in `server/` from
`uv run --no-project --with radon==6.0.1 radon cc -s -n C server`:

| Rank | CC | Grade | Location | Function |
|---|---|---|---|---|
| 1 | 30 | D | server/plane/calendar_rules/match.py:93 | `match_calendar_theme` |
| 2 | 27 | D | server/plane/calendar_rules/ics.py:182 | `parse_ics_events` |
| 3 | 25 | D | server/plane/detect.py:717 | `poll_current_aircraft` |
| 4 | 20 | C | server/plane/colour_rules.py:325 | `resolve_effective_theme_id` |
| 5 | 18 | C | server/plane/calendar_rules/__init__.py:177 | `fetch_ics` |

None of these five is a poll-cycle function — ARC-03 relocated
`calendar_rules.py`/`match_calendar_theme`/`parse_ics_events` into their
own package without reducing their complexity (out of this phase's own
scope), and `poll_current_aircraft`/`resolve_effective_theme_id` predate
this phase entirely. Every one of the five is still well under Before's
own #1 (`_run_once_locked`, CC 53).

### 3. Typed functions

Same inline command as Before, over `server`:

```
73 of 356 non-test server functions have any annotation
```

Before: **0 of 318**. The scanned total grew by 38 (356 vs 318) for the
same reason function-count grew in §1 — package splits add small named
functions. 73 are now annotated: the six modules typed at birth
(`device_policy`, `state_store`, `themes`, `net/safe_fetch`,
`calendar_rules/{ics,match}`), the five modules 39-12 annotated end to end
(`wake`, `panel_format`, `atomic_io`, `runway_config`, `colour_rules`),
and `poll_cycle.py`'s typed pure core (`decide_hold`, `advance_is_due`,
`normalise_pending`, `enqueue_pending`, `pop_fresh_pending`,
`CycleContext`).

`server/.venv/bin/mypy` (this plan's Task 1, `server/poll_cycle.py` added
to `[tool.mypy] files`):

```
Success: no issues found in 12 source files
```

Before: mypy was not yet a dependency (0 files). 12 = the 11 files 39-12
established plus `poll_cycle.py` this plan.

### 4. Companion imports of server.poll_loop

`grep -rn "poll_loop" companion --include=*.py | grep -v "/test_"`
(non-test files):

| File | Mention |
|---|---|
| `companion/wake.py` | comment only ("the real arithmetic lives in server/wake.py so server/poll_loop.py can...") |
| `companion/app.py` | two comments (the sys.path bootstrap note, a print-prefix note) |
| `companion/pages/history_page.py` | comment only (`_save_to_gallery()` naming convention) |
| `companion/pages/config_page.py` | comment only (cooldown/`run_once()` naming) |

**Zero statement-level imports** — confirmed with a repo-wide
`grep -rn "import server.poll_loop\|from server import poll_loop\|from server\.poll_loop" companion`,
no matches. Every one of Before's four real call sites
(`companion/app.py`, `companion/pages/health_page.py`,
`companion/pages/airlines_page.py`) now imports `server.state_store`
and/or `server.poll_cycle` instead (39-07, 39-10). The same grep
restricted to test files still finds prose/monkeypatch-target mentions in
`test_request_connections.py`, `test_freshness_token.py` (×2),
`test_companion_app_05.py`, `test_companion_app_helpers.py` and
`test_browser_ux_03.py` — none a statement-level import either.
`test_status_pages_05b.py`'s Before-era identity assertion pinning
`airlines_page`'s module attribute to `poll_loop` was retargeted to
`state_store` in 39-07, as Before's own record anticipated.

### 5. Module-global setters

`grep -rn "set_override_state_dir\|set_manual_registry_state_dir\|set_colour_rules_state_dir" server companion stub-server --include=*.py`:

```
server/test_manual_resolutions.py:355:    for name in ("set_manual_registry_state_dir", "_cached_registry"):
server/test_illustrations.py:766:    for name in ("set_override_state_dir", "_override_state_dir"):
server/test_colour_rules.py:470:    for name in ("set_colour_rules_state_dir", "_cached_rules"):
```

All three setters are **deleted outright** (39-02/39-03), not merely
uncalled by the companion as Before recorded — every remaining mention is
inside a `test_no_setter_or_module_global_remains()` drift guard in the
three modules that used to define them, asserting `not hasattr(module,
name)`. `server/poll_loop.py`'s three former call sites are gone along
with the rest of the cycle body it moved to `poll_cycle.py`, which itself
never calls any of the three — every state dir a cycle needs is now
passed explicitly (ARC-04).

### 6. Duplicated device policy

Re-verified file:line for every row of the Before table, now that every
one of the first nine rows is a single definition in
`server/device_policy.py` (`server/state_store.py` for the battery-critical
latch reader), with byos and the companion each an identity rebind/
re-export rather than a second copy:

| Logic | Single definition | byos rebind | Companion rebind/re-export |
|---|---|---|---|
| `seconds_until_quiet_hours_end` | `server/device_policy.py:205` | `byos_server.py:375` (`= device_policy.seconds_until_quiet_hours_end`) | n/a |
| `HHMM_RE` | `server/device_policy.py` (module-level) | `byos_server.py:87` (`_HHMM_RE = device_policy.HHMM_RE`) | n/a |
| `QUIET_HOURS_TZ` | `server/device_policy.py:189` | `byos_server.py:88` | n/a |
| `DISPLAY_OFF_SLEEP_S` | `server/device_policy.py:173` | `byos_server.py:91` | n/a |
| `BATTERY_CRITICAL_SLEEP_S` | `server/device_policy.py:177` | `byos_server.py:92` | n/a |
| `WAKE_INTERVAL_MIN_S`/`MAX_S` | `server/device_policy.py:168-169` | `byos_server.py:89-90` | n/a |
| `BATTERY_CRITICAL_RECOVER_MV` | `server/device_policy.py:39` | `byos_server.py:93` | n/a |
| battery-critical latch reader | `server/state_store.py:123 read_battery_critical` | `byos_server.py:344` (`read_battery_critical = state_store.read_battery_critical`) | n/a |
| discharge curve + percent estimate | `server/device_policy.py:96 BATTERY_DISCHARGE_CURVE`/`:119 battery_fraction`/`:149 battery_percent` | n/a (byos never showed the companion's own life-estimate chart) | `companion/battery.py:16-18` (`from server.device_policy import BATTERY_DISCHARGE_CURVE, ..., battery_fraction, battery_percent  # noqa: F401`) |
| **Quiet-hours invalid-time fallback** | `server/device_policy.py:240 quiet_hours_window` (called from `device_config.quiet_hours_status` and `byos_server.py:400 read_quiet_hours`) | same function, both sides | n/a |

The tenth row — the one Before flagged as **"NO — different"** — is now
**unified (D-4)**: both `device_config.quiet_hours_status()` and byos's
`read_quiet_hours()` resolve an invalid stored time through the same
`device_policy.quiet_hours_window()`, falling back to the default
23:00–07:00 window (and a hold/sleep-extension) on both sides.
`server/test_device_policy.py:150
test_quiet_hours_invalid_stored_time_falls_back_to_default_window` and
`stub-server/test_poll_cycle.py:346
test_read_quiet_hours_invalid_time_falls_back_to_default_window` each pin
the merged behaviour on their own side.

### 7. Suite

`./scripts/run-all-tests.sh`:

```
2995 passed, 139 skipped, 57 warnings in 81.99s (0:01:21)
```

Same 139 pre-existing skips as Before (Chromium-dependent browser tests
plus one root-euid skip — this container). 2995 = Before's 2915 plus 80
new tests across every plan in this phase (poll-cycle step/spy tests,
render/calendar package surface tests, mypy-annotation tests, the D-4/D-5
pinning tests above, this plan's own tree-wide size-gate test, etc.).

Coverage:

```
TOTAL                                     10751    616    94%
29 files skipped due to complete coverage.
Required test coverage of 93.0% reached. Total coverage: 94.27%
```

Up from Before's 94.07% — every split module kept its own tests, and
`poll_cycle.py`'s new step-ordering spy tests added coverage no
`_run_once_locked` monolith test could isolate.

`server/.venv/bin/ruff check .`: **All checks passed!**

`server/.venv/bin/python scripts/check_comment_history.py check`: no
output, exit 0 (clean).

## Criteria

| # | ROADMAP criterion | Evidence command | Verdict |
|---|---|---|---|
| 1 | No function in `server/` over 80 code lines; `run_once` CC measured before/after | `check --max 80 server stub-server` → `401 functions scanned, none over 80`; `radon cc -s server/poll_cycle.py` → `run_once` A(3), highest named step `advance_display_queue` B(10), vs Before's `_run_once_locked` F(53) | **Met** |
| 2 | `server/state_store.py` owns `poll_state.json`; the companion never imports `server.poll_loop` | `state_store.py` holds `load_poll_state`/`save_poll_state`/`serialize_poll_state`/`persist_poll_state_if_changed`/`poll_state_path`/`DEFAULT_STATE_DIR`; `grep -rn "import server.poll_loop\|from server import poll_loop\|from server\.poll_loop" companion` → no matches | **Met** |
| 3 | `render.py`/`calendar_rules.py` split into packages, theme logic in `themes.py`, one shared `net/safe_fetch.py` | `server/plane/render/{__init__,style,text,glyphs,hold_screens,layout,cli}.py`; `server/plane/calendar_rules/{__init__,ics,registry,match}.py`; `server/themes.py`; `server/net/safe_fetch.py` (`notify.py` imports it directly — `grep -n "calendar_rules" server/notify.py` returns nothing) | **Met** |
| 4 | No module-global setters; type hints on the pure core; mypy in CI | `grep -rn "set_override_state_dir\|set_manual_registry_state_dir\|set_colour_rules_state_dir" server companion stub-server` → only drift-guard test mentions, no definitions; `server/.venv/bin/mypy` → `Success: no issues found in 12 source files`; `.github/workflows/ci.yml` carries the blocking "Type check" step plus this plan's own "Function size gate" step | **Met** |

## Intentional behaviour changes

The only two behaviour changes this phase made — everything else is
*where* code lives, not *what* it does — both developer-approved in
`39-CONTEXT.md`, both already shipped earlier in this phase and repeated
here for the closing record:

- **D-4 — unified quiet-hours invalid-time fallback.** With
  `quiet_hours_enabled: true` and an invalid stored start/end time, the
  server used to fall back to 23:00–07:00 and hold the display; byos used
  to treat quiet hours as disabled outright. Both sides now resolve
  through the same `device_policy.quiet_hours_window()` and fall back to
  the server's own 23:00–07:00 + hold behaviour. The *reachable*
  (valid-config) behaviour is unchanged on both sides — only the
  invalid-config edge case moved. Pinned by
  `server/test_device_policy.py::test_quiet_hours_invalid_stored_time_falls_back_to_default_window`
  and
  `stub-server/test_poll_cycle.py::test_read_quiet_hours_invalid_time_falls_back_to_default_window`
  (39-02/39-06).
- **D-5 — vendored-only theme preview.** Deleting
  `illustrations.set_override_state_dir`/`_override_state_dir` (ARC-04)
  means `companion/theme_preview.py`'s bare `select_illustration()` call
  (it never passes a `state_dir`) can no longer inherit an in-process
  `/poll-now`'s last-used override directory — it now always sees the
  vendored/on-disk illustration set only, matching the fresh-process
  behaviour it already had before any poll ran. No companion file was
  edited for this; it is a pure consequence of the setter's removal.
  Pinned by
  `server/test_illustrations.py::test_select_illustration_state_dir_override_vs_no_state_dir`
  (39-03).
