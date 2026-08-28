---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 12
status: gaps-addressed-awaiting-final-approval
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

Checkpoint presented; developer worked through all 11 items on phone and
laptop and reported specific findings for each (not a blanket approval).
Recorded verbatim by item below, per this task's own instruction that an
untried item is recorded as skipped, never as passed — every item below
was actually tried.

1. **Access gate.** Not commented on directly; implicitly fine (the
   developer reached and used every other page, which requires this gate
   to work).
2. **Config, theme.** OK, no issues.
3. **Config, runway.** OK, no issues with save/confirmation. Follow-up
   feature request: show the runway *number* more clearly, and an airport
   map alongside the picker to show which physical runway is selected —
   backlogged as **999.4**.
4. **Config, poll trigger.** **Real defect.** Clicking the button showed
   "can't save settings" and did not visibly trigger the frame. Root
   cause found and fixed live (see below): `--geofence` was never passed
   to the companion service, so every trigger raised `FileNotFoundError`
   under a misleading flash message. Also flagged: the cooldown/timing
   UX is unclear beyond the crash — backlogged as part of **999.6**.
5. **Health, device checkin.** OK the two freshness signals are shown
   separately as required, but raw-timestamp formatting isn't very
   readable — backlogged as part of **999.6**.
6. **Health, battery trend.** OK, present and shows a trend, but
   feature request: an interactive chart with an overall status
   indicator would be more useful than the current static sparkline —
   backlogged as **999.5**.
7. **Health, corroboration.** OK, functionally present, but unclear
   copy for a non-expert and not visually polished — backlogged as part
   of **999.3** (visual) and **999.6** (copy).
8. **Airlines.** OK, no issues with the read-only design or resolution
   percentage.
9. **History.** OK, no issues.
10. **Preview.** OK. Question asked and answered: the gallery keeps 25
    panels on disk (`GALLERY_MAX_ENTRIES`), displaying the newest 12
    (`GALLERY_DISPLAY_LIMIT`).
11. **Dark and light.** OK, both palettes readable, but the toggle
    control takes up too much visual space in its current placement —
    backlogged as part of **999.3**.
12. **Phone.** **Real defect.** "Navigation is not usable as-is" — the
    Airlines Unresolved table and the History table were cropped on
    phone. Root cause found and fixed live (see below): `data_table()`
    had no horizontal-scroll container.
13. **Overall.** "Globally very functional, well done" — but the
    interface reads as very plain/monotone and wants more personality;
    the desktop view is one long scrolling list that could be better
    laid out on wider screens. Mobile layout itself (navigation,
    responsiveness) was called "really perfect" aside from the two
    cropped tables above. Backlogged as **999.3**.

### Fixed live during this checkpoint (not just recorded — shipped and re-verified)

Both concrete defects (items 4 and 12) were root-caused, fixed, tested,
and deployed within this same session, then re-verified against the real
production service before reporting back:

- **Poll-trigger crash + misleading message**: `deploy/skypane-companion.service`
  now passes `--geofence /opt/skypane/config/runway3.json` (matching
  `skypane-poll.service`'s existing pattern); a genuine failure now
  redirects with a distinct `poll_failed` flash key instead of reusing
  `save_failed`'s "couldn't save settings" copy. Verified: a real
  `POST /poll-now` against the live service now returns
  `flash=poll_triggered`.
- **Mobile table cropping**: `layout.data_table()` (shared by History,
  Airlines, Health) now wraps its `<table>` in a horizontally-scrollable
  container, the same fix `.nav-bar` already used for the identical
  problem. Verified: the fix is present in the deployed `style.css`.
- Two new regression tests added (`companion/test_companion_app.py`,
  51/51). PR: #14 (same PR as Task 1's verification doc — CI green,
  merged).

### Not yet re-confirmed by the developer

All UX/design feedback not listed as a "real defect" above (runway map,
interactive battery chart, timestamp readability, dark/light toggle
placement, overall visual personality, desktop layout) is intentionally
**deferred, not fixed** — backlogged as phases **999.3** through **999.6**
for future planning, per the developer's own framing of these as "would
be nicer" rather than "broken." The two functional defects are fixed and
live. Phase closure is not yet declared — awaiting the developer's
explicit "approved" (or further findings) now that both real bugs are
resolved.
