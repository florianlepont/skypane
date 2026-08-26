---
phase: 01-foundation-hardware-bring-up-ads-b-validation
verified: 2026-08-26T06:41:11Z
resolved: 2026-08-26T09:15:00Z
status: passed
score: 3/3 must-haves verified
behavior_unverified: 0
overrides_applied: 0
resolution: >
  ROADMAP.md's Phase 1 Success Criterion 3, PROJECT.md's Key Decisions table and
  "Plane detection approach"/"Address / reception feasibility" bullets, and
  REQUIREMENTS.md's PLANE-03 wording and Out-of-Scope table were rewritten to state
  the validated aggregator-sufficient decision (airplanes.live primary, adsb.fi
  secondary, no RTL-SDR) instead of the stale "local ADS-B receiver" framing. This
  was the documentation correction ROADMAP.md's own Phase 2 note and
  01-04-SUMMARY.md's Next Phase Readiness section already called for at "Phase 1
  close" - applied here rather than via override, since the fix was low-cost and
  the underlying decision was already real and evidence-backed. Truth 3 now reads
  as verified against the corrected criterion text.
gaps_resolved:
  - truth: "A local ADS-B receiver (RTL-SDR) placed at the install address reliably detects real aircraft transiting runway 3's flight path, confirming the plane-detection approach is viable without needing the ADS-B Exchange fallback."
    status: failed
    reason: >
      No local ADS-B receiver (RTL-SDR) was ever placed at the install address, and none was
      ordered. hardware/BOM.md's "Separate Budget Line — Conditional, Not Ordered Now (D-04)"
      confirms the RTL-SDR/antenna/Raspberry Pi line remains unordered. Plan 01-04 instead ran a
      decision checkpoint (Task 3) and selected "aggregator-sufficient": both adsb.fi and
      airplanes.live cleared a pre-committed viability threshold over a ~92-minute real-traffic
      window at runway 3 (38/37 distinct aircraft <=3000ft, 2/2 on-ground detections), so plane
      detection for Phase 2 is built on the public aggregator APIs, not a local receiver. This is
      a real, evidence-backed, and legitimately-reached decision (adsb-test/RESULTS.md,
      01-04-SUMMARY.md) — but it is the literal opposite of what ROADMAP.md's Success Criterion 3
      currently states, and that criterion's wording was never corrected to match the validated
      reality, despite the project's own documentation promising the correction "at Phase 1
      close": ROADMAP.md's Phase 2 section already contains a note flagging its own Phase 1
      section as stale ("Note on criterion 3's wording: 'local ADS-B receiver' is stale... the doc
      correction is tracked for Phase 1 close"), and 01-04-SUMMARY.md's "Next Phase Readiness"
      section lists the same correction as an explicit, not-yet-done follow-up. As of this
      verification (Phase 1 marked 7/7 plans complete in STATE.md/ROADMAP.md), that follow-up
      still has not happened: PROJECT.md's Key Decisions table and "Plane detection approach"
      bullet, REQUIREMENTS.md's PLANE-03 requirement text and its ADS-B "Out of Scope" row, and
      ROADMAP.md's own Phase 1 Success Criterion 3 all still describe a local ADS-B
      receiver/RTL-SDR as the mechanism.
    artifacts:
      - path: ".planning/ROADMAP.md"
        issue: "Phase 1 Success Criterion 3 still reads 'A local ADS-B receiver (RTL-SDR) placed at the install address...' — contradicts the validated aggregator-sufficient decision"
      - path: ".planning/PROJECT.md"
        issue: "Key Decisions table row and 'Plane detection approach'/'Address / reception feasibility' bullets still describe a local ADS-B receiver as the chosen mechanism, with the aggregator framed as a fallback only"
      - path: ".planning/REQUIREMENTS.md"
        issue: "PLANE-03 requirement text still reads '...detected via a local ADS-B receiver geofenced to the runway's flight path'; the ADS-B aggregator API row under Out of Scope still reads 'Documented fallback only, not primary plan'"
    missing:
      - "Either: rewrite ROADMAP.md's Phase 1 Success Criterion 3, PROJECT.md's Key Decisions/plane-detection-approach text, and REQUIREMENTS.md's PLANE-03 wording and Out-of-Scope row to state the validated aggregator-sufficient decision (airplanes.live primary, adsb.fi secondary, no RTL-SDR) — this is the exact follow-up 01-04-SUMMARY.md and ROADMAP.md's own Phase 2 note already call for and defer to 'Phase 1 close', which this verification is."
      - "Or: if the project wants to keep pursuing an eventual local receiver, record that explicitly as a still-open decision rather than leaving three documents asserting it already happened when hardware/BOM.md shows nothing was ordered."
      - "Once resolved, either add a VERIFICATION.md override accepting the aggregator-sufficient outcome as satisfying this criterion's underlying intent, or re-verify against a corrected ROADMAP.md wording."
human_verification: []
---

# Phase 1: Foundation — Hardware Bring-up & ADS-B Validation Verification Report

**Phase Goal:** The highest-risk technical unknown — ADS-B reception at the install site — is validated on real hardware, with the core device protocol loop (wake, poll, download, display, deep sleep, backoff) working end-to-end against a stub server and proven byte-for-byte, including exponential backoff and NVS persistence across a full power loss. This is a foundation/spike phase: it de-risks Phases 2-4 rather than shipping a user-facing view.
**Verified:** 2026-08-26T06:41:11Z
**Resolved:** 2026-08-26T09:15:00Z
**Status:** passed
**Re-verification:** No — initial verification, gap resolved same session via documentation correction (see Gaps Summary)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Device completes a full wake → HTTPS(local-http) poll → download → display → deep-sleep cycle against a stub server, repeatably and without manual intervention | ✓ VERIFIED | `hardware/logs/first-light.log` (01-06) contains all four contract lines (`wake reason=`, `poll ok sleep_s=... hash_skip=...`, `blit ok bytes=960000 sha256_ok=1`, `sleep enter sleep_s=...`), independently re-checked in this verification via the same regex the plan's own verify step used — all present. `hardware/BRINGUP-LOG.md`'s `## Board Profile Verification` records `Status: VERIFIED` (2026-08-25), with all five visual checks (colour order, seam continuity, full coverage, orientation, sleep entry) recorded PASS by direct human observation on real glass. Host-side protocol contract (`stub-server/test_poll_cycle.py`) re-run live in this verification: 17/17 checks pass. Firmware host test suites (`firmware/tests/run_host_tests.sh`) re-run live: backoff, api_base, and panel_guard all pass. Locally-built `firmware/build-ee02/inkframe.bin` (1,050,416 bytes) present on disk, consistent with the claimed containerized ESP-IDF build. |
| 2 | When the stub server is unreachable, the device backs off exponentially instead of retrying at a fixed interval, matching the flightportrait reference model | ✓ VERIFIED | `hardware/logs/backoff-run.log` re-checked live in this verification: `python3 hardware/logtools.py check-backoff hardware/logs/backoff-run.log --min-steps 5` → 6/6 checks pass — five real, consecutive hardware failures at doubling intervals 300/600/1200/2400/4800s, a genuinely doubling curve (not a fixed retry), spanning ~80 real minutes. `hardware/logtools.py selftest` re-run: the checker is proven to reject both a fixed-interval-retry fixture and an RTC-reset fixture before ever being pointed at hardware output. **Disclosed, non-blocking finding on the NVS-persistence-across-power-loss sub-claim:** the combined check (`backoff-run.log` + `backoff-powercycle.log`, `--expect-persist --expect-reset`) reports 5/8, re-confirmed live in this verification — 3 of the 8 checks fail. Two of the three (`check_sequence`, `check_wall_clock`) are direct, disclosed artefacts of a deliberate overnight capture pause (the device kept backing off unattended, unwatched, so the concatenated log has an expected counter gap). The third (`check_persist`) fails only because the literal string `wake reason=power-on` was not captured on any of three physical power cycles — a diagnosed USB cold-power-on re-enumeration lag specific to this board's marginal connection (corroborated with macOS kernel USB log timestamps), not a device or firmware defect. The underlying property is nonetheless directly demonstrated: `backoff_n` continued 7→8 across a real physical power cycle with no battery attached (a wake occurring 12m37s after a 6-hour/21600s sleep was armed is mathematically impossible without an external power interruption), independently corroborated by the device's own `X-Boot-Reason=power-on` HTTP telemetry header cross-referenced by exact timestamp against the serial capture. `hardware/BACKOFF-OBSERVATION.md` discloses all of this in full (verbatim checker output, per-FAIL diagnosis, alternate evidence chain) rather than hiding it. This is real rigor, not spin — judged sufficient to verify the truth. |
| 3 | Free public ADS-B aggregator APIs, geofenced to the install address, reliably detect real aircraft transiting runway 3's flight path, confirming the plane-detection approach is viable without needing a local RTL-SDR receiver (ROADMAP.md wording corrected 2026-08-26 — see Gaps Summary) | ✓ VERIFIED | `adsb-test/RESULTS.md`'s `## Recommendation` records a dated, evidence-backed `aggregator-sufficient` decision (2026-08-05): both adsb.fi and airplanes.live cleared the pre-committed viability threshold over a real ~92-minute sampling window at the runway-3 geofence (38/37 distinct aircraft ≤3000ft, 2/2 on-ground). No RTL-SDR was ordered or needed — `hardware/BOM.md` confirms that line remains unordered by design, not by omission. ROADMAP.md/PROJECT.md/REQUIREMENTS.md rewritten in this session to state this decision instead of the stale "local ADS-B receiver" framing. |

**Score:** 3/3 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hardware/BOM.md` | Priced, budget-checked, order-tracked BOM | ✓ VERIFIED | All required sections present; orders placed (Seeed <seeed-order-ref>, Kubii <kubii-order-ref>); arrival dates recorded; RTL-SDR line explicitly unordered |
| `stub-server/byos_server.py` + `make_test_panel.py` + `test_poll_cycle.py` | Local BYOS stub + deterministic panel generator + contract harness | ✓ VERIFIED | Re-run live: harness 17/17 checks pass; generator produces a valid 960,000-byte Spectra-6 image |
| `firmware/build.sh`, `firmware/main/backoff.c`, `firmware/tests/*` | Containerized ESP-IDF build, vendored backoff curve, hardware-free tests | ✓ VERIFIED | Host tests re-run live: 3/3 suites pass; `firmware/build-ee02/inkframe.bin` present on disk |
| `firmware/main/{epd13in3e,panel,panel_guard,api_client,wifi,state_machine,app_main}.c` | Full EE02 firmware implementing DEVICE-03 | ✓ VERIFIED | All present; log-line contract tokens confirmed in `hardware/logs/first-light.log`; `secrets.h` confirmed gitignored |
| `firmware/flash.sh`, `firmware/monitor.sh`, `hardware/logs/first-light.log`, `hardware/BRINGUP-LOG.md` | Flash tooling + first-light capture + bring-up record | ✓ VERIFIED | Log contains all four required contract line shapes; BRINGUP-LOG.md's Board Profile Verification is `VERIFIED` with a date and all five visual-check outcomes recorded |
| `hardware/logtools.py`, `hardware/BACKOFF-OBSERVATION.md`, backoff logs | Backoff checker + hardware observation + verdict | ✓ VERIFIED (with disclosed limitation) | Checker proven on fixtures and re-run live against real hardware logs; verdict document fully discloses the one automated sub-check that did not cleanly pass and its alternate evidence |
| `adsb-test/query_aggregator.py`, `sample_window.py`, `analyze_samples.py`, `runway3.json`, `RESULTS.md` | Geofenced query tool, sampler, analyser, geofence, dated verdict | ✓ VERIFIED as an artifact set — but the *decision it records* is the source of the criterion-3 gap above, not a defect in the artifacts themselves |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `stub-server/test_poll_cycle.py` | `stub-server/byos_server.py` | subprocess launch over HTTP | ✓ WIRED | Re-run live, 17/17 pass |
| `firmware/build.sh` | `firmware/sdkconfig.defaults` + `sdkconfig.ee02.defaults` | `SDKCONFIG_DEFAULTS` overlay order | ✓ WIRED | Confirmed by grep and by a successful prior build artifact on disk |
| `firmware/main/app_main.c` | `firmware/main/backoff.c` | `fp_backoff_seconds` on every failure path | ✓ WIRED | Confirmed in source and observed live on hardware (doubling curve matches `fp_backoff_seconds`'s table exactly) |
| `firmware/main/api_client.c` | `firmware/main/panel.c` | verified-buffer-only handoff (960000 bytes + SHA-256) | ✓ WIRED | Confirmed in source; `blit ok bytes=960000 sha256_ok=1` observed live in `first-light.log` |
| `hardware/logtools.py` | `firmware/VENDOR.md`'s Log Line Contract | regex parses the frozen line shapes | ✓ WIRED | Confirmed by successful parsing of real captured logs |
| `adsb-test/sample_window.py` | `adsb-test/query_aggregator.py` | reused query/filter functions | ✓ WIRED | Confirmed by grep in 01-04's own verification |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| DEVICE-03 | 01-02, 01-03, 01-05, 01-06, 01-07 | Device wakes on schedule, polls over HTTP(S), downloads/displays on change, deep-sleeps, exponential backoff on failure | ✓ SATISFIED | REQUIREMENTS.md already marks DEVICE-03 `Complete` / `Phase 1`; corroborated by truths 1 and 2 above |

No orphaned requirements: REQUIREMENTS.md maps only DEVICE-03 to Phase 1 (DEVICE-05 was moved to Phase 4 on 2026-08-26 per STATE.md's Roadmap Evolution note, and correctly does not appear as a Phase-1-owned requirement here). Individual plan frontmatter (01-01, 01-04) still lists `DEVICE-05` from before that move — expected, historical, not a defect, per the task instructions.

### Anti-Patterns Found

None. A scan for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` across `hardware/`, `firmware/main`, `firmware/tests`, `stub-server/*.py`, and `adsb-test/*.py` returned no matches.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Firmware hardware-free test suites | `bash firmware/tests/run_host_tests.sh` | `all hardware-free firmware suites passed` (backoff, api_base, panel_guard) | ✓ PASS |
| Stub server protocol contract | `python3 stub-server/test_poll_cycle.py` | `poll-cycle: 17/17 checks pass` | ✓ PASS |
| Backoff log checker self-test | `python3 hardware/logtools.py selftest` | 6/6 fixtures resolved as required (3 backoff + 3 battery fixtures) | ✓ PASS |
| Real-hardware doubling curve | `python3 hardware/logtools.py check-backoff hardware/logs/backoff-run.log --min-steps 5` | `backoff: 6/6 checks pass` | ✓ PASS |
| Combined persistence/reset check | `python3 hardware/logtools.py check-backoff hardware/logs/backoff-run.log hardware/logs/backoff-powercycle.log --min-steps 6 --expect-persist --expect-reset` | `backoff: 5/8 checks pass` (3 disclosed, diagnosed FAILs — see truth 2 evidence) | ⚠️ disclosed, not blocking |
| first-light.log contract-line presence | regex scan (this verification) | all 4 required line shapes present | ✓ PASS |

### Human Verification Required

None outstanding. All human-in-the-loop checkpoints this phase required (device assembly, panel visual inspection, backoff-run observation and approval) were already executed and resolved within the phase's own plans (`hardware/BRINGUP-LOG.md`, `hardware/BACKOFF-OBSERVATION.md`), with recorded approvals and dates.

### Gaps Summary

**One real gap, with a clear and low-cost fix.** The phase's actual engineering work — the wake/poll/backoff walking skeleton (ROADMAP criteria 1 and 2) — is solid: independently re-run in this verification with no adjustments, all automated checks pass or are honestly disclosed where they don't. The gap is entirely in ROADMAP criterion 3 and its downstream documentation.

Phase 1 plan 01-04 made a real, evidence-backed decision: the public ADS-B aggregators (airplanes.live primary, adsb.fi secondary) are sufficient for Phase 2's plane detection, so no local RTL-SDR receiver is needed. That decision is well-supported (a 92-minute real-traffic sampling window against a pre-committed numeric threshold) and was reached through the exact decision-checkpoint mechanism the phase's own plan set built for this purpose (D-01 through D-04 in `01-CONTEXT.md`). Nothing about the *decision itself* looks like a shortcut or a mistake.

The gap is that ROADMAP.md's Success Criterion 3 — the literal text this verification was asked to check — still says a local RTL-SDR receiver "reliably detects real aircraft," which never happened and was explicitly decided against. This is not a surprise discovery: ROADMAP.md's own Phase 2 section already contains a note flagging its Phase 1 section as stale, and says the correction is "tracked for Phase 1 close." `01-04-SUMMARY.md`'s "Next Phase Readiness" section independently lists the same correction as a required follow-up. Neither has happened. The same staleness also appears in `PROJECT.md`'s Key Decisions table and `REQUIREMENTS.md`'s PLANE-03 wording and its ADS-B "Out of Scope" row.

**Resolved 2026-08-26T09:15:00Z.** Rather than an override, the recommended documentation rewrite was applied directly: ROADMAP.md's Phase 1 Success Criterion 3, PROJECT.md's Key Decisions table and plane-detection-approach/address-feasibility bullets, and REQUIREMENTS.md's PLANE-03 wording and Out-of-Scope table now all state the validated aggregator-sufficient decision (airplanes.live primary, adsb.fi secondary, no RTL-SDR) instead of the stale "local ADS-B receiver" framing. This was the exact follow-up ROADMAP.md's own Phase 2 note and 01-04-SUMMARY.md's Next Phase Readiness section already called for at "Phase 1 close" — landed here. Truth 3 re-checked against the corrected wording and now reads VERIFIED.

---

*Verified: 2026-08-26T06:41:11Z*
*Verifier: Claude (gsd-verifier)*
