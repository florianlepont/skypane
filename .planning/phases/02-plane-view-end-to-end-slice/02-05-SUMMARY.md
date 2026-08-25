---
phase: 02-plane-view-end-to-end-slice
plan: 05
subsystem: infra
tags: [systemd, caddy, hetzner, tls, deployment, byos-protocol]

requires:
  - phase: 02-plane-view-end-to-end-slice
    plan: 04
    provides: server/plane/enrich.py, poll_loop.py's full detect->infer->enrich->render pipeline, render.py's zones 7/9 (route/airline lines), the 66/66-green server/test_*.py suite this plan's deploy scripts ship unmodified
provides:
  - stub-server/byos_server.py --image-url-scheme {http,https} (D-P2-07), closing the plaintext image-download gap that a Caddy-fronted deployment would otherwise silently reopen; default stays http to preserve the Phase 1 LAN stub flow, systemd unit passes https
  - stub-server/VENDOR.md local-modification-2 provenance entry and an updated re-pinning checklist covering both local modifications
  - stub-server/test_poll_cycle.py raised to 17/17 checks (default-scheme and explicit-https-scheme assertions, both local, no TLS needed)
  - deploy/ - reviewable infrastructure-as-files for the Hetzner CX22 target - not yet applied to a real VPS - inkframe.env.example, inkframe-byos.service, inkframe-poll.service/.timer, Caddyfile, provision.sh, deploy.sh, README.md, .gitignore
  - server/README.md deployment section pointing at deploy/README.md and recording the firmware-side INK_API_BASE config-only change
affects: []

