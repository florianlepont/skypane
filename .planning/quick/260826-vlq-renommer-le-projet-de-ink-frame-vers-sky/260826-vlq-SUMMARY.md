---
phase: quick-260826-vlq
plan: 01
subsystem: infra
tags: [rename, systemd, esp-idf, cmake, deploy, ovh-vps]

requires: []
provides:
  - "SkyPane name applied to all live documentation and cosmetic code identifiers"
  - "Firmware renamed (CMake project, log tag, NVS namespace, SKYPANE_ macro prefix), containerized build verified green, artifact skypane.bin produced"
  - "Deployment artifacts (systemd units, deploy.sh, provision.sh, Caddyfile comment, env template) renamed locally, nothing yet sent to the VPS at that point"
  - "Live OVH VPS cut over: service account renamed in place (UID/GID preserved), application root moved intact, env file rewritten, new units installed and enabled, old units removed, deploy.sh run against the renamed root"
affects: [quick-260826-vlq-task-5-github-rename]

tech-stack:
  added: []
  patterns:
    - "systemd service-account rename via usermod -l/groupmod -n (UID/GID-preserving) instead of new-account + chown, to avoid a state-file ownership window"
    - "Application-root migration via a single same-filesystem mv (byte-for-byte, ownership-preserving) rather than copy+delete"

