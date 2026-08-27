---
phase: 05
slug: low-battery-indicator
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-27
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Covers this phase's second plan (the low-battery-indicator UI) — 05-01's battery-measurement plan has its own already-executed validation.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (server)** | `pytest` via `coverage run` — `scripts/run-all-tests.sh`'s canonical 9-harness list |
| **Framework (firmware, pure-logic only)** | Plain `cc -std=c11`, no framework — `firmware/tests/run_host_tests.sh`'s `run_suite()` pattern |
| **Config file** | `pyproject.toml` (server coverage, `fail_under=75`); `firmware/tests/run_host_tests.sh` (fixed script, no separate config) |
| **Quick run command (server)** | `server/.venv/bin/python3 -m pytest server/test_poll_loop.py server/test_render.py -x` |
| **Quick run command (firmware)** | `sh firmware/tests/run_host_tests.sh` |
| **Full suite command** | `scripts/run-all-tests.sh` (server) + `sh firmware/tests/run_host_tests.sh` (firmware) — run independently, never combined |
| **Estimated runtime** | ~30s server suite + ~5s firmware host tests |

---

## Sampling Rate

- **After every task commit:** the relevant quick-run command above for whichever side (server/firmware) that task touches
- **After every plan wave:** both full suite commands
- **Before `/gsd-verify-work`:** both full suites green, plus the one `checkpoint:human-verify` real-hardware ADC-vs-multimeter cross-check
- **Max feedback latency:** ~35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-02-01 | 02 | TBD | DEVICE-04 | T-05-02-01 | `battery_math_apply_divider()` converts a divider-reduced mV reading back to real battery mV | unit (firmware, host `cc`) | `sh firmware/tests/run_host_tests.sh` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | TBD | DEVICE-04 | T-05-02-02 | Real ADC reading matches a real multimeter reading within tolerance | manual (`checkpoint:human-verify`) | n/a — real hardware | n/a | ⬜ pending |
| 05-02-03 | 02 | TBD | DEVICE-04 | T-05-02-03 | `X-Battery-Mv` header validated (numeric, non-negative, sane upper bound) before persistence — malformed/hostile values rejected, never crash | unit (stub-server) | `pytest stub-server/test_poll_cycle.py -k battery -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | TBD | DEVICE-04 | T-05-02-04 | `apply_battery_hysteresis()` arms/holds/clears correctly across the 3500/3600 boundary, including the never-reported (`None`) case | unit (server) | `pytest server/test_poll_loop.py -k hysteresis -x` | ❌ W0 | ⬜ pending |
| 05-02-05 | 02 | TBD | DEVICE-04 | T-05-02-05 | `render.py` draws the icon only when `battery_low=True`, at 05-UI-SPEC.md's exact geometry/color, panel stays pixel-identical when `battery_low=False` | unit (server) | `pytest server/test_render.py -k battery -x` | ❌ W0 | ⬜ pending |

*Exact task IDs/wave assignments are placeholders — the planner finalizes these; this table's requirement→test mapping is the binding contract regardless of final task numbering.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `firmware/tests/test_battery_math.c` — new host-testable suite for the pure divider-ratio conversion, appended to `run_host_tests.sh`'s `run_suite()` call list
- [ ] New test cases appended to `server/test_poll_loop.py` (hysteresis), `server/test_render.py` (icon draw), `stub-server/test_poll_cycle.py` (header validation) — no new test *files* for these three, all already exist and are already wired into `scripts/run-all-tests.sh`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Real ADC reading on the physical device matches a real multimeter reading within a reasonable tolerance | DEVICE-04 | No automated command can validate real analog hardware against a real battery — same category as Phase 1's `hardware/BRINGUP-LOG.md` bring-up checks | Charge the pack to a known voltage, read it with a multimeter at the JST connector, compare against the device's own reported `X-Battery-Mv` telemetry (server log or `stub-server` stdout) for the same moment; repeat at a second, lower voltage to confirm the divider ratio holds across the range, not just at one point |
| GPIO1 is genuinely free/isolated on the real assembled board before soldering a divider to it | DEVICE-04 (prerequisite) | 05-RESEARCH.md's GPIO recommendation is derived from this project's own pin map plus an unofficial forum thread, not an official Seeed schematic for this exact board combination — a continuity/multimeter check is the only way to be certain before modifying hardware | With the board unpowered, use a multimeter in continuity mode between the candidate GPIO1 pad and every other claimed pin in `firmware/sdkconfig.ee02.defaults`/`hardware/BOM.md` to confirm no unexpected trace connection exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
