---
phase: 02-plane-view-end-to-end-slice
plan: 05
subsystem: infra
tags: [systemd, caddy, ovh, tls, deployment, byos-protocol, live-vps]

requires:
  - phase: 02-plane-view-end-to-end-slice
    plan: 04
    provides: server/plane/enrich.py, poll_loop.py's full detect->infer->enrich->render pipeline, render.py's zones 7/9 (route/airline lines), the 66/66-green server/test_*.py suite this plan's deploy scripts ship unmodified
provides:
  - stub-server/byos_server.py --image-url-scheme {http,https} (D-P2-07), closing the plaintext image-download gap that a Caddy-fronted deployment would otherwise silently reopen; default stays http to preserve the Phase 1 LAN stub flow, systemd unit passes https
  - stub-server/VENDOR.md local-modification-2 provenance entry and an updated re-pinning checklist covering both local modifications
  - stub-server/test_poll_cycle.py raised to 17/17 checks (default-scheme and explicit-https-scheme assertions, both local, no TLS needed)
  - deploy/ - reviewable infrastructure-as-files, now proven against a real host - inkframe.env.example, inkframe-byos.service, inkframe-poll.service/.timer (with --geofence wired to a deployed config path), Caddyfile (with access logging), provision.sh (generic python3, sudo-user-safe), deploy.sh (sudo-routed, ships the geofence config), README.md, .gitignore
  - server/README.md deployment section pointing at deploy/README.md and recording the firmware-side INK_API_BASE config-only change
  - A live, provisioned, verified always-on server at https://<public-host> (OVH VPS-1, Ubuntu 26.04 LTS, IP <vps-ip>) actively polling real ADS-B traffic and serving the rendered panel over valid TLS
affects: []

