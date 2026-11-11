# Photo mode: mode-switch workflow (companion Home)

Status: proposal for the owner, 2026-11-11. Based on a read of the real code on
branch `sketch/photo-companion`; no production code was changed. It refines
`photo-mode-concept.md` and `photo-companion-navigation.md`, and replaces one
decision of the latter: plane pages are **no longer hidden** in photo mode.
They stay in the menu and show a banner.

## Goal

The owner (or a co-manager) switches a frame between **Planes** and **Photos**
from the Home page, in one tap, and always knows what the frame shows now and
when a change will reach it. The menu never changes shape with the mode. The
frame stays dumb (wake, poll, show, sleep). Photos are kept when the frame
returns to planes. The admin never sees user photos and never switches a
user's frame.

## Decisions kept (not reopened)

One mode per frame. A change takes effect at the frame's next wake. No
automatic switch. Photos kept on return to planes. The admin never sees user
photos. Wake interval following the rotation is a later phase (68), gated on
the battery work.

## Proposed workflow

States: **planes**, **pending-to-photos**, **photos**, **pending-to-planes**.
"Saved mode" is the config value; "shown mode" is the mode of the image the
frame last received.

1. Planes (saved = shown = planes). The owner sees Home as today plus a block
   "This frame shows: **Planes** | Photos", Planes selected, no pending line.
2. The owner taps **Photos**. One POST sets the saved mode to photos (explicit
   value, not a toggle). Home reloads with Photos selected and a pending line
   "Switching to photos. Applies at the next wake, around 14:32."
   (pending-to-photos).
3. Within 30 s the poll cycle renders the photo (or the waiting screen) into
   `panel.bin`. At its next wake the frame gets the new hash and redraws.
4. First check-in after that render: shown = saved = photos. The pending line
   disappears on the next Home refresh. Photos state.
5. Photos state. Home shows the current photo in the hero (managers only) and
   the block with Photos selected. Plane pages show the banner "This frame is
   showing photos. Plane pages stay available but do not change the frame."
   with a link to Home.
6. Back: the owner taps **Planes** (Home block or the banner link). Same as
   step 2 mirrored (pending-to-planes), "Switching to planes. Applies at the
   next wake, around HH:MM." Photos stay stored.

| State | Home | Plane pages (Flights, Location, Style, Airlines) | Photos page |
|---|---|---|---|
| planes | Block: Planes selected. Hero = latest plane screen. | Normal, no banner. | Reachable; empty or kept photos; "Switch this frame to photo mode" action. |
| pending-to-photos | Block: Photos selected. Info line with next-wake time. Hero still the plane screen. | Banner already shown (saved mode is photos). | Full page (upload, list, rotation). |
| photos | Block: Photos selected. Hero = current photo or waiting screen. | Banner. | Full page. |
| pending-to-planes | Block: Planes selected. Info line with next-wake time. Hero still the photo. | No banner (saved mode is planes). | Reachable, as in planes. |

Rule: banner and block follow the **saved** mode at once (the owner has decided);
only the pending line and the hero follow the **shown** mode.

Admin on a user's frame: sees the same Home read-only (mode line as plain text,
no switch, no photo in the hero, a neutral placeholder), plane pages with a
neutral banner, and no Photos entry (it would answer 404).

## Findings by question

### 1. Home today and the next-wake figure

Home (`home_page.render`, `companion/pages/home_page.py:729`) shows: a hero with
the newest gallery image, frame name, status pill and the "Next refresh in N
min" row; the Frame group (Screen and Quiet hours switches, Battery row); the
recent flights; the quiet-hours dialog. The page already holds
`ctx.last_checkin_ts` (`page_context.py:262,401`), battery percent and the
battery-empty latch, the device config and `wake.next_wake_status(...)`
(`home_page.py:343-366`).

