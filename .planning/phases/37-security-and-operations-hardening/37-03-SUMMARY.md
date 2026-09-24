---
phase: 37-security-and-operations-hardening
plan: 03
subsystem: infra
tags: [caddy, hsts, systemd, systemd-analyze, ci, github-actions, deploy, hardening]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest infrastructure (conftest.py, pyproject.toml [tool.pytest.ini_options], no-network socket guard)
provides:
  - "deploy/render_caddyfile.sh: the one anchored, hostname-validated Caddyfile renderer both provision.sh and the future activate.sh (Plan 37-06) call"
  - "deploy/Caddyfile: HSTS (max-age=31536000, no preload, no includeSubDomains) on both site blocks"
  - "deploy/skypane-{byos,companion,poll}.service: release-layout ExecStart paths (/opt/skypane/current/...), full SEC-06 directive set, companion --bind 127.0.0.1"
  - "deploy/skypane-backup.service + .timer: nightly (03:15 UTC) oneshot snapshot unit, PrivateNetwork=true, ready for Plan 37-04's skypane_backup.py CLI contract"
  - "deploy/tests/{test_caddyfile,test_units,test_ci_secrets}.py: 41 new pytest tests"
  - ".github/workflows/ci.yml: DEPLOY_HOST_KEY/DEPLOY_SSH_TARGET via env: (no more ${{ secrets.* }} inside run:); offline systemd-analyze gate in the test job"
