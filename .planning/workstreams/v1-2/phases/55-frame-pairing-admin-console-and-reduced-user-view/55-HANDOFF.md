# Phase 55 handoff

Phase 55 delivers frame pairing, the administrator console and the reduced user
view. It is complete in code on branch `milestone/v1.2-phase-55-pairing-admin`.
No production deploy happened: nothing in this phase was deployed, no real
Auth0 tenant was used and no real pairing code or secret is in the repository.
This document records what the phase unblocks, the go-live checklist, the facts
the owner needs and what stays open.

Related: [`deploy/README.md`](../../../../../deploy/README.md) sections
"Pairing, retiring and re-activating a frame" and "Schema v3 and rollback",
[`55-PLAN-COVERAGE.md`](55-PLAN-COVERAGE.md), [`55-UI-SPEC.md`](55-UI-SPEC.md),
the Phase 54 handoff.

## A. What this phase delivered

The three roadmap success criteria, each with the test that proves it.

1. **An administrator pairs a frame to a user with a short, single-use,
   expiring, audited code.** A registered but unowned frame shows an 8-character
   code on its panel; the administrator types it on the Fleet page and picks the
   owner. Proof: `server/test_fleet_ops.py` (atomic claim, two-thread race,
   identical refusals), `stub-server/test_pending_pairing.py` (the byos pending
   path through a real subprocess, code rotation, claim hand-over, isolation from
   the live frame), `companion/test_console_pairing.py` (throttle, audit without
   the guess), `companion/test_browser_console.py::test_pairing_flow_in_the_browser`
   (a real browser, code issued by the real byos function, wrong codes show one
   identical error).
2. **The administrator console shows every frame with owner, hardware, last
   seen, battery and firmware, and manages users, reassignment, retirement and
   releases.** Pages: Fleet, Users, Locations, Audit log, Releases, all under an
   "Administration" group. Proof: `companion/test_console_fleet_page.py`,
   `test_console_lifecycle.py`, `test_console_users.py`,
   `test_console_audit_page.py`, `test_console_locations.py` and the browser
   suites `test_browser_fleet_page.py`, `test_browser_audit_page.py`,
   `test_browser_console.py` (360 px layout, 44 px targets, scripts blocked, both
   themes, French).
3. **A user sees only their own frames, with fewer options and no fleet or
   release controls.** Proof: `companion/test_user_view_http.py` (real handlers:
   own frame 200, another user's frame byte-identical to the unknown-path 404,
   crafted settings POST cannot change the admin-only keys),
   `companion/test_access_matrix.py` (every route for every role, both URL
   forms), `companion/test_browser_console.py::test_user_sees_no_administrator_entry`
   and `::test_admin_urls_are_the_unknown_path_page_for_a_user` (real DOM, tab bar
   is Home, Flights, Display, Health, Account).

Also delivered: schema 3 of `fleet.db` (pending frames, append-only audit log,
`locations.owner_user_id`); CSRF tokens on every new admin and pairing POST,
on `/update*` and on the four existing destructive POSTs; the Phase 54 section A
items (real owner-scoped device routes, matrix rows per route, Account frames
list, CSRF revisited).

Closed during the last plan: the Users page card pushed its status pill 8 px past
the edge at 360 px; fixed with one tokens-only rule in
`companion/static/style.css`.

## B. What this phase unblocks

- **Phase 60 (co-management).** Extend `access.authorized_device_id`. It still
  takes the owner as input and is unchanged by this phase (`companion/access.py`
  has no diff). Add the co-manager rows to the access matrix
  (`test-support/matrix_rows_*.py`, `UNPREFIXED_OUTCOMES`), the audit events
  (`audit.py` and the action label table in `console_lifecycle.py`), and the
  console actions for adding a co-manager. The ownership gate in
  `companion/app.py::_effective_access` and the per-user frame list in
  `device_scope.load_devices_for` are the two places that read ownership.
- **Phase 57 (combined OTA), still gated on Phase 47.** The current firmware
  needs no change for pairing or retirement: it reads `image_url`, `image_hash`
  and `sleep_s` and ignores the rest. Retired frames keep a valid token. What
  remains for Phase 57: recovery of a frame after a 401, and any on-device
  pairing UI.