"Next wake at about HH:MM" is derivable with no new data: `wake.next_wake_status`
(`server/wake.py:147`) gives last check-in plus the effective interval, with the
quiet-hours extension. The wording exists: "Applies at the next wake, around
%s." and the quiet-hours variant (`companion/frame_state.py:47-53`, chosen by
`delay_sentence_template` at `:132`, already used by `flash.py:533` and
`ui_components.py:569-588`). It is an estimate (the check-in is stamped at the
start of the wake; the panel draw takes about 20-25 s). Until Phase 68 it is
also honest for photo frames, which keep the plane cadence.

A pending change cannot be derived from the config alone: it needs a stamp.
Proposal: the poll cycle writes `rendered_mode` and `rendered_at` into
`poll_state.json` when it first renders a mode. Pending = saved mode differs
from `rendered_mode`, or `last_checkin_ts` is older than `rendered_at`. This
also covers a switch during a wake (see edge cases). Home refreshes on its own
because `device_config.json` and `panel.bin` are in the freshness token
(`freshness.py:79`). The new block must be added to Home's swap selectors
(`ui_nav.py` `REFRESH_SWAP_SELECTORS_BY_PAGE`, mirrored in `static/freshness.js`).

### 2. Health and alerts

| Signal | Where | Uses the wake interval how | Today | Photo frame, later phase |
|---|---|---|---|---|
| Overdue (amber) | `frame_state.resolve_state` `:93` | late at next wake + 2 x effective interval, no floor | fine at plane cadence | would show "Overdue" and the Home notice after 2 intervals if the effective interval stays 30 s while the frame sleeps hours |
| Long overdue | `frame_state.py:101` | 3 x interval | same | same |
| "No contact" (red) | `device_scope.device_status` `:287-300` | 2 x **config** `wake_interval_s`, default 3600 (not the effective interval) | fine | a 6 h/12 h/daily frame would sit in "No contact" permanently |
| Health connection row | `health_signals.py:590`, thresholds `wake.py:29-36` (3x warn, 12x error, floors 300/1200 s) | effective interval | fine | wrong unless the effective interval is mode-aware |
| Flight-data (pipeline) | `health_signals.py:31` warn 180 s | last pipeline run stamp | **bites if photo frames are skipped by the cycle without a heartbeat** (the hold branch writes one for this reason, `poll_cycle.py:808`) | same |
| Charging and autonomy | `health_signals.py:294`, home battery row | interval | fine | must use the mode-aware interval |

What must change in Phase 68: one mode-aware `effective_wake_interval_s`
(`wake.py:58`), and `device_status` must call it instead of reading the config
key. Also the hard ceiling: `WAKE_INTERVAL_MAX_S = 3600`
(`device_policy.py:198`) is enforced by `device_config.py:394` and silently
ignored by the BYOS (`byos_server.py:542` falls back to the default), while the
firmware accepts up to 86400 (`firmware/main/validate.h:17`). A daily rotation
needs a separate photo-mode source, not the `wake_interval_s` key. Battery-empty
pins sleep to a flat 3600 s (`device_policy.py:206`, `byos_server.py:630`), which
would shorten a daily wake: decide whether that is acceptable.

Does anything bite today? Not on staleness: with a plane cadence (30 s env
default, config 60-3600 s) the thresholds hold. Only the "skipped without
heartbeat" case in the pipeline row is a real trap for Phase 66. The user's
Home attention row ignores the pipeline state (`home_page.py:664-669`); only
the admin Health and Fleet would warn.

### 3. Poll loop and request budget

The timer runs every 30 s (`deploy/skypane-poll.timer`). `run_fleet`
(`server/fleet_cycle.py:475`) groups non-held devices by exact zone
(`plan_zones` `:284`), fetches each zone once, two providers per zone
(`detect.py:102`, adsb.fi and adsb.lol), with 1.1 s spacing across all
requests (`request_budget.py` `MIN_SPACING_S`) and no new zone after 25 s
(`fleet_cycle.py:46`, about a dozen zones). Held devices (battery-empty,
display-off, quiet hours via `peek_hold`, `poll_cycle.py:719`) join no zone and
cost no request (`:289-292`).

Today a photo-mode frame would still be fetched and, worse, `run_once` would
render a plane canvas over `panel.bin`. A mode branch is needed whatever is
chosen. Marginal cost of fetching for a photo frame: zero if a plane frame
shares its exact zone, else 2 requests per cycle (about 2.2 s of the 25 s
window).