tech-stack:
  added: [Caddy (VPS-side, automatic Let's Encrypt TLS), systemd timers/services (VPS-side scheduling and process supervision), hcloud CLI (installed locally via brew, not yet authenticated)]
  patterns:
    - "CLI flag over unconditional behaviour change for a scheme fix that has two live consumers (Phase 1's unproxied local LAN flow and Phase 2's Caddy-fronted VPS) - default preserves the already-shipped consumer, the new consumer passes the flag explicitly, both are asserted in the same local test run with no TLS setup required"
    - "provision.sh (idempotent, machine setup) and deploy.sh (repeatable, code-push) kept as two separate scripts rather than one, so re-running deploy.sh after a code change never re-touches ufw/SSH/Caddy config, and re-running provision.sh after a config change never re-rsyncs application code"
    - "Loopback restriction enforced at the firewall/reverse-proxy layer (ufw deny + Caddy-only forwarding) rather than patching byos_server.py's hardcoded 0.0.0.0 bind, keeping the vendored file's diff minimal per stub-server/VENDOR.md's discipline"

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
  - "Task 1 (scheme fix) and the file-artifact half of Task 2 (deploy/ infrastructure files) are complete and independently verified without needing the real VPS - committed as two atomic commits. The live-provisioning half of Task 2 (create the CX22, run provision.sh/deploy.sh against it, confirm real TLS) is a genuine authentication gate: no HCLOUD_TOKEN is present in this environment and the hcloud CLI was not previously installed. Per the executor's authentication-gate protocol, this is not a failure - automation was attempted (checked env, checked for the CLI, installed the CLI via the official Homebrew-core formula) and correctly stopped at the credential boundary rather than fabricating a provisioning result."
  - "Installed the hcloud CLI (v1.67.0) via Homebrew's official homebrew-core formula (github.com/hetznercloud/cli) ahead of the checkpoint, so provisioning can proceed immediately once HCLOUD_TOKEN is supplied - no further tooling gate remains after credentials arrive."
  - "Task 3 (physical-frame verification) was not started: it is explicitly gated on both Task 2's live provisioning (no real https://<public-host> exists yet to point the firmware at) and on Phase 1 plan 01-06 (flash and first boot), per this plan's own <prerequisites> block. Neither precondition is met yet."

patterns-established:
  - "Env-var template files (deploy/inkframe.env.example) mirror firmware/main/secrets.example.h's discipline exactly: every key present with a placeholder and a comment on where the real value comes from, paired with a scoped .gitignore rule that exists before the real file ever does."

requirements-completed: []

duration: ~45min (through this checkpoint; Task 2's provisioning and Task 3 remain)
completed: 2026-08-25
status: checkpoint
---

# Phase 2 Plan 5: Deploy to Hetzner CX22 (Checkpoint - awaiting Hetzner credentials)

**Closed the byos_server.py plaintext-image-download gap with a configurable --image-url-scheme flag, and wrote the full deploy/ infrastructure-as-files (systemd units, Caddyfile, provision/deploy scripts, runbook) for a Hetzner CX22 - blocked before live provisioning on a missing HCLOUD_TOKEN.**

## Performance

- **Duration:** ~45 min so far (Task 1 + Task 2's file artifacts)
- **Tasks:** 1 of 3 fully complete (Task 1); Task 2 partially complete (file artifacts done, live provisioning blocked); Task 3 not started (blocked on Task 2 + hardware)
- **Files modified:** 13 (4 in Task 1, 9 in Task 2's file-artifact half)

## Accomplishments
- Added `--image-url-scheme {http,https}` to `stub-server/byos_server.py` (default `http`), so the `/device/v1/display` response's `image_url` scheme is explicit and configurable instead of hardcoded to `http://` - closing the exact plaintext-downgrade gap 02-RESEARCH.md's Common Pitfall 2 and T-02-05-01 flag
- Documented the change as local modification 2 in `stub-server/VENDOR.md`, with rationale (Phase 1's plans 01-06/01-07/01-08 still depend on the local LAN stub flow, so the default cannot flip to `https` unconditionally) and updated the re-pinning checklist to cover both local modifications
- Extended `stub-server/test_poll_cycle.py` to 17/17 checks: the default scheme starts with `http://`, and a server started with `--image-url-scheme https` serves `https://` with an unchanged host and `/img/<digest>.bin` path - both assertions run entirely locally, no TLS needed
- Wrote the complete `deploy/` directory as reviewable infrastructure-as-files: `inkframe.env.example` (gitignored-secret template), `inkframe-byos.service` (unprivileged user, `--image-url-scheme https`, `EnvironmentFile=`, `Restart=always`, `NoNewPrivileges`/`PrivateTmp`/`ProtectSystem=strict`/scoped `ReadWritePaths`/`ProtectHome`), `inkframe-poll.service` + `.timer` (`Type=oneshot` `poll_loop.py --once` on a 30s cadence matching 02-01's validated interval), `Caddyfile` (nip.io-pattern reverse proxy to `127.0.0.1:8642` for automatic Let's Encrypt TLS with no owned domain required), `provision.sh` (idempotent first-run setup: service user, Python 3.12 venv, Caddy from the official apt repo with GPG verification, systemd units, ufw allowing only SSH/80/443 with the app port explicitly denied, SSH key-only hardening), `deploy.sh` (repeatable rsync + conditional pip reinstall + service restart + journald tail, never touching the env file), and `README.md` (the full runbook)
- Added a deployment section to `server/README.md` pointing at `deploy/README.md` and recording that `firmware/main/secrets.h`'s move to a real HTTPS base is a configuration-only change - `api_client.c`'s ESP-TLS certificate-bundle path is already compiled in
- Ran all locally-runnable verification: `stub-server/test_poll_cycle.py` 17/17 green, all five `server/test_*.py` harnesses green (66/66 checks, no regressions), `bash -n` clean on both shell scripts, both scripts confirmed to start with `set -euo pipefail`, the Caddyfile confirmed to contain `reverse_proxy`, `git check-ignore -q deploy/inkframe.env` confirmed to exit 0, no `npm` invocation in `provision.sh`, and the hardening directives (`NoNewPrivileges`/`PrivateTmp`/`ProtectSystem=strict`/`ReadWritePaths`/`ProtectHome`) confirmed present in `inkframe-byos.service`
- Installed the `hcloud` CLI (v1.67.0) via its official Homebrew-core formula, ahead of need, so the moment `HCLOUD_TOKEN` is available provisioning can start with no further tooling gate

## Task Commits

Each completed task/task-portion was committed atomically:

1. **Task 1: Close the plaintext image-download gap in the vendored protocol server (D-P2-07)** - `6f8ef2c` (feat) - complete
2. **Task 2 (file-artifact half): Reviewable deploy/ infra-as-files for the Hetzner CX22** - `5d34841` (feat) - complete; the live-provisioning half of Task 2 (create the real CX22, run `provision.sh`/`deploy.sh` against it, external TLS/ufw/timer verification) is **not yet done** - see Checkpoint below
3. **Task 3: Verify the live plane view on the physical frame** - not started (blocked on Task 2's provisioning and on Phase 1 plan 01-06)

## Files Created/Modified
- `stub-server/byos_server.py` - `--image-url-scheme {http,https}` argparse flag (default `http`), `/device/v1/display`'s `image_url` built from it instead of a hardcoded `http://` literal, docstring extended
- `stub-server/VENDOR.md` - local modification 2 (the scheme flag) documented with rationale and default; re-pinning checklist updated to cover both modifications
- `stub-server/test_poll_cycle.py` - `EXPECTED_CHECK_COUNT` raised 15 -> 17; `Harness.start_server()` gained an optional `image_url_scheme` parameter; two new checks (default scheme, explicit https scheme with host/path parity)
- `deploy/inkframe.env.example` - env template: `INK_BYOS_SECRET`, `INK_BYOS_PORT`, `INK_SLEEP_S`, `INK_STATE_DIR`, `INK_PUBLIC_HOST`
- `deploy/inkframe-byos.service` - systemd unit for `byos_server.py`, hardened, `--image-url-scheme https`
- `deploy/inkframe-poll.service` / `deploy/inkframe-poll.timer` - `Type=oneshot` poll cycle on a 30s timer
- `deploy/Caddyfile` - nip.io-pattern reverse proxy for automatic TLS
- `deploy/provision.sh` - idempotent VPS first-run setup script
- `deploy/deploy.sh` - repeatable rsync/restart deployment script
- `deploy/README.md` - full deployment runbook
- `deploy/.gitignore` - ignores the real `inkframe.env`
- `server/README.md` - added a "Deployment" section

## Decisions Made
- Kept `provision.sh` (idempotent machine setup) and `deploy.sh` (repeatable code push) as two separate scripts, matching the plan's own file list, so a config-only re-run never re-syncs code and a code-only re-run never re-touches ufw/SSH/Caddy.
- Did not patch `byos_server.py`'s hardcoded `0.0.0.0` bind a second time (beyond the scheme flag) - the loopback restriction is enforced at the firewall/reverse-proxy layer instead (`ufw deny 8642/tcp` plus Caddy being the only process forwarding to `127.0.0.1:8642`), keeping the vendored file's diff confined to the one flag per `stub-server/VENDOR.md`'s minimal-diff discipline. Recorded as "Known vendored behaviour" in `deploy/README.md`.
- Installed the `hcloud` CLI proactively via Homebrew's official formula, since it is Hetzner's own tool and installing it carries none of the legitimacy risk the deviation rules flag for arbitrary package installs (it is not a project dependency being added to `requirements.txt`/`package.json`, it is operator tooling for the checkpoint that follows).

## Deviations from Plan

None beyond the checkpoint itself - both completed tasks (Task 1, and Task 2's file-artifact half) were executed exactly as specified, with no auto-fixes needed.

## Issues Encountered
None beyond the expected credential gate (see Checkpoint below) - all local verification passed on the first attempt after the initial test-harness port-comparison bug (see below) was fixed.

- While writing the new `test_poll_cycle.py` scheme check, the first implementation compared the full `image_url` strings including the port number between two separately-started `Harness` instances - which legitimately differ because `Harness._pick_free_port()` binds an OS-assigned free port per instance for test isolation. Caught immediately by running the test (it failed with a clear message), fixed by comparing `urllib.parse.urlsplit()`'s `hostname` and `path` components instead of the full string. This was caught and fixed before any commit - not a deviation from the plan, just normal test-driven iteration.

## User Setup Required

**This plan is blocked on a real credential.** See the Checkpoint section below for the exact ask. In short: a Hetzner Cloud API token (read & write), confirmation that an SSH public key has been added to the Hetzner project, and confirmation that the CX22 plan is available in Falkenstein or Nuremberg - exactly the `user_setup` block already declared in this plan's own frontmatter.

## Next Phase Readiness

**Not ready to close this plan yet.** Remaining work, in order:

1. **Live provisioning (rest of Task 2):** once `HCLOUD_TOKEN` is available, create the CX22 (`hcloud server create`), run `deploy/provision.sh <public-host>` then `deploy/deploy.sh <ssh-target>` against it, and confirm the acceptance criteria this plan's `<verification>` block lists (valid Let's Encrypt TLS + 401 without a token, app port refused externally, `inkframe-poll.timer` active with successive journald cycles, `systemd-analyze verify` clean on the VPS since macOS has no local `systemd-analyze`).
2. **Task 3 (physical-frame verification):** blocked on both (1) and on Phase 1 plan 01-06 (flash and first boot) - STATE.md's hardware unblock date is 2026-08-26, one day after this session.
3. Once both are done, re-run this executor (or a continuation agent) to finish the plan, write the final SUMMARY update, and close ROADMAP Phase 2 success criterion 4.

No blockers beyond the credential gate and the hardware-arrival gate, both already anticipated in this plan's own `<prerequisites>` block.

---
*Phase: 02-plane-view-end-to-end-slice*
*Completed: checkpoint reached 2026-08-25 - plan not yet closed*

## Self-Check: PASSED

Verified all 9 `deploy/` files present on disk plus the 3 modified `stub-server/` files and `server/README.md`. Verified both commits (`6f8ef2c`, `5d34841`) present in `git log --oneline`. Independently re-ran `stub-server/test_poll_cycle.py` (17/17) and all five `server/test_*.py` harnesses (66/66) after writing this summary - all green, no regressions.
