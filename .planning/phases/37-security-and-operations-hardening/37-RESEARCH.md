# Phase 37: Security and operations hardening - Research

**Researched:** 2026-09-23
**Domain:** Web-app hardening (throttle, CSRF, HSTS), Linux ops (atomic deploys, systemd sandboxing, SSH, backups), macOS launchd
**Confidence:** HIGH for the repo facts (every claim has a file:line reference, re-read for this document); MEDIUM for platform behaviour (Caddy, systemd and launchd come from official docs or were measured locally); LOW where tagged `[ASSUMED]`

## Summary

Phase 37 is mostly infrastructure work in `deploy/`, plus two small companion changes (per-IP throttle, Origin check) and one health-page line. The code is easy to find. Most of the risk is operational: cutting production over to a release layout, tightening SSH, and changing file ownership on a live VPS. Every one of those steps is a human checkpoint (D-21). The planner should put the risky work into testable scripts (`deploy/activate.sh`, the backup job, the backup gate) that pytest can run in CI against a fake root with a stubbed `systemctl`, `curl` and `caddy`. The VPS checkpoints should then only run those scripts and read the results.

Five facts shape the plan. (1) Caddy already drops any `X-Forwarded-For` the client sends and sets its own, because no `trusted_proxies` is configured. When the TCP peer is loopback, the right-most XFF entry is therefore the real client IP. (2) No process reads `/opt/skypane/skypane.env` itself. The only readers are systemd's `EnvironmentFile=` (as PID 1) and the new deploy activation script (as root), so `root:root 600` is safe. (3) The companion **cannot** take `IPAddressDeny=any`. It makes outbound calls: `/poll-now` runs `poll_loop.run_once()` in-process (`companion/app.py:3310`), plus calendar fetches and ntfy notifications. D-18's optional companion IP filter is therefore not feasible without a Python `--bind` change. (4) `/opt/skypane/state/calendar_url.secret` is created with mode `0600` (`server/plane/calendar_rules.py:325`), so only the `skypane` user can read all of the state. The nightly snapshot must run as `skypane`, and the SSH pull user must never join the `skypane` group, because `state/` is group-writable (`provision.sh:97`). (5) `systemd-analyze security --offline=true --threshold=N` runs on the ubuntu-24.04 runner's systemd 255. I measured it locally: today's three units score **8.3 EXPOSED**, and a draft hardened poll unit scores **1.1**. `--threshold` is in tenths, so a 1.1 score fails `--threshold=10` and passes `--threshold=20`.

**Primary recommendation:** Build one idempotent `deploy/activate.sh` that runs on the VPS as root. It stages the release, installs units and the rendered Caddyfile, swaps the symlink atomically, probes, and rolls back. `deploy.sh` becomes `git archive | ssh` plus a call to that script. Test both with pytest against a fake root. Build the backup as a stdlib Python snapshot job running as `skypane`, and serve it through a small Python forced-command gate (`list` / `get NAME` / `ack NAME`) for a dedicated non-root `skypane-backup` user. Do **not** use rsync/rrsync for the pull: that avoids macOS openrsync compatibility problems entirely.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Waves and dependencies (developer, 2026-09-23)
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

#### SEC-04 — backups (developer, 2026-09-23)
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

#### SEC-08 — SSH (developer, 2026-09-23)
- **D-08:** The production `DEPLOY_SSH_TARGET` logs in as **`ubuntu@`**
  (non-root, passwordless sudo). `PermitRootLogin no` therefore does not
  break deploys and is applied directly. Hardening moves to
  `/etc/ssh/sshd_config.d/00-skypane.conf` (first match wins, so `00-`
  beats cloud-init's `50-cloud-init.conf`), validated with `sshd -t`
  before reload, and the live values checked with `sshd -T`. The
  production application of this change is a human checkpoint that keeps
  one SSH session open while a second one proves login still works.

#### SEC-05 — deploy (Claude's discretion within the ledger)
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

#### SEC-01 / SEC-02 / SEC-03 — companion (Claude's discretion within the ledger)
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

#### SEC-06 / SEC-07 — units and secrets (Claude's discretion within the ledger)
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

#### Human checkpoints (developer instruction)
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

### Deferred Ideas (OUT OF SCOPE)
- Encryption of the Mac-side backup copies at rest (FileVault already
  covers the Mac disk) — not requested.
- A second, cloud off-box destination — the developer chose the SSH pull
  only.

Also out of scope (Phase Boundary): flock/atomic writes (Phase 36), per-device enrolment secret (Phase 34 FW-08), companion route split (Phase 40), comment purge (Phase 35).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEC-01 | Per-client-IP throttle (trusted `X-Forwarded-For` from loopback Caddy) | §SEC-01: Caddy ignores client XFF by default; `client_address[0]` + right-most XFF; bounded LRU table; existing tests to migrate |
| SEC-02 | `Strict-Transport-Security` | §SEC-02: `header Strict-Transport-Security "max-age=31536000"` in both site blocks; firmware ignores it (verified `firmware/main/api_client.c`) |
| SEC-03 | `Origin`/`Sec-Fetch-Site` check on every POST | §SEC-03: 18 POST branches in one `do_POST` (`app.py:3453-3615`); compare Origin netloc with `Host`; one fetch POST (`quick-switch.js:301`) sends Origin |
| SEC-04 | Nightly `sqlite3 .backup` + off-box copy; README corrected | §SEC-04: state inventory, WAL, snapshot job as `skypane`, `skypane-backup` user + Python gate, launchd agent, marker, restore |
| SEC-05 | Release dir + symlink swap; post-deploy `is-active` + HTTP probes fail the job; units/Caddyfile deployed with `daemon-reload` | §SEC-05: activate.sh design, probe endpoints (byos `/device/v1/display`→401, companion `/login`→200), `curl --resolve` HTTPS probe, Caddyfile render + validate, cutover |
| SEC-06 | `CapabilityBoundingSet=`, `PrivateDevices`, `ProtectKernel*`, `RestrictAddressFamilies`, `SystemCallFilter=@system-service`, `UMask=0027`; byos `--bind 127.0.0.1` + `IPAddressDeny=any`/`IPAddressAllow=localhost` | §SEC-06: per-unit directive table, measured offline scores 8.3 → 1.1 / 0.9, CI `--threshold`, companion IP filter infeasible |
| SEC-07 | Secret via env; env file `root:root 600`; secret passed through `env:` | §SEC-07: no direct reader (grep), ci.yml `env:` pattern, byos argparse env default (Wave B) |
| SEC-08 | `sshd_config.d/00-skypane.conf`, `PermitRootLogin no`, validated | §SEC-08: first-value-wins, `sshd -t`, `sshd -T`, `systemctl try-reload-or-restart ssh` under socket activation |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Production dependencies are stdlib + Pillow + requests only** (`server/requirements.txt`). Backup job, backup gate, throttle and Origin check must be stdlib (`sqlite3`, `tarfile`, `hashlib`, `ipaddress`, `collections.OrderedDict`). No new pip package.
- **The server runs as systemd units on an OVH VPS-1 (Ubuntu) with Caddy for TLS.** Three units today (`skypane-byos`, `skypane-companion`, `skypane-poll` + timer); this phase adds `skypane-backup.service` + `.timer`.
- **Tests/CI:** today stdlib harnesses (`./scripts/run-all-tests.sh`), ruff, a coverage gate, Playwright, and a GitHub Actions deploy gated by a reviewer. Per D-01, new tests are **pytest** tests on Phase 32's infrastructure.
- **Companion UI is bilingual EN/FR.** New strings need French in `companion/i18n_fr/health.py` (keyed by the English sentence today, `companion/i18n.py:21`; CMP-09 in Phase 40 will change this).
- **Design system:** health-page additions follow `Skill("sketch-findings-skypane")`. Use `layout.status_dot()`, `layout.card_status_class()`, `layout.concise_timestamp_html()` (`companion/layout.py:3300,3812,1559`) and the `.page-section--nested` card pattern.
- **Audit rule D-A3:** everything in English (code, comments, docs, commits). Comments explain *why*; no plan or ticket history in comments.
- **GSD workflow:** edits happen only through GSD commands (execution phase).
- **Ruff scope:** `ruff check .` lints every Python file, including new ones under `deploy/`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-IP login throttle | Companion (API) `companion/auth.py` + `app.py` | Caddy (sets trusted XFF) | Only the app knows about failed logins; Caddy only supplies the IP |
| HSTS | Caddy (edge) | — | A transport policy, set once at the TLS terminator for both hosts |
| CSRF Origin / Sec-Fetch-Site check | Companion `do_POST` | Browser (sends headers) | Needs the Host header and the route; one choke point |
| Consistent state snapshot | VPS systemd oneshot (`skypane` user) | SQLite online backup API | Must read `0600` files and WAL database pages |
| Off-box copy | Developer Mac (launchd pull) | VPS forced-command gate | D-04: pulled, not pushed |
| Backup freshness | Companion health page | Marker written by the gate | D-07 |
| Atomic deploy + probes + rollback | VPS `activate.sh` (root) | CI job / `deploy.sh` (transport + exit status) | Swap and probes must be local to the box; CI only relays the result |
| Unit sandboxing | systemd unit files | CI offline `systemd-analyze` | Declarative, scored |
| Secret delivery | systemd `EnvironmentFile=` (root) | byos argparse env default (Wave B) | Keeps the secret out of argv |
| SSH policy | `sshd_config.d/00-skypane.conf` | `provision.sh` | First value wins |

## Standard Stack

### Core (all already present; no new packages)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python `sqlite3.Connection.backup` | stdlib (3.12 CI / distro 3.14 prod) | Consistent online copy of WAL-mode `history.db` | Official online-backup API, page-consistent even under concurrent writers [CITED: docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup] |
| Python `tarfile`, `hashlib`, `ipaddress`, `collections.OrderedDict` | stdlib | Archive, checksum, IP parsing, bounded LRU | stdlib-only rule |
| Caddy `header` directive | Caddy v2 (official apt repo, `provision.sh:73-84`) | HSTS | Official: `header Strict-Transport-Security "max-age=31536000;"` [CITED: caddyserver.com/docs/caddyfile/directives/header] |
| systemd sandboxing directives | systemd 255 (runner; verified locally 255.4) / Ubuntu 26.04 on VPS | SEC-06 | `systemd-analyze security` is the scoring tool [VERIFIED: local run] |
| OpenSSH `sshd_config.d` drop-ins | Ubuntu default `Include /etc/ssh/sshd_config.d/*.conf` | SEC-08 | "for each keyword, the first obtained value will be used" [CITED: sshd_config(5)] |
| launchd LaunchAgent | macOS | Nightly pull that catches up at wake | "launchd will start the job the next time the computer wakes up… coalesced into one event" [CITED: launchd.plist(5)] |

### Supporting (CI only)
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| shellcheck | 0.9.0 preinstalled on ubuntu-24.04 runner [CITED: actions/runner-images Ubuntu2404-Readme] | Lint `deploy/*.sh`, the Mac pull script (`--shell=sh`) | Every CI run |
| `systemd-analyze security --offline=true --threshold=N` | systemd 255.4 on runner [CITED: runner-images readme] | Score gate on the unit files | Every CI run |
| pytest (Phase 32) | whatever Phase 32 pins (TST-01/TST-08) | All new tests | Re-read Phase 32's `conftest.py` at execution (D-02) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python forced-command gate (`list`/`get`/`ack`) | `rrsync -ro` (Ubuntu ships `/usr/bin/rrsync` since Debian moved it out of `/usr/share/doc`; runner has rsync 3.2.7) | rrsync validates rsync's server arguments. macOS 15+ ships openrsync as `/usr/bin/rsync`, Apple's old one is 2.6.9, and whether either works against rrsync is untested `[ASSUMED]`. The gate also needs a separate `ack` verb, so you would write a dispatcher anyway. The gate is simpler and fully testable in CI. |
| Rendering the Caddyfile with anchored `sed` / Python | Caddy `{$SKYPANE_PUBLIC_HOST}` env placeholders | Caddy only expands them from **its own** process environment. Giving `caddy.service` `EnvironmentFile=skypane.env` would hand Caddy the BYOS secret and the companion password. Rejected. |
| Shared `/opt/skypane/venv` (D-09) | One venv per requirements hash, symlinked from each release | More correct rollback across a dependency change, but it goes beyond D-09's wording. Use the shared venv and let rollback re-run `pip install -r <prev>/server/requirements.txt` when the hash differs. |
| `git archive HEAD … \| ssh … tar -x` | rsync of the working tree | `git archive` ships exactly the committed tree for that SHA: no `.venv`, no `server/state/*`, no stray local `skypane.env`, no uncommitted edits. rsync `--link-dest` saves bandwidth, but the tree is small. |

**Installation:** none. Phase 37 adds no pip or apt package. `rsync` is no longer needed by the new deploy path, and `curl` is already installed by `provision.sh:78`.

## Package Legitimacy Audit

Phase 37 installs **no new external packages** (pip, npm or apt). Every Python module used is stdlib. pytest/pytest-xdist/pytest-cov come from Phase 32 and are audited there. An optional CI download of a pinned `caddy` release binary (see Open Questions) would be a GitHub release asset verified by sha256, not a registry package. If the planner adopts it, gate it behind a `checkpoint:human-verify` task.

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none) | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck not run; nothing to check)
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────── GitHub Actions (push to main, reviewer-gated) ───────────┐
                         │ deploy.sh: SHA=$(git rev-parse HEAD)                                  │
                         │   git archive HEAD <paths> ──ssh──► sudo /opt/skypane/…/activate.sh  │
                         │   exit status of activate.sh ⇒ job green/red                          │
                         └───────────────────────────────┬───────────────────────────────────────┘
                                                         ▼
 VPS (root) activate.sh: extract → releases/<sha>/ (root-owned) → compileall → pip if req hash changed
   → smoke import → render Caddyfile from skypane.env (safe parse) → caddy validate
   → [prev=readlink current] install units → daemon-reload → ln -s tmp; mv -T tmp current
   → restart byos, companion; restart poll timer; reload caddy if changed
   → probes (retry ≤30 s): is-active ×4 · 127.0.0.1:8642/device/v1/display=401 · 127.0.0.1:8643/login=200
        · curl --resolve PUBLIC:443:127.0.0.1 https://PUBLIC/device/v1/display=401
        · curl --resolve COMPANION:443:127.0.0.1 https://COMPANION/login=200
   ├─ all ok ─► prune releases (keep 5, never current/prev) ─► exit 0
   └─ any fail ─► swap back to prev, reinstall prev units + Caddyfile, restart, re-probe, journal tail ─► exit 1

 Browser ──HTTPS──► Caddy (HSTS, sets XFF=peer) ──► companion 127.0.0.1:8643
     do_POST: Origin/Sec-Fetch-Site gate (403) → login: key=client_ip() → LoginThrottle[key]

 Nightly on VPS: skypane-backup.timer → skypane-backup.service (User=skypane)
     state/history.db ──sqlite backup API──► tmp copy ─┐
     state/{json, secret, illustration_overrides/} ────┴► /var/lib/skypane-backup/archives/
                                                           skypane-state-<UTC>.tar.gz (+ .sha256), keep 14
 Mac launchd (daily + wake catch-up) ──ssh key, forced command──► backup_gate.py (user skypane-backup)
     list → get NAME (stream) → shasum verify → keep 30 daily + monthly → ack NAME
     ack writes /var/lib/skypane-backup/pulled/last-pull (content = archive name)
 Companion health page reads the marker (path from env) → "Last off-box backup N ago" → warn if > 3 days or never
