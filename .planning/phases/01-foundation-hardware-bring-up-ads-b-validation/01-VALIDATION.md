---
phase: 1
slug: foundation-hardware-bring-up-ads-b-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-04
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | flightportrait's own `tests/` directory — pure-C contract tests, compile with plain `cc`, no hardware or ESP-IDF toolchain required. Everything else in this phase is manual hardware-in-the-loop observation (no unit-test framework applies to physical validation). |
| **Config file** | none — greenfield repo, no existing project test infrastructure (see Wave 0) |
| **Quick run command** | `cc -o /tmp/test_backoff tests/test_backoff.c main/backoff.c && /tmp/test_backoff` (pattern from flightportrait's `tests/`; confirm exact vendored filenames when forking) |
| **Full suite command** | Manual: observe a full wake → poll → download → verify → display → deep-sleep cycle against the local stub server, repeated over multiple cycles |
| **Estimated runtime** | Unit test: <1s. Full hardware-in-loop cycle observation: minutes to hours per cycle (device-driven interval), days for the battery time-to-depletion criterion. |

---

## Sampling Rate

- **After every task commit:** Run the pure-C `backoff.c` unit test where applicable (fast, no hardware needed).
- **After every plan wave:** Full manual hardware-in-loop cycle observation — this phase is inherently manual/hardware-gated; most "tests" here are physical observations, not CI-automatable assertions.
- **Before `/gsd-verify-work`:** All 4 phase success criteria (repeatable full cycle, exponential backoff, ADS-B reception validated, measured mAh/cycle) confirmed via direct observation.
- **Max feedback latency:** N/A for hardware-in-loop steps (device-paced); <5s for the pure-C backoff unit test.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-TBD | 01 | 0 | DEVICE-03 | — | Backoff formula `min(2^n × 5min, 6h)` matches vendored `backoff.c` exactly | unit | `cc -o /tmp/test_backoff tests/test_backoff.c main/backoff.c && /tmp/test_backoff` | ❌ Wave 0 — must vendor/write | ⬜ pending |
| 01-TBD | 01 | 1+ | DEVICE-03 | — | Full wake→poll→download→verify→display→sleep cycle repeats without manual intervention | manual/hardware-in-loop | Observe N consecutive cycles against local stub server; log boot reason each wake | ❌ needs stub server + real hardware | ⬜ pending |
| 01-TBD | 01 | 1+ | DEVICE-03 | — | Exponential backoff (not fixed-interval retry) triggers when stub server unreachable | manual/hardware-in-loop | Stop stub server; observe sleep-interval growth across consecutive failed wakes via serial log | ❌ needs real hardware | ⬜ pending |
| 01-TBD | 01 | 1+ | DEVICE-05 | — | Real measured mAh/cycle from unattended time-to-depletion run | manual | Charge full, run unattended, log days-to-dead, compute mAh/cycle | ❌ needs real hardware + battery pack | ⬜ pending |
| 01-TBD | 01 | 0 | (validation, not a formal REQ) | — | ADS-B aggregator returns plausible near-ground position data for runway 3 | manual/scripted | `curl`/Python script against adsb.fi and airplanes.live during a known departure/arrival window | ❌ Wave 0 — throwaway script, no existing file | ⬜ pending |

*Exact Task IDs assigned by the planner; the rows above map phase requirements to their validation approach per RESEARCH.md's Validation Architecture section.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_backoff.c` (or equivalent vendored/adapted from flightportrait's `tests/`) — pure-C unit test confirming the backoff formula in isolation, no hardware or ESP-IDF needed
- [ ] `stub-server/byos_server.py` vendored from flightportrait's `examples/` and confirmed runnable (stdlib-only, zero install) — needed before any firmware can be tested
- [ ] `adsb-test/query_aggregator.py` — throwaway script querying adsb.fi / airplanes.live near Orly runway 3 — needed before the ADS-B validation criterion can be tested; runnable before any hardware ships
- [ ] ESP-IDF build environment confirmed working (Docker build succeeds against a minimal `app_main.c`) — needed before hardware arrives so build issues surface early

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full wake→poll→download→display→sleep cycle, repeatable | DEVICE-03 | Requires real ESP32-S3 hardware, real e-paper panel, and physical observation of the display — not automatable | Flash firmware, run stub server locally, observe N consecutive cycles via serial log + physical panel refresh |
| Exponential backoff on server unreachability | DEVICE-03 | Requires inducing a real failure (stopping the stub server) and observing real device sleep-interval growth over multiple wake cycles | Stop stub server, watch serial log backoff_n increment and sleep interval double (capped at 6h) across consecutive failed wakes |
| Time-to-depletion battery measurement | DEVICE-05 | Physical battery drain over real time cannot be simulated or automated | Charge pack fully, let device run unattended, log elapsed days until dead/low-battery, compute mAh ÷ days |
| ADS-B aggregator near-ground coverage at runway 3 | (validation, not a formal REQ) | Depends on real-world feeder coverage at this specific site and cannot be determined from documentation alone | Query adsb.fi and airplanes.live during a known runway-3 departure/arrival window; check for plausible low-altitude/ground-speed aircraft data |
| EE02 board profile pin/console correctness on real hardware | DEVICE-03 (indirect — driver bring-up) | `sdkconfig.ee02.defaults` is explicitly unverified on live hardware by flightportrait's own maintainers | First successful blit on real EE02 hardware IS the verification event |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (where automatable; hardware-in-loop tasks use manual verification instructions instead, per this phase's nature as a hardware spike)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify or an explicit manual-verification instruction
- [ ] Wave 0 covers all MISSING references (backoff unit test, stub server, ADS-B test script, ESP-IDF build env)
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s for the automatable backoff unit test; hardware-in-loop steps are device/real-time-paced by nature
- [ ] `nyquist_compliant: true` set in frontmatter once the planner's tasks satisfy the map above

**Approval:** pending
