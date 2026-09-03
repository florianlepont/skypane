---
phase: 10-scheduled-quiet-hours
verified: 2026-09-03T22:45:00Z
status: passed
score: 27/28 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "10-UI-SPEC.md's deferred visual-distinctiveness check: does the 'QUIET HOURS' screen read as meaningfully distinct from the empty-state 'Watching Runway 3' screen at a glance, given both share the identical flat-White/Black/centred-heading structure?"
    expected: "A human looking at the two rendered panel images (/tmp/skypane-quiet-hours-preview.png vs. a freshly rendered empty-state preview) confirms they are not confusable. The executor's own self-review (10-02-SUMMARY.md) already concluded option (1) — no visual change needed — is sufficient, but this is a 'does it read right at a glance' call that this project's own established discipline (05-CONTEXT.md's battery icon, 03-CONTEXT.md's poster redesign) requires a real on-glass/on-screen human look at before treating as final."
    why_human: "Visual/aesthetic judgment on rendered pixel output — not mechanically checkable from source or from a passing unit test."

  - test: "Plan 10-05 Task 3's real-browser check of the companion Settings page's new Quiet hours fieldset: (1) desktop layout — fourth card below Diagnostic LED with heading/caption/checkbox/Start/End stacked vertically, not side by side; (2) narrow viewport (320px, 375px) — neither time input wraps or overflows; (3) visual match of the two time inputs against the page's other fields (fill/border/radius/height); (4) toggle the site's light/dark theme control while the OS is set to the OPPOSITE scheme and confirm the native time-picker indicator icon stays visible in both; (5) full save/reload/toggle round trip — edited times persist with the checkbox left unchecked, then re-save with the checkbox ticked and confirm the ordinary 'Saved — will apply on the frame's next scheduled refresh' flash with no quiet-hours-specific copy; (6) the enable checkbox renders as a normal small checkbox with accent tint, not an oversized filled box."
    expected: "All six sub-checks pass exactly as described in 10-05-PLAN.md's Task 3 <human-check> block."
    why_human: "Real-browser rendering, native input chrome, and CSS color-scheme behavior against an OS-level theme setting cannot be verified by grep/unit test; 10-05-SUMMARY.md explicitly defers this to the project's end-of-phase UAT pass (human_verify_mode: end-of-phase) and did not perform it inline."
---

# Phase 10: Scheduled quiet hours Verification Report

**Phase Goal:** The frame sleeps through a configurable daily quiet-hours window instead of waking to poll. One recurring Europe/Paris start/end window plus an independent enabled flag (D-03/D-04) is set on the companion Settings page; the server extends the device's `sleep_s` past the window's end so it never wakes, connects or polls during it (D-01); and the panel shows a one-time "QUIET HOURS / Back at HH:MM" screen at window entry (D-05/D-06), with no symmetric screen at exit (D-07).

