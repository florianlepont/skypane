---
phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
plan: 05
subsystem: docs
tags: [readme, architecture, documentation, attribution, adsb]

requires:
  - phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
    provides: "04-02's scripts/run-all-tests.sh (canonical test entry point), 04-03's LICENSE/COMPLIANCE.md/check-attribution.sh, 04-04's CI workflows this README documents as the same commands"
provides:
  - "Repo-root README.md: newcomer front door (hardware/server/tests/firmware/deployment, each pointing at the authoritative doc)"
  - "Repo-root ARCHITECTURE.md: current-state system description grounded in the shipped code"
  - "Visible adsb.fi attribution in README.md's Data Sources section, closing the visible half of D-14"
  - "Status note on .planning/research/ARCHITECTURE.md marking it superseded pre-project research"
affects: [04-06]

tech-stack:
  added: []
  patterns:
    - "Root-level docs point at subdirectory READMEs (server/, deploy/) rather than duplicating their content"

key-files:
  created:
    - README.md
    - ARCHITECTURE.md
  modified:
    - .planning/research/ARCHITECTURE.md

key-decisions:
  - "ARCHITECTURE.md written directly from the code (state_machine.c, backoff.c, poll_loop.py, detect.py, enrich.py, render.py, panel_format.py, byos_server.py), not from the pre-project research document, per D-16"
  - "Deployment topology described with placeholder host references only (<public-host>, loopback/all-interfaces prose instead of dotted-quad addresses) to avoid reintroducing scrubbed literals"

requirements-completed: [D-14, D-15, D-16]

coverage:
  - id: D1
    description: "Repo-root README.md lets a newcomer go from clone to running server/flashed device, with every command verified to actually work"
    requirement: D-15
    verification:
      - kind: other
        ref: "grep-based acceptance check in 04-05-PLAN.md Task 1 (scripts/run-all-tests.sh, deploy/README.md, hardware/BOM.md, firmware/build.sh, adsb.fi link, airplanes.live, COMPLIANCE.md, LICENSE all present; no dotted-quad/vps-hostname)"
        status: pass
      - kind: other
        ref: "./scripts/run-all-tests.sh (the exact command README.md recommends)"
        status: pass
    human_judgment: false
  - id: D2
    description: "adsb.fi attribution visible in README.md's Data Sources section, satisfying their cite-and-link requirement"
    requirement: D-14
    verification:
      - kind: other
        ref: "grep -qi 'https://adsb.fi' README.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "ARCHITECTURE.md describes the shipped system (firmware state machine, server render pipeline, deployment topology), grounded in named source files, with an ASCII data-flow diagram and a deliberate-constraints section"
    requirement: D-16
    verification:
      - kind: other
        ref: "grep-based acceptance check in 04-05-PLAN.md Task 2 (all 8 implementing files named, 'deep sleep', 'backoff', research/ARCHITECTURE.md pointer present; no dotted-quad/vps-hostname)"
        status: pass
    human_judgment: false
  - id: D4
    description: ".planning/research/ARCHITECTURE.md carries a status note (first 20 lines) pointing at the new root ARCHITECTURE.md, with zero lines deleted from the original content"
    requirement: D-16
    verification:
      - kind: other
        ref: "head -20 grep for supersession language + ARCHITECTURE.md pointer, git diff --numstat showing 0 deletions"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-08-26
status: complete
---

# Phase 4 Plan 05: README and ARCHITECTURE Documentation Summary

**Repo-root README.md (newcomer front door, adsb.fi attribution visible) and ARCHITECTURE.md (current-state system description written from the shipped code) plus a superseded-status note on the pre-project research doc**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3
- **Files modified:** 3 (2 new, 1 additive edit)

## Accomplishments

