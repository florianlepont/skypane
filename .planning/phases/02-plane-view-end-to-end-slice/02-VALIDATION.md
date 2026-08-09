---
phase: 02
slug: plane-view-end-to-end-slice
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-08
updated: 2026-08-09
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib-only harness scripts (project convention — no pytest; see `stub-server/test_poll_cycle.py`, which asserts protocol behavior directly via `assert` statements and a `main()`/exit-code pattern) |
| **Config file** | none — each `test_*.py` is directly executable |
| **Quick run command** | `python3 server/test_<module>.py` |
| **Full suite command** | `for f in server/test_*.py stub-server/test_poll_cycle.py; do python3 "$f" || exit 1; done` |
| **Estimated runtime** | ~10 seconds (fixture-driven unit tests, no live network calls) |
| **Interpreter** | `server/.venv/bin/python3` — created by plan 02-01 Task 1 with `Pillow` and `requests` pinned in `server/requirements.txt`. Every `python3` in the commands below means that interpreter; the render and enrichment harnesses import Pillow and so cannot run under bare system `python3`. |
| **Fixture location** | `server/fixtures/` (committed, provenance in `server/fixtures/README.md`). RESEARCH.md's original wording pointed tests at `adsb-test/samples/*.jsonl`, which is **gitignored and local-only** — plan 02-01 Task 1 extracts the real records into committed fixtures so "tested against real captured data" stays true on a fresh clone. |

---

## Sampling Rate

