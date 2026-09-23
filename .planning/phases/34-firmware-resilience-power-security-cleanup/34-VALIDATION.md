---
phase: 34
slug: firmware-resilience-power-security-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-23
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Plain C `assert()` host tests compiled with the system `cc` (`firmware/tests/`); byos checks follow the existing `stub-server/` harness, written as plain functions/asserts so they migrate trivially to Phase 32's pytest |
| **Config file** | none — `firmware/tests/run_host_tests.sh` is the runner |
| **Quick run command** | `sh firmware/tests/run_host_tests.sh` |
| **Full suite command** | `sh firmware/tests/run_host_tests.sh && ./firmware/build.sh && python3 stub-server/test_poll_cycle.py` (plus the FW-08 registry test file if separate) |
| **Estimated runtime** | ~1 s quick; full ~3–6 min (containerised ESP-IDF build) |

---

## Sampling Rate

- **After every task commit:** Run `sh firmware/tests/run_host_tests.sh`
- **After every plan wave:** Run the full suite command (host tests + containerised build + byos tests)
- **Before `/gsd:verify-work`:** Full suite green AND the single hardware-session plan signed off
- **Max feedback latency:** 5 s for the quick command

---

## Per-Task Verification Map

Filled from the plans' `<verify>` blocks; every task in plans 34-01..34-N carries an `<automated>` command except the tasks of the single hardware-session plan.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (see PLAN.md files) | | | FW-01..FW-15 | | | unit / build / integration / manual | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `firmware/tests/test_reset_reason.c` — FW-01 reset-reason classification
- [ ] `firmware/tests/test_wake_deadline.c` — FW-02 deadline boundary math
- [ ] `firmware/tests/test_validate.c` — FW-03/04/06/07 response validation (compiled twice: `CONFIG_SKYPANE_ALLOW_HTTP` off and on)
- [ ] `firmware/tests/test_sleep_decision.c` — FW-06 sleep decision
- [ ] battery averaging math in `firmware/tests/test_battery_math.c` — FW-11
- [ ] byos device-registry checks (registered+match, registered+mismatch, unregistered, token revocation) — FW-08
- [ ] `firmware/tests/run_host_tests.sh` gains a `run_suite` line per new file
- [ ] `.github/workflows/firmware.yml` runs `run_host_tests.sh` before the Docker build (NOT `ci.yml` — Phase 32 owns it)

---

## Manual-Only Verifications (the ONE hardware session)

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Panic / WDT / brownout reset → backoff sleep, not immediate poll | FW-01, FW-02 | Needs a real reset | Dev-only fault trigger build; capture serial log |
| Hung wake bounded by the global deadline | FW-02 | Real timers + radio | Dev-only hang trigger; time to deep sleep |
| Server-revoked token → 401 → token purge → re-enrol next wake, no reflash | FW-03, FW-08 | End-to-end device ↔ byos | Revoke token in byos state; watch two wakes |
| `sleep_s` > 86400 rejected with `step=json` | FW-04 | Real device parse path (also unit-tested) | Stub serving 86401 |
| Secret provisioned via serial into its own NVS partition; existing keys preserved | FW-08 | Real flash | Run provisioning script, confirm token/hash survive |
| No-change wake duration before/after (DHCP, TLS reuse, memtest) + ~28 s overhead explained | FW-09, FW-10, FW-12 | Wall-clock on real radio/VPS | Timed runs, LAN stub and VPS |
| Battery reading vs multimeter, before Wi-Fi, 8 samples | FW-11 | Analog hardware | Compare `X-Battery-Mv` with multimeter |
| `X-Fw-Version` shows `git describe` | FW-15 | Real build + boot | Boot log / server telemetry |
| ISRG-only bundle validates the VPS chain; http:// refused in production build | FW-07 | Real TLS | Normal wake against VPS; http base URL refused |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5 s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