```

### Recommended file layout (new files)
```
deploy/
├── activate.sh                    # runs ON the VPS as root; swap/probe/rollback; overridable roots for tests
├── deploy.sh                      # rewritten: git archive | ssh; calls activate.sh; no sha256sum on the laptop
├── Caddyfile                      # + HSTS lines; placeholders kept for anchored render
├── skypane-backup.service/.timer  # nightly snapshot
├── backup/
│   ├── skypane_backup.py          # snapshot job (stdlib)
│   ├── backup_gate.py             # forced command for skypane-backup (stdlib)
│   └── mac/
│       ├── skypane-backup-pull.sh           # POSIX sh (macOS bash 3.2 / zsh safe)
│       ├── skypane-backup-pull.plist.template
│       └── install-launchagent.sh
└── tests/ (or wherever Phase 32 puts tests)   # test_activate.py, test_backup.py, test_backup_gate.py, test_units.py, test_caddyfile.py, test_mac_pull.py
```

### Pattern: fake-root shell testing (the main CI lever for SEC-05)
`activate.sh` reads every system path from an overridable variable (`SKYPANE_ROOT=/opt/skypane`, `SYSTEMD_UNIT_DIR=/etc/systemd/system`, `CADDYFILE=/etc/caddy/Caddyfile`, `ENV_FILE=$SKYPANE_ROOT/skypane.env`, `BACKUP_GATE_DIR=/usr/local/lib/skypane`). pytest creates a tmp root and puts executable stubs for `systemctl`, `curl`, `caddy`, `runuser`, `chown` and `journalctl` first on `PATH`. The stubs log their argv to a file and read scripted results from env vars (e.g. `FAKE_INACTIVE=skypane-companion.service`, `FAKE_HTTP_skypane_login=500`). Tests assert on the final `readlink current`, the exit code and the stub call log. This proves SC-4 ("a deploy that leaves a unit inactive fails the CI job") without a VPS.

### Anti-patterns to avoid
- **`source`-ing `skypane.env` as root** in the activate script. systemd `EnvironmentFile=` syntax is not shell syntax, and sourcing executes the file as root. Parse the keys you need with a strict line regex (`^SKYPANE_PUBLIC_HOST=([A-Za-z0-9.-]+)$`) and validate them the way `provision.sh:43-48` already does.
- **Pointing the forced command into `/opt/skypane/...`.** `useradd --create-home` on current Ubuntu makes home directories `0750` `[ASSUMED]`, and `/opt/skypane` is `skypane`'s home (`provision.sh:55-57`), so `skypane-backup` may not be able to traverse it. Install the gate at `/usr/local/lib/skypane/backup_gate.py` (root-owned, `0755`) from `activate.sh`.
- **Adding `skypane-backup` to the `skypane` group.** `state/` is `g+ws` (`provision.sh:97`), so group membership would mean write access to live state.
- **Using `StateDirectory=` for the archive directory.** It makes the directory owned by `User:Group` of the service (`skypane:skypane`), so the pull user could only read it through the `skypane` group. Create `/var/lib/skypane-backup/archives` explicitly as `skypane:skypane-backup 2750`.
- **Running `caddy validate` as root against a config whose log output path does not exist yet.** It might create `caddy-access.log` owned by root `[ASSUMED]`. Run it as `runuser -u caddy --`.
- **Using `PrivateUsers=true` on the units.** Supplementary groups are not mapped, so the `caddy:skypane` access log (read through group) and similar files may become unreadable. Not in the ledger set; leave it out.

## SEC-01 — Per-IP login throttle (findings)

- **Current code:** `LoginThrottle` is process-global (`companion/auth.py:301-356`), singleton `LOGIN_THROTTLE = auth.LoginThrottle()` (`app.py:688`), used only in `_handle_login_post` (`app.py:3053-3080`: `locked_out()` → 429, `record_success()`, `record_failure()`). The limits are `LOGIN_FAILURE_LIMIT = 5` and `LOGIN_LOCKOUT_S = 300` (`auth.py:69-70`).
- **Client address:** `BaseHTTPRequestHandler.client_address[0]` is the TCP peer. The companion binds `("0.0.0.0", port)` (`app.py:3665`), IPv4 only, so the peer is `127.0.0.1` when the request comes from Caddy. No code reads `X-Forwarded-For` today (grep: 0 hits).
- **Caddy behaviour:** "For these `X-Forwarded-*` headers, by default, the proxy will ignore their values from incoming requests, to prevent spoofing." [CITED: caddyserver.com/docs/caddyfile/directives/reverse_proxy]. There is no `trusted_proxies` in `deploy/Caddyfile`, so the header reaching the app holds exactly the real client IP. **Take the right-most comma-separated entry**, strip it, parse it with `ipaddress.ip_address`, and fall back to the peer if parsing fails. Treat the peer as loopback when `ip.is_loopback`, or when `ip.ipv4_mapped` is set and that address is loopback.
- **Design:** `client_ip(peer, xff_header) -> str` as a pure function (easy to test). `LoginThrottle` holds an `OrderedDict[key] -> (failures, locked_until, last_seen)` behind the existing `threading.Lock`, with an injectable `clock=time.time`. Methods take a `key`: `locked_out(key)`, `seconds_remaining(key)`, `record_failure(key)`, `record_success(key)`. Keep the current contract: a failure after the window has elapsed starts a fresh count (`auth.py:331-342`). Bound the table with `max_entries` (e.g. 4096). On insert, first drop entries that are unlocked and stale (older than `lockout_s`), then evict the least recently seen. Evicting an attacker's own locked entry only resets the attacker, which is acceptable for a courtesy guard backed by a 256-bit password. Key IPv6 addresses by their `/64` so one host cannot get 2^64 fresh buckets `[ASSUMED: IPv6 reaching the VPS; harmless either way]`.
- **Existing tests to migrate:** the harness checks at `companion/test_companion_app.py:1720-1786` construct `LoginThrottle(limit=3, lockout_s=…)`, call the methods with no key and time-travel through `throttle._locked_until` (`:1775`). They must be rewritten for the keyed API with the injected clock, in whatever form Phase 33 left them. The HTTP lockout checks (`test_companion_app.py:7938-7990`, `test_browser_ux.py:3396`) send from `127.0.0.1` without XFF, so they still lock their own isolated harness and keep passing unchanged.
- **New pytest tests:** (a) unit: IP A reaches the limit and IP B is not locked; (b) unit: the table never exceeds its cap under a spray; (c) unit: `client_ip` honours XFF only from a loopback peer, takes the right-most entry, and rejects garbage; (d) integration against the Phase 32/33 companion server fixture: 5 wrong POSTs with `X-Forwarded-For: 203.0.113.5`, then the right password with `X-Forwarded-For: 198.51.100.7` → **303** (`redirect()` is 303, `app.py:1333`), while 203.0.113.5 still gets **429**.

## SEC-02 — HSTS (findings)

- `deploy/Caddyfile` has two site blocks (`:45` device, `:94` companion) and no `header` directive today.
- Add `header Strict-Transport-Security "max-age=31536000"` to **both** blocks. Leave out `includeSubDomains` and `preload` (D-15). `includeSubDomains` would add nothing: `config-…nip.io` is not a subdomain of the device host, and the companion's own name has no children. No `defer` is needed because the upstreams never set that header [CITED: Caddy header docs].
- **Byos block is harmless:** HSTS is a browser (user-agent) policy. The firmware uses `esp_http_client` with `esp_crt_bundle_attach` against the configured `https` base URL (`firmware/main/api_client.c:204-208,281-283,370-373,403-405`) and never reads that header. The only header handling is `esp_http_client_fetch_headers` for the content length (`:156,:417`). The only cost is a few bytes per response and per Caddy JSON log line (`resp_headers`).
- Test: pytest parses the rendered Caddyfile and asserts each site block contains the HSTS line. The live check is `curl -sI https://<host>/login | grep -i strict-transport-security` at the cutover checkpoint.

