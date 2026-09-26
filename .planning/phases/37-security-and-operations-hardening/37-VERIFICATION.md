---
phase: 37-security-and-operations-hardening
verified: 2026-09-26T12:37:05Z
status: passed
score: 13/13 must-haves verified
overrides_applied: 0
human_verification: []
---

# Phase 37: Security and operations hardening Verification Report

**Phase Goal:** The companion cannot be locked by a stranger, deploys are atomic and verified, state is backed up off-box, and services, secrets and SSH are hardened.
**Verified:** 2026-09-26T12:37:05Z
**Status:** passed
**Re-verification:** No — initial verification
**Code state:** `main` at `34bc038` (PR #143, plan 37-11 merged), all 11 plans executed with a SUMMARY.

Live-only truths rest on the checkpoint records the developer made on production (`37-SEC-BASELINE.md` CP-1, CP-3..CP-6, CP-8..CP-11; 37-08..37-11 SUMMARY files, CP-7 in 37-11-SUMMARY). No remote host was contacted during this verification.

## Goal Achievement

### Observable Truths (Roadmap Success Criteria + requirements)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1 / SEC-01: failed logins from one IP never lock another | VERIFIED | `companion/auth.py`: `LoginThrottle` keyed per caller (bounded `OrderedDict`, `max_entries=4096`, eviction drops idle/unlocked buckets first), `client_ip()` trusts `X-Forwarded-For` (rightmost entry) only from a loopback peer (IPv4-mapped loopback included), `login_throttle_key()` collapses IPv6 to /64. `companion/app.py:1871` feeds `client_address[0]` + XFF into it. Tests `test_throttle_locks_only_the_offending_key`, `test_client_ip_ignores_xff_from_a_non_loopback_peer`, `test_five_wrong_passwords_from_one_ip_lock_only_that_ip` (live app server) — all pass in this session. |
| 2 | SC-2 / SEC-02: HSTS present | VERIFIED | `deploy/Caddyfile:16,49` — `header Strict-Transport-Security "max-age=31536000"` in both site blocks (rendered by `deploy/render_caddyfile.sh`); `deploy/tests/test_caddyfile.py::test_each_site_block_carries_hsts_no_preload_no_include_subdomains` passes; `activate.sh` probes HSTS and rolls back if missing (`test_rollback_on_http_probe_failure_and_missing_hsts` passes). Live: CP-4 recorded `max-age=31536000` on both hosts. |
| 3 | SC-2 / SEC-03: a cross-origin POST is rejected | VERIFIED | `companion/auth.py::post_origin_ok()` (Sec-Fetch-Site cross-site/same-site → reject; `Origin: null` → reject; Origin netloc must equal Host) gates `do_POST` before routing (`companion/app.py:2072-2073` → 403). `companion/test_post_origin.py` covers every POST route, unknown paths, login with correct password + cross-site origin, 403 body — all pass. `test_browser_origin.py` (Playwright) cannot launch Chromium locally (environment limit); CI ran it green on PR #143. Live: CP-4 `POST /login` with `Origin: https://evil.example` → 403. |
| 4 | SC-3 / SEC-04: nightly `sqlite3 .backup` + off-box copy | VERIFIED | `deploy/backup/skypane_backup.py` uses the sqlite3 backup API (`src.backup(dst)`); `deploy/skypane-backup.timer` `OnCalendar=*-*-* 03:15:00 UTC`, `Persistent=true`; forced-command gate `deploy/backup/backup_gate.py`; Mac pull `deploy/backup/mac/skypane-backup-pull.sh` + LaunchAgent; Health off-box freshness card (`companion/test_health_offbox.py` passes). `deploy/tests/test_backup.py`, `test_backup_gate.py`, `test_mac_pull.py`, `test_install_backup_key.py` pass. Live: CP-8 (key can only list/get archives; traversal and arbitrary commands refused, exit 2), CP-9 (LaunchAgent pulled + acked, Health green). |
| 5 | SC-3: a restore from the nightly backup is rehearsed once and documented; README corrected | VERIFIED | `deploy/README.md` "Restore" procedure and "### Rehearsal log" row dated 2026-09-24, archive `skypane-state-20260924T200731Z.tar.gz`, integrity_check ok, served by a local companion. CP-10 in `37-SEC-BASELINE.md`. README describes the pulled (not pushed) off-box copy (line ~358); `deploy/tests/test_docs.py` passes. |
| 6 | SC-4 / SEC-05: a deploy that leaves a unit inactive fails the CI job | VERIFIED | `deploy/activate.sh`: release dir + `mv -T` symlink swap, `systemctl daemon-reload`, `probe_once()` runs `systemctl is-active` per unit + HTTP probes, rollback on failure with non-zero exit; `deploy/deploy.sh` is `set -euo pipefail` and relays the remote exit status; `ci.yml:200` runs `./deploy/deploy.sh`. Tests `test_rollback_on_inactive_unit`, `test_caddy_validate_failure_blocks_swap`, `test_failure_with_no_previous_release` pass. Live: CP-5 deliberately broken companion unit → probe failed, rollback to previous release, `deploy-exit=1`, previous units reinstalled. |
| 7 | SC-4 / SEC-05: units and Caddyfile are deployed (with `daemon-reload`) | VERIFIED | `activate.sh` installs `deploy/skypane-*.service`/`.timer` and renders SkyPane's own site file `/etc/caddy/sites/skypane.caddy` (host Caddyfile never written — `test_host_caddyfile_byte_identical_after_deploy_and_rollback` passes), then `daemon-reload` (lines 237, 334). Live: CP-4 cutover via CI; CP-7 confirmed installed units reference only `/opt/skypane/current/` and `/opt/skypane/venv/`, old in-place dirs removed. |
| 8 | SC-5: `systemd-analyze security` score recorded before/after | VERIFIED | `37-SEC-BASELINE.md`: online byos/companion/poll 8.3 EXPOSED (CP-1) → 1.5 OK (CP-6), byos 1.3 OK (CP-11), backup 0.8 SAFE. Re-run here: `systemd-analyze security --offline=true --threshold=20 deploy/*.service` (systemd 255.4) exits 0 with byos 1.3 OK, companion 1.5 OK, poll 1.5 OK, backup 0.8 SAFE — matching the record. Same gate runs in `ci.yml:113`. |
| 9 | SEC-06: `CapabilityBoundingSet=`, `PrivateDevices`, `ProtectKernel*`, `RestrictAddressFamilies`, `SystemCallFilter=@system-service`, `UMask=0027` on all units | VERIFIED | All four `deploy/skypane-*.service` carry every listed directive (checked by grep); `deploy/tests/test_units.py` passes. |
| 10 | SC-5 / SEC-06 remainder: byos reachable on loopback only (`--bind 127.0.0.1` + `IPAddressDeny=any`/`IPAddressAllow=localhost`) | VERIFIED | `stub-server/byos_server.py:845` `--bind` flag, `:887` `ThreadingHTTPServer((args.bind, args.port), Handler)`; `deploy/skypane-byos.service` ExecStart has `--bind 127.0.0.1`, `IPAddressDeny=any`, `IPAddressAllow=localhost` (companion/poll have no IP filter, asserted by `test_units.py`). `stub-server/test_byos_bind_secret.py` proves the only LISTEN socket is `0100007F` with the flag (passes). Live: CP-11 `ss -ltnp` → `127.0.0.1:8642` only; public `/device/v1/display` → 401 via Caddy; frame fetched `/img/<sha>.bin` from the new process. |
| 11 | SC-5 / SEC-07: no secret in `ps`; secret passed via env | VERIFIED | byos unit has no `--secret` and no `SKYPANE_BYOS_SECRET`; `skypane.env.example` has no such assignment (`test_units.py`); `test_byos_bind_secret.py` checks `/proc/<pid>/cmdline` and `environ` hold no secret. `ProtectProc=invisible` on units. Live: CP-11 `pgrep -af byos_server.py` shows no `--secret`; stale `SKYPANE_BYOS_SECRET=` line deleted from the live env file (count 0). |
| 12 | SEC-07: env file `root:root 600`; CI secrets via `env:` | VERIFIED | `deploy/provision.sh:106-108` `chown root:root` + `chmod 600` on `skypane.env`; `ci.yml:186-200` passes `DEPLOY_HOST_KEY` and `DEPLOY_SSH_TARGET` through `env:`; no `${{ }}` interpolated into a `run:` line in any workflow (grep); `deploy/tests/test_ci_secrets.py` passes. Live: CP-3 and CP-11 `600 root:root`. |
| 13 | SEC-08: `sshd_config.d/00-skypane.conf`, `PermitRootLogin no`, validated with `sshd -t` | VERIFIED | `deploy/harden_sshd.sh` writes `00-skypane.conf` (`PermitRootLogin no`, `PasswordAuthentication no`, `PermitEmptyPasswords no`), validates with `sshd -t` before reload and restores on rejection; `deploy/tests/test_provision.py` passes. Live: CP-3 `sshd -T` → `permitrootlogin no`, `passwordauthentication no` (was `yes` before), second session logged in, `root@` refused. |

**Score:** 13/13 truths verified (5 roadmap SCs covered by truths 1-8, 10, 11; SEC-01..SEC-08 all mapped)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `companion/auth.py` | `client_ip`, `login_throttle_key`, `LoginThrottle`, `post_origin_ok` | VERIFIED | Substantive; wired from `companion/app.py` (1871, 2072). |
| `companion/app.py` | `--bind` flag, throttle + origin gate wiring | VERIFIED | `--bind` at 2231, server at 2270. |
| `deploy/Caddyfile`, `deploy/render_caddyfile.sh` | HSTS on both site blocks, shared renderer | VERIFIED | Used by `activate.sh`; tests pass. |
| `deploy/activate.sh`, `deploy/deploy.sh` | Atomic release swap, daemon-reload, probes, rollback | VERIFIED | Tests pass; exercised live (CP-4, CP-5). |
| `deploy/skypane-{byos,companion,poll,backup}.service`, `skypane-backup.timer` | Hardened units, nightly backup | VERIFIED | Offline scores 0.8-1.5, gate exits 0. |
| `deploy/backup/` (snapshot, gate, key installer, Mac pull + LaunchAgent) | Off-box backup machinery | VERIFIED | Tests pass; live CP-8/CP-9. |
| `deploy/harden_sshd.sh`, `deploy/provision.sh` | SSH drop-in, env file perms | VERIFIED | Tests pass; live CP-3. |
| `.github/workflows/ci.yml` | Secrets via `env:`, offline systemd-analyze gate, deploy relays failure | VERIFIED | Lines 107-120, 184-200. |
| `stub-server/byos_server.py`, `stub-server/test_byos_bind_secret.py` | `--bind`, no secret in argv/env | VERIFIED | Test passes. |
| `companion/pages/health_page.py` (off-box card) | Backup freshness + warn nav dot | VERIFIED | `companion/test_health_offbox.py` passes; live CP-9. |
| `deploy/README.md` | Backup/restore docs, rehearsal log, loopback byos section | VERIFIED | Present. |
| `37-SEC-BASELINE.md` | Before/after record | VERIFIED | CP-1..CP-6, CP-8..CP-11 recorded; no secret values. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `companion/app.py` login handler | `auth.LoginThrottle` | `login_throttle_key(client_address[0], X-Forwarded-For)` | WIRED | app.py:1867-1871 |
| `companion/app.py do_POST` | `auth.post_origin_ok` | 403 before routing | WIRED | app.py:2072-2073 |
| CI deploy job | `activate.sh` exit status | `deploy.sh` (`set -euo pipefail`, ssh relays exit) | WIRED | ci.yml:200, deploy.sh:49 |
| `skypane-byos.service` | byos loopback bind | `--bind 127.0.0.1` in ExecStart | WIRED | parsed at byos_server.py:845/887 |
| Mac LaunchAgent | VPS archives | forced-command `backup_gate.py` (list/get/ack only) | WIRED | CP-8/CP-9 live |
| `skypane-backup.timer` | `skypane-backup.service` | systemd timer, nightly 03:15 UTC | WIRED | unit files |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| Health off-box card | last off-box snapshot time | `/var/lib/skypane-backup/pulled/last-pull` marker written by the Mac pull's ack | Yes (CP-9: "22:07 (il y a 12 min)", green) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Phase 37 tests | `server/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider deploy/tests/ stub-server/test_byos_bind_secret.py stub-server/test_devices_registry.py companion/test_login_throttle.py companion/test_post_origin.py companion/test_health_offbox.py companion/test_companion_app_01.py` | 293 passed, 2 skipped (root-euid `requires_non_root` skips, pre-existing) | PASS |
| Offline hardening gate | `systemd-analyze security --offline=true --threshold=20 deploy/*.service` | exit 0; byos 1.3, companion 1.5, poll 1.5, backup 0.8 | PASS |
| Lint | `ruff check deploy stub-server companion/auth.py companion/app.py` | All checks passed | PASS |
| Comment-history rule | `scripts/check_comment_history.py check` | exit 0 | PASS |
| Browser tests (`companion/test_browser_origin.py`) | pytest-playwright | Chromium cannot launch in this sandbox; green in CI on PR #143 | SKIP (environment) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` is declared by any Phase 37 plan. The deploy-time probes live inside `deploy/activate.sh` and are exercised by `deploy/tests/test_activate.py` (passes) and live by CP-4/CP-5.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| SEC-01 | 37-01 | Per-client-IP throttle (trusted XFF from loopback Caddy) | SATISFIED | Truth 1 |
| SEC-02 | 37-03 | `Strict-Transport-Security` | SATISFIED | Truth 2 |
| SEC-03 | 37-05 | `Origin`/`Sec-Fetch-Site` check on every POST | SATISFIED | Truth 3 |
| SEC-04 | 37-02, 37-04, 37-07, 37-10 | Nightly backup + off-box copy; README corrected | SATISFIED | Truths 4, 5 |
| SEC-05 | 37-03, 37-06, 37-09 | Release dir + symlink swap; is-active + HTTP probes fail the job; units/Caddyfile with daemon-reload | SATISFIED | Truths 6, 7 |
| SEC-06 | 37-03, 37-09, 37-11 | Unit sandboxing; byos `--bind 127.0.0.1` + IP filter | SATISFIED | Truths 8, 9, 10 |
| SEC-07 | 37-03, 37-07, 37-11 | Secret via env; env file `root:root 600`; secrets through `env:` | SATISFIED | Truths 11, 12 |
| SEC-08 | 37-07, 37-08 | `00-skypane.conf`, `PermitRootLogin no`, validated | SATISFIED | Truth 13 |

No orphaned requirement: every SEC ID mapped to Phase 37 is claimed by at least one plan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `deploy/backup/mac/skypane-backup-pull.sh` | 82 | `XXXXXX` | Info | `mktemp` template, not a debt marker |
| `.planning/ROADMAP.md` | Phase 37 | `10/11 plans executed`, 37-11 checkbox `[ ]` | Info | Resolved in the Phase 37 close-out commit (now `11/11 plans complete`, 37-11 `[x]`) |
| `.planning/REQUIREMENTS.md` | 173-174, 423-424 | SEC-06 / SEC-07 `[ ]` / `Pending` | Info | Resolved in the same close-out commit (`[x]` / `Complete`) |
| `deploy/activate.sh` | failure path | Journal tail unbounded by `--since`; final status names last probe run, not first failure | Info | Cosmetic, recorded in CP-5 notes |

No TBD/FIXME debt markers in files modified by this phase.

### Human Verification Required

None outstanding. Every live-only truth (HSTS and cross-origin 403 on production, cutover, deliberate failed deploy, online scores, backup key restrictions, Mac pull, restore rehearsal, loopback-only listen, no secret in `ps`, frame still fetching, old directories removed) has a recorded checkpoint result in `37-SEC-BASELINE.md` or the 37-08..37-11 SUMMARY files.

### Gaps Summary

No gaps. The phase goal is met in code and, for the live-only parts, in the recorded production checkpoints. Out of scope and not Phase 37 gaps: the root-euid legacy-harness items in `deferred-items.md`, the missing local Chromium for browser tests, and the VPS's pending package updates/restart noted in 37-11-SUMMARY. The orchestrator should tick 37-11 in ROADMAP.md and mark SEC-06/SEC-07 complete in REQUIREMENTS.md when closing the phase.

---

_Verified: 2026-09-26T12:37:05Z_
_Verifier: Claude (gsd-verifier)_
