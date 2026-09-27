---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 13
subsystem: measurement
tags: [efficiency, baseline, caddy, verification]
requires:
  - phase: 38-efficiency-companion-poll-cycle-storage
    provides: "38-01's efficiency_probe/measure_efficiency instruments and the Before tables; 38-02..38-12's behaviour changes"
provides:
  - "38-EFF-BASELINE.md: After tables, Deltas, Criteria check (ROADMAP criteria 1-4 all hold), and the live VPS compression rows"
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - .planning/phases/38-efficiency-companion-poll-cycle-storage/38-EFF-BASELINE.md
key-decisions:
  - "The live 'before' rows could not be captured, because production already served the new headers when the check ran (38-02 had been merged and deployed with #147). The pre-change values come from the in-process Before table."
requirements-completed: [EFF-01, EFF-02, EFF-03, EFF-04, EFF-05, EFF-06]
duration: n/a
completed: 2026-09-27
---

# Phase 38 Plan 13: After measurement and live compression check

**All four ROADMAP criteria for Phase 38 hold, both in-process and live. On production, `style.css` is served zstd-compressed (140,426 → 39,361 bytes) with `public, no-cache`, and revalidation returns 304 through Caddy.**

## Tasks
1. **After tables, Deltas and Criteria** (`ba6c601`). The full suite was green apart from the known local old-Chromium test, then `scripts/measure_efficiency.py --label after` ran with the Before defaults. Main results:
   - First load of `/`: 306,755 → 215,351 bytes.
   - SQLite connections: 9-12 per page → 1, and 3 per poll cycle → 1.
   - Static revalidation and the freshness tick: 304 with 0 bytes.
   - The fixed 1.1 s provider sleep is gone. With 0 latency, the empty-sky cycle takes 1.17 → 0.07 s.
2. **Live VPS check** (human). The developer ran the curl commands on 2026-09-27:
   - `content-encoding: zstd`, `etag: "…-zstd"`, `cache-control: public, no-cache`, `vary: Accept-Encoding`;
   - `size_download=39361`;
   - `revalidate=304 size=0`.
3. **Live rows recorded** in `38-EFF-BASELINE.md` "Live compression (VPS)". The freshness.js and device-host checks are marked pending as optional follow-ups; the device-block `encode` absence is already asserted by `deploy/tests/test_caddyfile.py`.

## Deviations
- There are no live "before" rows, because by the time of the check production already ran the static-cache and `encode` changes (merged in #147). The before values are the in-process measurements of the unmodified tree, and the table says so.
- Task 3 was completed by the orchestrator from the developer's reply, not by a fresh executor.

## Self-Check: PASSED
- `grep -c "^## Live compression (VPS)$" 38-EFF-BASELINE.md` returns 1, and the table has two before rows and measured or pending after rows.
- No secret, cookie, host key or IP address is recorded; the companion host is written as `<companion host>`.
