---
phase: 02-plane-view-end-to-end-slice
plan: 05
subsystem: infra
tags: [systemd, caddy, ovh, tls, deployment, byos-protocol]

requires:
  - phase: 02-plane-view-end-to-end-slice
    plan: 04
    provides: server/plane/enrich.py, poll_loop.py's full detect->infer->enrich->render pipeline, render.py's zones 7/9 (route/airline lines), the 66/66-green server/test_*.py suite this plan's deploy scripts ship unmodified
provides:
  - stub-server/byos_server.py --image-url-scheme {http,https} (D-P2-07), closing the plaintext image-download gap that a Caddy-fronted deployment would otherwise silently reopen; default stays http to preserve the Phase 1 LAN stub flow, systemd unit passes https
  - stub-server/VENDOR.md local-modification-2 provenance entry and an updated re-pinning checklist covering both local modifications
  - stub-server/test_poll_cycle.py raised to 17/17 checks (default-scheme and explicit-https-scheme assertions, both local, no TLS needed)
  - deploy/ - reviewable infrastructure-as-files, provider-agnostic (targets any fresh Ubuntu 24.04 box over SSH) - not yet applied to a real VPS - inkframe.env.example, inkframe-byos.service, inkframe-poll.service/.timer, Caddyfile, provision.sh, deploy.sh, README.md, .gitignore
  - server/README.md deployment section pointing at deploy/README.md and recording the firmware-side INK_API_BASE config-only change
affects: []

