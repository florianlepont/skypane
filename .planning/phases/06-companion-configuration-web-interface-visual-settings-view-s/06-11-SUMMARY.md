---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 11
subsystem: deployment
tags: [deploy, systemd, caddy, ufw, coverage, ci]
dependency-graph:
  requires: [06-07, 06-08, 06-09, 06-10]
  provides: [companion-deployment, durable-battery-log, canonical-15-harness-suite]
  affects: [deploy/, scripts/run-all-tests.sh, pyproject.toml, README.md, ARCHITECTURE.md]
tech-stack:
  added: []
  patterns:
    - "Second systemd unit + Caddy site block + ufw deny, mirroring the existing device-protocol service's exact discipline (D-03/D-05)"
    - "Vendored-code limitation solved at the infrastructure layer (Caddy durable access log) rather than by patching the vendored file (D-03, Pattern 6)"
    - "Subprocess-driven HTTP service omitted from coverage scope, same M5 rationale already applied to stub-server/byos_server.py"
key-files:
  created:
    - deploy/skypane-companion.service
  modified:
    - deploy/skypane.env.example
    - deploy/provision.sh
    - deploy/Caddyfile
    - deploy/deploy.sh
    - deploy/README.md
    - README.md
    - ARCHITECTURE.md
    - scripts/run-all-tests.sh
    - pyproject.toml
decisions:
  - "companion/app.py added to pyproject.toml's coverage omit list (deviation, not in the plan's literal instruction) — every companion/test_*.py harness drives it as a real, uninstrumented subprocess (never in-process), exactly the M5 structural-unmeasurability finding already documented for stub-server/byos_server.py. Left in scope it measured ~21% and would have permanently pinned total coverage down for a reason unrelated to actual regression."
  - "Coverage threshold ratcheted from 75 to 83 (4-point margin below the freshly measured 87%, same margin discipline as the prior 75-below-79% derivation), with a fully rewritten derivation comment naming the new measurement, scope, margin, and date."
  - "README.md's stale '9 harnesses, 212 checks' claim corrected to '15 harnesses, 394 checks' as part of this plan's already-touched-file cleanup, even though scripts/run-all-tests.sh and pyproject.toml were the plan's only declared <files> for Task 3."
metrics:
  duration: "~35min"
  completed: 2026-08-28
status: complete
---

# Phase 06 Plan 11: Deploy the Companion Service and Register Its Test Suite Summary