## SEC-03 — Origin / Sec-Fetch-Site on every POST (findings)

- **One dispatcher:** `do_POST` (`app.py:3453-3615`). There is no `do_PUT`/`do_DELETE`/`do_PATCH` (grep `def do_`: only `:2901` GET and `:3453` POST). POST routes: `LOGIN_ROUTE` (:3457), `SETTINGS_ROUTE` (:3460), `POLL_ROUTE` (:3465), `QUICK_DISPLAY_ROUTE` (:3470), `QUICK_QUIET_HOURS_ROUTE` (:3475), `QUICK_LED_ROUTE` (:3489), `THEME_ROUTE` (:3501), `LANG_ROUTE` (:3509), `LOGOUT_ROUTE` (:3529), `airlines_page.RESOLVE_ROUTE` (:3541), the manual-resolution delete prefix (:3549), the illustration upload prefix (:3562), `RULES_ADD_ROUTE` (:3573), `CALENDAR_DISCONNECT_ROUTE` (:3581), `CALENDAR_CONNECT_ROUTE` (:3587), `NOTIFICATIONS_TEST_ROUTE` (:3594), and the rules delete prefix (:3604); the fall-through 404 is at :3615.
- **Hook:** the first statement of `do_POST`, before any routing and before `read_form()`. For example `if not self._post_origin_ok(): return self.send_html(403, self._forbidden_page())`. This covers login (D-16) and any route added later. Phase 40 (CMP-01 route table) will move this into its dispatcher; keep it a single helper so the move is trivial.
- **Rule:**
  - `sfs = headers.get("Sec-Fetch-Site")` → reject if the value is `cross-site` or `same-site`.
  - `origin = headers.get("Origin")` → if present: reject `"null"`; otherwise compare `urlsplit(origin).netloc.lower()` with `headers.get("Host","").lower()`, normalising a default `:443`/`:80` port.
  - Neither header present → allow (the session cookie is still required).
  - Comparing against `Host` is sound for CSRF: a browser always sets `Host` to the real target, and an attacker page cannot forge it. Caddy passes `Host` through unchanged by default [CITED: reverse_proxy docs].
  - Behind Caddy: Origin `https://skypane.algernon.ovh` matches Host `skypane.algernon.ovh`. In Playwright: Origin `http://127.0.0.1:PORT` matches Host `127.0.0.1:PORT`. Local test hosts therefore need no allowlist, and `SKYPANE_COMPANION_HOST` does not need to be read.
- **JS:** the only `fetch` POST is `companion/static/quick-switch.js:301-305` (`method: "POST", credentials: "same-origin", redirect: "manual"`). The other `fetch` (`freshness.js:886`) is a GET. Browsers send `Origin` on every non-GET/HEAD fetch and on form POSTs, and send `Sec-Fetch-Site: same-origin` for same-origin requests `[CITED: Fetch standard; ASSUMED for exact per-browser version floors]`. Pages send `Referrer-Policy: same-origin` (`app.py:1253`), which only changes cross-origin requests (their Origin becomes `null`, which is rejected anyway).
- **Tests keep passing:** harness and pytest HTTP clients (`urllib`/`http.client`) send neither header. Playwright form posts and `fetch` calls are same-origin. Playwright `APIRequestContext` posts send no `Origin`.
- **New pytest tests:** POST `/login` and `/poll-now` with `Origin: https://evil.example` → 403; with `Sec-Fetch-Site: cross-site` → 403; with `same-site` → 403; with matching `Origin` + `same-origin` → normal behaviour; with neither header → normal behaviour; `Origin: null` → 403. One Playwright test: a page on a second loopback origin (e.g. `http://localhost:<other port>` serving a form that targets `http://127.0.0.1:<companion port>/quick/display`) is rejected with 403 and the device config is unchanged.

## SEC-04 — Backups (findings)

### State inventory (`/opt/skypane/state`, from `os.path.join(state_dir, …)` and filename constants)

| File / dir | Writer | Back up? | Why |
|------------|--------|----------|-----|
| `history.db` (+ `-wal`, `-shm`) | poll, companion (`server/history_db.py:43,189-199`, **WAL**) | **YES** (online backup API; do not copy the -wal/-shm) | Flight history and battery telemetry; irreplaceable |
| `byos_state.json` | byos (`byos_server.py:142-159`) | **YES** | Device bearer tokens. Losing it forces re-enrolment, and with FW-08 "refuse to re-enrol a known MAC" it could lock the frame out |
| `device_config.json` | companion/byos (`server/device_config.py:495`) | **YES** | Every setting, including the notifications topic URL (secret-shaped) |
| `calendar_rules.json`, `calendar_url.secret` (`0600`) | companion/poll (`calendar_rules.py:107,122,325`) | **YES** | User config; the secret file forces the snapshot to run as `skypane` |
| `colour_rules.json` | companion (`colour_rules.py:54`) | **YES** | User config |
| `manual_resolutions.json` | companion (`manual_resolutions.py:60`) | **YES** | User-curated registry |
| `illustration_overrides/*.png` | companion upload (`illustrations.py:770`) | **YES** | Uploaded images |
| `poll_state.json` | poll (`poll_loop.py:334`) | **YES** (small) | Enrichment cache, unresolved-prefix registry (durable per `deploy/README.md:233-240`), battery-critical flag |
| `battery_state.json` | byos (`byos_server.py:499`) | yes (tiny) | Refreshed on the next wake; cheap to include |
| `panel.bin` | poll | no | Re-rendered every 30 s |
| `gallery/` (≤25 PNGs, `poll_loop.py:83-84`) | poll | **yes** (D-24) | Rendered cache, but the developer wants the visual history kept (D-24, 2026-09-23) |
| `theme_previews/` | companion (`theme_preview.py:149`) | no | Cache |
| `caddy-access.log*` | caddy | no | D-03; already ingested into `history.db` |
| `calendar_rules.lock`, `*.tmp`, future `poll.lock` (INT-01), `img/` (INT-05, Phase 36) | various | no | Locks, temp files, content-addressed panel copies |
| `/opt/skypane/skypane.env` | human | **never** (D-05) | Secrets are recreated from the password manager at restore time |

Planner note: build the archive from an **include list** (the YES rows plus `illustration_overrides/`), not an exclude list, so a file added in a later phase is not silently skipped. Log any unlisted top-level file in the job output so drift gets noticed.

### Snapshot job (`deploy/backup/skypane_backup.py`, stdlib)
- Run as `User=skypane Group=skypane` from `skypane-backup.timer`: `OnCalendar=*-*-* 03:15:00 UTC`, `Persistent=true`, `RandomizedDelaySec=10m`. The unit carries the same SEC-06 hardening plus `PrivateNetwork=true` (it needs no network) and `ReadWritePaths=/opt/skypane/state /var/lib/skypane-backup/archives`.
- **Why the state directory must be writable:** opening a WAL database, even to read it, needs write access to `-shm` [ASSUMED from SQLite WAL documentation; verify in the fake-root test by running the backup with the state directory read-only and expecting failure].
- `src = sqlite3.connect(state/history.db, timeout=30)`; `dst = sqlite3.connect(tmp/history.db)`; `src.backup(dst)`; then `dst.execute("PRAGMA integrity_check")` must return `ok`; close both. The backup API copies pages consistently while other connections write [CITED: Python sqlite3 docs].
- The JSON files are replaced atomically with `os.replace` by their writers (`byos_server.py:155-159`; INT-02 in Phase 36 centralises this), so a plain copy reads the old or the new version, never a torn file. Optionally take Phase 36's `state/poll.lock` flock if it exists, for a multi-file-consistent snapshot. Do not depend on it (Wave A must not require Phase 36).
- Write `skypane-state-YYYYMMDDTHHMMSSZ.tar.gz` with `tarfile.open(..., "w:gz")` into `archives/.partial-*`, fsync, then `os.replace` into its final name. Write `<name>.sha256` the same way. With `UMask=0027` the files are `0640`, and the setgid directory gives them group `skypane-backup`. Retention: keep the 14 newest, prune the rest (plus their `.sha256`).