| Option | What | Cost | Risk |
|---|---|---|---|
| A. Photo as a hold kind (recommended) | Lowest-priority kind after `decide_hold` (`poll_cycle.py:704`), seen by `peek_hold`, so `plan_zones` treats the frame as held (no fetch). `run_once` then calls a photo branch: render rotation, write `panel.bin`, record the heartbeat. | 0 requests | Small; plane path and golden fixtures untouched if the branch sits after the existing holds. |
| B. Branch in `run_once` only | Fetch still happens for the zone, photo branch ignores it. | 2 req/cycle if alone in zone | Wasteful, but simplest. |
| C. Filter in `runnable_devices` (`:222`) | Photo frames not run at all. | 0 | Rejected: no heartbeat, no rotation advance, false pipeline warnings. |

### 4. Permissions

| Kind (`companion/route_types.py`) | Passes | Used for |
|---|---|---|
| `OWNER_DEVICE` `:33` | owner, co-manager, **admin** (`access.py:64`) | every per-device setting today: settings, detection, quick switches, quiet hours, rules, calendar (`routes.py:236-300`), gallery and previews (`:213-226`) |
| `OWNER_ONLY_DEVICE` `:40` | owner, admin | co-manager add/remove, remove frame (`routes.py` end of POST table) |
| `ADMIN_DEVICE` `:38` | admin | airline editor |

There is **no `MANAGER_DEVICE` kind yet**. The mode switch, the Photos page and
every photo route need a new one: owner and co-manager only, with the admin
shortcut in `authorized_device_id` (`access.py:64`) skipped (an admin who owns
or co-manages a frame still passes as such). Touches `access.py`,
`route_types.py`, the hand-written table in `test_access_matrix.py`, and
Phase 65's PRIV-01. Admin on a foreign frame is already detectable
(`device_scope.foreign_frame_owner_email`, `:352`; the "Viewing owner" strip
`ui_shell.py:452`).

Two privacy traps: (a) `publish_canvas` archives every new panel into the
gallery (`poll_cycle.py:739-755`) and the gallery route is `OWNER_DEVICE`, so
the admin could open it: photo renders must call `write_panel_atomic` only and
never the gallery; (b) Home's hero reads the newest gallery file
(`home_page.py:217-246`), so in photo mode it needs a manager-only source.

### 5. Storage and delivery

Per-device settings live in `device_config.json` in the device's state
directory (`server/device_config.py:279` load, `:458` save, `:409` merge), not
in `fleet.db` (`devices` table, `fleet_db.py:138-148`, has no settings). A
`display_mode` key needs: a normaliser, a key in `load_device_config`, a
parameter in `_merged_config`/`save_device_config` and validation. Write it
only when not "planes" (as `timezone`, `detection`, `layout` do) so plane
frames keep their file bytes. No `fleet.db` migration is needed for the mode.

Delivery: the companion writes the config; the poll cycle reads it every 30 s
and writes `panel.bin` only if the bytes changed (`poll_cycle.py:274`); the
BYOS hashes `panel.bin` at the wake and answers `image_url`, `image_hash`,
`sleep_s` (`byos_server.py:1628-1710`); the firmware skips the redraw when the
hash is unchanged (`state_machine.c:282`, `app_main.c:410`). The BYOS has no
Pillow, so all photo rendering belongs to the poll cycle (or the save). A photo
held between rotations and the waiting screen are therefore byte-stable, hence
no redraw; keep clocks and counters off the waiting screen.

Which one wins (image): battery-empty > display-off > quiet hours
(`decide_hold`, `poll_cycle.py:704-716`), all above photo mode. Battery-empty
always paints its own screen; display-off blanks the panel. Quiet hours is open
(question 1). Sleep composition in the BYOS is wake base, then display-off
300 s, then battery pin 3600 s, then quiet-hours extension
(`byos_server.py:1693-1701`); Phase 68 only replaces the base.

### 6. Navigation

