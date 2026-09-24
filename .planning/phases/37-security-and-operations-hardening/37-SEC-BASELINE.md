# Phase 37 — security baseline and before/after record

Single record for every before/after value the Phase 37 checkpoints produce
(ROADMAP SC-5, D-17). No secret value is ever written here.

Code state measured: branch `claude/plan-phase-37` at `b8d74fd` (plans 37-01..37-07 executed).
Pre-phase units: `deploy/skypane-*.service` at `9d38c21` (main before Phase 37).

## Offline scores (CI tool, systemd 255)

`systemd-analyze security --offline=true <unit>` (systemd 255.4), lower is better.

| Unit | Before | After |
|------|--------|-------|
| skypane-byos.service | 8.3 EXPOSED | 1.5 OK |
| skypane-companion.service | 8.3 EXPOSED | 1.5 OK |
| skypane-poll.service | 8.3 EXPOSED | 1.5 OK |
| skypane-backup.service | — (new) | 0.8 SAFE |

## Online scores on the VPS

`sudo systemd-analyze security <unit>` on production.

| Unit | Before (CP-1) | After (CP-6) |
|------|---------------|--------------|
| skypane-byos.service | | |
| skypane-companion.service | | |
| skypane-poll.service | | |
| skypane-backup.service | — (new) | |

## Live Caddyfile diff (CP-1)

_Pending CP-1._

## sshd -T before/after

| Directive | Before (CP-1) | After (CP-3) |
|-----------|---------------|--------------|
| permitrootlogin | | |
| passwordauthentication | | |
| kbdinteractiveauthentication | | |
| pubkeyauthentication | | |
| maxauthtries | | |

## skypane.env ownership before/after

| Path | Before (CP-1) | After (CP-3) |
|------|---------------|--------------|
| /opt/skypane | | |
| /opt/skypane/skypane.env | | |
| /opt/skypane/venv | | |

## GitHub deploy target (CP-2)

_Pending CP-2._

## Services under sandbox (CP-4)

_Pending CP-4 (Plan 37-09)._

## Deliberate failed deploy (CP-5)

_Pending CP-5 (Plan 37-09)._

## Wave B (CP-11)

_Pending CP-11 (Plan 37-11, after Phase 36)._