- **Phases 52, 53, 56 notes.** Migration index 3 is Phase 55's; later phases
  append v4 and up. `locations.owner_user_id` exists and the Locations page
  writes it; Phase 53 owns outbound sharing rules and any coarser rounding.
  Hot files edited here in bounded ways: `companion/app.py`, `companion/routes.py`,
  `companion/page_context.py`, `companion/pages/config_page.py` (an optional
  `handler` argument), `stub-server/byos_server.py` (pending path only). The poll
  files and `_handle_poll_now` were not edited. The fleet poll (Phase 52) is what
  writes a claimed non-live frame's image.

## C. Owner go-live checklist

Nothing below has been done.

1. Deploy dry-run: confirm `activate.sh` prints `upgrade fleet.db schema 2 -> 3`
   and that Health shows no fleet fault once the new release is live.
2. Restore a backup of a schema 3 `fleet.db` into a scratch directory and open
   it with this release (see "Restore" in `deploy/README.md`).
3. Real-panel check of the pairing screen: legibility of the code from
   normal viewing distance, and the red header band (see D.9).
4. Dry run on a spare frame: register, pair, retire, re-activate, pair again
   (commands below).
5. Confirm the schema 3 rollback behaviour on paper (D.2) and decide whether a
   rollback window is acceptable before the first real claim.
6. Keep Auth0 sign-ups disabled in the tenant (D.8).

Commands, from `deploy/README.md` (`FLEET` is the shell variable defined there):

```bash
FLEET="sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/fleet_cli.py --state-dir /opt/skypane/state"

# 1. provision over USB; prints the MAC and the SHA-256 of the secret
firmware/provision.sh <serial-port>

# 2. register as pending (or use Fleet -> "Register a frame" in the console)
ssh <ssh-target> "$FLEET devices register-pending --mac <mac> --secret-sha256 <hash>"
ssh <ssh-target> "$FLEET devices pending-list"

# 3. power the frame, read the code on its panel (up to 5 minutes), then pair it
#    in the console: Fleet -> "Pair a frame"

# 4. retire, then re-activate (re-activation wipes and shows a new code)
ssh <ssh-target> "$FLEET devices retire --id <d_xxxxxxxx>"
ssh <ssh-target> "$FLEET devices reactivate --id <p_xxxxxxxx>"

# 5. hard deletion of a pending or retired frame (CLI only)
ssh <ssh-target> "$FLEET devices remove --mac <mac>"

# pre-deploy dry-run of the migration, as activate.sh does
python3 -m server.fleet_migrate --state-dir /opt/skypane/state --dry-run
```

## D. Facts surfaced to the owner

1. **Redraw cost of an unclaimed frame.** It wakes every 5 minutes but redraws
   only when the image hash changes, which is when the code rotates: a code is
   valid for 30 minutes and rotates at the next wake after that, about every 35
   minutes, roughly 40 redraws a day (hash-skip).
2. **Schema 3 rollback caveat.** The previous release's byos refuses a schema it
   does not know (`FleetDbTooNew`) and falls back to the legacy files; Health
   shows a fleet fault. The migration is expand-only, so data is intact. Frames
   claimed after the upgrade have no legacy token and fail 401 then 403 with up
   to 6 h backoff on rollback. Frames enrolled before the upgrade keep working.
3. **`devices assign` now wipes.** The CLI goes through the same operation as the
   console reassign: assigning a non-live frame wipes the previous owner's data
   and re-provisions it; the live frame only changes owner. Update any runbook.
4. **In-memory throttles.** The pairing-claim throttle, the location mutation
   throttle and the one-shot flash messages are per process and reset when the
   companion restarts.
5. **byos imports Pillow.** byos now imports `server.pairing_image` (Pillow) and
   `server.fleet_ops`. Pillow is in the shared venv (`server/requirements.txt`);
   a byos run without it fails at import.
6. **A claimed non-live frame stays blank.** After a claim the frame stays white
   or on its last image until a poll writes its image. The fleet poll is
   Phase 52; users have no poll-now.
7. **French term for Fleet is "Cadres"** (existing vocabulary; neither "Parc" nor
   "Flotte"). The French labels are "Cadres", "Utilisateurs", "Lieux" and
   "Journal d'audit".