The personal menu is one table: `NAV_GROUPS` (`ui_base.py:122`, `NAV_TABS`
`:141`), sidebar pages `ui_nav.py:63`, phone bar pages `:65` (first four:
Home, History, Location, Style), More sheet gets Airlines and Account
(`_personal_bar`, `:585`). Adding one Photos entry: route constant, label
Message plus French (`i18n_fr/nav.py`), icon id in `NAV_ICON_IDS` (`:1022`)
and the sprite, an entry in `NAV_GROUPS` and the sidebar tuple, a place in the
bar or More. `NAV_TABS` also feeds the page titles (`app.py:259`), the
device-prefix whitelist (`device_dispatch.py`) and `next_route` (`app.py:341`),
so those follow automatically. Recommended position: last, so it sits in More
on a phone and the four-cell bar keeps its alignment (several browser tests
pin it). Stable menu = no filtering by mode. One filter remains: show Photos
only to managers; `_user_can_open` (`ui_nav.py:268`) checks the role only, so
an admin on a foreign frame would get a link to a 404 unless the nav also
checks manager status.

Banner: no page passes `banner=` today, but the hook exists.
`_page_shell_for` (`app.py:927`) is the single assembly point and
`page_shell(banner=...)` renders it above the body (`ui_shell.py:341,483,528`).
The shared component is a docked info toast (`ui_components.toast_html`
`:205`, `docked=True`; `anomaly_banner` `:265` is the warning variant), and
`frame_notice_html` (`ui_shell.py:452`) is the precedent for a shell-level
strip. One edit in `_page_shell_for` covers Flights, Location, Style and
Airlines.

## Impacts

| Area | Today | Needed | Phase |
|---|---|---|---|
| Access kinds | No manager-only kind; admin passes `OWNER_DEVICE` | `MANAGER_DEVICE` (admin excluded), matrix rows | 65 |
| Photo cleanup | `reassign_frame` wipes the directory (`fleet_ops.py:439`); `retire_frame` keeps data (`:499`), wiped at reactivate (`:541`) | delete photos on reassign, retire and account deletion | 65 |
| Config | 13 keys, no mode | `display_mode` (default planes, written only if set) | 66 |
| Mode stamp | none | `rendered_mode`, `rendered_at` in `poll_state.json` | 66 |
| Poll cycle | plane render for every runnable frame | photo branch, no ADS-B fetch, heartbeat kept, no gallery write | 66 |
| Waiting screen, hash | none | static panel in both sizes, stable bytes | 66 |
| Home | no mode, hero from gallery | mode block, pending line, hero by mode and viewer, swap selector, French | 67 |
| Menu | five pages | one Photos entry (managers), no hiding | 67 |
| Plane pages | no banner | banner in photo mode via `_page_shell_for` | 67 |
| Wake interval, health | max 3600, `device_status` reads the config key | mode-aware effective interval; raise or bypass the ceiling; fix "No contact"; battery pin rule | 68 |

## Edge cases

| Case | Behaviour |
|---|---|
| Switch to photos with zero photos | Allowed. Frame shows the waiting screen. Home hero shows the same placeholder; a line links to the Photos page ("No photo yet, add one"). |
| Last photo deleted in photo mode | Stays in photo mode (no auto switch). Next cycle (under 30 s) renders the waiting screen; the frame follows at its next wake. Photos page shows its empty state. |
| Over quota | Only the upload is refused. Existing photos and the mode are untouched. |
| Ownership change (reassign) | Directory reset: config back to planes, photos deleted (Phase 65 must cover photos stored elsewhere). Co-managers are already removed. |
| Co-manager removed or leaves | Loses Photos and the Home block. Mode and photos stay with the frame. |
| Frame retired | BYOS serves the pairing screen whatever the mode. Delete photos at retire (recommended), not at reactivate. |
| Mode changed twice before the next wake | One field, last write wins, no queue. A to B to A leaves `panel.bin` unchanged, the frame sees the same hash, no redraw; Home shows no pending line. |
| Two managers switch together | Last write wins. The form posts an explicit target mode, so a stale page cannot invert someone else's choice. |
| Owner switches while the frame is mid-wake | The frame already holds an immutable hash URL for the old image and draws it. New image at the following wake. Pending stays until a check-in after `rendered_at`. |
| Screen off, quiet hours or battery-empty during a pending change | The hold headline keeps priority (`home_page.py:343-366`); the pending line uses the held wording ("Applies when quiet hours end, around HH:MM"). |
| Admin on a user's frame | Read-only mode line, no photo, no switch, no Photos entry; direct URLs answer 404. |
| Frame never seen or still pairing | Block not shown until the frame has checked in. |