### Pull access: dedicated `skypane-backup` user + Python gate (recommended over rrsync)
- Create the user with `useradd --system --home-dir /var/lib/skypane-backup --shell /bin/sh skypane-backup`, then `usermod -p '*' skypane-backup`.
  - The shell **must not** be `nologin`: sshd runs the forced command through the user's shell `[ASSUMED: standard OpenSSH behaviour]`.
  - `'*'` rather than `'!'` avoids the "locked account" refusal path `[ASSUMED]`.
- Directory layout:
  - `/var/lib/skypane-backup` `root:root 0755`
  - `.ssh/` `root:root 0755`, and `.ssh/authorized_keys` `root:root 0644`. Root ownership passes sshd StrictModes, and the user cannot rewrite its own key options.
  - `archives/` `skypane:skypane-backup 2750`
  - `pulled/` `skypane-backup:skypane-backup 0755`, holding `last-pull` (`0644`, readable by the companion running as `skypane`).
- `authorized_keys` line: `restrict,command="/usr/bin/python3 /usr/local/lib/skypane/backup_gate.py" ssh-ed25519 AAAA… skypane-backup-pull@mac`.
- The gate parses `SSH_ORIGINAL_COMMAND` with `shlex.split` (no shell, no eval) and accepts exactly these verbs:
  - `list` prints one line per archive: `name size sha256`, where the checksum comes from the `.sha256` file.
  - `get NAME` requires NAME to match `^skypane-state-\d{8}T\d{6}Z\.tar\.gz$` and the file to exist in `archives/`, then streams it with `shutil.copyfileobj` to `sys.stdout.buffer`.
  - `ack NAME` requires the same name validation and existence, then writes NAME atomically (tmp + `os.replace`) to `pulled/last-pull`.
  - Anything else exits 2 with a one-line error.
  - The gate never touches paths outside those two directories.
- **The marker holds the archive name, not a client timestamp.** The companion computes freshness from the **snapshot time in the name**. If the VPS job silently stops producing archives, or the Mac stops pulling, the age grows either way. A stolen key could only claim a snapshot that really exists.

### Mac side (`deploy/backup/mac/`)
- `skypane-backup-pull.sh`:
  - **POSIX sh**: macOS `/bin/bash` is 3.2, so no `mapfile` and no associative arrays. It uses `ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 -i "$KEY"` and a config file (`~/.config/skypane/backup.conf`: target, key path, destination).
  - Flow: `list`; for each archive missing locally, `get` it to `.partial` → `shasum -a 256` must match → `mv`; then `ack <newest pulled>`.
  - Retention: keep the 30 newest, plus the oldest archive of each `YYYYMM` for 12 months. Names sort lexically. Use `sort -r | tail -n +31`, never GNU `head -n -N`.
  - Retry `list` 3 times with a sleep, because the network may not be up right after wake.
- **launchd plist template:**
  - `Label` (e.g. `com.skypane.backup-pull`), `ProgramArguments` = `/bin/sh` + an absolute script path.
  - `StartCalendarInterval` `{Hour=9, Minute=30}` plus `RunAtLoad=true`. launchd coalesces missed runs while asleep, but its docs are silent about powered-off periods [CITED: launchd.plist(5)]. `RunAtLoad` covers logins after a shutdown, and the script is idempotent.
  - `StandardOutPath`/`StandardErrorPath` = `/Users/<you>/Library/Logs/skypane-backup-pull.log`. Paths in a plist are not tilde-expanded, so the install script substitutes `$HOME`.
- **Paths protected by macOS privacy controls (TCC):** a LaunchAgent cannot touch `~/Documents`, `~/Desktop` or `~/Downloads` without Full Disk Access `[ASSUMED]`. The installer copies the script to `~/Library/Application Support/SkyPane/` and stores backups in `~/Library/Application Support/SkyPane/backups/` (or `~/SkyPaneBackups/`), never inside a repo checkout under `~/Documents`.
- Install with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.skypane.backup-pull.plist`. Test with `launchctl kickstart -k gui/$(id -u)/com.skypane.backup-pull`, inspect with `launchctl print gui/$(id -u)/com.skypane.backup-pull`.

### Freshness line (D-07)
- The marker path reaches the companion through a new env var in `skypane.env` (e.g. `SKYPANE_OFFBOX_MARKER=/var/lib/skypane-backup/pulled/last-pull`), read with `os.environ.get` like `SKYPANE_SLEEP_S` (`app.py:145-152`). **Unset** (dev, tests, Playwright): the line is not rendered. **Set but missing or invalid**: status "never", treated as an alert.
- Parse the content with the same regex, take the UTC snapshot time from the name, and compute the age with `layout.age_seconds` (`layout.py:1052`). The status comes from `staleness_status(age, warn_s, error_s)` (`health_page.py:918-936`); note that it maps `None` (never) to `"warn"`. Suggested thresholds: warn at >3 days (D-07); planner decides whether "never" and "stale" should be `warn` or `error`.
- Render a nested card in the "Server data" section (`health_page.py` `render()`, around the `server_data_section_html` block) using `layout.card_status_class("page-section", state)`, `layout.status_dot(state, label)` and `layout.concise_timestamp_html(ts, now)`, so it becomes "Updated 14:32" server-side and the relative-time ticker upgrades it (skill: "Updated 0s ago" lesson). Planner decision: should the alert feed `overall_severity()` (`health_page.py:2039`) and so light the Health nav dot? Recommend **yes, as `warn`**.
- French strings go in `companion/i18n_fr/health.py`.

### Restore (documented in `deploy/README.md`, rehearsed once)
- **Rehearsal on the Mac (D-06):**
  - `tar -xzf <archive> -C "$SCRATCH"`
  - `python3 -c "import sqlite3; print(sqlite3.connect('$SCRATCH/history.db').execute('PRAGMA integrity_check').fetchone())"` should print `('ok',)`
  - Then run the companion from a repo venv: `SKYPANE_COMPANION_PASSWORD=x SKYPANE_COMPANION_INSECURE_COOKIES=1 server/.venv/bin/python3 companion/app.py --port 8650 --state-dir "$SCRATCH"`, open `http://127.0.0.1:8650`, and check that Flights and Health show the production history and that Display/Device show the production settings.
- **Production restore procedure (documented, not executed):**
  1. `systemctl stop skypane-poll.timer skypane-poll.service skypane-companion skypane-byos`
  2. `mv state state.broken-<date>`
  3. `install -d -o skypane -g skypane -m 2775 state`
  4. `tar -xzf … -C state`
  5. `chown -R skypane:skypane state`
  6. Recreate `skypane.env` from the password manager if the box was lost.
  7. Start the units and let `activate.sh`'s probes, or the Verify section, confirm.
- Correct `deploy/README.md:262-271`, which claims the "VPS state is fully reproducible", and fix its `root@` examples (SEC-08).

## SEC-05 — Atomic, verified deploy (findings)

- **Current flow** (`deploy/deploy.sh:36-85`): rsyncs `server/`, `stub-server/` and `companion/` in place with `--delete`, as `skypane` (`--rsync-path="sudo -u skypane rsync"`), while the services run. It copies `adsb-test/runway3.json` to `/opt/skypane/config/runway3.json`, compares the requirements hash **locally with `sha256sum`** (not on macOS by default), runs pip as `skypane`, restarts byos and companion, starts the timer, and prints the journals. There is no probe, and units and the Caddyfile are never shipped (they are installed only by `provision.sh:109-131`).
- **Hard-coded `/opt/skypane/<code dir>` references** (these must change):
  - `skypane-byos.service:17-25`
  - `skypane-companion.service:22-27` (incl. `--geofence /opt/skypane/config/runway3.json`)
  - `skypane-poll.service:15-21`
  - `provision.sh:58` (mkdir of the code dirs) and `:100-103` (venv owner)
  - `deploy.sh` (whole file)
  - `deploy/README.md` (many lines)
  - `Caddyfile:85` (`/opt/skypane/state/...`, stays)
- **Python code needs no change:** the only `/opt/skypane` strings in `.py` files are comments (`companion/app.py:149`, `companion/pages/config_page.py:5295`, `hardware/logtools.py:672`). Code roots come from `os.path.abspath(__file__)` (`app.py:61-64`, `poll_loop.py:57-60`), which does not resolve symlinks, so `_REPO_ROOT` becomes `/opt/skypane/current` and imports and static files resolve inside the active release. `poll_loop.DEFAULT_STATE_DIR` (`poll_loop.py:75`) is only a fallback; all units pass `--state-dir`.
- **Release contents:** `git archive --format=tar "$SHA" server stub-server companion deploy adsb-test/runway3.json`, piped into `ssh "$TARGET" "sudo /bin/sh -c 'mkdir -p … && tar -x -C …'"`.
  - Units use `/opt/skypane/current/adsb-test/runway3.json` for `--geofence`. This path is also `detect.py:155`'s default, so `/opt/skypane/config/` becomes obsolete after cutover.
  - Consider excluding `*/test_*.py` from the archive (git pathspec `':(exclude)**/test_*.py'`) to keep releases small.