8. **The invite sends no email.** It only pre-registers the address. Auth0
   sign-ups must stay disabled, otherwise an uninvited person could create an
   Auth0 account (the invite-only check at sign-in remains the only other gate).
9. **Pairing screen red header band.** The code is the single largest element and
   the red band (160, 32, 32) is the only colour on the screen. It is an owner
   visual item to confirm on the real panel.
10. **Code strength.** Alphabet of 30 symbols, 8 characters (about 39 bits), salted
    hash stored, constant-time compare, 30 minute validity, single use, throttled
    per session and globally, failures audited without the guess.
11. **Users page "Signed in".** It shows the newest live session time. Sessions are
    deleted on disable and unlink, so such a user reads "Never signed in".
12. **Locations.** Stored rounded to 4 decimals (about 11 m); quota of 10 per user
    (`USER_LOCATION_LIMIT`); France-only bounds are not enforced; Phase 53 owns
    outbound rules.
13. **CSRF scope** as decided: all new admin and pairing POSTs, `/update*` and
    four existing destructive POSTs. Not every legacy POST.
14. **No firmware need** was found for pairing or retirement.
15. **Calendar link on the combined settings form** is now validated like the
    dedicated connect route (closed in plan 08). The field error text reuses a
    slightly inaccurate string ("too long, or conflicts with the disconnect
    option"); a dedicated string is a small follow-up.
16. **Flaky test, not from this phase.** `stub-server/test_ota_offer.py` showed
    a port race once in CI. It is a test-harness port pick, unrelated to pairing.
17. **Branch state.** `origin/main` has moved on (Phase 56 and Phase 49 docs
    merged) since this branch was cut; the branch was merged with main (68796be6) onto it.

UI-SPEC open questions and the defaults taken:

| # | Question | Default taken |
|---|----------|---------------|
| 1 | Admin tab on the phone bar | An "Admin" tab to Fleet was added; Airlines moved into the More sheet |
| 2 | Invite email | None sent; helper text says so; owner to decide on messages later |
| 3 | French term for Fleet | "Cadres" |
| 4 | User tab bar | Home, Flights, Display, Health, Account; Airlines and Calendar reachable from Display and the sidebar |
| 5 | Pairing screen hierarchy | 168 px code as the largest element; red header band kept; owner to confirm on the panel |
| 6 | Location quota and range | 10 per user; latitude and longitude validated as numbers in range, 4 decimals stored |

## D2. Code review follow-up (after the phase verification)

The deep code review (`55-REVIEW.md`) found one critical and four warnings. The fixes are in `55-REVIEW-FIX.md`: crash-safe wipe order for reassign and re-activate (rename aside, commit, delete), consistent location save, state-path and device-id guards, `\Z` id matching, bidirectional characters stripped from location names, and a viewer-scoped location usage count. Left as they are, for the owner to decide:

- **Reassigning the live frame keeps the previous owner's data** (calendar secret, name, history), by design (owner decision D-13, which protects the Phase 47 measurements). If the live frame is ever handed to a different person, clear its calendar link by hand first.
- **CSRF scope** is the six routes you chose plus the new console routes. Other forms rely on the session cookie's SameSite setting and the Origin check, which accepts a request with no Origin header (pre-existing).
- **The CLI `devices assign` and `devices reactivate` wipe a frame directory without the busy guard** the console uses. Stop `skypane-byos` and the poll timer first, as the existing restart caution says.
- Remaining info items (pairing throttle is in memory and not atomic between check and record, Fleet page hides a device whose stored state path is invalid, `COMMIT` failure not rolled back by `fleet_db.transaction`, CLI `devices remove` leaves the directory) are low risk and recorded in `55-REVIEW.md`.

## E. What stays with the owner or later phases

- The production deploy of this phase and every item in section C.
- Firmware recovery after a 401 and any on-device pairing UI (Phase 57).
- Co-management of a frame (Phase 60) and view-as-user (AUTH-07).
- Audit log export or purge (the page is read-only; the table is append-only).
- Invitation emails.
- Zone and detection rules for locations, and outbound sharing rules (Phase 52
  and Phase 53).
- The Phase 47 gate on the combined OTA (Phase 57).