## Open questions for the owner

1. Quiet hours in photo mode: keep the photo on the glass, or show the
   quiet-hours screen as in plane mode? Recommended: keep the photo (a static
   picture needs no night screen); sleep is still extended. Display-off and
   battery-empty still win.
2. Pending wording: "Applies at the next wake, around 14:32" (reuse), or also a
   countdown? Recommended: the clock only, same sentence as the settings toast.
3. Banner on plane pages: informational with a link to Home, or with a
   "Switch back to planes" button? Recommended: link only; the switch lives in
   one place (Home).
4. Skip the ADS-B fetch for photo frames already in Phase 66, or later?
   Recommended: Phase 66 (option A above, small, and avoids a wrong plane
   render over a photo).
5. Delete a retired frame's photos at retire or at reactivate? Recommended: at
   retire.

## Evidence (file:line)

- Home: `companion/pages/home_page.py:217,343,390,629,664,729`; `page_context.py:262,401`
- Next wake and wording: `server/wake.py:58,87,147`; `companion/frame_state.py:47-53,93,101,132`; `flash.py:533`; `ui_components.py:569`
- Freshness: `companion/freshness.py:56-81,188`; `ui_nav.py` `REFRESH_SWAP_SELECTORS_BY_PAGE`
- Health: `health_signals.py:31,294,410,590`; `device_scope.py:287-300`; `console_pairing.py:91`
- Limits: `server/device_policy.py:198,202,206`; `device_config.py:394`; `stub-server/byos_server.py:542,630,1693`; `firmware/main/validate.h:17`
- Poll loop: `server/fleet_cycle.py:46,222,284,455,475`; `poll_cycle.py:274,704,719,739,758,808,1513`; `zone_fetch.py`; `request_budget.py`; `plane/detect.py:102`; `deploy/skypane-poll.timer`
- Access: `companion/access.py:61-92`; `route_types.py:33-40`; `routes.py:213-226,236-300`; `test_access_matrix.py:57`; `device_scope.py:352`; `ui_shell.py:452`
- Storage and delivery: `server/device_config.py:279,409,458`; `fleet_db.py:138`; `byos_server.py:1628-1710`; `firmware/main/state_machine.c:282`; `app_main.c:410`
- Lifecycle: `server/fleet_ops.py:439,499,541`
- Navigation and banner: `ui_base.py:111,122,141,1022`; `ui_nav.py:63-65,268,278,585`; `app.py:259,341,927`; `ui_shell.py:341,483,528`; `ui_components.py:205,265`
- Not found in code: any existing photo, mode or `MANAGER_DEVICE` symbol in `companion/`, `stub-server/`, `poll_cycle.py` or `device_config.py` (Phase 64 added only `server/photo/`).

## Decisions of 2026-11-11 (owner)

- The mode switch lives on the companion Home page. The menu stays stable:
  plane pages stay in the menu and show a banner while the frame is in photo
  mode. This replaces the earlier "hide plane pages" decision.
- Quiet hours in photo mode: **keep the photo on the glass** (the frame still
  sleeps longer). Display-off and battery-empty still win over photo mode.
- Defaults taken from the recommendations (the owner was not asked each one,
  and can change them): a pending change is shown with the clock time only
  ("Applies at the next wake, around 14:32"); the banner on a plane page is a
  link to Home only, so the switch lives in one place; the frame is skipped
  for the ADS-B fetch in photo mode, as the lowest-priority hold, in the
  server-side mode phase; a retired frame's photos are deleted at retire.