key-files:
  created:
    - deploy/skypane-byos.service
    - deploy/skypane-poll.service
    - deploy/skypane-poll.timer
    - deploy/skypane.env.example
  modified:
    - .claude/CLAUDE.md
    - README.md
    - ARCHITECTURE.md
    - server/README.md
    - firmware/CMakeLists.txt
    - firmware/main/*.c
    - firmware/main/*.h
    - deploy/deploy.sh
    - deploy/provision.sh
    - deploy/Caddyfile
    - deploy/README.md
    - .planning/STATE.md (additive only)
    - .planning/quick/260826-vlq-renommer-le-projet-de-ink-frame-vers-sky/260826-vlq-CONTEXT.md (hostname redaction only)

key-decisions:
  - "CONTEXT.md's real VPS hostname replaced with the deploy/README.md-established generic template form (vps-<id>.vps.ovh.net) rather than the <vps-ssh-target> placeholder, per Task 1's explicit instruction and to satisfy its own verify block; this generic OVH naming-convention template is not itself a secret"
  - "STATE.md's two forward-looking blocker bullets got their post-rename parentheticals as new appended lines rather than inline text additions, so git diff --numstat shows zero deletions (true additive-only edit, not just conceptually additive)"
  - "Gate 5 (device bearer-token survival) did not appear in this session's first ~20 minutes of monitoring, because the frame had already stopped polling the server roughly 3.5 hours before this session's cutover began (last real device request logged at 17:52:45, unrelated to this plan's work). Verified the identical outcome synthetically first (replayed the real device's own stored bearer token via the exact public HTTPS path, 200, zero 401s), then an extended background watch caught the real device reconnecting on its own (X-Boot-Reason=power-on) and completing a genuine 200 display poll + image download - gate 5 is now confirmed by both synthetic and real-device evidence"

requirements-completed: [QT-VLQ-01, QT-VLQ-02, QT-VLQ-03, QT-VLQ-04]

duration: ~90min (Tasks 1-4 to this point)
completed: 2026-08-26
status: in-progress
---

# Quick Task 260826-vlq: Rename Ink Frame -> SkyPane (Tasks 1-4) Summary

**Renamed all live documentation, firmware C sources/build artifact, and deployment tooling from Ink Frame to SkyPane, and cut the live OVH production VPS over to the new systemd units and application root — Task 5 (GitHub repo rename) intentionally not started, pending the developer's own physical-frame confirmation.**

## Performance

- **Tasks 1-3 duration:** ~35 min
- **Task 4 (VPS cutover) duration:** ~55 min, including diagnostic verification and an extended wait that ultimately caught the real device reconnecting and confirming gate 5 directly
- **Started:** 2026-08-26T~20:50:00Z (approx, first file read)
- **Task 4 downtime window:** 2026-08-26T21:09:25Z (services stopped) -> 2026-08-26T21:10:54Z (skypane-byos back up and serving) - approximately 89 seconds
- **Tasks completed:** 4 of 5 (Task 5 deliberately not started - orchestrator checkpoint)
- **Files modified:** 26 (Task 1) + 14 (Task 2) + 11 (Task 3) = 51 repository files across 3 commits; Task 4 touched zero repository files (VPS-only)

## IMPORTANT: Security incident during Task 4 diagnostics

While root-causing an apparent (later disproven) auth failure during Task 4's gate-5 investigation, one diagnostic command
(`cat /proc/<pid>/cmdline` on the running `skypane-byos.service` process, to confirm the correct binary/args were running
post-cutover) printed the live `SKYPANE_BYOS_SECRET` value in its command-line output. This value has NOT been written to
any file in this repository, has NOT been committed, and has NOT been repeated anywhere after that single tool-output
occurrence - but it did appear once in this session's tool-call transcript.

**This value never enters git or any file the plan writes**, so there is no code-level cleanup needed, but the developer
should be aware their terminal/session transcript for this dispatch contains that secret in plaintext and should treat
it as compromised. **Recommended developer action (not performed by this dispatch, out of Task 4's scope):** rotate
`SKYPANE_BYOS_SECRET` on the VPS (`/opt/skypane/skypane.env`) the next time the physical device is reflashed with a
matching `SKYPANE_SETUP_SECRET` value in `firmware/main/secrets.h` — the setup secret is only used during the one-time
enrollment call (`POST /device/v1/setup`), not for the device's ongoing bearer-token polling, so this exposure does not
affect the frame's current live operation, but it should still be rotated as a precaution before it's needed again.

## Accomplishments

- **Task 1** — Renamed the project across all live documentation and cosmetic code identifiers: `README.md`, `ARCHITECTURE.md`, `.claude/CLAUDE.md`, `pyproject.toml`, `scripts/run-all-tests.sh`, `scripts/check-attribution.sh`, `server/README.md`, `server/plane/detect.py`/`enrich.py` (User-Agent strings), three `server/test_*.py` tempfile prefixes, `server/assets/icons/illustrations/HANDOFF.md`, `stub-server/VENDOR.md`, `stub-server/byos_server.py` (local-modifications docstring line only), `adsb-test/query_aggregator.py` (User-Agent), `hardware/BOM.md`/`BATTERY-RUN.md`/`BRINGUP-LOG.md` (titles only — captured console transcripts left byte-identical), `hardware/logtools.py` (docstring/argparse/comment, regexes untouched), `.planning/PROJECT.md`/`ROADMAP.md`/`REQUIREMENTS.md`. `.planning/STATE.md` got two additive-only parenthetical lines (zero deletions, verified via `git diff --numstat`). The quick-task `CONTEXT.md`'s real VPS hostname was replaced with the established generic placeholder pattern before commit. All 9 test harnesses, `ruff check .`, and `scripts/check-attribution.sh` still pass.
- **Task 2** — Renamed the firmware: CMake `project(inkframe)` -> `project(skypane)` (drives the build artifact filename), ESP log tag and NVS namespace value -> `"skypane"` in `app_main.c`/`state_machine.c`/`nvs_schema.h` (the five Log Line Contract line *shapes* are untouched, only the tag preceding them changed), and the `INK_` credential macro prefix -> `SKYPANE_` across `secrets.example.h`, `wifi.c`/`.h`, `api_client.c`/`.h`, `state_machine.c`, plus matching updates to `firmware/VENDOR.md` and both GitHub Actions workflow files. The **local, gitignored** `firmware/main/secrets.h` had its four macro *names* renamed in place via an anchored `sed` substitution; every macro *value* was left byte-identical and never printed; this edit is deliberately not committed. The containerized build (`firmware/build.sh`, `espressif/idf:v5.3.1`) ran clean, emitting `firmware/build-ee02/skypane.bin`. Per D-02, the physical device is **not reflashed** by this task — it keeps running its previous firmware image (old NVS namespace, old log tag) against the renamed server, which is safe because the device/server protocol is plain HTTPS over three endpoints, decoupled from service names, the NVS namespace, and macro names. When the developer eventually reflashes, the new (empty) namespace will trigger a fresh `/device/v1/setup` enrollment, which will succeed because the firmware's setup-secret value still equals the server's BYOS secret value (both preserved unchanged by this plan).
- **Task 3** — `git mv`'d the four deployment artifacts to their new names (`skypane-byos.service`, `skypane-poll.service`, `skypane-poll.timer`, `skypane.env.example`) and rewrote their contents: `Description=`, `User=`/`Group=`, `EnvironmentFile=`, `WorkingDirectory=`, `ExecStart=`, `ReadWritePaths=`, and the timer's `Unit=` cross-reference all take the new name and `/opt/skypane` application root; env-var references take the `SKYPANE_` prefix. `deploy.sh`/`provision.sh` had `APP_ROOT`/`APP_USER`, all rsync/systemctl/journalctl invocations, and unit-install paths renamed. `deploy/Caddyfile`'s header comment and BYOS-unit cross-reference were updated; the site block, proxy target, and log directive were deliberately left untouched (Caddy on the VPS is not touched by Task 4). `deploy/README.md` had every occurrence renamed across the walkthrough, health-check, rollback, and secrets-hygiene sections, with the existing `<vps-ip>`/`vps-<id>.vps.ovh.net` placeholder forms left untouched. Both `.gitignore` files got their env-file ignore entries renamed to `skypane.env`. Nothing was sent to the VPS in this task.
- **Task 4** — Cut the live OVH VPS over to the new names, following the plan's ordered steps exactly to protect the device's bearer token (T-VLQ-01):
  1. **Pre-flight (read-only):** confirmed both old units active, app root and state dir present, state file present, env file owner/mode `inkframe:inkframe 600`, app root `inkframe:inkframe 750`, UID 999 / GID 986.
  2. **Quiesce:** stopped `inkframe-poll.timer`, `inkframe-poll.service`, `inkframe-byos.service`; disabled the byos service and poll timer. Downtime started here (2026-08-26T21:09:25Z).
  3. **Account rename in place:** `usermod -l skypane inkframe` + `groupmod -n skypane inkframe` + `usermod -d /opt/skypane skypane` — confirmed UID 999 / GID 986 preserved.
  4. **Application-root move:** single `mv /opt/inkframe /opt/skypane` — confirmed the state subtree (including `byos_state.json`, the bearer-token store) carried over intact, ownership `skypane:skypane` preserved.
  5. **Environment file rewrite:** renamed to `skypane.env`, rewrote all 5 variable keys with an anchored substitution (values never printed, verified by count only: 5 keys before, 5 after, 0 old-prefix keys remaining), rewrote the state-dir *value*'s path portion (`/opt/inkframe` -> `/opt/skypane`), re-asserted owner/mode `skypane:skypane 600` matching Step 0.
  6. **Virtualenv rebuild:** removed the moved (stale-shebang) venv, recreated it at `/opt/skypane/venv` as the `skypane` user, confirmed the new shebang points at the new path, deleted the requirements-hash marker so `deploy.sh` reinstalls on next run.
  7. **Unit swap:** copied the three renamed unit files to the VPS, installed them at mode 644, removed the three old-named unit files, `daemon-reload`, enabled the new byos service and poll timer. Caddy was left completely untouched and remained active throughout.
  8. **Deploy:** ran `deploy/deploy.sh <vps-ssh-target>` from the repository root — reinstalled the (changed-hash) pinned requirements, restarted `skypane-byos.service`, started `skypane-poll.timer`, both came up clean.
  9. **Health gates** (see below) — all 7 automated gates PASS, including gate 5 confirmed directly by the real physical device reconnecting during an extended post-deploy watch.

## Task 4 Health Gates — Results and Evidence

| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 1 | New BYOS service active | **PASS** | `systemctl is-active skypane-byos.service` -> `active` |
| 2 | New poll timer active | **PASS** | `systemctl is-active skypane-poll.timer` -> `active` |
| 3 | Zero old-named units on the box | **PASS** | `systemctl list-unit-files` and `/etc/systemd/system` both show 0 matches for `^inkframe` |
| 4 | Poll unit journal shows a real, completed detect/render pass since cutover | **PASS** | Multiple real cycles observed post-cutover, e.g. `poll_loop: hex=39de50 callsign=TVF27SZ altitude_ft=0.0 confirmed_state=arriving render_state=arriving state_source=held route_source=miss panel_changed=True` and a later `hex=4952c8 callsign=TAP442 ... panel_changed=True` — genuine detect/enrich/render passes, not startup lines |
| 5 | **Decisive gate:** the device's own display request answered 200, zero 401s | **PASS — confirmed by the real device** | See "Gate 5: confirmed by the real device" below. |
| 6 | Unauthenticated request over HTTPS returns 401 | **PASS** | `curl -sI https://<public-host>/device/v1/display` (no Authorization header) -> `401`, confirmed in Caddy's own access log (`"status":401`) |
| 7 | App port not externally reachable | **PASS** | `nc -z -w 5 <public-host> 8642` from the laptop timed out/refused (never connected); `ufw status` on the VPS shows `8642/tcp DENY Anywhere` (and v6) |
| — | Human-check: physical frame still refreshing | **UNCONFIRMED — AWAITING DEVELOPER** | Cannot be performed by this dispatch (no visual access to the device). Explicitly not assumed passed, even though gate 5's automated evidence is now conclusive. |

### Gate 5: confirmed by the real device

The physical frame sent no request during this session's first ~20 minutes of monitoring — cross-checking Caddy's
structured access log showed every `/device/v1/display` hit in that window came from this session's own diagnostic
tooling (`curl/8.18.0` for the gate-6 check, `Python-urllib/3.14` for a synthetic token-replay proof: replayed the
real device's own stored bearer token, MAC `94:a9:90:cf:80:08`, via loopback and via the public HTTPS path, both
returning HTTP 200 with zero 401s — direct proof the token in `byos_state.json` survived the move intact).

An extended background watch (started after the synthetic checks, ~9 more minutes) then caught the **real physical
device reconnecting on its own** at 21:39:42, identified unambiguously by Caddy's access log:

- `User-Agent: "ESP32 HTTP Client/1.0"`, real external client IP (not loopback, not this laptop)
- Real telemetry headers: `X-Fw-Version=0.1.0-p1`, `X-Boot-Reason=power-on`, `X-Rssi=-73`, `X-Battery-Mv=0`
- `GET /device/v1/display -> status 200`
- Followed 2 seconds later by `GET /img/e1922a638d82f84a2fb403ef7cd26b43b54405e3065a89c41c044e176092d0b0.bin -> status 200` (the device downloading the panel image the display response pointed it at)

Querying every Caddy log entry from that same real device IP since the cutover confirms **exactly two requests, both
`200`, zero `401`s.** This is the literal, decisive gate-5 evidence the plan asked for, not just the synthetic
substitute: the real device's own bearer token, unchanged since before this session, authenticated successfully
against the renamed `skypane-byos.service` after the full account-rename + application-root-move migration. T-VLQ-01
did not materialize.

(`X-Boot-Reason=power-on` indicates the device was power-cycled at some point during its earlier silence — consistent
with a normal reset, not evidence of any problem this plan caused.)

**Why the earlier absence of live traffic was not treated as a gate failure requiring rollback:** cross-referencing the
VPS's *pre-existing* journal history (retained under the old `inkframe-byos` unit name) showed the physical frame's
prior real `/device/v1/display` request was logged at **17:52:45** — roughly **3.5 hours before this session's Task 4
work even began** (downtime window opened 21:09:25). The device's earlier silence therefore predated and was unrelated
to this cutover. Waiting for it to reconnect on its own, rather than rolling back a verified-healthy, token-intact
migration on the basis of an absence of observed traffic, was the correct call — and it did in fact reconnect
successfully, confirming that judgment.

## Task Commits

1. **Task 1: Rename documentation and cosmetic code identifiers** — `7c1f0fe` (docs)
2. **Task 2: Rename firmware C sources, build artifact, and macro prefix** — `a6b5d50` (feat)
3. **Task 3: Rename deploy unit files, scripts, and env template (local only)** — `fab6c7a` (feat)
4. **Task 4: Cut the live production VPS over to the new names** — no repository commit (VPS-only, per its `<files>` declaration: "no repository files")

## Files Created/Modified

See frontmatter `key-files`. Full list: 26 files in Task 1's commit, 14 in Task 2's, 11 in Task 3's (4 as `git mv` renames). Task 4 touched zero repository files — it operated entirely on the live VPS's filesystem, systemd configuration, and running services.

## Decisions Made

- CONTEXT.md's hostname redaction used the plan-specified generic OVH template form (`vps-<id>.vps.ovh.net`), matching the exact literal already established in `deploy/README.md`, rather than the more generic `<vps-ssh-target>` placeholder — this satisfies the plan's own automated verify check and is not itself a secret (it's a documented naming-convention template, not a real value).
- STATE.md's two required parentheticals were added as new lines rather than inline appends, to genuinely satisfy "zero deletions" at the `git diff --numstat` level, not just in spirit.
- Two of the plan's own verify-block shell snippets (Task 2's and Task 3's `rg -c ... | rg -ic ...` zero-match checks) have a `ripgrep` quirk: `rg -c` prints nothing and exits 1 on zero matches (rather than printing `"0"`), so `test "$(...)" = "0"` evaluates false even when the substantive condition (zero old-name tokens remaining) is genuinely true. Re-verified both with an equivalent `| wc -l | tr -d ' '` normalization, which confirmed `0` in both cases. Documented here rather than silently treated as failing gates.
- Gate 5 substitute-evidence decision: see the dedicated section above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] STATE.md edit initially failed its own "zero deletions" requirement**
- **Found during:** Task 1 verification
- **Issue:** Appending the required post-rename parentheticals inline at the end of the two existing bullet lines caused `git diff --numstat` to report those two lines as 1 deletion + 1 addition each (a line-level diff always represents a modified line as delete-then-add), failing the plan's explicit "zero deleted lines" done criterion.
- **Fix:** Re-did the edit as new lines appended immediately after each original (untouched) bullet, so the diff shows pure additions (2 insertions, 0 deletions).
- **Files modified:** `.planning/STATE.md`
- **Verification:** `git diff --numstat .planning/STATE.md` -> `2  0  .planning/STATE.md`
- **Committed in:** `7c1f0fe` (Task 1 commit)

**2. [Rule 1 - Bug, investigation only, no code change] Misdiagnosed device 401s that were actually my own diagnostic traffic**
- **Found during:** Task 4 gate-5 investigation
- **Issue:** `byos_server.py`'s vendored logging only prints a telemetry line on requests that include real firmware telemetry headers — which my own `curl`/`python-urllib` diagnostic requests never send, success or not. I initially misread the absence of telemetry lines as evidence of live 401s from the physical device.
- **Fix:** Cross-referenced Caddy's structured JSON access log, which records the actual HTTP status and real `User-Agent` per request, and confirmed every observed `/device/v1/display` hit since cutover came from my own tooling (`curl/8.18.0`, `Python-urllib/3.14`), not firmware. No code or configuration change was needed — this was a diagnostic dead-end, not a real problem.
- **Files modified:** none (investigation only)
- **Verification:** Caddy access log entries showing `curl`/`Python-urllib` user-agents matching my own command timestamps exactly.
- **Committed in:** n/a (no commit; Task 4 has no repository files)

---

**Total deviations:** 2 (1 auto-fixed STATE.md formatting issue, 1 investigation-only misdiagnosis corrected before drawing conclusions). Neither affected scope or introduced unplanned changes.

## Issues Encountered

**Security note (see the dedicated section above):** a diagnostic `/proc/<pid>/cmdline` inspection during Task 4 troubleshooting printed the live `SKYPANE_BYOS_SECRET` value into this session's tool output once. Never written to a file, never committed. Flagged prominently for the developer; recommended rotation on next firmware reflash.

**Gate 5 (device bearer-token survival) was not immediately observable** because the physical frame had already stopped polling the server ~3.5 hours before this session began, for reasons unrelated to this plan. Addressed first via synthetic token-replay proof, then **confirmed directly** when an extended background watch caught the real device reconnecting on its own and completing a genuine 200 poll + image download (see the Health Gates table above). Task 5 still waits for the developer's own visual confirmation — see "AWAITING DEVELOPER CONFIRMATION" below — but the automated risk (T-VLQ-01) is now fully closed out.

## User Setup Required

None - no external service configuration required. (Task 4's VPS reconfiguration was performed by this dispatch, not left for the user.)

## AWAITING DEVELOPER CONFIRMATION

**Task 5 (GitHub repository rename) has intentionally NOT been started.** Per the orchestrator's explicit instruction for this dispatch, this quick task stops here so the developer can personally confirm the physical frame is still displaying and refreshing correctly before the least-reversible step (renaming the public GitHub repository) proceeds.

**Update: the automated risk this check exists to catch (T-VLQ-01, the device getting permanently locked out) is now
directly disproven** — the real physical device reconnected on its own during this session (21:39:42 UTC) and
successfully completed a display poll + image download against the renamed server (see Gate 5 above). The remaining
ask is purely the visual confirmation the plan's `<human-check>` item requires, which this dispatch has no way to
perform itself:

1. Look at the physical frame. It should be showing a rendered panel and should refresh on its normal wake/poll cycle.
2. Given the real device already successfully polled and downloaded a fresh image at 21:39:42 UTC this session, the panel should already reflect that — if it looks frozen, blank, or stale despite that, it would warrant a second look before Task 5 proceeds.
3. Once confirmed, re-invoke this quick task's execution to run Task 5.

**Also flag for the developer's attention (not blocking Task 5, but should not be forgotten):** the `SKYPANE_BYOS_SECRET` exposure noted above — plan to rotate it on the VPS the next time the firmware is reflashed with a matching value.

## Next Phase Readiness

- Tasks 1-3 are fully committed, verified, and require no further action.
- Task 4's live cutover is complete and healthy by every automated measure, including a direct real-device confirmation of gate 5; only the human's own visual look at the physical frame remains outstanding.
- Task 5 (GitHub repo rename, remote repoint, push, stale-deployment rejection) is fully specified and ready to execute once the developer gives the go-ahead.
- The local directory rename (`/Users/florian/Projects/ink-frame` -> `/Users/florian/Projects/skypane`) remains the very last, deliberately unattempted step — it must wait until after Task 5 pushes, and will require the current session to be restarted from the new path.

---
*Phase: quick-260826-vlq*
*Status: in-progress (Tasks 1-4 of 5 complete)*

## Self-Check: PASSED

All claimed files verified present on disk (`firmware/build-ee02/skypane.bin`, all four `deploy/skypane-*` artifacts, this SUMMARY itself). All three task commit hashes (`7c1f0fe`, `a6b5d50`, `fab6c7a`) verified present in `git log --oneline --all`.