- **Ownership:** releases are `root:root`, not writable by the service user. Pre-compile with `/opt/skypane/venv/bin/python3 -m compileall -q releases/<sha>`, because services cannot write `__pycache__` under `ProtectSystem=strict`. At cutover, consider `chown root:skypane /opt/skypane && chmod 0750 /opt/skypane`, plus a root-owned venv, so a compromised service cannot rewrite its own code or interpreter. `ProtectSystem=strict` already blocks writes from inside the units.
- **venv:** keep the shared `/opt/skypane/venv` (D-09). Compare the hash of the release's requirements file (Phase 32 TST-08 may rename it to a lock file; re-read at execution) with `/opt/skypane/venv/.requirements.sha256`, and run `pip install -r` **before** the swap. Rollback does the same against the previous release's file when the hashes differ.
- **Smoke check before the swap:** `cd releases/<sha> && /opt/skypane/venv/bin/python3 -c "import server.poll_loop, companion.app"`, plus `python3 stub-server/byos_server.py --help`. Importing does not require the password, which is checked only in `main()` (`app.py:3651-3656`). This catches syntax and import errors without touching the network. Do **not** gate on a synchronous `systemctl start skypane-poll.service`: an upstream ADS-B outage would make every deploy roll back.
- **Swap:** `ln -sfn "releases/$SHA" "$ROOT/.current.tmp" && mv -T "$ROOT/.current.tmp" "$ROOT/current"`. `mv -T` is an atomic `rename(2)` over the existing symlink (GNU coreutils; the VPS is Linux). Restart `skypane-byos` and `skypane-companion` immediately after the swap: until then, a running companion that re-reads static files through `_HERE` would already see the new release's files.
- **Units:** `install -m 644 releases/<sha>/deploy/*.service,*.timer /etc/systemd/system/` → `systemctl daemon-reload` → `systemctl enable skypane-backup.timer` (first time) → restart. Rollback reinstalls the previous release's units.
- **Caddyfile:**
  - Render from the release's `deploy/Caddyfile` with the anchored substitution already proven in `provision.sh:116-123`. Move it into one shared function or script used by both scripts.
  - Take the hostnames from a **strict parse** of `skypane.env` (`SKYPANE_PUBLIC_HOST`, `SKYPANE_COMPANION_HOST`), validated against `^[A-Za-z0-9.-]+$`.
  - Write to `/etc/caddy/Caddyfile.new`, run `runuser -u caddy -- caddy validate --config /etc/caddy/Caddyfile.new --adapter caddyfile`, then, only if `cmp` shows a difference: keep a `.prev` copy, `mv` the new file into place and `systemctl reload caddy`. On rollback, restore `.prev` and reload.
  - `systemctl reload caddy` returns non-zero and keeps the old config if the new one fails `[ASSUMED: caddy.service ExecReload=caddy reload --force]`.
- **Probes** (retry every 1 s for up to 30 s, since services need a moment to bind):
  - `systemctl is-active --quiet` for `skypane-byos.service`, `skypane-companion.service`, `skypane-poll.timer` and `caddy.service`.
  - `curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:${SKYPANE_BYOS_PORT}/device/v1/display` = `401` (unauthenticated → 401, `byos_server.py:611-613`).
  - `http://127.0.0.1:${SKYPANE_COMPANION_PORT}/login` = `200` (`app.py:2905-2914`).
  - HTTPS through Caddy without a hairpin: `curl --resolve "${PUBLIC}:443:127.0.0.1" https://${PUBLIC}/device/v1/display` = `401` and `curl --resolve "${COMPANION}:443:127.0.0.1" https://${COMPANION}/login` = `200`.
  - Also assert that the `Strict-Transport-Security` header is present (SEC-02 verified on every deploy).
- **Failure path:** swap back to the previous release (if there is none, as on the first cutover, fail loudly without swapping), reinstall its units and Caddyfile, daemon-reload, restart, re-probe, print `journalctl -u <failed unit> -n 50 --no-pager`, and `exit 1`. `deploy.sh` runs under `set -euo pipefail` and `ssh` propagates the remote exit status, so the CI step goes red.
- **Pruning:** keep 5 releases by modification time. Never delete `readlink current` or the previous release.
- **Re-deploying the same SHA** (a re-run job): extract into `releases/.partial-<sha>-$$` and `mv -T` into place only if `releases/<sha>` is absent. If `current` already points at it, restart and probe only.
- **Cutover (D-12):** run the updated `provision.sh` (creates `releases/`, the backup user and directories, the SSH drop-in and env ownership), then the first new `deploy.sh`. The old `/opt/skypane/{server,stub-server,companion,config}` directories stay untouched as a manual fallback until the developer confirms, then are deleted by hand.
- **ci.yml:** the CI job stays a single `./deploy/deploy.sh "$DEPLOY_SSH_TARGET"` step (D-20). Concurrency is unchanged (D-13).

## SEC-06 — systemd hardening (findings)

**Measured locally** (systemd 255.4, `systemd-analyze security --offline=true`): all three current units score **8.3 EXPOSED**. A draft poll unit with the set below scores **1.1 OK**, and byos with `IPAddressDeny=any` + `IPAddressAllow=localhost` scores **0.9 SAFE**. `--threshold=N` exits non-zero when exposure×10 > N (1.1 passes `--threshold=20` and fails `--threshold=10`) [VERIFIED: local run].

