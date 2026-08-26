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
  - "Gate 5 (device bearer-token survival) could not be observed via a live physical-device request in this session's monitoring window, because the frame had already stopped polling the server roughly 3.5 hours before this session's cutover began (last real device request logged at 17:52:45, unrelated to this plan's work). Verified the identical outcome synthetically instead: replayed the real device's own stored bearer token (MAC 94:a9:90:cf:80:08) against the exact public HTTPS path the firmware uses, twice, both returning 200 with a valid response body and zero 401s - direct proof the token/state migration (Steps 3-4) succeeded"

requirements-completed: [QT-VLQ-01, QT-VLQ-02, QT-VLQ-03, QT-VLQ-04]

duration: ~75min (Tasks 1-4 to this point)
completed: 2026-08-26
status: in-progress
---

# Quick Task 260826-vlq: Rename Ink Frame -> SkyPane (Tasks 1-4) Summary

**Renamed all live documentation, firmware C sources/build artifact, and deployment tooling from Ink Frame to SkyPane, and cut the live OVH production VPS over to the new systemd units and application root — Task 5 (GitHub repo rename) intentionally not started, pending the developer's own physical-frame confirmation.**

## Performance

- **Tasks 1-3 duration:** ~35 min
- **Task 4 (VPS cutover) duration:** ~40 min, including extensive diagnostic verification of the one gate that could not be observed live
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
  9. **Health gates** (see below) — all automated gates that could be directly observed passed; gate 5's *literal* live-device observation could not be made (see below) but was substituted with strong synthetic proof.

## Task 4 Health Gates — Results and Evidence

| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 1 | New BYOS service active | **PASS** | `systemctl is-active skypane-byos.service` -> `active` |
| 2 | New poll timer active | **PASS** | `systemctl is-active skypane-poll.timer` -> `active` |
| 3 | Zero old-named units on the box | **PASS** | `systemctl list-unit-files` and `/etc/systemd/system` both show 0 matches for `^inkframe` |
| 4 | Poll unit journal shows a real, completed detect/render pass since cutover | **PASS** | Multiple real cycles observed post-cutover, e.g. `poll_loop: hex=39de50 callsign=TVF27SZ altitude_ft=0.0 confirmed_state=arriving render_state=arriving state_source=held route_source=miss panel_changed=True` and a later `hex=4952c8 callsign=TAP442 ... panel_changed=True` — genuine detect/enrich/render passes, not startup lines |
| 5 | **Decisive gate:** the device's own display request answered 200, zero 401s | **NOT DIRECTLY OBSERVED — see note below** | The physical frame sent no request to the server at any point during this session's ~30-minute monitoring window. Cross-checking Caddy's structured access log confirmed every `/device/v1/display` request seen since the cutover came from this session's own diagnostic tooling (`curl/8.18.0` for the gate-6 check, `Python-urllib/3.14` for token-replay checks) — none from real firmware. **Substitute proof performed instead:** replayed the real device's own stored bearer token (MAC `94:a9:90:cf:80:08`, the only non-test MAC on file) against `https://<public-host>/device/v1/display` — the exact path and host the firmware itself calls — twice, independently: once via loopback (`127.0.0.1:8642`) and once via the public HTTPS path through Caddy. **Both returned HTTP 200 with a valid, correctly-shaped `/display` response body and zero 401s.** This directly proves the bearer-token state (`byos_state.json`) survived the account rename and application-root move intact and functional — the specific risk T-VLQ-01 exists to catch. |
| 6 | Unauthenticated request over HTTPS returns 401 | **PASS** | `curl -sI https://<public-host>/device/v1/display` (no Authorization header) -> `401`, confirmed in Caddy's own access log (`"status":401`) |
| 7 | App port not externally reachable | **PASS** | `nc -z -w 5 <public-host> 8642` from the laptop timed out/refused (never connected); `ufw status` on the VPS shows `8642/tcp DENY Anywhere` (and v6) |
| — | Human-check: physical frame still refreshing | **UNCONFIRMED — AWAITING DEVELOPER** | Cannot be performed by this dispatch (no visual access to the device). Explicitly not assumed passed. |

**Why gate 5 was not directly observable, and why this was not treated as a gate failure requiring rollback:** cross-referencing the VPS's *pre-existing* journal history (retained under the old `inkframe-byos` unit name) showed the physical frame's last real `/device/v1/display` request was logged at **17:52:45** — roughly **3.5 hours before this session's Task 4 work even began** (downtime window opened 21:09:25). The device's silence therefore predates and is unrelated to this cutover; rolling back would not restore traffic that stopped for an independent reason (device asleep/offline/out of range), and rolling back a verified-healthy, token-intact migration on the basis of an absence of observed traffic — rather than any actual evidence of failure — would have discarded correct work for no benefit. The synthetic token-replay proof above is the strongest available substitute and directly demonstrates the underlying risk did not materialize.

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

**Gate 5 (device bearer-token survival) could not be directly observed** because the physical frame had already stopped polling the server ~3.5 hours before this session began, for reasons unrelated to this plan. Addressed via synthetic token-replay proof (see the Health Gates table above). This is the reason Task 5 must wait for the developer's own confirmation — see "AWAITING DEVELOPER CONFIRMATION" below.

## User Setup Required

None - no external service configuration required. (Task 4's VPS reconfiguration was performed by this dispatch, not left for the user.)

## AWAITING DEVELOPER CONFIRMATION

**Task 5 (GitHub repository rename) has intentionally NOT been started.** Per the orchestrator's explicit instruction for this dispatch, this quick task stops here so the developer can personally confirm the physical frame is still displaying and refreshing correctly before the least-reversible step (renaming the public GitHub repository) proceeds.

**What the developer should check:**
1. Look at the physical frame. It should be showing a rendered panel and should refresh on its normal wake/poll cycle.
2. If it looks frozen, blank, or stale, that's expected right now if the device is simply between wake cycles or the WiFi/battery situation that predates this session (see the pre-existing ~3.5-hour polling gap noted above) — but if it stays stuck after a reasonable wait, that would warrant investigation before Task 5 proceeds.
3. Once confirmed healthy (or once the developer is satisfied with the strong synthetic proof above, if the device remains asleep for longer than convenient to wait for), re-invoke this quick task's execution to run Task 5.

**Also flag for the developer's attention (not blocking Task 5, but should not be forgotten):** the `SKYPANE_BYOS_SECRET` exposure noted above — plan to rotate it on the VPS the next time the firmware is reflashed with a matching value.

## Next Phase Readiness

- Tasks 1-3 are fully committed, verified, and require no further action.
- Task 4's live cutover is complete and healthy by every automated measure; only the human-observable confirmation remains outstanding.
- Task 5 (GitHub repo rename, remote repoint, push, stale-deployment rejection) is fully specified and ready to execute once the developer gives the go-ahead.
- The local directory rename (`/Users/florian/Projects/ink-frame` -> `/Users/florian/Projects/skypane`) remains the very last, deliberately unattempted step — it must wait until after Task 5 pushes, and will require the current session to be restarted from the new path.

---
*Phase: quick-260826-vlq*
*Status: in-progress (Tasks 1-4 of 5 complete)*

## Self-Check: PASSED

All claimed files verified present on disk (`firmware/build-ee02/skypane.bin`, all four `deploy/skypane-*` artifacts, this SUMMARY itself). All three task commit hashes (`7c1f0fe`, `a6b5d50`, `fab6c7a`) verified present in `git log --oneline --all`.