affects: [37-04 (skypane_backup.py implements the ExecStart contract this plan wrote), 37-05, 37-06 (activate.sh calls render_caddyfile.sh and installs these units), 37-09 (production cutover), 37-11 (byos loopback bind, Wave B)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One shared, argument-validated shell renderer (deploy/render_caddyfile.sh) instead of the anchored sed duplicated inline in both provision.sh and the future activate.sh"
    - "systemd unit hardening as one large, repeated directive block per unit (not a systemd drop-in), matching the existing single-file-per-unit layout"
    - "GitHub Actions secrets always via env:, never interpolated into run: script text — a run: block containing '${{ secrets.' is a text-scan-detectable regression (deploy/tests/test_ci_secrets.py)"

key-files:
  created:
    - deploy/render_caddyfile.sh
    - deploy/skypane-backup.service
    - deploy/skypane-backup.timer
    - deploy/tests/test_caddyfile.py
    - deploy/tests/test_units.py
    - deploy/tests/test_ci_secrets.py
  modified:
    - deploy/Caddyfile
    - deploy/skypane-byos.service
    - deploy/skypane-companion.service
    - deploy/skypane-poll.service
    - .github/workflows/ci.yml
    - pyproject.toml

key-decisions:
  - "pyproject.toml [tool.pytest.ini_options] already uses --import-mode=importlib (Phase 32), so no deploy/tests/__init__.py was needed for basename-collision safety — the plan's own conditional instruction for the default 'prepend' mode does not apply here; documented rather than added speculatively."
  - "No equivalent to companion/test_legacy_harness_shim.py's on-disk drift guard exists for deploy/ — that guard only enumerates companion/'s own directory (os.listdir(_COMPANION_DIR)) — so deploy/tests/ needed no exemption entry anywhere; confirmed by reading the guard's source, not assumed."
  - "pyproject.toml [tool.coverage.run] source gained 'deploy/backup' ahead of Plan 37-04 (which will populate that directory with skypane_backup.py/backup_gate.py) rather than waiting for 37-04 to add it itself, per this plan's own action text ('add deploy/backup to coverage source if Phase 32's coverage config lists sources explicitly' — it does). deploy/tests/ and deploy/render_caddyfile.sh (a shell script) are deliberately left out of coverage source."
  - "Comments that would otherwise contain the literal strings 'skypane.env' or 'IPAddressDeny' for explanatory purposes were reworded to avoid them, since this plan's own acceptance criteria grep those exact substrings across the whole file (not just non-comment lines) to prove the property never appears — a documentation comment about the absence of a secret file reference or an IP filter must not itself trip the same detector."
  - "Byos's --secret argparse line was confirmed already absent in this checkout (Phase 34 plan 34-03 has already landed and retired the shared secret; stub-server/byos_server.py's own comment says '--secret is retired and grants nothing') — left exactly as found, no change made, matching the plan's explicit instruction either way."

requirements-completed: [SEC-02, SEC-04, SEC-05, SEC-06, SEC-07]

# Metrics
duration: 13min
completed: 2026-09-24
---

# Phase 37 Plan 03: HSTS, hardened systemd units, nightly backup unit, CI secrets via env: Summary

**Both Caddy site blocks now send `Strict-Transport-Security: max-age=31536000` through one shared, hostname-validated `render_caddyfile.sh`; all four deploy units (byos/companion/poll + a new nightly `skypane-backup` oneshot) carry the full SEC-06 systemd hardening directive set and score 0.8-1.5 offline (down from 8.3 EXPOSED); and `ci.yml`'s deploy job passes both production secrets through `env:` instead of splicing them into `run:` script text, with a new CI step failing the build if any unit's offline exposure exceeds the 2.0 threshold.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-09-24T08:04:00Z
- **Completed:** 2026-09-24T08:12:51Z (Task 3 commit)
- **Tasks:** 3/3 completed
- **Files modified:** 12 (6 created, 6 modified)

## Accomplishments
- `deploy/Caddyfile`: `header Strict-Transport-Security "max-age=31536000"` added to both the device and companion site blocks, right after each `reverse_proxy` line, with no `preload` and no `includeSubDomains` (SEC-02, D-15). The two anchor lines (`^203-0-113-10\.nip\.io {` / `^config-203-0-113-10\.nip\.io {`) are byte-identical to before.
- `deploy/render_caddyfile.sh` (new, `chmod 755`): the single anchored, hostname-validated renderer — `render_caddyfile.sh <template> <public-host> <companion-host>` — that both `provision.sh` (unchanged in this plan, still has its own inline copy) and the future `activate.sh` (Plan 37-06) will call. Rejects any hostname outside `[A-Za-z0-9.-]+` before printing anything (empty stdout, exit 1), including spaces, `;rm -rf /`, `$(id)`, and `` `id` ``. Never reads the operator's env file directly.
- All three existing units (`skypane-byos.service`, `skypane-companion.service`, `skypane-poll.service`) moved to release-layout `ExecStart` paths (`/opt/skypane/current/...`, ahead of Plan 37-05/37-06's atomic symlink swap), and gained the full SEC-06 directive set (`CapabilityBoundingSet=`, `AmbientCapabilities=`, `PrivateDevices=true`, `DevicePolicy=closed`, `ProtectKernel{Tunables,Modules,Logs}=true`, `ProtectControlGroups=true`, `ProtectClock=true`, `ProtectHostname=true`, `ProtectProc=invisible`, `ProcSubset=pid`, `RestrictNamespaces=true`, `RestrictRealtime=true`, `RestrictSUIDSGID=true`, `LockPersonality=true`, `SystemCallArchitectures=native`, `MemoryDenyWriteExecute=true`, `SystemCallFilter=@system-service`, `SystemCallErrorNumber=EPERM`, `UMask=0027`). `companion` additionally gained `--bind 127.0.0.1` (D-22) and both `companion`/`poll` keep `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX` with no IP address allow-list filter (they make outbound calls). Byos's `--secret` line was confirmed already gone (Phase 34's 34-03 retired it) — left untouched either way.
- New `deploy/skypane-backup.service` + `.timer`: a nightly (`OnCalendar=*-*-* 03:15:00 UTC`, `Persistent=true`, `RandomizedDelaySec=10m`) oneshot snapshot job, `User=skypane`, `PrivateNetwork=true`, `RestrictAddressFamilies=AF_UNIX`, `ReadWritePaths=/opt/skypane/state /var/lib/skypane-backup/archives`, `ExecStart` matching the CLI contract Plan 37-04's `skypane_backup.py` implements exactly (`--state-dir --archive-dir --keep`).
- Measured offline `systemd-analyze security --offline=true` scores (systemd 255.4, local, `--threshold=20` all exit 0):

  | Unit | Before | After |
  |------|--------|-------|
  | `skypane-byos.service` | 8.3 EXPOSED | 1.5 OK |
  | `skypane-companion.service` | 8.3 EXPOSED | 1.5 OK |
  | `skypane-poll.service` | 8.3 EXPOSED | 1.5 OK |
  | `skypane-backup.service` | (new) | 0.8 SAFE |

- `.github/workflows/ci.yml`: the "Trust the production host key" and "Deploy" steps in the `deploy` job now receive `DEPLOY_HOST_KEY`/`DEPLOY_SSH_TARGET` through `env:` and reference them as `"$DEPLOY_HOST_KEY"`/`"$DEPLOY_SSH_TARGET"` — no `${{ secrets.* }}` remains inside any `run:` block anywhere in the file (SEC-07, D-20). No `concurrency`/`cancel-in-progress`/`group:` line was touched (D-13, verified by diff). A new "Score systemd units (offline, fail above 2.0)" step runs in the `test` job, after lint, looping `systemd-analyze security --offline=true --threshold=20` over every `deploy/*.service`.
- `pyproject.toml`: `deploy` added to pytest `testpaths`; `deploy/backup` added to `[tool.coverage.run] source` ahead of Plan 37-04.
- `deploy/tests/{test_caddyfile,test_units,test_ci_secrets}.py`: 41 new pytest tests total (13 + 24 + 4), all stdlib/subprocess-based (no PyYAML, no caddy binary, no systemd-analyze hard dependency — the offline-score test in `test_units.py` skips cleanly if `systemd-analyze --offline` is unavailable, while CI's own dedicated step in `ci.yml` runs the same check unconditionally).

## Task Commits

Each task was committed atomically:

1. **Task 1: Phase 32 gate, HSTS in both site blocks, shared anchored renderer, pytest wiring for deploy/** - `47bab5d` (feat)
2. **Task 2: Harden all units, move them to /opt/skypane/current, add the nightly backup unit and timer** - `75809b7` (feat)
3. **Task 3: CI secrets through env: and an offline systemd-analyze gate** - `2c96166` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `deploy/Caddyfile` - HSTS header added to both site blocks; anchor lines untouched
- `deploy/render_caddyfile.sh` - New, executable (0755): anchored, hostname-validated Caddyfile renderer
- `deploy/skypane-byos.service` - `ExecStart` moved to `/opt/skypane/current/`; full SEC-06 directive set appended
- `deploy/skypane-companion.service` - Same, plus `--bind 127.0.0.1`; header comment rewritten (no longer claims `0.0.0.0`); no `IPAddressDeny`/`IPAddressAllow`
- `deploy/skypane-poll.service` - Same directive set; `--geofence` moved to the release-layout path; no IP filter (outbound ADS-B calls)
- `deploy/skypane-backup.service` - New: nightly snapshot oneshot unit
- `deploy/skypane-backup.timer` - New: 03:15 UTC, `Persistent=true`, `RandomizedDelaySec=10m`
- `.github/workflows/ci.yml` - Deploy job secrets via `env:`; new offline systemd-analyze step in the test job
- `pyproject.toml` - `deploy` in `testpaths`; `deploy/backup` in coverage `source`
- `deploy/tests/test_caddyfile.py` - New: 13 tests
- `deploy/tests/test_units.py` - New: 24 tests
- `deploy/tests/test_ci_secrets.py` - New: 4 tests

## Decisions Made
- See `key-decisions` in the frontmatter above (import-mode already `importlib` so no `deploy/tests/__init__.py` needed; no drift-guard exemption needed for `deploy/tests/`; `deploy/backup` added to coverage source ahead of Plan 37-04; two explanatory comments reworded to avoid tripping this plan's own grep-based acceptance criteria; byos `--secret` confirmed already retired by Phase 34 and left untouched).

## Deviations from Plan

None — plan executed exactly as written. The two comment rewordings (avoiding the literal strings `skypane.env` and `IPAddressDeny` in explanatory prose) are not scope deviations: they exist purely so the file's own documentation doesn't accidentally satisfy a "this string must never appear" grep the same plan specifies as its own acceptance test, and are recorded above as a decision rather than a deviation since no behavior changed.

## Issues Encountered

None new. Re-ran the full suite (`server/.venv/bin/python -m pytest deploy/ server/ stub-server/ companion/ test-support/`) after all three tasks: 850 passed, 6 skipped (3 root-euid permission-bit skips, 3 Playwright/Chromium-unavailable skips), 2 failed — both are the pre-existing, sandbox-root-only `test_companion_app`/`test_status_pages` legacy-harness failures already documented in `deferred-items.md` by 37-01/37-02 (unrelated to this plan's files; Phase 33 scope). 809 (37-02's own baseline) + 41 (this plan's new tests) = 850, confirming no regression. `server/.venv/bin/ruff check .` clean.

## User Setup Required

None — no external service configuration required. This plan's units and Caddyfile are not installed anywhere yet: they are only shipped to production by the new `activate.sh` (Plan 37-06) at the supervised cutover (Plan 37-09). The old `deploy.sh` never ships units, so merging these files is inert until then, exactly as the plan's objective states.

## Next Phase Readiness
- `deploy/render_caddyfile.sh` is ready for `activate.sh` (Plan 37-06) to call directly with hostnames parsed from `skypane.env`.
- `deploy/skypane-backup.service`'s `ExecStart` is an exact, already-verified CLI contract for Plan 37-04's `skypane_backup.py --state-dir /opt/skypane/state --archive-dir /var/lib/skypane-backup/archives --keep 14` — no further unit change needed once that script exists.
- All four units are ready for Plan 37-05/37-06's release-layout install (`install -m 644 ... /etc/systemd/system/`) — their `ExecStart` paths already assume `/opt/skypane/current/`.
- Wave B (Plan 37-11, after Phase 36) still owns byos's `--bind 127.0.0.1` + `IPAddressDeny=any`/`IPAddressAllow=localhost` — deliberately not touched here.
- No blockers for the rest of Wave A.

---
*Phase: 37-security-and-operations-hardening*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 12 files claimed as created/modified exist on disk. All three task
commits (`47bab5d`, `75809b7`, `2c96166`) are present in `git log --oneline --all`.