| Directive | byos | companion | poll | backup | Note |
|-----------|------|-----------|------|--------|------|
| `CapabilityBoundingSet=` (empty), `AmbientCapabilities=` | ✓ | ✓ | ✓ | ✓ | Unprivileged ports only (8642/8643) |
| `PrivateDevices=true`, `DevicePolicy=closed` | ✓ | ✓ | ✓ | ✓ | `/dev/null`, `/dev/urandom` stay available |
| `ProtectKernelTunables/Modules/Logs=true`, `ProtectControlGroups=true`, `ProtectClock=true`, `ProtectHostname=true` | ✓ | ✓ | ✓ | ✓ | |
| `ProtectProc=invisible` | ✓ | ✓ | ✓ | ✓ | Also hides argv from other users (helps "no secret in ps" before Wave B) |
| `ProcSubset=pid` | ✓ | ✓ | ✓ | ✓ | `[ASSUMED]` safe for CPython/Pillow; drop it if a VPS smoke run fails |
| `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX` | ✓ | ✓ | ✓ | `AF_UNIX` only | AF_UNIX for resolved/nss; glibc tolerates a refused AF_NETLINK `[ASSUMED]` |
| `RestrictNamespaces=true`, `RestrictRealtime=true`, `RestrictSUIDSGID=true`, `LockPersonality=true`, `SystemCallArchitectures=native` | ✓ | ✓ | ✓ | ✓ | `RestrictSUIDSGID` does not stop the kernel from inheriting setgid on new directories in `state/` |
| `MemoryDenyWriteExecute=true` | ✓ | ✓ | ✓ | ✓ | CPython's experimental JIT is off by default; Pillow and sqlite do no W+X `[ASSUMED]`; verify on the VPS |
| `SystemCallFilter=@system-service`, `SystemCallErrorNumber=EPERM` | ✓ | ✓ | ✓ | ✓ | |
| `UMask=0027` | ✓ | ✓ | ✓ | ✓ | See below |
| `IPAddressDeny=any` + `IPAddressAllow=localhost` | **Wave B** | **✗ (not possible)** | ✗ | `PrivateNetwork=true` instead | The companion makes outbound calls (`/poll-now` → `run_once`, `app.py:3310`; ICS fetch; ntfy `notify.send_notification`, `app.py:2829`). systemd IP filters apply to both directions. |
| Existing: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome`, `ReadWritePaths=/opt/skypane/state` | keep | keep | keep | + archives dir | |

- **D-18 companion loopback filter:** not feasible without a Python change. The alternative is a `--bind 127.0.0.1` flag in `companion/app.py:3665`, which D-18 puts out of Wave A. It needs a developer decision (Open Question 1).
- **UMask=0027 is safe here:** new files are `0640` and new directories `2750` inside the setgid `state/`. The only cross-user access is (a) caddy writing its own `caddy-access.log` with an explicit `mode 660` (`Caddyfile:84-91`), which our umask does not affect, and (b) poll and companion reading that log through the `skypane` group, also unaffected. Backup archives stay group-readable (`0640`) by `skypane-backup` through the setgid `archives/` directory. No process reads state as "other".
- **ReadWritePaths must exist** or the unit fails with status 226/NAMESPACE. `provision.sh` creates the backup directories before the backup unit is first enabled, and `activate.sh` checks those prerequisites and fails with a clear message.
- **CI:** `for u in deploy/*.service; do systemd-analyze security --offline=true --threshold=20 "$u"; done`, plus a pytest that parses each unit with `configparser` (`strict=False`, multi-value aware) and asserts the required directive set. `systemd-analyze verify` would fail in CI on `ExecStart` paths that don't exist (observed locally: "Command /opt/skypane/venv/bin/python3 is not executable"). Run `verify` only on the VPS.
- **Before/after record (D-17):**
  - Before: at the first checkpoint, `sudo systemd-analyze security skypane-byos.service skypane-companion.service skypane-poll.service` on the VPS (online scores can differ slightly from offline).
  - After: the same command after cutover.
  - Offline before/after values from CI go in the SUMMARY.

## SEC-07 — Secrets (findings)

- **No direct reader of `skypane.env`:**
  - `os.environ` reads in production code are only `companion/auth.py:166` (password), `auth.py:254` (insecure cookies) and `server/wake.py:86` (`SKYPANE_SLEEP_S`, used by the companion through `app.py:946`).
  - Every `skypane.env` string in `.py` files is in a comment or a test that reads `skypane.env.example` (`test_companion_app.py:1683`).
  - `config_page.py:5296` is a comment describing systemd injection.
  - byos opens only state files and the image (`byos_server.py:148-720`).
  - Conclusion: `root:root 0600` is safe because systemd reads `EnvironmentFile=` as PID 1 `[CITED: systemd.exec(5) behaviour; ASSUMED wording]`. The new `activate.sh` reads it as root, which is fine.
- Update `provision.sh` (after the file exists: `chown root:root`, `chmod 600`, idempotent) and `deploy/README.md:126-127,133-134` (today they say `chown skypane:skypane`).
- **ci.yml (D-20):**
  - Replace `echo "${{ secrets.DEPLOY_HOST_KEY }}" >> ~/.ssh/known_hosts` (`ci.yml:141`) with `env: DEPLOY_HOST_KEY: ${{ secrets.DEPLOY_HOST_KEY }}` and `printf '%s\n' "$DEPLOY_HOST_KEY" >> ~/.ssh/known_hosts`.
  - Replace `./deploy/deploy.sh "${{ secrets.DEPLOY_SSH_TARGET }}"` (`:147`) with `env: DEPLOY_SSH_TARGET: …` and `./deploy/deploy.sh "$DEPLOY_SSH_TARGET"`.
  - The `webfactory/ssh-agent` `with:` input (`:129-131`) is not a `run:` script and stays as is.
  - Phase 32 (TST-04/06/07) also edits `ci.yml`: re-read it at execution.
- **Wave B (after Phase 36):**
  - Today `--secret` is an argparse option with `default=""` (`byos_server.py:741-742`), compared at `:584-586`. The bind address is hard-coded at `:766`, and there is **no `--bind` flag** yet.
  - Change: `ap.add_argument("--secret", default=os.environ.get("SKYPANE_BYOS_SECRET", ""))`. Keep `--secret` for the LAN stub flow and document that it is visible in `ps`.
  - Add `ap.add_argument("--bind", default="0.0.0.0")`, keeping the LAN default, and use `ThreadingHTTPServer((args.bind, args.port), Handler)`. Update the startup print.
  - Unit: drop `--secret ${SKYPANE_BYOS_SECRET}` (`skypane-byos.service:22`), add `--bind 127.0.0.1`, `IPAddressDeny=any`, `IPAddressAllow=localhost`.
  - If Phase 34 FW-08 replaced the single setup secret with per-device secrets, apply the same "env, not argv" rule to whatever secret remains (D-01).
  - Tests that spawn byos (`stub-server/test_poll_cycle.py`, `server/test_pipeline_e2e.py:88`) pass no `--secret` today (grep).

## SEC-08 — SSH (findings)

- Today `provision.sh:159-164` runs `sed` over `/etc/ssh/sshd_config` (PasswordAuthentication/KbdInteractiveAuthentication), then `systemctl reload ssh || … || true`. Nothing validates the result, and there is no `PermitRootLogin`.
- Ubuntu's `sshd_config` starts with `Include /etc/ssh/sshd_config.d/*.conf`, and "for each keyword, the first obtained value will be used" [CITED: sshd_config(5)]. `00-skypane.conf` therefore beats cloud-init's `50-cloud-init.conf` (D-08).
- Drop-in (`install -m 0644` to `/etc/ssh/sshd_config.d/00-skypane.conf.new`, then `sshd -t -f /etc/ssh/sshd_config`; on success `mv` into place; on failure delete it and exit non-zero):
  ```
  PermitRootLogin no
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  PubkeyAuthentication yes
  PermitEmptyPasswords no
  X11Forwarding no
  MaxAuthTries 3
  ```
  Leave out `AllowUsers`: it is too easy to lock out an unforeseen login. `Match` blocks inside include files have version-dependent scope `[ASSUMED]`, so avoid them.
- **Reload:** Ubuntu ≥22.10 uses socket activation (`ssh.socket` starts `ssh.service` on the first connection) [CITED: discourse.ubuntu.com/t/30189]. Use `systemctl try-reload-or-restart ssh.service`. It reloads a running sshd, and if sshd is not running, the next connection starts it with the new config anyway. The existing `|| true` must go: a failure must be visible.
- **Verify:** `sudo sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|maxauthtries) '` → `no no no yes 3`. If cloud-init or an image file has `Match` blocks, use `sshd -T -C user=ubuntu,host=x,addr=203.0.113.1`.
- **Test in CI:** pytest runs `provision.sh`'s SSH step as an extracted function against a tmp `sshd_config.d` with a stub `sshd`, or at minimum checks that the drop-in text contains the keys. shellcheck covers the script. Real validation is VPS-only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Consistent copy of a WAL SQLite database under writes | `cp history.db*` | `sqlite3.Connection.backup` | Copying live -wal/-shm files gives torn or corrupt snapshots |
| IP parsing and loopback detection | string prefix `"127."` | `ipaddress.ip_address(...).is_loopback`, `.ipv4_mapped` | IPv6 and mapped forms, garbage input |
| Parsing the forced command | `eval`, `case $SSH_ORIGINAL_COMMAND in *` globbing | `shlex.split` + exact verb + strict regex | Injection through the command string |
| Atomic symlink swap | `rm current; ln -s` | `ln -sfn tmp && mv -T tmp current` | A window with no `current` means a unit start fails |
| Freshness age with ticking relative time | new JS | `layout.concise_timestamp_html` + existing `relative-time.js` | Design contract (skill) |
| Caddyfile hostname templating | Caddy `{$ENV}` with the env file in caddy.service | Anchored render from a strict parse | Caddy would receive every secret |
| Loading the env file in shell | `source skypane.env` as root | Regex extraction of the named keys | Code execution as root; syntax mismatch |

## Runtime State Inventory (cutover/migration items)

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `/opt/skypane/state/*` (see SEC-04 table) is unchanged by the move. `/opt/skypane/.requirements.sha256` (`deploy.sh:65,68`) moves to `venv/.requirements.sha256` | Code edit (activate.sh); the first new deploy re-runs pip once |
| Live service config | `/etc/caddy/Caddyfile` (installed by `provision.sh`, hand-edited per `README.md:100-108`, carries production hosts `skypane.algernon.ovh` + nip.io) | The first `activate.sh` overwrites it from the template + `skypane.env`. **Checkpoint:** diff the rendered file against the live one before the first swap (hand edits would be lost) |
| OS-registered state | systemd units in `/etc/systemd/system/skypane-*.{service,timer}` (from `provision.sh:110-113`); ufw rules; `caddy` in group `skypane`; new `skypane-backup` user and `skypane-backup.timer` | activate.sh reinstalls units; provision.sh creates the user and directories |
| Secrets/env vars | `/opt/skypane/skypane.env` owned `skypane:skypane 600` (README) → `root:root 600`; new key `SKYPANE_OFFBOX_MARKER`; GitHub secrets `DEPLOY_SSH_TARGET` (must be `ubuntu@…`), `DEPLOY_HOST_KEY`, `DEPLOY_SSH_PRIVATE_KEY` (names unchanged) | Human checkpoint: chown/chmod + add key; confirm or reset `DEPLOY_SSH_TARGET` |
| Build artifacts | Old in-place code dirs `/opt/skypane/{server,stub-server,companion,config}` and their `__pycache__`; venv owned by `skypane` | Leave until verified, then remove by hand; optionally `chown -R root:root venv` |

## Common Pitfalls

### 1. Forced command with a `nologin` shell
**What goes wrong:** the pull key authenticates, then every command fails with "This account is currently not available".
**How to avoid:** give `skypane-backup` `/bin/sh`. `restrict` + `command=` already prevent interactive use.
**Warning sign:** a `list` over ssh prints the nologin message.

### 2. Archive directory made unreadable, or state made readable, by group choices
**What goes wrong:** the pull user is put in group `skypane` to "fix" access, and can now write live state.
**How to avoid:** use the dedicated `skypane-backup` group on a setgid `archives/` directory.

### 3. First deploy after cutover rolls back with nowhere to go
**What goes wrong:** the probe fails and there is no previous release.
**How to avoid:** the script handles "no previous" by failing loudly without a swap-back, and the old in-place directories stay as a manual fallback during the cutover checkpoint.

### 4. The HTTPS probe depends on hairpin NAT or DNS from the VPS
**How to avoid:** `curl --resolve host:443:127.0.0.1`. Caddy listens on all addresses, loopback included.

### 5. Hand-edited production Caddyfile overwritten
**What goes wrong:** the README tells operators to hand-edit `/etc/caddy/Caddyfile` (`README.md:100-108`), and the first render overwrites those edits.
**How to avoid:** diff at the cutover checkpoint, make `skypane.env` the source of truth, and update the README paragraph.

### 6. SSH lock-out
**How to avoid:** D-08 procedure: keep session 1 open, apply the change, run `sshd -t`, reload, open session 2 as `ubuntu@` with the deploy key, and only then close session 1. Also check that `DEPLOY_SSH_TARGET` is `ubuntu@` **before** applying `PermitRootLogin no`.

### 7. The Mac pull cannot reach its files (TCC) or runs before the network is up
**How to avoid:** use the Application Support paths, retries, and `RunAtLoad`. Check the log at `~/Library/Logs/skypane-backup-pull.log`.

### 8. `ReadWritePaths` path missing → unit fails with status 226/NAMESPACE
**How to avoid:** provision creates the directories; activate checks them first.

### 9. Test isolation for the throttle
**What goes wrong:** the process-global singleton leaks between in-process tests.
**How to avoid:** tests build their own `LoginThrottle(clock=…)`. HTTP-level tests use isolated server fixtures, as today's harness already does (`test_companion_app.py:7938-7946`).

### 10. `MemoryDenyWriteExecute`/`ProcSubset` surprises on the distro Python 3.14
**How to avoid:** at the VPS checkpoint, watch one poll cycle (`journalctl -u skypane-poll -n 20`), one companion page load, a `/poll-now`, and a theme preview (Pillow). Revert only the offending directive, and record it.

## Code Examples

```python
# Source: stdlib docs (sqlite3.Connection.backup) — snapshot step
import sqlite3
def snapshot_db(src_path, dst_path):
    src = sqlite3.connect(src_path, timeout=30)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("backup copy failed integrity_check")
    finally:
        dst.close()
        src.close()
```

```python
# client IP for SEC-01 (pure, testable)
import ipaddress
def client_ip(peer, xff):
    try:
        p = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    loop = p.is_loopback or (getattr(p, "ipv4_mapped", None) and p.ipv4_mapped.is_loopback)
    if loop and xff:
        candidate = xff.split(",")[-1].strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    return str(p)
```

```python
# SEC-03 gate, called first in do_POST
from urllib.parse import urlsplit
_DEFAULT_PORT = {"https": "443", "http": "80"}
def post_origin_ok(headers):
    if headers.get("Sec-Fetch-Site", "").lower() in ("cross-site", "same-site"):
        return False
    origin = headers.get("Origin")
    if origin is None:
        return True
    if origin == "null":
        return False
    o = urlsplit(origin)
    netloc = o.netloc.lower()
    if o.port is not None and str(o.port) == _DEFAULT_PORT.get(o.scheme):
        netloc = o.hostname          # "https://h:443" -> "h"
    host = headers.get("Host", "").lower()
    for default in (":443", ":80"):
        if host.endswith(default):
            host = host[: -len(default)]
    return bool(host) and netloc == host
```

```
# Caddyfile (both site blocks)
header Strict-Transport-Security "max-age=31536000"
```

```yaml
# ci.yml deploy job (D-20)
- name: Trust the production host key
  env:
    DEPLOY_HOST_KEY: ${{ secrets.DEPLOY_HOST_KEY }}
  run: |
    install -d -m 700 ~/.ssh
    printf '%s\n' "$DEPLOY_HOST_KEY" >> ~/.ssh/known_hosts
    chmod 644 ~/.ssh/known_hosts
- name: Deploy
  env:
    DEPLOY_SSH_TARGET: ${{ secrets.DEPLOY_SSH_TARGET }}
  run: ./deploy/deploy.sh "$DEPLOY_SSH_TARGET"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tokens for CSRF only | Fetch Metadata (`Sec-Fetch-Site`) + Origin checking as a defence layer | Fetch Metadata shipped in all major browsers by 2023 `[ASSUMED]` | A stateless check at one choke point |
| rrsync as compressed doc script | `/usr/bin/rrsync` shipped by Debian/Ubuntu rsync | Debian bug #911321 resolution | Available if ever wanted; not used here |
| Apple rsync 2.6.9 | openrsync as `/usr/bin/rsync` on macOS 15+ `[ASSUMED]` | macOS Sequoia | Reason to avoid an rsync protocol dependency on the Mac |
| sshd non-socket | `ssh.socket` activation | Ubuntu 22.10 | Use `try-reload-or-restart ssh.service` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | sshd runs forced commands through the user's login shell, so `nologin` breaks them | SEC-04 | The gate fails. Caught at the backup-key checkpoint |
| A2 | `usermod -p '*'` avoids the locked-account refusal under Ubuntu's `UsePAM yes` | SEC-04 | Key login refused. Caught at the checkpoint |
| A3 | Opening a WAL database needs write access to its `-shm`, so the snapshot unit gets `ReadWritePaths` on state | SEC-04 | Only least privilege is affected; the job works either way |
| A4 | `/opt/skypane` is `0750` (Ubuntu `HOME_MODE`), which is why the gate goes in `/usr/local/lib` | SEC-04 | None; the placement is safe either way |
| A5 | `caddy validate` may open log files; run it as `caddy` | SEC-05 | A root-owned log file breaks log writes. Mitigated by `runuser` |
| A6 | `systemctl reload caddy` fails without applying a bad config | SEC-05 | Validate runs first anyway |
| A7 | `ProcSubset=pid`, `MemoryDenyWriteExecute`, and `RestrictAddressFamilies` without AF_NETLINK are fine for CPython 3.14 + Pillow + requests on Ubuntu 26.04 | SEC-06 | The service fails at runtime. VPS checkpoint smoke test; revert that one directive |
| A8 | Ubuntu 26.04 still uses `ssh.socket` activation with unit name `ssh.service` | SEC-08 | `try-reload-or-restart` is correct either way |
| A9 | LaunchAgents cannot reach TCC-protected folders without Full Disk Access | SEC-04 Mac | Pull fails with EPERM. Avoided by the path choice |
| A10 | Exact browser version floors for sending Origin/Sec-Fetch-Site | SEC-03 | Old browsers send neither header and are allowed (D-16), so there is no false reject |
| A11 | `Match` scope inside `sshd_config.d` files varies by version | SEC-08 | Avoided by using no `Match` |
| A12 | The VPS may receive IPv6 clients (`/64` keying) | SEC-01 | None |

## Open Questions

1. **Companion loopback-only (D-18).** An IP filter is impossible because the companion needs outbound access. A `--bind 127.0.0.1` flag is a ~3-line `app.py` change, and D-18 excludes Python changes from Wave A.
   - Recommendation: ask the developer whether to add a companion `--bind` flag in Wave A (it does not touch `byos_server.py`, so it does not conflict with Phase 36). Otherwise record ufw as the control and leave it to a later phase.
2. **Should the backup alert light the Health nav dot?** Recommend yes, as `warn`. The planner confirms it with the UI-phase gate.
3. ~~Include `gallery/` in backups?~~ **Resolved (D-24): yes, included.**
4. **Caddy in CI.** The runner has no `caddy`. Options: the render test only (recommended), or download a pinned caddy release with sha256 verification and run `caddy adapt --adapter caddyfile` (syntax only). The real `caddy validate` runs on the VPS in activate.sh.
5. **Phase 32 test layout.** It is unknown whether tests will live beside the code (`companion/test_*.py`) or under `tests/`. Follow whatever Phase 32 ships. New `deploy/` Python needs adding to pytest `testpaths` and possibly to coverage `source` (`pyproject.toml` `[tool.coverage.run] source`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| systemd-analyze (offline security) | SEC-06 CI gate | ✓ runner / ✓ local | 255.4 | — |
| shellcheck | Shell lint in CI | ✓ runner (not local sandbox) | 0.9.0 | `bash -n` locally |
| rsync / rrsync | Not required by the recommended design | ✓ runner 3.2.7 | — | — |
| caddy | `caddy validate` | ✗ CI, ✓ VPS | — | Render test in CI; validate on the VPS |
| sshd | `sshd -t` | ✗ CI, ✓ VPS | — | Text tests in CI; VPS checkpoint |
| python3 (system) on VPS | backup_gate.py (user skypane-backup) | ✓ (`provision.sh:70-71`) | distro 3.14 | — |
| curl on VPS | probes | ✓ (`provision.sh:78`) | — | — |
| macOS `shasum`, `/bin/sh`, `launchctl` | Mac pull | ✓ (stock macOS) `[ASSUMED]` | — | — |
| pytest + conftest (Phase 32) | All new tests | ✗ until Phase 32 merges | — | Wave A blocked on Phase 32 (D-01) |

**Missing dependencies with no fallback:** Phase 32's pytest infrastructure (an ordering dependency, not an install).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ xdist, cov) as delivered by Phase 32 (TST-01); Playwright for browser checks |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (created by Phase 32; re-read at execution) |
| Quick run command | `server/.venv/bin/python -m pytest -x -q <new test files>` |
| Full suite command | `./scripts/run-all-tests.sh` (a thin pytest wrapper after Phase 33) or `server/.venv/bin/python -m pytest -n auto` |
| Extra CI gates | `shellcheck deploy/*.sh deploy/backup/mac/*.sh`; `for u in deploy/*.service; do systemd-analyze security --offline=true --threshold=20 "$u"; done` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | IP A locked does not lock IP B; the table is capped; XFF is trusted only from loopback, right-most entry | unit + integration | `pytest -q -k "throttle or client_ip"` (e.g. `companion/test_login_throttle.py`) | ❌ Wave 0 |
| SEC-01 | Legacy throttle checks ported to the keyed API | unit | same file | ❌ (rewrite `test_companion_app.py:1720-1786` checks) |
| SEC-02 | Both rendered site blocks carry HSTS | unit | `pytest -q deploy/tests/test_caddyfile.py` | ❌ Wave 0 |
| SEC-02 | Header live on both hosts | manual/probe | activate.sh probe + `curl -sI https://<host>/ \| grep -i strict-transport` | VPS checkpoint |
| SEC-03 | Cross-origin / `same-site` / `null` Origin POST → 403 on every route incl. login; same-origin and header-less → unchanged | integration | `pytest -q companion/test_post_origin.py` | ❌ Wave 0 |
| SEC-03 | Real browser cross-origin form post rejected; same-origin UI still works | browser | `pytest -q -k origin companion/test_browser_*` | ❌ Wave 0 |
| SEC-04 | Snapshot has a consistent db (integrity ok) under a concurrent writer; include list honoured; retention 14; files 0640 | unit (tmp dirs) | `pytest -q deploy/tests/test_backup.py` | ❌ Wave 0 |
| SEC-04 | Gate: only `list`/`get`/`ack`; rejects path traversal, bad names, extra args; ack writes the marker | unit (subprocess, env `SSH_ORIGINAL_COMMAND`) | `pytest -q deploy/tests/test_backup_gate.py` | ❌ Wave 0 |
| SEC-04 | Mac script: pulls missing archives, verifies sha, retention, acks newest (fake `ssh` on PATH → gate) | integration | `pytest -q deploy/tests/test_mac_pull.py` + `shellcheck --shell=sh` | ❌ Wave 0 |
| SEC-04 | Health line: never → alert; > 3 days → alert; fresh → ok; unset env → hidden; FR string | unit (render) | `pytest -q -k offbox` | ❌ Wave 0 |
| SEC-04 | Restore rehearsal | manual-only | Mac checkpoint | — |
| SEC-05 | Happy path swaps `current`, installs units, daemon-reload, probes; failure (inactive unit / bad HTTP code) swaps back and exits ≠ 0; no-previous case; prune keeps 5 and never current/prev | integration (fake root + stubs) | `pytest -q deploy/tests/test_activate.py` | ❌ Wave 0 |
| SEC-05 | Caddyfile render: anchored substitution, rejects bad hostnames, never sources the env | unit | `pytest -q deploy/tests/test_caddyfile.py` | ❌ Wave 0 |
| SEC-05 | Real cutover + a deliberately failing deploy | manual-only | VPS checkpoint | — |
| SEC-06 | Units carry the directive set; offline score ≤ 2.0 | unit + CI | `pytest -q deploy/tests/test_units.py`; `systemd-analyze security --offline=true --threshold=20 deploy/<unit>` | ❌ Wave 0 |
| SEC-06 | Online before/after scores; services work under the sandbox | manual-only | VPS checkpoint | — |
| SEC-06/07 (Wave B) | byos `--bind 127.0.0.1` bound to loopback only; secret from env; no `--secret` in the unit | integration | `pytest -q stub-server/test_byos_bind_secret.py` | ❌ Wave B |
| SEC-07 | No `${{ secrets.* }}` inside any `run:` of ci.yml | unit (YAML text parse) | `pytest -q deploy/tests/test_ci_secrets.py` | ❌ Wave 0 |
| SEC-07 | Env file `root:root 600`; `pgrep -af byos_server` shows no secret | manual-only | VPS checkpoint | — |
| SEC-08 | Drop-in content; provision step validates with `sshd -t` before reload (stub `sshd`) | unit | `pytest -q deploy/tests/test_provision_ssh.py` | ❌ Wave 0 |
| SEC-08 | Live values and second-session login | manual-only | VPS checkpoint | — |

### Sampling Rate
- **Per task commit:** the quick command on the files touched, plus `ruff check .`
- **Per wave merge:** full pytest suite + shellcheck + offline systemd-analyze
- **Phase gate:** full suite green; all VPS/Mac checkpoints signed off before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Phase 32 merged (pytest, `conftest.py`, socket guard allowing loopback, companion server fixture from Phase 33 if available; otherwise a local fixture spawning `companion/app.py` on a free port)
- [ ] `deploy/tests/conftest.py` (or Phase 32's equivalent): a fake-root fixture and PATH stubs for `systemctl`, `curl`, `caddy`, `runuser`, `journalctl`, `sshd`, `ssh`
- [ ] pytest `testpaths` includes `deploy/`
- [ ] CI steps for shellcheck and `systemd-analyze security --offline=true --threshold=20` (add to the `test` job without touching concurrency, D-13)

## Security Domain

### Applicable ASVS Categories (Level 1)
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Per-IP throttle (SEC-01); long shared secret unchanged |
| V3 Session Management | yes | SameSite=Strict (existing) + Origin/Fetch-Metadata (SEC-03) |
| V4 Access Control | yes | Forced-command least privilege (SEC-04); `PermitRootLogin no` (SEC-08); root-owned releases |
| V5 Input Validation | yes | XFF parsed with `ipaddress`; gate verbs by regex; hostname regex before render |
| V6 Cryptography | limited | sha256 archive integrity (hashlib); no custom crypto |
| V9 Communications | yes | HSTS (SEC-02) |
| V14 Configuration | yes | systemd sandboxing, secrets out of argv, env file `0600 root` |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Owner lockout by a stranger's wrong guesses | DoS | Per-IP buckets, bounded table |
| XFF spoofing to dodge the throttle | Spoofing | Trust XFF only from a loopback peer; Caddy strips client XFF |
| Cross-site form/fetch POST | Tampering (CSRF) | Origin == Host, reject `Sec-Fetch-Site` cross-site/same-site |
| SSL-strip on first visit | Info disclosure | HSTS |
| Stolen backup key | Info disclosure / Elevation | Forced command, no shell or forwarding, archives only, never the env file; the key can only claim real archives |
| Half-deployed code / broken release | Availability | Atomic swap + probes + rollback |
| Secret in `ps` | Info disclosure | Env instead of argv (Wave B) + `ProtectProc=invisible` |
| Root SSH brute force | Elevation | `PermitRootLogin no`, key-only |

## Human Checkpoints (VPS / GitHub / Mac): exact commands

**CP-1 Baseline (before any change):**
```bash
ssh ubuntu@<vps>
sudo systemd-analyze security skypane-byos.service skypane-companion.service skypane-poll.service | tee ~/sec-before.txt
stat -c '%a %U:%G %n' /opt/skypane /opt/skypane/skypane.env /opt/skypane/state /opt/skypane/venv
sudo du -sh /opt/skypane/state/* | sort -h
sudo diff <(sed -n '/^[^#]/p' /etc/caddy/Caddyfile) <(sed -n '/^[^#]/p' /home/ubuntu/deploy/Caddyfile) || true   # record hand edits
sudo sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication) '
ls /etc/ssh/sshd_config.d/
```
**CP-2 GitHub:** `gh secret list; gh secret list --env production`. Confirm the target is `ubuntu@<vps>`, or re-set it with `gh secret set DEPLOY_SSH_TARGET --env production --body 'ubuntu@<vps>'` (use the level that already holds it).

**CP-3 Provision + env ownership + SSH drop-in (keep session 1 open):**
```bash
scp -r deploy ubuntu@<vps>:/home/ubuntu/deploy-37
ssh ubuntu@<vps>        # session 1 - keep open
sudo /home/ubuntu/deploy-37/provision.sh <public-host> skypane.algernon.ovh
sudo stat -c '%a %U:%G' /opt/skypane/skypane.env          # expect 600 root:root
echo 'SKYPANE_OFFBOX_MARKER=/var/lib/skypane-backup/pulled/last-pull' | sudo tee -a /opt/skypane/skypane.env >/dev/null
sudo sshd -t && sudo sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|maxauthtries) '
# from the laptop, a NEW terminal (session 2):
ssh -o PreferredAuthentications=publickey ubuntu@<vps> true && echo LOGIN-OK
ssh root@<vps> true    # expect: Permission denied
```
**CP-4 Cutover to the release layout (first new deploy):** push/merge → approve the production deploy in GitHub. Or from the laptop: `deploy/deploy.sh ubuntu@<vps>`. Then:
```bash
ssh ubuntu@<vps> 'readlink /opt/skypane/current; systemctl is-active skypane-byos skypane-companion skypane-poll.timer caddy skypane-backup.timer'
curl -sI https://<public-host>/device/v1/display | grep -Ei '^(HTTP|strict-transport)'
curl -sI https://skypane.algernon.ovh/login | grep -Ei '^(HTTP|strict-transport)'
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Origin: https://evil.example' https://skypane.algernon.ovh/login   # expect 403
ssh ubuntu@<vps> 'sudo journalctl -u skypane-poll -n 20 --no-pager'   # a cycle succeeded under the sandbox
```
Then log in in a browser, trigger Poll now, change a setting, and open Health.

**CP-5 Deliberate failed deploy (proves SC-4):** on a throwaway branch, run `deploy/deploy.sh ubuntu@<vps>` with a commit whose companion exits at start (e.g. an unset required argument). Expect a non-zero exit, `readlink /opt/skypane/current` unchanged, and services active. Revert.

**CP-6 After scores:** `sudo systemd-analyze security skypane-byos.service skypane-companion.service skypane-poll.service skypane-backup.service | tee ~/sec-after.txt`, and `sudo systemd-analyze verify /etc/systemd/system/skypane-*.service`.

**CP-7 Old layout removal (after a few days):** `sudo rm -rf /opt/skypane/{server,stub-server,companion,config}`.

**CP-8 Backup key (Mac → VPS):**
```bash
# Mac
ssh-keygen -t ed25519 -N '' -C skypane-backup-pull@mac -f ~/.ssh/skypane_backup_ed25519
# VPS (paste the .pub content)
sudo /opt/skypane/current/deploy/backup/install-backup-key.sh 'ssh-ed25519 AAAA… skypane-backup-pull@mac'
sudo systemctl start skypane-backup.service && ls -l /var/lib/skypane-backup/archives/
# Mac
ssh -i ~/.ssh/skypane_backup_ed25519 -o IdentitiesOnly=yes skypane-backup@<vps> list
ssh -i ~/.ssh/skypane_backup_ed25519 -o IdentitiesOnly=yes skypane-backup@<vps> 'cat /opt/skypane/skypane.env'   # expect refusal
ssh -i ~/.ssh/skypane_backup_ed25519 -o IdentitiesOnly=yes -t skypane-backup@<vps>                              # expect no shell
```
**CP-9 launchd on the Mac:**
```bash
deploy/backup/mac/install-launchagent.sh skypane-backup@<vps> ~/.ssh/skypane_backup_ed25519
launchctl kickstart -k gui/$(id -u)/com.skypane.backup-pull
tail -n 30 ~/Library/Logs/skypane-backup-pull.log
ls -l ~/Library/Application\ Support/SkyPane/backups/
```
Then check that the Health page shows the off-box backup line as fresh.

**CP-10 Restore rehearsal (Mac):**
```bash
SCRATCH=$(mktemp -d); tar -xzf ~/Library/Application\ Support/SkyPane/backups/<newest>.tar.gz -C "$SCRATCH"
python3 -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone())" "$SCRATCH/history.db"
SKYPANE_COMPANION_PASSWORD=rehearsal SKYPANE_COMPANION_INSECURE_COOKIES=1 server/.venv/bin/python3 companion/app.py --port 8650 --state-dir "$SCRATCH"
# open http://127.0.0.1:8650 - Flights/Health show production history; record the result in deploy/README.md
```
**CP-11 (Wave B, after Phase 36):** deploy, then `pgrep -af byos_server.py` (no `--secret`, has `--bind 127.0.0.1`), `sudo ss -ltnp | grep 8642` (`127.0.0.1:8642` only), `curl -s -o /dev/null -w '%{http_code}\n' https://<public-host>/device/v1/display` (401), and let the frame wake once to confirm it still fetches. Then record `systemd-analyze security skypane-byos.service`.

## Sources

### Primary (HIGH confidence)
- Repository files re-read for this research: `companion/auth.py`, `companion/app.py`, `companion/static/*.js`, `companion/pages/health_page.py`, `stub-server/byos_server.py`, `server/history_db.py`, `server/poll_loop.py`, `server/plane/*.py`, `deploy/*`, `.github/workflows/ci.yml`, `firmware/main/api_client.c`, `pyproject.toml`
- Local measurement: `systemd-analyze security --offline=true` (systemd 255.4) on the current and draft units; `--threshold` semantics
- [Caddy reverse_proxy docs](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy): X-Forwarded-* ignored from untrusted clients; Host passed through
- [Caddy header docs](https://caddyserver.com/docs/caddyfile/directives/header): HSTS syntax, defer
- [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html): StartCalendarInterval wake coalescing, RunAtLoad, StandardOutPath
- [GitHub runner image Ubuntu 24.04 readme](https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md): shellcheck 0.9.0, rsync 3.2.7, systemd 255.4, no caddy
- Python docs: `sqlite3.Connection.backup`

### Secondary (MEDIUM confidence)
- [Ubuntu discourse: sshd socket activation (22.10+)](https://discourse.ubuntu.com/t/sshd-now-uses-socket-based-activation-ubuntu-22-10-and-later/30189)
- [Debian bug #911321](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=911321): rrsync moved to `/usr/bin`
- sshd_config(5): first obtained value wins; Include

### Tertiary (LOW confidence)
- Items A1-A12 in the Assumptions Log

## Metadata

**Confidence breakdown:**
- Repo facts and code hooks: HIGH (file:line verified)
- Deploy/backup architecture: MEDIUM-HIGH (standard patterns; platform details partially assumed and gated by checkpoints)
- systemd directive compatibility with distro Python 3.14: MEDIUM (offline scores measured; runtime behaviour must be smoke-tested on the VPS)
- Mac/launchd specifics: MEDIUM

**Research date:** 2026-09-23
**Valid until:** 2026-10-23 (re-read `byos_server.py`, `ci.yml` and Phase 32 fixtures at execution: they will have changed)