- `README.md` created at the repo root: opens with what the project is and its honest v1 scope (single plane view; RER view and the physical button both explicitly deferred to v2), a six-directory navigation table, then Hardware/Server/Tests/Firmware/Deployment sections each pointing at the authoritative document (`hardware/BOM.md`, `server/README.md`, `scripts/run-all-tests.sh`, `firmware/build.sh` + `firmware/VENDOR.md`, `deploy/README.md`) rather than restating it. A Data Sources section credits adsb.fi (with a live link, satisfying their cite-and-link term), airplanes.live, and adsbdb.com, and links `COMPLIANCE.md` for the full terms analysis. A Licence section links `LICENSE` and flags that vendored assets carry separate licences.
- `ARCHITECTURE.md` created at the repo root, written directly from the source files (not the stale research doc): the firmware wake→poll→display→deep-sleep cycle (state_machine.c's `fp_poll_once()`, the hash-skip short-circuit, the deferred-vs-failed panel-guard distinction, backoff.c's doubling/6h-cap formula, the frozen 5-line Log Line Contract, the measured ~31.5s full-refresh duration); the server render pipeline (detect.py's deterministic multi-aircraft selection, runway_config.py's vertical-rate deadband, enrich.py's persistent hit+miss cache with its ~52.6% real-world hit rate documented as a first-class fallback state rather than an edge case, render.py's two-flight poster composition, panel_format.py's wire encoding, byos_server.py serving as the real production protocol handler); and the OVH VPS deployment topology (Caddy/ufw network-layer loopback enforcement, systemd units, bearer-token auth, deploy.sh). Includes a plain-ASCII end-to-end data-flow diagram and a closing section recording battery-only power, the poll-only security model, single-view v1 scope, and the absent staleness indicator as deliberate choices with reasons.
- `.planning/research/ARCHITECTURE.md` got a short, additive status note in its first 5 lines pointing at the new root `ARCHITECTURE.md` and stating its own nature (2026-08-04 domain research, pre-code) — zero lines of the original content deleted, confirmed via `git diff --numstat`.

## Task Commits

1. **Task 1: Root README — the project's front door** - `6b4d719` (docs)
2. **Task 2: ARCHITECTURE.md — the system as built** - `ec78543` (docs)
3. **Task 3: Mark the pre-project research document as superseded** - `6bd3a9f` (docs)

## Files Created/Modified

- `README.md` — new repo-root front door
- `ARCHITECTURE.md` — new repo-root current-state architecture description
- `.planning/research/ARCHITECTURE.md` — additive status note only, original content untouched

## Commands Executed While Writing the README (all verified working)

- `python3 -m venv <scratch-dir>` + `<venv>/bin/pip install -r server/requirements.txt` — clean-venv install path exercised end to end; succeeded (the run's pip output shows retries against a sandbox-local package proxy configured in this execution environment, not a real-world failure mode — the already-provisioned `server/.venv` used for every other command in this plan is the same install path and works cleanly).
- `server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 --out <scratch>/panel.bin` — wrote a 960,000-byte panel, printed its SHA-256.
- `server/.venv/bin/python3 server/poll_loop.py --once --state-dir <scratch>/poll-state-test` — ran a real poll cycle. The live `airplanes.live` call returned HTTP 403 in this sandboxed execution environment (outbound network is proxied/restricted here, not a code defect), and the cycle correctly fell through to the Empty-state render and logged `poll_loop: ... confirmed_state=None render_state=empty ... panel_changed=True` — this is exactly the designed no-detection fallback behaviour described in ARCHITECTURE.md, not a bug.
- `./scripts/run-all-tests.sh` — all 9 harnesses pass (117 checks), coverage 79% (threshold 75%). Run twice (once ahead of Task 1's verification, once again in the plan-level verification pass) with identical results.
- `server/.venv/bin/ruff check .` — `All checks passed!`, exit 0.
- `./scripts/check-attribution.sh` — `PASS: 23 asset file(s) all attributed in 3 VENDOR.md file(s); 3 font family(ies) all have licence text.`

## Decisions Made

- ARCHITECTURE.md is written from the code, not lightly edited from `.planning/research/ARCHITECTURE.md` — per D-16, the research document is background/rationale material only, and re-publishing it would misdescribe the system (it predates the actual two-flight-poster render design, the real detect/enrich/render module split, and the OVH-not-Hetzner deployment).
- The deployment-topology section describes network binding in prose ("the app's loopback address", "binds every interface") instead of literal `127.0.0.1`/`0.0.0.0` — the plan's dotted-quad-address prohibition (T-04-05-01) is written broadly enough to catch even non-sensitive loopback/wildcard addresses, so this was corrected during Task 2's verification pass rather than argued around.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ARCHITECTURE.md's initial draft failed its own verification twice**
- **Found during:** Task 2 (ARCHITECTURE.md verification)
- **Issue:** Two literal strings tripped the task's own automated grep checks: `esp_deep_sleep_start()` (no space) didn't satisfy the required case-insensitive `deep sleep` substring, and the deployment section's `127.0.0.1:8642` / `0.0.0.0` literals matched the dotted-quad-address prohibition regex even though neither is a real production address.
- **Fix:** Added a plain-English "deep sleep" phrase in the ASCII data-flow diagram, and rewrote the two IP-literal sentences in the deployment topology section to describe the binding behaviour in prose instead of by address.
- **Files modified:** `ARCHITECTURE.md`
- **Verification:** Re-ran the task's exact automated verification command; it printed `ARCHITECTURE_OK`.
- **Committed in:** `ec78543` (Task 2 commit — fixed before commit, so no separate fix commit was needed)

---

**Total deviations:** 1 auto-fixed (1 bug, self-caught by the task's own verification before committing)
**Impact on plan:** No scope creep — both fixes were wording corrections inside the already-planned content, caught by the plan's own automated checks exactly as designed.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both root-level documents exist, are cross-linked correctly, and pass every automated check the plan specified (link resolution, no scrubbed-literal patterns, all 8 named source files present, all 9 test harnesses + ruff + attribution check still green).
- Plan 04-06 (repo push + secrets/environment provisioning) is the only remaining plan in Phase 4 — this plan introduces no blocker for it.

---
*Phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests*
*Completed: 2026-08-26*

## Self-Check: PASSED
