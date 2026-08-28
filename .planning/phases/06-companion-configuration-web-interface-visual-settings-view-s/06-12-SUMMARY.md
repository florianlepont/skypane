---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 12
status: checkpoint-pending
---

## Task 1: Runway gate live-capture verification

Complete. See `adsb-test/RUNWAY-GATE-VERIFICATION.md` (PR #14). 90-minute
capture, 480 polls, 95 selections, zero exclusivity violations. Runway 3
confirmed, 06-24 still unvalidated (genuine null result), 02-20 partially
confirmed (real traffic selects correctly; full empty-band threshold
re-derivation needs rejected-candidate data this capture method doesn't
produce). No threshold values changed.

## Task 2: Caddy log field-path + network posture confirmation

Complete, with two real bugs found and fixed along the way (not just
verified):

1. **Assumption A3 confirmed as documented** — a real captured
   `caddy-access.log` line shows `request.headers.X-Battery-Mv` exactly
   as `server/history_db.py` reads it. No extraction-logic correction
   needed.
2. **Found live: the companion hostname never resolved.**
   `config-vps-1440bce3.vps.ovh.net` is a real OVH reverse-DNS name, not
   a nip.io wildcard — `deploy/Caddyfile`'s template assumed the latter.
   Fixed by using the IP-derived nip.io form
   (`config-92-222-92-167.nip.io`) for the companion site only, leaving
   the already-working device-protocol site's real-domain hostname
   untouched.
3. **Found live: `ingest_caddy_battery_log()` was never called by
   anything in production**, despite being built and unit-tested in plan
   06-01. The durable log accumulated real telemetry with no reader.
   Fixed in PR #13: new `server/poll_loop.py --caddy-log` flag, wired
   into every cycle, plus the file-permission chain between the `caddy`
   and `skypane` system users (`mode 660` + setgid + group membership,
   documented in `deploy/README.md`'s Assumption A3 section).

Verified live, all passing:
- Companion hostname answers over TLS; an unauthenticated request to
  `/config` redirects to `/login` (HTTP 303), not page content.
- The companion port (8643) refuses a direct connection from outside the
  VPS.
- The device-protocol hostname still rejects an unauthenticated request
  (HTTP 401) and `skypane-poll.timer` is active with recent cycles in the
  journal — no regression from the access-log directive change.
- Real `device_health` rows are landing in the deployed database with
  plausible millivolt values (confirmed multiple non-null readings,
  e.g. 4010mV, 4078mV, 4090mV).

PRs: #12 (phase 6), #13 (battery-ingestion wiring fix), #14 (Task 1
verification doc) — all merged except #14, which is open pending merge.

## Task 3: Developer sign-off

**Pending.** Checkpoint presented to the developer; awaiting response.

The companion service is confirmed running and reachable at
**`https://config-92-222-92-167.nip.io`**, with real content on every
page: recent flight activity (runway 3 actively tracking, e.g. a Wizz Air
A321neo arrival), real battery-voltage history, and a populated render
gallery (5+ recent panel images from the last 15 minutes). Nothing is
empty by omission — any page that looks sparse reflects genuinely limited
history since this is the service's first live deployment, not a bug.
