# Doc-drift evidence log: deploy/ and CI documentation surface

Scope: DOC-01 part 1 (41-01) — `deploy/README.md`, `deploy/skypane.env.example`,
`deploy/Caddyfile`, every `deploy/*.sh` and systemd unit/timer comment, and the
header comments of `.github/workflows/ci.yml` and `firmware.yml`. Every claim
below was re-checked against the code as it stands on top of base commit
`7bd8664`, not against the 2026-09-23 audit ledger's original snapshot.
Date: 2026-09-28.

Verdict vocabulary: `accurate` (claim matches current code, no edit needed),
`corrected` (claim was wrong, edited in place), `removed` (claim deleted rather
than restated), `handed to 41-02` (drift found in a file owned by part 2 of
DOC-01 — logged here, left untouched).

## Task 1 — deploy config, unit, script and workflow comments

| # | Doc location (before) | Claim | Checked against | Verdict | Change |
|---|---|---|---|---|---|
| 1 | `deploy/skypane.env.example:3` | "Copy this file to `deploy/skypane.env` ON THE VPS ONLY" | `deploy/provision.sh:162-164` (`install -m 600 -o root -g root deploy/skypane.env.example ${APP_ROOT}/skypane.env`, `APP_ROOT=/opt/skypane`) and `deploy/skypane-byos.service:15` `EnvironmentFile=/opt/skypane/skypane.env` | corrected | Install path corrected to `/opt/skypane/skypane.env` |
| 2 | `deploy/skypane.env.example:56` | "byos_server.py itself persists nothing" | `stub-server/byos_server.py:557-565` `save_battery_state()` writes `battery_state.json`; also writes `byos_state.json` (tokens, lines 194-195), `devices.json` (registry, lines 243-250) and content-addressed `img/<sha256>.bin` (lines 484-502) | corrected | Replaced with "byos_server.py persists only the latest battery reading (battery_state.json), so this access log is the only durable per-request history" |
| 3 | `deploy/Caddyfile:20-21` | "byos_server.py prints it but persists nothing, so this file is the only durable record" | Same evidence as row 2 | corrected | Replaced with "byos_server.py persists only the latest reading (battery_state.json), so this file is the only durable per-request record" |
| 4 | `deploy/provision.sh:85-86` | "caddy ... writes it via Caddyfile's `mode 640`" | `deploy/Caddyfile:33` `mode 660` | corrected | `mode 640` -> `mode 660` |
| 5 | `.github/workflows/ci.yml:1-7` (header) | "`test`: lint + full pytest suite (coverage gate) + attribution check" | `.github/workflows/ci.yml:95-131` — steps also run the comment history guard (`check_comment_history.py check`, line 98), `mypy` (line 101), the function size gate (`check_function_size.py`, line 104), `shellcheck` (line 109) and `systemd-analyze security --offline` unit scoring (lines 111-120) | corrected | Header rewritten to list all `test` job checks: ruff lint, comment-history guard, mypy, function-size gate, shellcheck, offline systemd-unit security scoring, full pytest suite (coverage gate), attribution check |
| 6 | `.github/workflows/ci.yml` (ledger's "18 harnesses" wording) | Whether the obsolete "18 harnesses" phrase is still present | `` `grep -n "harness" .github/workflows/ci.yml` `` — no output | accurate | None — the phrase is already gone; the header (row 5) described the checks by name, not by harness count, so no restatement is needed |
| 7 | `deploy/skypane-byos.service:1-7` | "byos listens on 127.0.0.1 only, the IP filter below drops anything non-loopback, and provision.sh's ufw denies the port from outside" | `deploy/skypane-byos.service:19` `--bind 127.0.0.1`; `:48-52` `RestrictAddressFamilies`/`IPAddressDeny=any`/`IPAddressAllow=localhost`; `deploy/provision.sh:152` `ufw deny 8642/tcp` | accurate | None |
| 8 | `deploy/skypane-companion.service:1-11` | "This process also binds 127.0.0.1 itself (--bind), so loopback is enforced twice over" | `deploy/skypane-companion.service:27` `--bind 127.0.0.1`; `deploy/provision.sh:155` `ufw deny 8643/tcp` | accurate | None |
| 9 | `deploy/skypane.env.example:24-27` | "Directory holding panel.bin / poll_state.json / enrichment cache. skypane-poll.service and skypane-byos.service must agree on this path" | `deploy/skypane-poll.service:31` `--state-dir ${SKYPANE_STATE_DIR}`; `deploy/skypane-byos.service:22` `--state-dir ${SKYPANE_STATE_DIR}` | accurate | None |
| 10 | `deploy/provision.sh:162-164` (echo reminder) | "install -m 600 -o root -g root deploy/skypane.env.example ${APP_ROOT}/skypane.env" | `` `sed -n '18,20p' deploy/provision.sh` `` shows `APP_ROOT="/opt/skypane"` | accurate | None — this line is itself the evidence used to correct row 1 |
| 11 | `deploy/skypane-backup.service:1-6`, `deploy/skypane-backup.timer:1-13` | "Triggered by skypane-backup.timer at 03:15 UTC. Snapshots history.db (sqlite3 .backup) plus other irreplaceable state files into a dated tar.gz + .sha256. Never leaves the VPS" | `deploy/skypane-backup.timer:10` `OnCalendar=*-*-* 03:15:00 UTC`; `deploy/backup/skypane_backup.py:106-122` `snapshot_db()` uses `sqlite3`'s `backup()` API; `:125-137` `_write_checksum()` writes a `.sha256`; `:180-181` archive name is `skypane-state-<ts>.tar.gz` | accurate | None |
| 12 | `.github/workflows/firmware.yml:1-8` (header) | "Two independent jobs ... `build` runs firmware/build.sh directly ... plus the production-config and Log Line Contract checks" | `.github/workflows/firmware.yml:53-69` — `check_production_config.sh static`, `check_log_contract.sh`, `./firmware/build.sh`, then `check_production_config.sh built` | accurate | None |
| 13 | `deploy/deploy.sh:10-16` | "`git archive` streams exactly the committed tree at HEAD — no local edits, untracked files, state/, venv/ or skypane.env ever leave this machine" | `deploy/deploy.sh:39-45` `git archive --format=tar "${SHA}" -- server stub-server companion deploy adsb-test/runway3.json ':(exclude)server/state/**'` | accurate | None |
| 14 | `deploy/activate.sh:10-19` (header flow) | Stage -> install deps if hash changed -> byte-compile -> smoke-test -> render+validate Caddy -> install units + atomic swap -> restart/reload -> probe -> rollback on failure | `deploy/activate.sh:134-385` implements each step in that order (requirements hash check at :149-160, smoke test at :165-172, Caddy render/validate at :194-216, atomic swap at :240-242, probe loop at :298-311, rollback at :313-352) | accurate | None |
| 15 | `deploy/harden_sshd.sh:1-21` | Writes a validated SSH hardening drop-in (PermitRootLogin no) before any reload, restoring the previous config on a validation failure | `deploy/harden_sshd.sh:53-61` (`PermitRootLogin no` in the written drop-in), `:65-76` (`sshd -t` validated before `try-reload-or-restart`, previous drop-in restored on failure) | accurate | None |
| 16 | `deploy/render_caddyfile.sh:1-9` | Output is only the two rendered site blocks, not a whole Caddyfile, no global options block | `deploy/render_caddyfile.sh:43-45` `sed` substitutes exactly the two anchored site-block header lines from the template | accurate | None |
| 17 | `.claude/CLAUDE.md` hosting row | "OVH VPS-1, Ubuntu, Caddy for TLS, three systemd units" | `` `ls deploy/*.service deploy/*.timer` `` lists six unit files: `skypane-byos.service`, `skypane-companion.service`, `skypane-poll.service`, `skypane-poll.timer`, `skypane-backup.service`, `skypane-backup.timer` | handed to 41-02 | None — `.claude/CLAUDE.md` is owned by 41-02; left untouched here |

## Task 2 — deploy/README.md, section by section

(continues numbering from Task 1)