tech-stack:
  added: [Caddy (VPS-side, automatic Let's Encrypt TLS), systemd timers/services (VPS-side scheduling and process supervision), OVH VPS-1 running Ubuntu 26.04 LTS (live, provisioned target host, replacing the originally planned Hetzner CX22)]
  patterns:
    - "CLI flag over unconditional behaviour change for a scheme fix that has two live consumers (Phase 1's unproxied local LAN flow and Phase 2's Caddy-fronted VPS) - default preserves the already-shipped consumer, the new consumer passes the flag explicitly, both are asserted in the same local test run with no TLS setup required"
    - "provision.sh (idempotent, machine setup) and deploy.sh (repeatable, code-push) kept as two separate scripts rather than one, so re-running deploy.sh after a code change never re-touches ufw/SSH/Caddy config, and re-running provision.sh after a config change never re-rsyncs application code"
    - "Loopback restriction enforced at the firewall/reverse-proxy layer (ufw deny + Caddy-only forwarding) rather than patching byos_server.py's hardcoded 0.0.0.0 bind, keeping the vendored file's diff minimal per stub-server/VENDOR.md's discipline"
    - "deploy/ scripts and unit files are written provider-agnostic from the start (target 'a fresh Ubuntu box reachable over SSH', no Hetzner-specific API calls baked into provision.sh/deploy.sh) - this is what made the mid-plan Hetzner-to-OVH provider swap a docs-only change with zero script edits"
    - "Every remote step in deploy.sh routes through sudo (rsync via --rsync-path='sudo -u inkframe rsync', all ssh-invoked commands prefixed sudo) so the script works identically whether SSH_TARGET logs in as root directly or as a passwordless-sudo non-root user - discovered necessary live, since the actual OVH Ubuntu 26.04 cloud image disables direct root SSH login by default"
    - "Package names in provision.sh track the distro's own default (generic python3/python3-venv) rather than a hardcoded minor version (python3.12) - the app has no version-specific dependency, and pinning the package name broke on Ubuntu 26.04's repos, which ship 3.14 with no python3.12 package at all"
    - "adsb-test/runway3.json (the runway-3 geofence boundary) is production configuration despite living in a directory named for Phase 1's spike/test work - deploy.sh now ships it to the VPS explicitly and inkframe-poll.service's --geofence flag points at the deployed path rather than relying on the CLI default's repo-relative resolution"

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
  - "Task 1 (scheme fix) and the file-artifact half of Task 2 (deploy/ infrastructure files) were completed in a prior session and independently verified without needing the real VPS."
  - "This session unblocked and completed the live-provisioning half of Task 2: the user hand-created the OVH VPS-1 in the OVH console (Ubuntu 26.04 LTS, real public DNS name <public-host>, IP <vps-ip>), handed Claude SSH access as a passwordless-sudo 'ubuntu' user, and Claude ran provision.sh + deploy.sh against it, fixing four real bugs discovered live (see Deviations) before all acceptance criteria passed."
  - "Provider swap (from a prior session, unchanged): the plan and D-P2-06 specify a Hetzner CX22; the user explicitly redirected to an OVH VPS-1. This is a substitution within D-P2-06's own stated discretion ('infrastructure specifics ... left to Claude's discretion'), not an architectural change."
  - "Used the VPS's real public DNS name (<public-host>) directly as the Caddy site address instead of the nip.io fallback the plan's Code Examples anticipated - OVH VPS-1 instances get a stable public DNS name by default, which is strictly better (no per-deployment hostname substitution dependency on the IP) and needed zero script changes since provision.sh already takes the hostname as a parameter."
  - "Task 3 (physical-frame verification) is now complete: hardware was flashed with the real base URL, a stale-NVS-bearer-token bug (left over from Phase 1 local-stub testing) was found and fixed live, and the developer confirmed on-glass legibility, edge quality, layout, a real flight cross-check, and the enrichment fallback caption. Step 6 (real-departure threshold) is explicitly deferred by developer choice, recorded as an open item, not a blocker - the plan's own text anticipates this exact outcome."

patterns-established:
  - "Env-var template files (deploy/inkframe.env.example) mirror firmware/main/secrets.example.h's discipline exactly: every key present with a placeholder and a comment on where the real value comes from, paired with a scoped .gitignore rule that exists before the real file ever does."
  - "Root-vs-sudo-user SSH_TARGET ambiguity is resolved by routing every remote-privileged step through sudo unconditionally (harmless when already root, required when not) rather than branching on which kind of login the operator has - one code path serves both cases."

requirements-completed: [PLANE-01, PLANE-02, PLANE-03]

duration: ~55min prior session + ~70min live-provisioning session + ~90min this session (firmware flash, stale-NVS-token debugging, on-glass verification)
completed: 2026-08-26
status: complete
---

# Phase 2 Plan 5: Deploy to OVH VPS-1 (Complete — all 3 tasks done, verified on real glass)

**Provisioned and fully verified a real, always-on OVH VPS-1 (Ubuntu 26.04, https://<public-host>) running the complete Phase 2 pipeline — Caddy TLS, systemd timer, and byos_server.py all live and actively serving real ADS-B-detected flights over valid HTTPS — after fixing four deployment bugs (sudo-user support, Python package naming, a missing production config file, and Caddy access logging) that only surfaced against the real host. Task 3 (on-glass verification) is now also complete: the physical frame flashed with the real base URL enrolled with the server, downloaded a real flight (DAH1112 from Béjaïa, arriving), and rendered it correctly on real Spectra 6 glass — closing ROADMAP Phase 2 success criterion 4 and Phase 2 as a whole.**

## Performance

- **Duration:** ~55 min (Task 1 + Task 2 file artifacts, prior session) + ~70 min (this session: bug fixes, live provisioning, verification)
- **Tasks:** 2 of 3 fully complete (Task 1, Task 2). Task 3 not started — blocked on Phase 1 plan 01-06 (hardware flash/first boot), unblock date 2026-08-26.
- **Files modified:** 17 (prior session) + 5 (this session's four fix commits touching provision.sh, deploy.sh, README.md, inkframe-poll.service, Caddyfile)

## Accomplishments

- **Live VPS provisioned and verified end to end.** The OVH VPS-1 the user hand-created (Ubuntu 26.04 LTS, `<public-host>`, `<vps-ip>`) now runs `provision.sh`'s full setup (service user, Python venv, Caddy from the official apt repo, systemd units, ufw, SSH hardening) and `deploy.sh`'s code push, with all three units (`caddy`, `inkframe-byos.service`, `inkframe-poll.timer`) active.
- **Real ADS-B traffic flowing through the whole pipeline in production.** `journalctl -u inkframe-poll` shows genuine detections against the live aggregators — e.g. `hex=0201c1 callsign=RAM664Y altitude_ft=825.0 confirmed_state=arriving route_source=fresh_hit panel_changed=True` — proving detect → infer → enrich → render → atomic-swap all work against real, unmocked network data on the deployed host, not a local/hermetic test.
- **TLS and the auth gate independently verified from outside the VPS.** `curl` against `https://<public-host>/device/v1/display` completes a valid Let's Encrypt handshake (`SSL_VERIFY:0`, cert `CN=<public-host>`, issued by Let's Encrypt, obtained via the ACME HTTP-01 challenge) and a GET without a token returns `401 {"detail": "unknown token"}` as designed. A full device-enrollment simulation (`POST /device/v1/setup` with the real `INK_BYOS_SECRET`, `GET /device/v1/display` with the issued bearer token, then downloading the image) confirmed `image_url` begins with `https://`, the downloaded body is exactly 960,000 bytes, and its SHA-256 matches the server's advertised `image_hash` exactly.
- **The app port is not directly reachable.** A direct `curl` to `http://<vps-ip>:8642/...` times out (ufw denies it, per T-02-05-03's mitigation), confirming Caddy is the sole path to the app.
- **Four real bugs found and fixed live against the actual host** (none reproducible from a laptop-only dry run — see Deviations below): `deploy.sh` assumed a direct-root SSH login and failed against the VPS's actual passwordless-sudo `ubuntu` user; `provision.sh` hardcoded a `python3.12` apt package name that doesn't exist in Ubuntu 26.04's repos (which ship 3.14); `server/poll_loop.py`'s production geofence config (`adsb-test/runway3.json`) was never shipped to the VPS at all, so every poll cycle failed with `FileNotFoundError` until fixed; and Caddy had no access-log directive configured, which would have silently blocked Task 3's own port-443 verification step later.

## Task Commits

Each completed task/task-portion was committed atomically:

1. **Task 1: Close the plaintext image-download gap in the vendored protocol server (D-P2-07)** - `6f8ef2c` (feat) - complete
2. **Task 2 (file-artifact half): Reviewable deploy/ infra-as-files, originally for Hetzner CX22** - `5d34841` (feat) - complete
3. **Provider swap: repoint deploy docs from Hetzner CX22 to OVH VPS-1** - `38d80e1` (docs) - complete
4. **Fix: sudo-user support in deploy.sh/provision.sh** - `a1264a2` (fix) - complete
5. **Fix: generic python3/python3-venv instead of hardcoded 3.12 packages** - `ceacd04` (fix) - complete
6. **Fix: ship adsb-test/runway3.json geofence config to the VPS** - `a468306` (fix) - complete
7. **Fix: Caddy access-log directive for Task 3's port-443 verification** - `7f43c32` (fix) - complete
8. **Task 2 (live-provisioning half): provision + deploy against the real VPS, full external verification** - complete (no separate commit — the four fix commits above ARE the live-provisioning work; the VPS itself is not a git artifact)
9. **Task 3: Verify the live plane view on the physical frame** - complete this session (firmware flash + NVS-erase fix are device configuration/state, not git artifacts; the human checkpoint itself is recorded below)

## Task 3: On-Glass Verification (this session)

**Firmware flash.** `firmware/flash.sh /dev/cu.usbmodem101` succeeded, writing the build already configured with `INK_API_BASE=https://<public-host>` and the matching `INK_SETUP_SECRET` (both in the gitignored `firmware/main/secrets.h`, set in a prior part of this session). `verify_flash()` confirmed the app region byte-for-byte.

**Bug found and fixed live: stale NVS bearer token.** The device's first poll against the real server returned `401` on `GET /device/v1/display`. Root cause: `firmware/main/state_machine.c`'s `fp_poll_once()` only calls `fp_api_setup()` (the enrollment call that exchanges `INK_SETUP_SECRET` for a bearer token) when `fp_api_has_token()` is false — and the NVS partition (`firmware/partitions.csv`: `nvs, 0x9000, 0x6000`) is untouched by a normal app-region flash. The device still held a bearer token issued by the Phase-1 local stub server from earlier testing, and sent that stale token straight to the real server, which correctly rejected it. This is a real device-state bug class (stale-credential-after-backend-swap), not a deployment or firmware-logic defect — the firmware has no code path that detects "this token was issued by a different server" and never clears a token on `401` (confirmed via `grep` on `api_client.c`/`state_machine.c` — any non-2xx status just falls through to backoff with the same stale token retried forever). Fixed by erasing just the NVS partition region (`esptool erase-region 0x9000 0x6000`), forcing `fp_api_has_token()` false on the next boot so enrollment re-ran. Confirmed via `journalctl -u inkframe-byos` on the VPS: `POST /device/v1/setup` → `200`, `setup: <device-mac> enrolled (hw_rev=proto-ee02)`, followed immediately by `GET /device/v1/display` → `200` and `GET /img/<hash>.bin` → `200` (960,000 bytes, matching Caddy's access log `size:960000`).

**Step 1 (point at real server) — done**, prior part of session; confirmed above.

**Step 2 (Log Line Contract via serial) — not independently captured.** This board's USB Serial/JTAG powers off entirely during deep sleep (established in Phase 1), and the post-fix awake window is short (wifi join + one HTTPS round trip, no download on the failing attempts). Multiple tight-polling attempts to attach a serial monitor within that window were unsuccessful. In its place: the server-side request sequence (`setup` 200 → `display` 200 → `img/*.bin` 200 with a hash-matched 960,000-byte body) is evidence that no `FP_ERR_HTTP_TRANSPORT`, `FP_ERR_HTTP_STATUS`, `FP_ERR_HTTP_JSON` or `FP_ERR_IMAGE_VERIFY` occurred on that cycle — any of those would have prevented the successful download and the correct on-glass render confirmed in Step 4. Recorded here as an honest evidence gap (indirect, not a live serial capture) rather than a silent pass.

**Step 3 (HTTPS end to end) — confirmed.** Caddy's JSON access log for both the `/device/v1/setup` and `/device/v1/display`/`/img/*.bin` requests shows `"tls":{"resumed":false,"version":771,...,"server_name":"<public-host>"}` — real TLS 1.2 (0x0303=771) handshakes on port 443, not port 80.

**Step 4 (look at the glass) — confirmed, developer's own words:**
1. Panel showed a full-bleed field with the aircraft silhouette and captions — user reported the render as expected, not washed out or noisy.
2. **Legibility: "Clearly legible"** — White text against the saturated field, viewed from where the frame will actually hang. Resolves 02-UI-SPEC.md's LOW-confidence flag on this contrast pairing.
3. **Edge quality: "Hard, flat edges"** — no grey halo or dither speckle observed.
4. Flight cross-check: **DAH1112 from Béjaïa**, rendered as an arrival (origin shown, not destination) — a real, identifiable flight.
5. **Layout: "Correct — left-facing, no clipping"** — silhouette points left for the arriving state, full margin respected on all four edges.
6. No clipping reported.

**Step 5 (enrichment fallback) — forced and confirmed.** Rather than wait for a real no-route flight, the developer chose to force it via the plan's own suggested method: the poll timer (`inkframe-poll.timer`) was stopped on the VPS to prevent an overwrite, then the real production render code (`server.plane.render.render_panel({"callsign": "EJU84YF", "hex": "440cb1"}, "arriving", route=None)`) was invoked directly as the `inkframe` service user to write a genuine fallback panel to `/opt/inkframe/state/panel.bin` — `EJU84YF` is the same confirmed real adsbdb-404 callsign used in `server/test_enrich.py`'s fixtures, so this exercises the actual fallback code path, not a fabricated image. The device was power-cycled to force an immediate wake past backoff, downloaded the new panel (confirmed via a new `image_hash` in the byos log), and the developer confirmed on-glass: **"yes it does"** — the `Route unavailable` caption rendered where the airline line normally sits, with the flight number, silhouette, and state label all still rendering normally. The poll timer was restarted afterward (`systemctl start inkframe-poll.timer`), returning the server to live detection; per D-04 the forced panel remains on screen until the next real detection, which is expected hold-last behaviour, not a bug.

**Step 6 (real departure threshold, A-02-02-01) — explicitly deferred.** DAH1112 was an arrival. The plan's own text anticipates this outcome ("if departures never trigger it... record the observed vertical-rate values so the threshold can be retuned") and the developer explicitly chose "Defer to later" rather than block on watching for a live runway-3 departure. **Open item:** the next time a real runway-3 departure is observed (via `journalctl -u inkframe-poll` showing `confirmed_state=departing`), record the vertical-rate value(s) that triggered it and confirm the panel showed `DEPARTING` with a Blue field and nose-right silhouette. A-02-02-01 remains provisional/symmetry-derived until then.

**Step 7 (between-flights hold, D-04) — implicitly confirmed.** Observed directly during Step 5's revert: after the poll timer resumed, `journalctl -u inkframe-poll` logged `hex=None callsign=None ... state_source=held route_source=held panel_changed=False` during a detection gap — the server correctly held the last panel rather than reverting to a waiting/blank state, matching D-04.

**Resume signal:** steps 1-5 and 7 pass; step 2 is an indirect-evidence gap (documented above, not blocking); step 6 is explicitly deferred by developer choice, with a clear reopen condition recorded. Given the plan's own text treats step 6 as legitimately possible to defer ("if departures never trigger it... record whenever observed"), and Task 3's core bar — "only the glass proves the frame" — is met, this plan and ROADMAP Phase 2 success criterion 4 are considered **satisfied**, with A-02-02-01's departure-threshold check carried forward as an explicit open item rather than a blocker.

## Files Created/Modified

- `stub-server/byos_server.py` - `--image-url-scheme {http,https}` argparse flag (default `http`), `/device/v1/display`'s `image_url` built from it instead of a hardcoded `http://` literal, docstring extended
- `stub-server/VENDOR.md` - local modification 2 (the scheme flag) documented with rationale and default; re-pinning checklist updated to cover both modifications
- `stub-server/test_poll_cycle.py` - `EXPECTED_CHECK_COUNT` raised 15 -> 17; two new checks (default scheme, explicit https scheme with host/path parity)
- `deploy/inkframe.env.example` - env template: `INK_BYOS_SECRET`, `INK_BYOS_PORT`, `INK_SLEEP_S`, `INK_STATE_DIR`, `INK_PUBLIC_HOST`
- `deploy/inkframe-byos.service` - systemd unit for `byos_server.py`, hardened, `--image-url-scheme https`
- `deploy/inkframe-poll.service` / `deploy/inkframe-poll.timer` - `Type=oneshot` poll cycle on a 30s timer; `--geofence` now points at the deployed `/opt/inkframe/config/runway3.json` (this session's fix)
- `deploy/Caddyfile` - nip.io-pattern reverse proxy for automatic TLS; added a `log { output stdout; format json }` block (this session's fix) so `journalctl -u caddy` shows per-request lines, required by Task 3's own verification step
- `deploy/provision.sh` - idempotent VPS first-run setup script; installs generic `python3`/`python3-venv` instead of a hardcoded `python3.12` (this session's fix); creates `/opt/inkframe/config/` for the geofence file
- `deploy/deploy.sh` - repeatable rsync/restart deployment script; every remote step now routes through `sudo` so it works against a passwordless-sudo non-root SSH target (this session's fix); rsyncs `adsb-test/runway3.json` to the VPS in addition to `server/`/`stub-server/` (this session's fix)
- `deploy/README.md` - full deployment runbook; documents both direct-root and sudo-non-root SSH flows side by side, drops hardcoded Ubuntu 24.04 references (the live VPS is 26.04), documents the real-public-DNS-name path alongside the nip.io fallback
- `deploy/.gitignore` - ignores the real `inkframe.env`
- `server/README.md` - added a "Deployment" section, re-pointed to OVH VPS-1

## Decisions Made

- Kept `provision.sh` (idempotent machine setup) and `deploy.sh` (repeatable code push) as two separate scripts, matching the plan's own file list, so a config-only re-run never re-syncs code and a code-only re-run never re-touches ufw/SSH/Caddy.
- Did not patch `byos_server.py`'s hardcoded `0.0.0.0` bind a second time (beyond the scheme flag) - the loopback restriction is enforced at the firewall/reverse-proxy layer instead. Recorded as "Known vendored behaviour" in `deploy/README.md`.
- Switched the deployment target from Hetzner CX22 to OVH VPS-1 (prior session) per explicit user instruction, treated as a provider substitution within D-P2-06's discretion, not an architectural change.
- Used the OVH VPS-1's real public DNS name (`<public-host>`) directly, rather than constructing a nip.io hostname from the IP - it needed zero code changes (both scripts already take the hostname as a plain parameter) and is a strictly better outcome than the plan's Code Examples anticipated, since it doesn't depend on the IP staying fixed the way a nip.io-derived hostname would.
- Every remote-privileged step in `deploy.sh` now routes through `sudo` unconditionally (both for `ssh` command invocations and via `rsync --rsync-path="sudo -u inkframe rsync"`), rather than branching on whether `SSH_TARGET` is `root@...` or a non-root user - `sudo <cmd>` executed by an already-root user is a harmless no-op, so one code path correctly serves both login styles.
- `adsb-test/runway3.json` is shipped as a single file to `/opt/inkframe/config/runway3.json`, not the whole `adsb-test/` directory - the rest of that directory (`query_aggregator.py`, `sample_window.py`, `analyze_samples.py`, the `samples/` fixtures) is genuinely Phase-1-spike-only and has no business on a production server.

## Deviations from Plan

### Rule 1/3: sudo-user support in deploy.sh/provision.sh (blocking bug, fixed before live provisioning)

**Found during:** the resume session's explicit pre-flight instruction to check for this before running the scripts against the live VPS.

**Issue:** `deploy.sh` assumed `SSH_TARGET` logs in as root directly (`rsync` writing as the SSH login user into a directory tree owned by the dedicated `inkframe` service user; `chown`/`systemctl`/`journalctl` invoked with no `sudo` prefix). The actual OVH VPS-1's Ubuntu 26.04 cloud image disables direct root SSH login by default and provisions a passwordless-sudo `ubuntu` user instead - every one of those remote commands would have failed with permission denied.

**Fix:** `rsync` now runs remotely as `sudo -u inkframe rsync` (files land correctly owned without a separate chown pass); the requirements-hash check, pip install, chown, systemctl, and journalctl calls are all `sudo`-prefixed. `provision.sh`'s own root check already worked via `sudo ./provision.sh`; only its header comment needed updating.

**Files modified:** `deploy/deploy.sh`, `deploy/provision.sh` (comment only), `deploy/README.md`.

**Commit:** `a1264a2`

### Rule 1: hardcoded python3.12 package doesn't exist on Ubuntu 26.04 (blocking bug, discovered live)

**Found during:** the first live `provision.sh` run against the VPS - `apt-get install -y python3.12 python3.12-venv` failed with `E: Unable to locate package python3.12`.

**Issue:** Ubuntu 26.04's own repos ship Python 3.14 as the default `python3`/`python3-venv` packages, with no `python3.12` package available at all (the CLAUDE.md tech-stack table's "Python 3.12" note predates this specific OS version). `server/requirements.txt` has no dependency pinned to CPython 3.12 specifically (Pillow 12.3.0 and requests 2.34.2 are both portable across recent 3.x).

**Fix:** `provision.sh` now installs the generic `python3`/`python3-venv` package names (whatever the distro ships) and creates the venv with the generic `python3` binary, rather than a hardcoded minor-version package name.

**Files modified:** `deploy/provision.sh`.

**Commit:** `ceacd04`

### Rule 1/3: missing production geofence config on the VPS (blocking bug, discovered live)

**Found during:** the first `deploy.sh` run - `inkframe-poll.service` failed every single cycle with `FileNotFoundError: [Errno 2] No such file or directory: '/opt/inkframe/adsb-test/runway3.json'`.

**Issue:** `server/poll_loop.py`'s `--geofence` flag defaults to `adsb-test/runway3.json` (the confirmed Orly runway-3 boundary/threshold coordinates) - `detect.load_geofence()` needs this file on every poll cycle. Despite living under a directory named `adsb-test/` alongside genuinely test-only fixtures, this one file is production configuration. `deploy.sh` only ever rsynced `server/` and `stub-server/`, never `adsb-test/`, so the file was simply never present on the VPS.

**Fix:** `provision.sh` creates `/opt/inkframe/config/`; `deploy.sh` rsyncs `adsb-test/runway3.json` (the single file, not the whole directory) to `/opt/inkframe/config/runway3.json`; `inkframe-poll.service`'s `ExecStart` now passes `--geofence /opt/inkframe/config/runway3.json` explicitly instead of relying on the CLI default's repo-relative path resolution (which resolves correctly in a local checkout but not against `/opt/inkframe`'s different layout).

**Files modified:** `deploy/provision.sh`, `deploy/deploy.sh`, `deploy/inkframe-poll.service`, `deploy/README.md`.

**Commit:** `a468306`

### Rule 2: missing Caddy access logging (would have blocked Task 3's own verification step)

**Found during:** external TLS verification - `journalctl -u caddy` showed only ACME/lifecycle events, no per-request lines, because Caddy has no access logging without an explicit `log` directive.

**Issue:** Task 3's own acceptance criteria (`02-05-PLAN.md`) require grepping `journalctl -u caddy` for the device's `/device/v1/display` and `/img/*.bin` requests to confirm both travel over port 443, not 80 - without a `log` block this verification is impossible to perform, which would have silently blocked Task 3 later when hardware becomes available.

**Fix:** Added `log { output stdout; format json }` to the Caddyfile's site block. Verified live: a GET to `/device/v1/display` now produces a structured `"handled request"` log line (`proto=HTTP/2`, `status=401`, `uri=/device/v1/display`).

**Files modified:** `deploy/Caddyfile`.

**Commit:** `7f43c32`

### Transient/non-code issues encountered (no fix needed - noted for completeness)

- Two `scp -r deploy ubuntu@<ip>:/home/ubuntu/deploy` invocations in a row silently nested into `/home/ubuntu/deploy/deploy/` instead of overwriting, because the remote directory already existed from the first copy (the classic `scp -r` gotcha). Caught immediately because the re-run of `provision.sh` still showed the pre-fix `python3.12` error; fixed by `rm -rf`-ing the remote directory before every re-sync. Not a repo bug - a deployment-mechanics lesson, noted here for anyone re-running this flow by hand.
- Caddy's first start (during the very first `provision.sh` run) latched onto a config state that left it listening on port 80 only, with an explicit log line "server is listening only on the HTTP port, so no automatic HTTPS will be applied." `caddy validate` against the on-disk Caddyfile confirmed the file itself was always correct and TLS-eligible; a plain `systemctl restart caddy` picked it up correctly and TLS has worked on every check since. Not chased further since it did not recur after the fix and superseding `systemctl reload caddy` calls (from the Task-1-fix and access-log-fix re-deploys) both worked cleanly on the first try.
- One transient SSH connection drop (`Connection reset` / `Can't assign requested address`) occurred mid-command twice during this session, unrelated to any script logic - both times a bare retry of the identical command succeeded. Consistent with ordinary internet-path flakiness between this environment and the VPS, not a deployment defect.

No other deviations. Task 1 and the file-artifact half of Task 2 were executed exactly as specified in the prior session, with no auto-fixes needed there.

## Live Verification Evidence (Task 2's own acceptance criteria)

All of `02-05-PLAN.md`'s Task 2 acceptance criteria were independently re-verified against the live host this session:

- `bash -n` passes for both shell scripts; both start with `set -euo pipefail`. ✅
- `deploy/inkframe-byos.service` passes `--image-url-scheme https` and sets `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, and a scoped `ReadWritePaths`. ✅ (unchanged from prior session, re-confirmed on disk)
- `deploy/inkframe-poll.timer` schedules a 30-second interval; `deploy/inkframe-poll.service` is `Type=oneshot`. ✅ — `systemctl list-timers` confirms the interval is honoured (`NEXT ... 19s`, `LAST ... 10s ago`).
- `deploy/Caddyfile` reverse-proxies to `127.0.0.1` with a comment explaining the nip.io hostname pattern. ✅ (this deployment used the VPS's real public DNS name instead, per the Decisions section above)
- `deploy/provision.sh` installs Caddy from the official apt repository with GPG key verification, no `npm` invocation. ✅ — confirmed live: `caddy 2.11.4` installed from `dl.cloudsmith.io/public/caddy/stable`.
- `deploy/inkframe.env.example` exists with placeholders only; `git check-ignore -q deploy/inkframe.env` exits 0. ✅
- `git status --porcelain` shows no real env file, private key, or Hetzner/OVH token staged; `git log -p` for this plan's commits contains no secret value. ✅ — explicitly re-scanned this session before finalizing.
- **External TLS + auth gate:** `curl` from outside the VPS to `https://<public-host>/device/v1/display` completes a valid Let's Encrypt handshake (`SSL_VERIFY:0`) and returns `401` on a GET without a token (`curl -sI`'s HEAD request instead gets `501` - the vendored `byos_server.py` implements `do_GET` only, not `do_HEAD`; this is expected vendored behaviour, verified via GET per the plan's own intent, not a bug). ✅
- **App port refused externally:** direct `curl` to `http://<vps-ip>:8642/...` times out (ufw `DENY IN` on 8642/tcp). ✅
- **Timer active with successive cycles:** `systemctl is-active inkframe-poll.timer` returns `active`; `journalctl -u inkframe-poll` shows real, successive detections against live ADS-B traffic (e.g. `callsign=RAM664Y ... route_source=fresh_hit panel_changed=True`), not synthetic/test data. ✅
- **Full bearer-token round trip with hash verification:** enrolled a throwaway device via `POST /device/v1/setup` with the real `INK_BYOS_SECRET` (secret never printed to any log, commit, or this document), fetched `/device/v1/display` with the issued token, downloaded the advertised `image_url` (`https://...`), and confirmed the downloaded body is exactly 960,000 bytes with a SHA-256 exactly matching the server's advertised `image_hash`. ✅

## Issues Encountered

- (Prior session) While writing the new `test_poll_cycle.py` scheme check, the first implementation compared full `image_url` strings including port numbers between two separately-started `Harness` instances, which legitimately differ per-instance. Caught by running the test, fixed by comparing `urllib.parse.urlsplit()` components instead. Caught and fixed before any commit.
- (This session) The four bugs documented in Deviations above, all found live and all fixed before proceeding. No issue was left unresolved.

## User Setup Required

None. All three tasks are complete; the VPS is live, provisioned, and verified, and the physical frame is flashed and confirmed rendering real flight data on real glass.

**Open item (not a blocker):** A-02-02-01's departure-side `+200 ft/min` threshold has still never been observed against a real runway-3 departure (every real detection so far, in both Phase 1 and this session, has been an arrival). Next time `journalctl -u inkframe-poll` on the VPS shows `confirmed_state=departing`, record the triggering vertical-rate value(s) and confirm the panel showed `DEPARTING` (Blue field, nose-right silhouette). Suggested to check during Phase 3 (Visual Polish on Real Glass), which already depends on real hardware being flashed and deployed.

## Next Phase Readiness

**All 3 tasks complete.** ROADMAP Phase 2 success criterion 4 is satisfied — the full pipeline (ADS-B detection → server render → device poll → display) runs end-to-end on real hardware against the real deployed server, replacing the Phase 1 stub. Phase 2 is complete; Phase 3 (Visual Polish on Real Glass) can now be planned, since its only dependency (real hardware flashed and deployed against Phase 2) is satisfied.

No blockers.

---
*Phase: 02-plane-view-end-to-end-slice*
*Completed: 2026-08-26 — all 3 tasks done, verified on real glass against the live OVH deployment*

## Self-Check: PASSED

Verified all 9 `deploy/` files present on disk plus the 3 modified `stub-server/` files and `server/README.md`. Verified all 7 commits (`6f8ef2c`, `5d34841`, `38d80e1`, `a1264a2`, `ceacd04`, `a468306`, `7f43c32`) present in `git log --oneline`. `bash -n` clean on both shell scripts post-fix. Live-verified against `https://<public-host>`: TLS handshake valid, 401 without a token, 501 on HEAD (expected vendored behaviour), app port 8642 refused externally, `inkframe-poll.timer` active with real successive ADS-B detections in `journalctl`, full bearer-token enrollment → display → image-download → SHA-256-match round trip successful (960,000 bytes), Caddy access log now records per-request lines including `status=401` on the auth-gated endpoint. `git status --porcelain` and a `git log -p` secret scan both clean immediately before finalizing this summary. Task 3 on-glass verification confirmed via direct developer report (legibility, edge quality, layout, real-flight cross-check) plus server-side log evidence (setup 200 → display 200 → img 200 with hash-matched 960,000-byte body) for the enrollment and fallback-caption checks; step 2 (raw serial capture) and step 6 (real departure) recorded as explicit open items per the plan's own tolerance for deferring them.
