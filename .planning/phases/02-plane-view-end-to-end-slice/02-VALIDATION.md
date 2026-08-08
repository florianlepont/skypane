---
phase: 02
slug: plane-view-end-to-end-slice
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-08
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
| TBD | TBD | TBD | PLANE-01 | — | Departing flight (climbing, enrichment hit) renders flight number/airline/destination correctly | unit, fixture-driven (recorded real ADS-B record + recorded real adsbdb response, no live network call) | `python3 server/test_render.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PLANE-01 | — | Enrichment miss on a departing flight renders the "Route unavailable" fallback (Route line + gap omitted, Airline line shows fallback alone — per 02-UI-SPEC.md's resolved ambiguity) | unit | `python3 server/test_render.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PLANE-02 | — | Arriving flight (descending, enrichment hit) renders flight number/airline/origin correctly, silhouette mirrored nose-left | unit | `python3 server/test_render.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PLANE-02 | — | D-03 threshold correctly classifies the real recorded arrival sequences from `adsb-test/samples/` (all 20 real tracked hexes) | unit, fixture-driven against real captured data | `python3 server/test_runway_config.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PLANE-03 | — | Detection module correctly filters a multi-aircraft geofence snapshot and applies the planner-resolved selection rule (Open Question 1) | unit | `python3 server/test_plane_detection.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PLANE-03 | — | Full pipeline end-to-end: extended `byos_server.py` serves a freshly rendered, correctly-sized (960,000-byte), correctly-hashed image over the real protocol contract | integration/smoke, extends existing harness | `python3 stub-server/test_poll_cycle.py` (extended) | ✅ exists (extend, don't replace) | ⬜ pending |
| TBD | TBD | TBD | All three | — | `image_url` in `/device/v1/display` uses `https://` once Caddy-fronted (regression guard for the plaintext-downgrade bug RESEARCH.md found in `byos_server.py`) | integration/smoke | manual-only for local dev (no TLS locally); automated smoke curl once deployed | ❌ W0 | ⬜ pending |

*Task IDs, Plan, and Wave columns are TBD — the planner fills these in once PLAN.md files exist; the Req/Behavior/Command mapping above is locked from RESEARCH.md's Validation Architecture section.*

---

## Wave 0 Requirements

- [ ] `requirements.txt` — does not exist yet; needed before any test below can run (`Pillow==12.3.0`, `requests==2.34.2`)
- [ ] `server/test_plane_detection.py` — covers PLANE-03 (geofence filtering + selection rule)
- [ ] `server/test_runway_config.py` — covers PLANE-01/PLANE-02 (D-03 thresholds against real recorded data)
- [ ] `server/test_enrich.py` — covers the enrichment cache/fallback logic (recorded fixtures for both hits and the real recorded `TVF*` misses)
- [ ] `server/test_render.py` — covers PLANE-01/PLANE-02 (render output correctness, both success and fallback paths)
- [ ] Extend `stub-server/test_poll_cycle.py` (or add a sibling) to assert the `https://` scheme fix (Common Pitfall 2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| White-on-saturated-Blue/Green legibility on the real Spectra 6 panel | PLANE-01, PLANE-02 | 02-UI-SPEC.md flags this as an unverified hardware contrast risk (no anti-aliasing, no dithering) — cannot be checked from rendered bytes alone, needs eyes on physical glass | Render a departing and an arriving test panel, flash/serve to the real device, visually confirm text and silhouette are legible from a few feet away |
| `image_url` served over real HTTPS in the deployed Caddy-fronted environment | All three | Requires the real Hetzner VPS + Caddy TLS termination — not reproducible in local dev | After deploying, `curl -I` the `/device/v1/display` response and confirm `image_url` starts with `https://`, not `http://` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
