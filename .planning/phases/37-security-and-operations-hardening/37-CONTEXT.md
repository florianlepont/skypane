# Phase 37: Security and operations hardening - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning
**Source:** Audit ledger `.planning/audits/2026-09-23-code-audit.md` (Phase 37 rows SEC-01..SEC-08, decisions D-A1..D-A6) + dependency correction and questions answered by the developer on 2026-09-23 (no separate discuss-phase run)

<domain>
## Phase Boundary

Remediate the eight security/operations findings of the 2026-09-23 audit:
the companion login throttle, HSTS, CSRF defence in depth, off-box backups
of `/opt/skypane/state`, atomic and verified deploys, systemd hardening,
secret handling, and SSH hardening. No new product feature except the
off-box-backup freshness line on the companion health page (D-07).

Out of scope: anything owned by another audit phase (flock/atomic writes —
Phase 36; per-device enrolment secret — Phase 34 FW-08; companion route
split — Phase 40; comment purge — Phase 35). Phase 37 must not re-do or
pre-empt them.

</domain>

<decisions>
## Implementation Decisions

### Waves and dependencies (developer, 2026-09-23)
- **D-01:** Phase 37 no longer depends on Phase 36 as a whole. Plans are
  split into two waves:
  - **Wave A — depends only on Phase 32** (pytest infrastructure; every new
    test is a pytest test using Phase 32's `conftest.py` fixtures, including
    its no-network socket guard): SEC-01, SEC-02, SEC-03, SEC-04, SEC-05,
    SEC-06 (everything except byos binding), SEC-07 (env file
    `root:root 600`, `DEPLOY_HOST_KEY` via `env:`), SEC-08.
  - **Wave B — depends on Phase 36** (which modifies
    `stub-server/byos_server.py`): byos `--bind 127.0.0.1` +
    `IPAddressDeny=any` / `IPAddressAllow=localhost` on
    `skypane-byos.service` (SEC-06 remainder), and the byos secret moved off
    the command line into the environment (SEC-07 remainder).
  - Wave B plans must not touch `byos_server.py` before Phase 36 has merged;
    they re-read the file as Phase 36 left it. If Phase 34 (FW-08,
    per-device enrolment secret) has changed how the byos secret is used,
    Wave B follows that shape — it only changes *how the secret reaches the
    process* (env, not argv), never the enrolment model.
- **D-02:** Phase 32 plans are not on `main` at planning time. Plans refer
  to Phase 32's deliverables as specified by its ledger rows (TST-01
  `conftest.py`/`pyproject.toml`, TST-03 socket guard + fake provider) and
  must re-read the actual fixtures at execution time.

### SEC-04 — backups (developer, 2026-09-23)
- **D-03:** Nightly backup **on the VPS**: a systemd timer (oneshot) takes a
  consistent SQLite snapshot of `history.db` (online backup API —
  `sqlite3 .backup` or Python `sqlite3.Connection.backup`, the latter keeps
  the "stdlib only" rule and needs no extra apt package) plus a copy of the
  other files of `/opt/skypane/state` that cannot be regenerated (tokens,
  device config, uploaded illustrations, calendar config, …). Regenerable
  files (`panel.bin`, rendered caches, Caddy access logs) are excluded —
  the researcher lists which is which. The result is one dated archive in a
  local backup directory with bounded local retention.
- **D-04:** The **off-box copy is PULLED over SSH by the developer's Mac**
  (not pushed to a cloud bucket). A script in the repository plus a
  **launchd** agent (a `LaunchAgent` plist template) runs nightly and
  catches up when the Mac wakes (launchd `StartCalendarInterval` runs a
  missed job at wake). The Mac keeps its own dated copies with retention.
- **D-05:** The pull uses a **dedicated SSH key restricted by a forced
  command** in `authorized_keys` (`restrict,command=...`) so the key can
  only read the backup directory — it can never read `skypane.env`, the
  live state, or open a shell. Whether that is a dedicated `skypane-backup`
  user or a forced command on an existing user is the researcher's call;
  it must not be `root`.
- **D-06:** A **restore is rehearsed once** (human checkpoint) from a copy
  pulled to the Mac, into a scratch state directory, and the procedure is
  written up in `deploy/README.md`. `deploy/README.md`'s claim that the VPS
  state is "fully reproducible from this repository" (lines ~263-269) is
  corrected.