tech-stack:
  added: [Caddy (VPS-side, automatic Let's Encrypt TLS), systemd timers/services (VPS-side scheduling and process supervision), OVH VPS-1 (target host, replacing the originally planned Hetzner CX22)]
  patterns:
    - "CLI flag over unconditional behaviour change for a scheme fix that has two live consumers (Phase 1's unproxied local LAN flow and Phase 2's Caddy-fronted VPS) - default preserves the already-shipped consumer, the new consumer passes the flag explicitly, both are asserted in the same local test run with no TLS setup required"
    - "provision.sh (idempotent, machine setup) and deploy.sh (repeatable, code-push) kept as two separate scripts rather than one, so re-running deploy.sh after a code change never re-touches ufw/SSH/Caddy config, and re-running provision.sh after a config change never re-rsyncs application code"
    - "Loopback restriction enforced at the firewall/reverse-proxy layer (ufw deny + Caddy-only forwarding) rather than patching byos_server.py's hardcoded 0.0.0.0 bind, keeping the vendored file's diff minimal per stub-server/VENDOR.md's discipline"
    - "deploy/ scripts and unit files are written provider-agnostic from the start (target 'a fresh Ubuntu 24.04 box reachable over SSH', no Hetzner-specific API calls baked into provision.sh/deploy.sh) - this is what made the mid-plan Hetzner-to-OVH provider swap a docs-only change with zero script edits"

key-files:
  created:
    - deploy/inkframe.env.example
    - deploy/inkframe-byos.service
    - deploy/inkframe-poll.service
    - deploy/inkframe-poll.timer
    - deploy/Caddyfile
    - deploy/provision.sh
    - deploy/deploy.sh
    - deploy/README.md
    - deploy/.gitignore
  modified:
    - stub-server/byos_server.py
    - stub-server/VENDOR.md
    - stub-server/test_poll_cycle.py
    - server/README.md

key-decisions:
  - "Task 1 (scheme fix) and the file-artifact half of Task 2 (deploy/ infrastructure files) are complete and independently verified without needing the real VPS - committed as atomic commits. The live-provisioning half of Task 2 (create the VPS, run provision.sh/deploy.sh against it, confirm real TLS) is a genuine human-action gate: the target VPS does not exist yet."
  - "Provider swap: the plan and D-P2-06 specify a Hetzner CX22; the user explicitly redirected to an OVH VPS-1 after a live price/locale comparison (price parity with the CX22, plus an already-active OVH account and preference). This is a substitution within D-P2-06's own stated discretion ('infrastructure specifics ... left to Claude's discretion'), not an architectural change - see Deviations below."
  - "OVH provisioning needs no API token: unlike the original Hetzner path (which pre-installed the hcloud CLI for automated server creation), a single one-off OVH VPS is created by hand in the existing OVH Manager console. This is simpler than the Hetzner path, not equivalent-effort - no cloud-provider credential is requested or stored anywhere in this flow."
  - "Task 3 (physical-frame verification) remains not started: it is gated on both Task 2's live provisioning (no real https://<public-host> exists yet to point the firmware at) and on Phase 1 plan 01-06 (flash and first boot, hardware unblock date 2026-08-26), per this plan's own <prerequisites> block. Neither precondition is met yet."

patterns-established:
  - "Env-var template files (deploy/inkframe.env.example) mirror firmware/main/secrets.example.h's discipline exactly: every key present with a placeholder and a comment on where the real value comes from, paired with a scoped .gitignore rule that exists before the real file ever does."

requirements-completed: []

duration: ~55min across two sessions (through this checkpoint; Task 2's provisioning and Task 3 remain)
completed: 2026-08-25
status: checkpoint
---

# Phase 2 Plan 5: Deploy to OVH VPS-1 (Checkpoint - awaiting VPS IP)

**Closed the byos_server.py plaintext-image-download gap with a configurable --image-url-scheme flag, wrote the full deploy/ infrastructure-as-files (systemd units, Caddyfile, provision/deploy scripts, runbook), and re-pointed the deployment target from Hetzner CX22 to OVH VPS-1 per an explicit user redirect - blocked before live provisioning on the OVH VPS not yet existing.**

## Performance

- **Duration:** ~55 min so far (Task 1 + Task 2's file artifacts + the provider-swap doc update)
- **Tasks:** 1 of 3 fully complete (Task 1); Task 2 partially complete (file artifacts done and re-pointed to OVH, live provisioning blocked); Task 3 not started (blocked on Task 2 + hardware)
- **Files modified:** 17 (4 in Task 1, 9 in Task 2's file-artifact half, 4 in the provider-swap doc update)

## Accomplishments
- Added `--image-url-scheme {http,https}` to `stub-server/byos_server.py` (default `http`), so the `/device/v1/display` response's `image_url` scheme is explicit and configurable instead of hardcoded to `http://` - closing the exact plaintext-downgrade gap 02-RESEARCH.md's Common Pitfall 2 and T-02-05-01 flag
- Documented the change as local modification 2 in `stub-server/VENDOR.md`, with rationale (Phase 1's plans 01-06/01-07/01-08 still depend on the local LAN stub flow, so the default cannot flip to `https` unconditionally) and updated the re-pinning checklist to cover both local modifications
- Extended `stub-server/test_poll_cycle.py` to 17/17 checks: the default scheme starts with `http://`, and a server started with `--image-url-scheme https` serves `https://` with an unchanged host and `/img/<digest>.bin` path - both assertions run entirely locally, no TLS needed
- Wrote the complete `deploy/` directory as reviewable infrastructure-as-files, deliberately provider-agnostic in every script and unit file: `inkframe.env.example` (gitignored-secret template), `inkframe-byos.service` (unprivileged user, `--image-url-scheme https`, `EnvironmentFile=`, `Restart=always`, `NoNewPrivileges`/`PrivateTmp`/`ProtectSystem=strict`/scoped `ReadWritePaths`/`ProtectHome`), `inkframe-poll.service` + `.timer` (`Type=oneshot` `poll_loop.py --once` on a 30s cadence matching 02-01's validated interval), `Caddyfile` (nip.io-pattern reverse proxy to `127.0.0.1:8642` for automatic Let's Encrypt TLS with no owned domain required), `provision.sh` (idempotent first-run setup: service user, Python 3.12 venv, Caddy from the official apt repo with GPG verification, systemd units, ufw allowing only SSH/80/443 with the app port explicitly denied, SSH key-only hardening), `deploy.sh` (repeatable rsync + conditional pip reinstall + service restart + journald tail, never touching the env file), and `README.md` (the full runbook)
- Added a deployment section to `server/README.md` pointing at `deploy/README.md` and recording that `firmware/main/secrets.h`'s move to a real HTTPS base is a configuration-only change - `api_client.c`'s ESP-TLS certificate-bundle path is already compiled in
- Ran all locally-runnable verification: `stub-server/test_poll_cycle.py` 17/17 green, all five `server/test_*.py` harnesses green (66/66 checks, no regressions), `bash -n` clean on both shell scripts, both scripts confirmed to start with `set -euo pipefail`, the Caddyfile confirmed to contain `reverse_proxy`, `git check-ignore -q deploy/inkframe.env` confirmed to exit 0, no `npm` invocation in `provision.sh`, and the hardening directives (`NoNewPrivileges`/`PrivateTmp`/`ProtectSystem=strict`/`ReadWritePaths`/`ProtectHome`) confirmed present in `inkframe-byos.service`
- **Provider swap (this session):** re-pointed `deploy/provision.sh`, `deploy/deploy.sh`, `deploy/README.md` and `server/README.md` from Hetzner CX22 to OVH VPS-1 per an explicit user redirect. Confirmed via `grep` that no functional script logic referenced Hetzner (both scripts already targeted a generic "fresh Ubuntu 24.04 box over SSH") - only comments and the README's one-time human steps changed. Re-wrote the one-time human steps to describe manual OVH VPS-1 creation in the existing OVH Manager console instead of Hetzner Cloud Console + `hcloud` CLI automation.

## Task Commits

Each completed task/task-portion was committed atomically:

1. **Task 1: Close the plaintext image-download gap in the vendored protocol server (D-P2-07)** - `6f8ef2c` (feat) - complete
2. **Task 2 (file-artifact half): Reviewable deploy/ infra-as-files, originally for Hetzner CX22** - `5d34841` (feat) - complete
3. **Provider swap: repoint deploy docs from Hetzner CX22 to OVH VPS-1** - `38d80e1` (docs) - complete; the live-provisioning half of Task 2 (create the real VPS, run `provision.sh`/`deploy.sh` against it, external TLS/ufw/timer verification) is **not yet done** - see Checkpoint below
4. **Task 3: Verify the live plane view on the physical frame** - not started (blocked on Task 2's provisioning and on Phase 1 plan 01-06)

## Files Created/Modified
- `stub-server/byos_server.py` - `--image-url-scheme {http,https}` argparse flag (default `http`), `/device/v1/display`'s `image_url` built from it instead of a hardcoded `http://` literal, docstring extended
- `stub-server/VENDOR.md` - local modification 2 (the scheme flag) documented with rationale and default; re-pinning checklist updated to cover both modifications
- `stub-server/test_poll_cycle.py` - `EXPECTED_CHECK_COUNT` raised 15 -> 17; `Harness.start_server()` gained an optional `image_url_scheme` parameter; two new checks (default scheme, explicit https scheme with host/path parity)
- `deploy/inkframe.env.example` - env template: `INK_BYOS_SECRET`, `INK_BYOS_PORT`, `INK_SLEEP_S`, `INK_STATE_DIR`, `INK_PUBLIC_HOST`
- `deploy/inkframe-byos.service` - systemd unit for `byos_server.py`, hardened, `--image-url-scheme https`
- `deploy/inkframe-poll.service` / `deploy/inkframe-poll.timer` - `Type=oneshot` poll cycle on a 30s timer
- `deploy/Caddyfile` - nip.io-pattern reverse proxy for automatic TLS
- `deploy/provision.sh` - idempotent VPS first-run setup script (comment updated to OVH VPS-1; no functional change)
- `deploy/deploy.sh` - repeatable rsync/restart deployment script (comment updated to OVH; no functional change)
- `deploy/README.md` - full deployment runbook, re-pointed to OVH VPS-1 and its manual console-creation flow
- `deploy/.gitignore` - ignores the real `inkframe.env`
- `server/README.md` - added a "Deployment" section, re-pointed to OVH VPS-1

## Decisions Made
- Kept `provision.sh` (idempotent machine setup) and `deploy.sh` (repeatable code push) as two separate scripts, matching the plan's own file list, so a config-only re-run never re-syncs code and a code-only re-run never re-touches ufw/SSH/Caddy.
- Did not patch `byos_server.py`'s hardcoded `0.0.0.0` bind a second time (beyond the scheme flag) - the loopback restriction is enforced at the firewall/reverse-proxy layer instead (`ufw deny 8642/tcp` plus Caddy being the only process forwarding to `127.0.0.1:8642`), keeping the vendored file's diff confined to the one flag per `stub-server/VENDOR.md`'s minimal-diff discipline. Recorded as "Known vendored behaviour" in `deploy/README.md`.
- Switched the deployment target from Hetzner CX22 to OVH VPS-1 (this session) per explicit user instruction. Treated as a provider substitution, not an architectural change, because: (1) D-P2-06 itself scopes "infrastructure specifics" as left to discretion, (2) the two boxes are spec-equivalent (2 vCPU/4GB/40GB NVMe, Ubuntu 24.04, always-on), and (3) zero lines of `provision.sh`/`deploy.sh` logic needed to change - both were already written against "a fresh Ubuntu 24.04 box over SSH" with no Hetzner-specific API calls. Only comments and `deploy/README.md`'s one-time human steps changed.
- Did not request or store an OVH API token. Unlike the Hetzner path (which pre-installed the `hcloud` CLI to automate `server create`), OVH provisioning here is a single manual VPS creation in the existing OVH Manager console - simpler than the path it replaces, and no credential enters this flow at all.

## Deviations from Plan

### Rule 4-adjacent: user-directed provider substitution (not an architectural change)

**What changed:** the plan text, its `user_setup` block, and decision D-P2-06 specify a Hetzner CX22 in Falkenstein or Nuremberg. This deployment instead targets an **OVH VPS-1** in Gravelines or Strasbourg.

**Why:** explicit user redirect after a live price/locale comparison - OVH VPS-1 came out at price parity with the Hetzner CX22, and the user already has an active OVH account and preferred it.

**Why this did not require a Rule 4 stop:** D-P2-06 is recorded in the plan itself as "research-resolved, infrastructure specifics ... left to Claude's discretion." A same-spec provider swap (2 vCPU / 4 GB RAM / 40 GB NVMe, Ubuntu 24.04, always-on, no scale-to-zero) falls inside that discretion rather than outside it. Nothing about the plan's actual architecture changed: systemd services/timer, Caddy for automatic TLS, ufw firewalling, key-only SSH, no Docker, no FastAPI, no APScheduler - all unchanged. The only edits were doc/comment prose in `deploy/provision.sh`, `deploy/deploy.sh`, `deploy/README.md`, and `server/README.md` (commit `38d80e1`); zero script logic changed.

**What did not change:** `.planning/phases/02-plane-view-end-to-end-slice/02-05-PLAN.md` itself was left untouched, per instruction - it is a historical planning artifact and its Hetzner references (objective text, D-P2-06, the `user_setup` block, threat T-02-05-02's prose, and the `<done>`/acceptance text) stand as originally written. This SUMMARY.md is the record of record for the provider substitution.

**Provisioning is simpler under the new provider:** OVH doesn't need API automation for a single one-off VPS-1. The user creates it by hand in the existing OVH Manager console (Ubuntu 24.04 image, Gravelines or Strasbourg datacenter, SSH public key attached at creation) and hands Claude the IP - no OVH API token/credential enters this flow anywhere, whereas the original Hetzner path pre-installed the `hcloud` CLI in anticipation of token-driven automation.

No other deviations. Task 1 and the file-artifact half of Task 2 were executed exactly as specified, with no auto-fixes needed.

## Issues Encountered
- While writing the new `test_poll_cycle.py` scheme check (prior session), the first implementation compared the full `image_url` strings including the port number between two separately-started `Harness` instances - which legitimately differ because `Harness._pick_free_port()` binds an OS-assigned free port per instance for test isolation. Caught immediately by running the test (it failed with a clear message), fixed by comparing `urllib.parse.urlsplit()`'s `hostname` and `path` components instead of the full string. Caught and fixed before any commit - normal test-driven iteration, not a plan deviation.
- No issues this session beyond the expected human-action gate below.

## User Setup Required

**This plan is blocked on a real, human-created resource: the OVH VPS-1 itself.** Per the resume instructions for this session, Claude does not automate OVH account or VPS creation. What's needed:

1. In the OVH Manager console, create a VPS-1 instance (2 vCPU / 4 GB RAM / 40 GB NVMe), Ubuntu 24.04 image, Gravelines or Strasbourg datacenter, with `~/.ssh/id_ed25519.pub` attached as the SSH key at creation.
2. Provide the resulting public IPv4 address (and confirm SSH access works) so Claude can build the nip.io hostname and resume provisioning.

No OVH API token or other credential is requested - only the IP, once the VPS exists.

## Next Phase Readiness

**Not ready to close this plan yet.** Remaining work, in order:

1. **Live provisioning (rest of Task 2):** once the OVH VPS-1's IP is available and SSH access is confirmed, build the nip.io hostname (`<ip-with-dashes>.nip.io`), run `deploy/provision.sh <public-host>` then `deploy/deploy.sh <ssh-target>` against it, and confirm the acceptance criteria this plan's `<verification>` block lists (valid Let's Encrypt TLS + 401 without a token, app port refused externally, `inkframe-poll.timer` active with successive journald cycles, `systemd-analyze verify` clean on the VPS since macOS has no local `systemd-analyze`).
2. **Task 3 (physical-frame verification):** blocked on both (1) and on Phase 1 plan 01-06 (flash and first boot) - STATE.md's hardware unblock date is 2026-08-26.
3. Once both are done, re-run this executor (or a continuation agent) to finish the plan, write the final SUMMARY update, and close ROADMAP Phase 2 success criterion 4.

No blockers beyond the VPS-creation gate and the hardware-arrival gate, both anticipated (the VPS gate is a provider-swapped version of this plan's own `<prerequisites>`-adjacent Hetzner credential gate; the hardware gate is explicitly named in `<prerequisites>`).

---
*Phase: 02-plane-view-end-to-end-slice*
*Completed: checkpoint reached 2026-08-25 - plan not yet closed*

## Self-Check: PASSED

Verified all 9 `deploy/` files present on disk plus the 3 modified `stub-server/` files and `server/README.md`. Verified all three commits (`6f8ef2c`, `5d34841`, `38d80e1`) present in `git log --oneline`. Independently re-ran `stub-server/test_poll_cycle.py` (17/17) and all five `server/test_*.py` harnesses (66/66) after writing this summary - all green, no regressions. Confirmed via `grep -rniE "hetzner|cx22|hcloud|falkenstein|nuremberg"` that only one intentional Hetzner mention remains across `deploy/provision.sh`, `deploy/deploy.sh`, `deploy/README.md`, `server/README.md` - the explanatory deviation note at the top of `deploy/README.md`.