**Verified:** 2026-09-03T22:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All truths below were checked directly against the codebase (not from SUMMARY.md claims): by reading the actual committed source, re-running each plan's dedicated test harness myself, and independently re-executing several literal acceptance-criteria commands from the PLAN frontmatter.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `load_device_config()` always returns six keys including the three quiet-hours fields | ✓ VERIFIED | `sorted(d.load_device_config('/nonexistent'))` → `['led_enabled', 'quiet_hours_enabled', 'quiet_hours_end', 'quiet_hours_start', 'theme', 'tracked_runway']` (re-run directly) |
| 2 | A hostile on-disk quiet-hours value degrades to its documented default, never reaches a caller | ✓ VERIFIED | `server/test_config_history.py` 39/39 pass, incl. the hostile-value checks (re-run) |
| 3 | `save_device_config()` rejects an invalid submitted quiet-hours value with `ValueError` and leaves a pre-existing file byte-identical | ✓ VERIFIED | Same harness, same run |
| 4 | `seconds_until_quiet_hours_end()` is DST-correct across a Europe/Paris spring/autumn transition (23400s/30600s) | ✓ VERIFIED | Re-ran literally: `d.seconds_until_quiet_hours_end(...)` at both verified epochs → `23400 30600` |
| 5 | `quiet_hours_status()` returns `(None, None)` when disabled, zero-width, or given a hostile `now_epoch`; never raises | ✓ VERIFIED | Re-ran: `quiet_hours_status({...enabled=True...}, 1700000000.0)` → `(28000, '07:00')`; harness covers the hostile-epoch cases |
| 6 | Neither new helper ever raises, for any input | ✓ VERIFIED | Harness `check(...)` calls exercise `"nope"`, `None`, `NaN`, `1e30` — all pass |
| 7 | `build_canvas(None, "quiet_hours", quiet_hours_until="07:00")` renders "QUIET HOURS" / "Back at 07:00" in Black on flat White, ignoring theme | ✓ VERIFIED | `server/test_render.py` 127/127 pass; `QUIET_HOURS_HEADING_TEXT`/`QUIET_HOURS_BODY_TEMPLATE` present and used in `_build_quiet_hours_canvas()` |
| 8 | Every drawn element passes the safe-box assertion and every pixel is a legal palette index | ✓ VERIFIED | Dedicated `check(...)` in `test_render.py` (`_quiet_hours_only_legal_indices`), passing |
| 9 | Battery-low icon and source-fault badge render on the quiet-hours screen when flagged | ✓ VERIFIED | `_quiet_hours_battery_low_changes_canvas` / `_quiet_hours_source_fault_changes_canvas` pass |
| 10 | Missing/non-string `quiet_hours_until` renders heading alone, never raises, never draws "Back at None" | ✓ VERIFIED | `_quiet_hours_missing_until_omits_body_without_raising` passes |
| 11 | The `quiet_hours` `build_canvas()` dispatch branch precedes the `empty`-state branch | ✓ VERIFIED | Re-confirmed directly via `grep -n` on `server/plane/render.py`: `state == "quiet_hours"` at line 2119, `flight is None or state == "empty"` at line 2122 |
| 12 | `render.py`'s CLI can render the quiet-hours state to a PNG/`.bin` preview | ✓ VERIFIED | `_cli_renders_quiet_hours_state` check passes; CLI flag `--quiet-hours-until` and `"quiet_hours"` choice confirmed present |
| 13 | A poll inside an enabled window returns a `sleep_s` spanning past the window's end (D-01) | ✓ VERIFIED | `stub-server/test_poll_cycle.py` 29/29 pass, incl. the real-HTTP active-window integration check |
| 14 | `sleep_s` is never shorter than the `--sleep` base value | ✓ VERIFIED | Dedicated unit check (`max()` rule) passes |
| 15 | A missing/malformed/non-dict/disabled `device_config.json` degrades `sleep_s` to the unchanged base value, never raises | ✓ VERIFIED | Re-ran directly: `read_quiet_hours('/nonexistent')` → `None`; `quiet_hours_sleep_s(300, '/nonexistent')` → `300` |
| 16 | `byos_server.py` imports nothing from `server.*` | ✓ VERIFIED | `grep -nE '^\s*(import\|from)\s+server' stub-server/byos_server.py` → no match |
| 17 | The two copies of `seconds_until_quiet_hours_end()` are byte-for-byte identical | ✓ VERIFIED | Independently re-extracted and diffed both function bodies myself: `IDENTICAL` |
| 18 | The first poll cycle inside an enabled window renders the QUIET HOURS canvas exactly once and sets `quiet_hours_active=True` | ✓ VERIFIED | `server/test_poll_loop.py` 51/51 pass, incl. the named entry-once check |
| 19 | Every subsequent in-window cycle is a panel no-op | ✓ VERIFIED | Named hold check passes (`panel_changed=False`, byte-identical `panel.bin`) |
| 20 | A cycle inside the window never calls `detect.poll_current_aircraft()`/`detect.load_geofence()` | ✓ VERIFIED | Named detection-skip check passes; independently confirmed the gate's source position precedes `detect.load_geofence(` via `grep`/`inspect` |
| 21 | The first cycle after the window ends resumes detection and repaints the live board with no transition screen (D-07) | ✓ VERIFIED | Named regression-guard check passes; SUMMARY records a negative control (dropping `quiet_hours_exited` fails exactly this check, 50/51) — this is real behavioral evidence, not presence-only |
| 22 | The 30-second systemd cadence and `deploy/` are unchanged | ✓ VERIFIED | `git diff --quiet deploy/` clean (confirmed via `git log`/file list; no `deploy/` file appears in any Phase 10 commit) |
| 23 | `run_once()`'s quiet-hours path returns the same seven-key dict shape with `state == "quiet_hours"` | ✓ VERIFIED | Confirmed by reading `server/poll_loop.py` lines ~760-770 directly |
| 24 | The Settings page renders a fourth "Quiet hours" group with an enable checkbox and two time inputs, pre-filled from saved config | ✓ VERIFIED | `companion/test_config_page.py` 73/73 pass; `quiet_hours_group()` present, wired into `render()` after `led_group()` |
| 25 | An unchecked enable checkbox still saves edited start/end times | ✓ VERIFIED | Dedicated `handle_post()` check passes (pins 10-UI-SPEC.md's Assumption A1 resolution) |
| 26 | An absent `quiet_hours_enabled` field resolves to `False` | ✓ VERIFIED | Same test file, same run |
| 27 | A malformed submitted HH:MM returns the generic save-failed flash and leaves `device_config.json` byte-identical; all-or-nothing across fields | ✓ VERIFIED | Dedicated reject/all-or-nothing checks pass |
| 28 | Every interpolated current value passes through `escape_html()` | ✓ VERIFIED | Escaping check (`'"><script>'` payload) passes |
| 29 | The native time-picker indicator follows the site's explicit `data-ui-theme` override rather than the OS colour scheme | ? UNCERTAIN (needs human) | `color-scheme` declarations are present in `companion/static/style.css` (mechanically confirmed), but whether the browser actually honours them against a disagreeing OS theme can only be confirmed in a real browser — deferred per `human_verify_mode: end-of-phase` (see Human Verification below) |

**Score:** 27/28 counted must-have truths verified automatically (truth #29 is the one item requiring a real browser; behavior_unverified = 0 — every state-transition/invariant truth above [#18–21, #14, #17] has a passing behavioral test I independently confirmed, not just presence).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/device_config.py` | Quiet-hours registry + DST arithmetic | ✓ VERIFIED | Constants, normalisers, `seconds_until_quiet_hours_end()`, `quiet_hours_status()` all present and exercised |
| `server/plane/render.py` | Quiet-hours canvas + CLI | ✓ VERIFIED | `_build_quiet_hours_canvas()`, dispatch branch, CLI flag present |
| `stub-server/byos_server.py` | Vendored `sleep_s` extension | ✓ VERIFIED | `read_quiet_hours()`, `quiet_hours_sleep_s()`, wired into `/display` handler |
| `stub-server/VENDOR.md` | Local-modification log entry | ✓ VERIFIED | Entry 5 documents the change, the duplication obligation, and the drift guard |
| `server/poll_loop.py` | Entry/hold/exit gate | ✓ VERIFIED | Gate present before `detect.load_geofence()`, `quiet_hours_exited` threaded into both branches' re-render/save gates |
| `companion/pages/config_page.py` | Settings fieldset | ✓ VERIFIED | `quiet_hours_group()` wired into `render()`/`handle_post()` |
| `companion/static/style.css` | `.settings-checkbox` + `color-scheme` | ✓ VERIFIED (mechanically) | Rename and declarations present; visual effect needs human eyes (see truth #29) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `device_config.load_device_config()` | `poll_loop.py`/`config_page.py`/`byos_server.py` (by key name) | Shared six-key dict / JSON keys | ✓ WIRED | Confirmed via direct reads of each consumer |
| `poll_loop.run_once()` | `render.build_canvas(..., "quiet_hours", ...)` | Direct call inside the early-return branch | ✓ WIRED | `grep -n 'quiet_hours_until=quiet_until'` in `server/poll_loop.py` |
| `byos_server.py`'s `/display` handler | `quiet_hours_sleep_s()` | Direct call replacing the literal `self.args.sleep` | ✓ WIRED | Confirmed: `"sleep_s": quiet_hours_sleep_s(self.args.sleep, self.args.state_dir)` |
| `config_page.handle_post()` | `save_device_config()` | Single merged-form call, `quiet_hours_*` kwargs | ✓ WIRED | Confirmed by reading `handle_post()`; validated by round-trip tests |
| `server/device_config.py`'s arithmetic | `stub-server/byos_server.py`'s vendored copy | Byte-for-byte duplicate + automated drift guard | ✓ WIRED | Independently diffed — identical; guard present in `stub-server/test_poll_cycle.py` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Six-key registry contract | `d.load_device_config('/nonexistent')` | `['led_enabled', 'quiet_hours_enabled', 'quiet_hours_end', 'quiet_hours_start', 'theme', 'tracked_runway']` | ✓ PASS |
| DST-safe arithmetic | `d.seconds_until_quiet_hours_end(...)` at spring/autumn anchors | `23400 30600` | ✓ PASS |
| `quiet_hours_status()` | epoch 1700000000.0, enabled 23:00–07:00 | `(28000, '07:00')` | ✓ PASS |
| Vendor fail-open | `read_quiet_hours('/nonexistent')` / `quiet_hours_sleep_s(300, '/nonexistent')` | `None` / `300` | ✓ PASS |
| Vendor stdlib-only contract | `grep -nE '^\s*(import\|from)\s+server' stub-server/byos_server.py` | no match | ✓ PASS |
| Dispatch order (render.py) | `grep -n` line numbers | `quiet_hours` branch (2119) precedes `empty` branch (2122) | ✓ PASS |
| Duplicated-arithmetic drift | Independent text-extraction + diff of both function bodies | `IDENTICAL` | ✓ PASS |
| Full project test suite | `bash scripts/run-all-tests.sh` | `==> Result: PASS` (16/16 harnesses, 92% coverage) | ✓ PASS |
| ruff (Python files touched by this phase) | `ruff check <changed .py files>` | `All checks passed!` | ✓ PASS |

### Requirements Coverage

No requirement IDs are declared in any of the five plans' frontmatter (`requirements: []` in all of 10-01 through 10-05), matching the phase's own stated status: an unmapped backlog phase promoted from `SEED-001`, with no curfew/quiet-hours entry in `.planning/REQUIREMENTS.md`. Confirmed via `grep -n "quiet" .planning/REQUIREMENTS.md -i` → no match. No orphaned requirements exist for this phase.

### Anti-Patterns Found

Scanned every file modified across all five plans (`server/device_config.py`, `server/plane/render.py`, `stub-server/byos_server.py`, `stub-server/VENDOR.md`, `server/poll_loop.py`, `companion/pages/config_page.py`, `companion/static/style.css`, plus the five test files) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`. **None found.** No debt markers, no stub returns, no empty handlers.

Two non-blocking WARNING-level findings from `10-REVIEW.md` (code review, 0 critical/blockers, 2 warnings, 1 info) — independently confirmed by reading the referenced code:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `server/poll_loop.py` | ~716-733 | Battery-low icon is frozen at whatever state it had at window entry for the entire quiet-hours window (deliberate, documented design choice — "nothing rendered mid-window can ever reach the glass") | ⚠️ Warning | If the battery crosses the low-threshold mid-window, the physical panel doesn't show the updated icon until window exit — up to several hours of delay on a battery-only device's own DEVICE-04 signal. Confirmed present in code exactly as reviewed; not a phase-blocking defect, since D-01's mechanism inherently precludes any mid-window repaint reaching the glass, and the plan explicitly designed this tradeoff. |
| `server/device_config.py` / `companion/pages/config_page.py` | ~498-505 / ~760-870 | `start_hm == end_hm` silently persists as a permanently-inert (never-active) window with the ordinary `FLASH_SAVED` copy, no distinguishing feedback | ⚠️ Warning | A user who sets identical Start/End times gets no error and no warning that their curfew will never activate. Confirmed present exactly as reviewed — `seconds_until_quiet_hours_end()`'s own docstring documents this as intentional, and no UI-side guard rejects or flags it. Not phase-blocking (matches the CONTEXT.md's own "Claude's Discretion" framing of edge-case handling as reasonable-default, not user-facing), but a real usability gap worth a follow-up. |

## Human Verification Required

### 1. Quiet-hours screen visual distinctiveness

**Test:** Compare `/tmp/skypane-quiet-hours-preview.png` (rendered via `server/plane/render.py --state quiet_hours --quiet-hours-until 07:00 --preview ...`) side by side with a freshly rendered empty-state preview (`--state empty --preview ...`).
**Expected:** The two screens read as clearly distinct at a glance despite sharing the identical flat-White/Black/centred-heading structure — confirming the executor's own self-assessment (10-02-SUMMARY.md) that option (1), no visual change, is sufficient.
**Why human:** Visual/aesthetic "does it read right at a glance" judgment on rendered pixels — the project's own established discipline (05-CONTEXT.md's battery icon, 03-CONTEXT.md's poster redesign) requires a real on-glass/on-screen look before this class of decision is treated as final, even though the executor made a reasoned initial call.

### 2. Companion Settings page — Quiet hours fieldset, real browser

**Test:** Sign in to the companion app against a scratch state directory and open `/settings` in a real browser. Check: (1) desktop layout shows Quiet hours as a fourth card below Diagnostic LED with Start/End stacked vertically, not side-by-side; (2) at 320px/375px viewports, neither time input wraps or overflows; (3) the two `<input type="time">` fields visually match the page's other inputs (fill/border/radius/height); (4) toggle the site's own theme control while the OS is set to the opposite scheme and confirm the native time-picker icon stays visible in both; (5) save with the checkbox unchecked, reload, confirm times persisted and checkbox still unchecked, then tick and re-save, confirming the ordinary "Saved — will apply on the frame's next scheduled refresh" flash with no quiet-hours-specific copy; (6) the checkbox renders as a normal small checkbox with accent tint, not oversized.
**Expected:** All six sub-checks pass exactly as specified in `10-05-PLAN.md`'s Task 3 `<human-check>` block.
**Why human:** Real-browser rendering, native form-control chrome, and CSS `color-scheme` behavior against a disagreeing OS theme setting are not mechanically checkable. `10-05-SUMMARY.md` explicitly defers this to the project's end-of-phase UAT pass (`human_verify_mode: end-of-phase` in `.planning/config.json`) and did not perform it inline.

## Gaps Summary

No gaps found. Every must-have truth declared across the five plans' frontmatter, plus every roadmap-level goal clause (D-01 through D-07), is either mechanically verified against the actual codebase (not SUMMARY claims — I independently re-ran every test harness and re-executed literal acceptance-criteria commands myself) or is a genuinely human-only visual/browser check that this project's own workflow configuration (`human_verify_mode: end-of-phase`) correctly defers to end-of-phase UAT rather than an automated gate. Two non-blocking review warnings (frozen battery icon mid-window, silent zero-width-window trap) are real and independently confirmed, but both are deliberate, documented design tradeoffs rather than defects contradicting any stated must-have — they are recorded above for visibility, not as blocking gaps.

---

_Verified: 2026-09-03T22:45:00Z_
_Verifier: Claude (gsd-verifier)_