- **D-07:** **Freshness alert in the companion** (developer chose it): each
  successful pull leaves a marker on the VPS (last successful off-box pull
  timestamp) through the same narrow forced command; the companion health
  page shows "last off-box backup N ago" (FR/EN) and turns into an alert
  when older than **3 days**, or when no pull has ever happened. The UI
  follows the existing health-page card/status patterns
  (`Skill("sketch-findings-skypane")`); no new page.

### SEC-08 — SSH (developer, 2026-09-23)
- **D-08:** The production `DEPLOY_SSH_TARGET` logs in as **`ubuntu@`**
  (non-root, passwordless sudo). `PermitRootLogin no` therefore does not
  break deploys and is applied directly. Hardening moves to
  `/etc/ssh/sshd_config.d/00-skypane.conf` (first match wins, so `00-`
  beats cloud-init's `50-cloud-init.conf`), validated with `sshd -t`
  before reload, and the live values checked with `sshd -T`. The
  production application of this change is a human checkpoint that keeps
  one SSH session open while a second one proves login still works.

### SEC-05 — deploy (Claude's discretion within the ledger)
- **D-09:** Release directories + atomic symlink swap (the ledger's first
  option): code goes to `/opt/skypane/releases/<git-sha>/`, then
  `/opt/skypane/current` is switched atomically (`ln -s` to a temp name +
  `mv -T`). Units point at `/opt/skypane/current/...`. The venv and
  `state/` stay outside releases. The last few releases are kept for
  rollback.
- **D-10:** After the swap, the job fails unless every unit is active
  (`systemctl is-active` on byos, companion, poll timer) and HTTP probes
  succeed (loopback probes on both app ports and at least one HTTPS probe
  through Caddy). On failure, the symlink is switched back to the previous
  release and the job still fails (red CI).
- **D-11:** Units and the Caddyfile are deployed by `deploy.sh`: units
  copied into `/etc/systemd/system/` followed by `systemctl daemon-reload`;
  the Caddyfile rendered with the real hostnames from `skypane.env`
  (`SKYPANE_PUBLIC_HOST`, `SKYPANE_COMPANION_HOST`), validated with
  `caddy validate` before `systemctl reload caddy`.
- **D-12:** Moving production from the current in-place layout to the
  release layout is a one-time, human-supervised cutover checkpoint.
- **D-13:** TST-06 (Phase 32) owns CI concurrency groups; Phase 37 does not
  change them.

### SEC-01 / SEC-02 / SEC-03 — companion (Claude's discretion within the ledger)
- **D-14:** Login throttle keyed on the client IP. The client IP is taken
  from `X-Forwarded-For` **only** when the TCP peer is loopback (Caddy);
  otherwise the peer address. The per-IP table is bounded (cap + eviction)
  so a spray of addresses cannot exhaust memory. Failures from one IP never
  lock another.
- **D-15:** HSTS on the companion site block (and on the byos site block if
  harmless for the device — the researcher confirms), no `preload`.
- **D-16:** Every POST is checked: rejected (403) when `Origin` is present
  and not the companion's own origin, or when `Sec-Fetch-Site` is
  `cross-site`/`same-site`. Requests carrying neither header are allowed
  (non-browser clients still need a valid session cookie). The login POST
  is checked too.

### SEC-06 / SEC-07 — units and secrets (Claude's discretion within the ledger)
- **D-17:** `systemd-analyze security` exposure score recorded **before and
  after** for each unit (on the VPS at the human checkpoint; an offline
  check in CI is welcome if the runner's systemd supports it).
- **D-18:** Hardening directives from the ledger on every unit, adjusted per
  unit: the poll service needs outbound IPv4/IPv6 (ADS-B providers), so no
  `IPAddressDeny` there; `IPAddressDeny=any`/`IPAddressAllow=localhost` is
  for byos (Wave B, with `--bind 127.0.0.1`). The companion also binds
  `0.0.0.0` today; loopback-only IP filtering on its unit is in scope for
  Wave A if it needs no Python change.
- **D-19:** `skypane.env` becomes `root:root 600` (systemd reads
  `EnvironmentFile=` as root before dropping privileges). The researcher
  must confirm no process reads that file directly as the `skypane` user.
  `provision.sh` and `deploy/README.md` are updated to match.
- **D-20:** `ci.yml` passes `DEPLOY_HOST_KEY` (and the SSH target) through
  `env:` instead of `${{ }}` interpolation inside `run:`.

### Follow-up decisions after research (developer, 2026-09-23)
- **D-22:** The companion gets a `--bind` flag in `companion/app.py`
  (default kept backward compatible) and `skypane-companion.service` passes
  `--bind 127.0.0.1` — **in Wave A** (no Phase 36 dependency). A systemd IP
  filter on the companion is NOT used: it makes outbound calls (`/poll-now`
  runs `run_once` in-process, calendar fetch, ntfy). This supersedes the
  "loopback-only IP filtering on its unit" part of D-18.
- **D-23:** A stale (> 3 days) or never-made off-box backup also lights the
  Health entry's nav dot, at **warning** level (not error).
- **D-24:** `gallery/` is **not** backed up (regenerable rendered cache).
- **D-25 (Claude's discretion):** In CI the Caddyfile is tested as rendered text
  (no Caddy binary download); `caddy validate` runs on the VPS inside
  `activate.sh`. The pull gate is a small Python forced-command script
  (`list` / `get NAME` / `ack NAME`) for a dedicated `skypane-backup` user,
  per RESEARCH.md, not rrsync.

### Human checkpoints (developer instruction)
- **D-21:** Every action on the production VPS or on GitHub settings is a
  human checkpoint with exact commands for the developer: first
  `systemd-analyze security` baseline, cutover to the release layout, SSH
  drop-in application, env file ownership change, backup user/key
  installation, launchd install on the Mac, restore rehearsal. Plans never
  assume credentials.

### Claude's Discretion
- Exact local backup retention on the VPS and on the Mac (suggested: 14
  nightly on the VPS, 30 nightly + monthly on the Mac).
- Backup archive format (tar + gzip is fine; stdlib `tarfile` if written in
  Python).
- Number of releases kept on the VPS (suggested: 5).
- Where the new pytest files live, following Phase 32's layout.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit and requirements
- `.planning/audits/2026-09-23-code-audit.md` — Phase 37 rows SEC-01..08 with file:line evidence; decisions D-A1..D-A6
- `.planning/REQUIREMENTS.md` — SEC-01..SEC-08 (section "Audit remediation")
- `.planning/ROADMAP.md` — Phase 37 entry (goal, success criteria, wave split); Phase 32 and Phase 36 entries (dependencies)

### Code touched
- `companion/auth.py` (`LoginThrottle`, ~line 301), `companion/app.py` (`LOGIN_THROTTLE` ~688, cookie/SameSite ~3480, POST dispatch)
- `deploy/Caddyfile`, `deploy/deploy.sh`, `deploy/provision.sh`, `deploy/README.md`, `deploy/skypane.env.example`
- `deploy/skypane-byos.service`, `deploy/skypane-companion.service`, `deploy/skypane-poll.service`, `deploy/skypane-poll.timer`
- `.github/workflows/ci.yml` (deploy job, ~lines 102-175)
- `stub-server/byos_server.py` (Wave B only, after Phase 36)
- `companion/pages/health_page.py` (freshness line, D-07)

### Design
- `.claude/skills/sketch-findings-skypane/SKILL.md` — companion design system for the freshness line

</canonical_refs>

<specifics>
## Specific Ideas

- Production hosts: companion `skypane.algernon.ovh` (PR #92); the repo's
  Caddyfile carries `nip.io` placeholders, hence templating (D-11).
- Success criteria wording from ROADMAP: failed logins from one IP never
  lock another; HSTS present and a cross-origin POST rejected; restore
  rehearsed once and documented; a deploy leaving a unit inactive fails the
  CI job and units/Caddyfile are deployed; `systemd-analyze security`
  before/after, byos loopback only, no secret visible in `ps`.

</specifics>

<deferred>
## Deferred Ideas

- Encryption of the Mac-side backup copies at rest (FileVault already
  covers the Mac disk) — not requested.
- A second, cloud off-box destination — the developer chose the SSH pull
  only.

</deferred>

---

*Phase: 37-security-and-operations-hardening*
*Context gathered: 2026-09-23 from the audit ledger and developer answers*