- **After every task commit:** Run the single `test_*.py` for the module just touched
- **After every plan wave:** Run the full suite (`server/test_*.py` + `stub-server/test_poll_cycle.py`)
- **Before `/gsd-verify-work`:** Full suite must be green, plus a real end-to-end check against the deployed Hetzner VPS (real device poll or curl-simulated poll over the real HTTPS endpoint)
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-04-T3 | 02-04 | 4 | PLANE-01 | T-02-04-01 | Departing flight (climbing, enrichment hit) renders flight number/airline/destination correctly | unit, fixture-driven (`geofence_multi_aircraft.json` + `adsbdb_hit_TVF16VB.json`, no live network call) | `python3 server/test_render.py` | ➕ created 02-02-T1, extended 02-03-T1 / 02-04-T1 | ⬜ pending |
| 02-04-T3 | 02-04 | 4 | PLANE-01 | T-02-04-01 | Enrichment miss on a departing flight renders the "Route unavailable" fallback (Route line + gap omitted, Airline line shows fallback alone — per 02-UI-SPEC.md's resolved ambiguity) | unit, fixture-driven (`adsbdb_miss_EJU84YF.json`, a real recorded adsbdb miss) | `python3 server/test_render.py` | ➕ extended 02-04-T1 | ⬜ pending |
| 02-03-T2 | 02-03 | 3 | PLANE-02 | T-02-03-03 | Arriving flight renders with the silhouette mirrored nose-left, hard-edged, canvas at exactly two palette indices | unit | `python3 server/test_render.py` | ➕ extended 02-03-T1 | ⬜ pending |
| 02-04-T3 | 02-04 | 4 | PLANE-02 | T-02-04-01 | Arriving flight (descending, enrichment hit) renders flight number/airline/origin with the `FROM` prefix | unit | `python3 server/test_render.py` | ➕ extended 02-04-T1 | ⬜ pending |
| 02-02-T2 | 02-02 | 2 | PLANE-02 | T-02-02-01 | D-03 deadband correctly classifies the real recorded arrival sequence and holds state through the real `+48 ft/min` flare artefact | unit, fixture-driven against real captured data (`server/fixtures/track_arrival_440cb1.json`) | `python3 server/test_runway_config.py` | ➕ created 02-02-T1 | ⬜ pending |
| 02-02-T3 | 02-02 | 2 | PLANE-01, PLANE-02 | T-02-02-01 | Departing renders a full-bleed Blue field with a `DEPARTING` label; arriving renders Green with `ARRIVING`; neither uses Black, Yellow or Red | unit | `python3 server/test_render.py` | ➕ created 02-02-T1 | ⬜ pending |
| 02-01-T2 | 02-01 | 1 | PLANE-03 | T-02-01-01 | Detection module filters a multi-aircraft geofence snapshot and applies the D-P2-01 selection rule deterministically (closes RESEARCH Open Question 1) | unit | `python3 server/test_plane_detection.py` | ➕ created 02-01-T1 | ⬜ pending |
| 02-01-T3 | 02-01 | 1 | PLANE-03 | T-02-01-03 | Full pipeline end-to-end: `poll_loop` renders and atomically swaps a 960,000-byte panel that `byos_server.py` serves and a simulated device hash-verifies; an empty geofence leaves it untouched (D-04) | integration/smoke | `python3 server/test_pipeline_e2e.py` | ➕ created 02-01-T1 | ⬜ pending |
| 02-04-T2 | 02-04 | 4 | PLANE-01, PLANE-02 | T-02-04-01, T-02-04-03 | Enrichment returns a clean miss for every hostile response shape, caches both hits and misses, and never re-queries a callsign | unit, fixture-driven, injected transport (passes offline) | `python3 server/test_enrich.py` | ➕ created 02-04-T1 | ⬜ pending |
| 02-05-T1 | 02-05 | 5 | All three | T-02-05-01 | `image_url` in `/device/v1/display` uses `https://` when the server runs with `--image-url-scheme https`, and `http://` at its Phase-1-compatible default (regression guard for the plaintext-downgrade bug) | integration/smoke, extends the existing harness — runs fully locally, no TLS needed | `python3 stub-server/test_poll_cycle.py` (extended) | ✅ exists (extend, don't replace) | ⬜ pending |
| 02-05-T2 | 02-05 | 5 | All three | T-02-05-01, T-02-05-03 | Deployed server terminates valid Let's Encrypt TLS, gates on the bearer token, and refuses direct access to the app port | integration/smoke against the real VPS | `curl -sI https://<public-host>/device/v1/display` returns 401 over verified TLS | ➕ created 02-05-T2 | ⬜ pending |
| 02-05-T3 | 02-05 | 5 | All three | T-02-05-01 | Real device completes the full Log Line Contract against the real HTTPS server, with both the metadata poll and the image fetch on port 443 | human-verify checkpoint (blocking) + automated server-side half | see 02-05-PLAN.md Task 3 `<verify>` | ➕ created 02-05-T3 | ⬜ pending |

**Wave 0 ownership:** every harness above is created by the first task of its own plan (the Wave 0 task), always in a RED state, before the implementation task that turns it green. `server/test_render.py` is created once in 02-02-T1 and *extended* — never rewritten — in 02-03-T1 and 02-04-T1, each raising `EXPECTED_CHECK_COUNT`.

**Sampling continuity:** no three consecutive tasks lack an `<automated>` verify. Every task across all five plans carries one, including the Wave 0 tasks (which assert the RED state) and the human checkpoint (which carries an automated server-side half alongside its `<human-check>`).

---

## Wave 0 Requirements

| Wave 0 item | Owning task | Wave |
|-------------|-------------|------|
| `server/requirements.txt` (`Pillow`, `requests`, pinned) + `server/.venv` | 02-01-T1 | 1 |
| `server/fixtures/*` — real captured records committed, because `adsb-test/samples/` is gitignored | 02-01-T1 | 1 |
| `server/assets/fonts/` — Inter Regular + Bold vendored with provenance | 02-01-T1 | 1 |
| `server/test_plane_detection.py` — PLANE-03 (geofence filtering + D-P2-01 selection rule) | 02-01-T1 | 1 |
| `server/test_pipeline_e2e.py` — PLANE-03 (full render → serve → hash-verify path, plus D-04) | 02-01-T1 | 1 |
| `server/test_runway_config.py` — PLANE-01/PLANE-02 (D-03 deadband against the real recorded arrival track) | 02-02-T1 | 2 |
| `server/test_render.py` — PLANE-01/PLANE-02 (state colour, labels; extended for silhouette and route zones) | 02-02-T1 | 2 |
| `server/test_enrich.py` — enrichment cache/fallback against a real hit and the real recorded `EJU84YF` miss | 02-04-T1 | 4 |
| Extend `stub-server/test_poll_cycle.py` with both `image_url` scheme assertions (Common Pitfall 2) | 02-05-T1 | 5 |

---

## Manual-Only Verifications

Full step-by-step instructions for each row live in `02-05-PLAN.md` Task 3's `<how-to-verify>`; this table maps each item to the step that closes it.

| Behavior | Requirement | Why Manual | Verified in |
|----------|-------------|------------|-------------|
| White-on-saturated-Blue/Green legibility on the real Spectra 6 panel | PLANE-01, PLANE-02 | 02-UI-SPEC.md flags this as an unverified hardware contrast risk (no anti-aliasing, no dithering) — cannot be checked from rendered bytes alone, needs eyes on physical glass. UI-SPEC's own remedy if it fails is a bolder stroke or thin outline, **not** a colour change (there is no legal 6-colour alternative to White on Blue/Green). | 02-05-T3 step 4.2 |
| `image_url` served over real HTTPS in the deployed Caddy-fronted environment | All three | The wire-level confirmation needs the real Hetzner VPS + Caddy. The *logic* is now automated locally by 02-05-T1's dual-scheme assertions (the planner chose a `--image-url-scheme` flag over an unconditional change precisely so this is testable without TLS). | 02-05-T3 step 3 (Caddy access logs show both requests on 443) |
| Departure-side D-03 threshold against a real climbing runway-3 track | PLANE-01 | Assumption A-02-02-01 / RESEARCH Open Question 2: all 20 real tracked aircraft in Phase 1's sample were arrivals, so `CLIMB_THRESHOLD_FPM = +200` is inferred by symmetry and has never been observed. Only a real departure retires this. | 02-05-T3 step 6 |
| `Route unavailable` fallback caption on real glass | PLANE-01, PLANE-02 | Note N-02-04-01: the miss path is the coin-flip case (52.6% real hit rate), so it must be seen, not just unit-tested. A QA session that only shows Air France has not exercised it. | 02-05-T3 step 5 |
| Occasional wrong-runway aircraft from the non-exclusive geofence | PLANE-03 | RESEARCH Pitfall 5 / `runway3.json`'s own sourcing note: the bbox is not perfectly exclusive of the nearby 06/24 runway. Accepted v1 limitation; watched for, not fixed. | 02-05-T3 step 4.4 |
| Between-flights persistence (D-04) with no expiry | PLANE-03 | Requires observing a real multi-minute traffic gap on the deployed system. | 02-05-T3 step 7 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — all 13 tasks across the five plans carry an `<automated>` block, including the Wave 0 tasks (which assert the RED state) and the human checkpoint (which pairs `<human-check>` with an automated server-side half)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — every task has one
- [x] Wave 0 covers all MISSING references — see the Wave 0 Requirements table above; each harness is created in its own plan's first task, one wave-step ahead of the implementation that turns it green
- [x] No watch-mode flags — all commands are single-shot and exit with a status code
- [x] Feedback latency < 10s — fixture-driven, no live network calls in any unit harness (`test_enrich.py` injects a fake transport so it passes offline)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved by gsd-planner 2026-08-09 — Task ID / Plan / Wave columns filled from the five PLAN.md files.

## Planner amendments to the locked RESEARCH mapping

Two rows deviate from RESEARCH.md's Validation Architecture, both to make a claim true rather than to weaken it:

1. **Fixture source.** RESEARCH pointed the runway-config and enrichment tests at `adsb-test/samples/*.jsonl`. That directory is gitignored (`adsb-test/.gitignore`) and exists only on the developer's machine, so those tests would not run on a fresh clone. Plan 02-01 Task 1 extracts the exact real records into committed `server/fixtures/` files with full provenance, preserving "tested against real captured data" as a checkable claim.
2. **`https://` scheme row.** RESEARCH marked this manual-only for local dev because it recommended an unconditional scheme change, which is only assertable against a deployed Caddy. The planner chose a `--image-url-scheme` flag instead (D-P2-07, which also avoids breaking Phase 1's still-unexecuted plans 01-06/01-07/01-08 on the LAN), so both schemes are now automated locally in `stub-server/test_poll_cycle.py`. The wire-level confirmation stays manual at 02-05-T3 step 3.