Deploys the companion configuration web interface as a fully independent systemd service — its own hardened unit, its own denied loopback port, its own TLS hostname — makes the device's battery telemetry durable by redirecting the existing device-protocol Caddy block's access log to a rolled file (the only path to that data given the vendored device server can't be touched), and closes out the phase's test-debt: all six harnesses phases 06-01 through 06-09 built land in the canonical suite, and the coverage scope/threshold are freshly re-derived for the enlarged (15-harness, three-package) scope.

## What Was Built

**Task 1 — companion systemd unit, env entries, provisioning (commit `6c76a7b`).**
`deploy/skypane-companion.service` is modelled directly on `deploy/skypane-byos.service`: same five hardening directives (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome`, `ReadWritePaths` scoped to `/opt/skypane/state`), same `EnvironmentFile=`/`Restart=always` shape, `ExecStart` running `companion/app.py --port ${SKYPANE_COMPANION_PORT} --state-dir ${SKYPANE_STATE_DIR}`. Its own comment block records D-03's separation rationale: three independent units, so a restart loop in the web-facing config interface never touches the ADS-B detection loop or the panel the device fetches. `deploy/skypane.env.example` gained four entries — `SKYPANE_COMPANION_PASSWORD` (same `openssl rand -hex 32` / never-committed discipline as the existing secret), `SKYPANE_COMPANION_PORT` (default 8643), `SKYPANE_COMPANION_HOST` (operator-convenience only, Caddy reads the real value from its own file), and `SKYPANE_CADDY_ACCESS_LOG`. `deploy/provision.sh` gained the companion directory in its layout step, the unit install, the enable (deliberately not started — code arrives via `deploy.sh`, matching the script's existing idempotence contract), and an explicit `ufw deny 8643/tcp` beside the existing app-port deny.

**Task 2 — Caddy site block, durable battery log, docs (commit `f811091`).**
Two Caddyfile changes. First, a new `config-`-prefixed site block (D-05) proxying to `127.0.0.1:8643`, keeping the console log stream (no durable-telemetry need of its own). Second — the load-bearing edit — the *existing* device-protocol block's log directive moved from `output stdout` (journald-bound, rotates) to `output file /opt/skypane/state/caddy-access.log` with `roll_size 10MiB`/`roll_keep 5`. This is the sole path to CFG-03's battery-voltage history: `stub-server/byos_server.py` prints `X-Battery-Mv` and persists nothing, and is explicitly off-limits to modify (D-03); Caddy's own redaction list doesn't cover that header, so it appears in the log, and `server/history_db.py`'s `tail_caddy_battery_log()` (built in 06-01) reads it via an explicit four-name allowlist, never the raw header map. `deploy/deploy.sh` gained a fourth rsync (`companion/`, same `--rsync-path` sudo wrapper as `server/`/`stub-server/`), added `skypane-companion.service` to the restart line, and a third journald tail. `deploy/README.md`, `README.md`, and `ARCHITECTURE.md` all gained companion coverage — including an explicit "Open verification item: Assumption A3" subsection in `deploy/README.md` recording that the exact Caddy JSON header-nesting shape (`request.headers.<Header-Name>`) is documented but not yet hand-verified against a real captured log line; plan 06-12 closes this on the live host.

**Task 3 — register the six new harnesses, extend and re-derive coverage (commit `855948b`).**
`scripts/run-all-tests.sh`'s `HARNESSES` array grew from 9 to 15: `server/test_config_history.py` and `server/test_panel_preview.py` inserted alphabetically among the existing `server/` entries, and the four `companion/test_*.py` harnesses added as a new trailing group. The stale "9"/"nine" references in the script's comments were replaced with the numeral 15. `pyproject.toml`'s coverage `source` list grew to `["server", "stub-server", "companion"]`; the `omit` list gained `companion/test_*.py`, and the two temporary 06-01/06-03 omit-deviations (`server/device_config.py`, `server/history_db.py`, `server/panel_preview.py`) were removed now that their harnesses are registered and their real coverage resumes counting.

The full suite was run twice. First pass (before the deviation below) measured **79%** — coincidentally identical to the pre-phase-6 measurement, because `companion/app.py`'s newly-in-scope 320 statements at ~21% coverage happened to offset the gains from `device_config.py`/`history_db.py`/`panel_preview.py` resuming real measurement. Investigating why `companion/app.py` measured so low surfaced the deviation below; after applying it, the second pass measured **87%**. The threshold was ratcheted from 75 to **83** (4 points below 87%, same margin discipline as the original 75-below-79% derivation), with the derivation comment fully rewritten to name the new measurement, scope, margin, and date (2026-08-28).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/measurement-accuracy] `companion/app.py` added to the coverage omit list**
- **Found during:** Task 3, after the first full-suite run measured coverage under the newly-widened scope.
- **Issue:** Every one of the four `companion/test_*.py` harnesses drives `companion/app.py` as a real, uninstrumented **subprocess** (a genuinely-running `ThreadingHTTPServer` on a free local port — the only way to prove D-02's whole-site auth gate over a real HTTP round trip), never by importing it and calling its route handlers in-process. Left in the coverage `source` scope, its ~320 statements measured ~21% (only module-level code executed by the few files that import `companion.app` for its constants), which would have permanently dragged total coverage down for a reason unrelated to any actual regression — exactly the same structural-unmeasurability finding (M5) `pyproject.toml`'s own omit-list comment already documents for `stub-server/byos_server.py`/`make_test_panel.py`.
- **Fix:** Added `companion/app.py` to the omit list with a comment naming the same M5 rationale, and noting every route it dispatches to is itself fully covered in-process via the individual `companion/pages/*.py` modules' own harnesses.
- **Files modified:** `pyproject.toml`
- **Commit:** `855948b`

**2. [Rule 1 - Bug/consistency] README.md's stale test-count claim corrected**
- **Found during:** Task 3, after computing the real post-registration check total (394 across 15 harnesses, up from the stale "212 checks... 9 harnesses" claim).
- **Issue:** `README.md`'s Tests section (already touched by this plan's Task 2 for the navigation table and companion-interface section) still claimed the pre-phase-6 harness/check counts.
- **Fix:** Updated to "15 harnesses, currently 394 checks total" and named `companion/test_*.py` alongside the existing two harness-directory globs.
- **Files modified:** `README.md`
- **Commit:** `855948b`

No other deviations — the rest of the plan executed exactly as written.

## Verification

- `scripts/run-all-tests.sh` exits 0, all 15 harnesses report individually (394 checks total), coverage 87% ≥ 83% threshold.
- `bash -n deploy/provision.sh` and `bash -n deploy/deploy.sh` — no syntax errors.
- `scripts/check-attribution.sh` exits 0.
- `server/.venv/bin/python3 -m ruff check .` — all checks passed.
- `deploy/Caddyfile` has exactly two site blocks (`grep -c "nip.io {"` = 2); the device-protocol block's log directive names a durable file path with rolling options, not `output stdout`; `format json` appears twice.
- `git status --porcelain stub-server/` — empty (vendored server untouched, D-03).
- `git grep -nE 'SKYPANE_COMPANION_PASSWORD\s*=\s*[^\s]' -- deploy/skypane.env.example` shows only the placeholder value.

## Self-Check: PASSED

- FOUND: deploy/skypane-companion.service
- FOUND: deploy/Caddyfile (config-203-0-113-10.nip.io block)
- FOUND: scripts/run-all-tests.sh (15-entry HARNESSES array)
- FOUND: pyproject.toml (source = ["server", "stub-server", "companion"], fail_under = 83)
- FOUND commit 6c76a7b
- FOUND commit f811091
- FOUND commit 855948b
