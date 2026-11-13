# Photo mode: where the simplification is

Status: critical rethink for the owner, 2026-11-11. Read-only on code. It
challenges `photo-mode-workflow.md`, `photo-companion-navigation.md` and sketch
011, and three points of `photo-mode-concept.md` (said explicitly below).

## 1. The core problem

The design treats "Photos" as a second **mode of the whole product**, and then
tries to tell the truth about the delay between the companion and the glass.
Everything heavy comes from those two choices:

- 4 mode states (planes, pending-to-photos, photos, pending-to-planes), times 3
  holds (battery-empty, screen off, quiet hours), times 3 viewers (manager,
  admin, other). The workflow note needs a 12-row edge-case table and still
  leaves 10 open points (5 in the note, 5 in sketch 011).
- 7 places to build: Home block, pending box with Cancel, Home hero by mode and
  viewer, banner on 4 plane pages, Photos page, adjust page, waiting screen in
  2 panel sizes. Plus a new server stamp (`rendered_mode`, `rendered_at`).
- Phase 68 then makes the pending promise false: with a daily wake, "switch
  back" can take a day (sketch 011, open point 2), and it forces a new wake
  ceiling, new health thresholds and a battery-pin rule.

The app already has the answer. Home has a Frame group with two switches,
**Screen** and **Quiet hours** (`companion/pages/home_page.py:480`). Both change
what the glass shows, both apply at the next wake, and neither has a pending
state, a Cancel, a banner or a stamp: the save message says "Applies at the
next wake, around HH:MM" (`companion/frame_state.py:47-53`) and that is all.
On the server they are "holds" (`server/poll_cycle.py:704`). Photos is the same
kind of thing: *the frame rests from planes and shows something else*.

## 2. Four simplifications

### A. Photos is the third switch (not a mode)

1. Owner opens Photos (menu) and uploads at least one photo.
2. On Home, Frame group, a third row appears: **Photos** off/on, with a link
   "12 photos" to the Photos page (as Quiet hours links to its window).
3. He turns it on. Save message: "Applies at the next wake, around 14:32."
4. Home headline says "Showing photos" (as it says "Screen off" today).
5. He turns it off: same message, planes come back.

- States: 2 (off, on). Screens: 1 row on Home, Photos page, adjust page.
- Disappears: pending box, Cancel, the stamp in `poll_state.json`, the banner
  on plane pages, the "This frame shows" block, the read-only mode line on the
  Photos page, the manager-only hero on Home (see cuts), the waiting screen.
- Gives up: an exact "the glass has changed now" confirmation. For up to one
  wake interval Home says "Showing photos" while the glass still shows a plane.
  Screen off has the same gap today and nobody asked for more.
- Risks: the Screen and Quiet switches are open to the admin (`OWNER_DEVICE`);
  this row must use the manager-only kind from Phase 65
  (`companion/route_types.py:43` on branch `phase/65-photo-storage-privacy`),
  so the Frame group gets one row with a different permission.

### B. No switch at all: photos fill the empty sky

Challenges brief decision 2 (no automatic switch).

1. Owner uploads photos. 2. Nothing else to do. 3. When a plane is tracked the
frame shows it. 4. When none is, it shows a photo instead of "Watching Runway
3". 5. Delete the photos to get the old empty screen back.

- States: 0 user-visible. Screens: Photos page, adjust page.
- Disappears: the switch, mode storage, all of A's Home changes.
- Costs: the frame keeps the plane cadence, so **no battery gain at all**.
  Each change is a full 20-25 s refresh; at Orly in daytime a photo would
  flash in between two planes, so a "calm delay" rule is needed, a hidden
  state again. The photo enters the plane render path (the empty screen) and
  `publish_canvas` (`server/poll_cycle.py:739`), which archives to the
  admin-visible gallery. A photo-only frame still needs a switch.
- Verdict: rejecting auto-switch did **not** create the complexity. The honest
  later version is narrow: "show photos during quiet hours", an option of A.

### C. A photo frame is a kind of frame, chosen at pairing

1. At pairing (or in the frame's settings) the owner picks "plane frame" or
"photo frame". 2. A photo frame has its own short menu: Home, Photos. 3. A
plane frame is exactly today's app. 4. Changing kind is a rare, deliberate
action in the frame's settings. 5. No switch on Home.

- States: 2, rarely crossed. Screens: kind choice, Photos page, adjust page,
  a second Home. Disappears: banner, pending, mixed plane and photo pages.
- Costs: two menus to build and test; the owner's only frame is a plane
  frame, so trying photos means "changing what the frame is" and back. It is
  A with the switch moved somewhere rare, plus more navigation work.
- Verdict: not needed now. With A, a device bought as a photo frame is simply
  a frame whose Photos switch stays on.

### D. Hourly wake, full stop (cuts Phase 68 to a few lines)

Challenges brief decision 6 (wake interval follows the rotation).

1. Photos on: the frame wakes every hour, whatever the rotation. 2. The server
changes the photo at the rotation time. 3. Unchanged photo, same hash, no
redraw (already true). 4. Any change in the companion reaches the glass within
the hour. 5. "Applies at the next wake, around HH:MM" stays true.

- Arithmetic (mine, from derived figures): one wake is 0.3378 mAh
  (`hardware/BATTERY-MODEL.md:55`). At 300 s that is 288 wakes, about 97 mAh a
  day. Hourly: 24 wakes, about 8 mAh. Daily: 0.3 mAh. Hourly already takes
  92 % of what a daily wake would save; the standing draw (7.3 mA in the
  central fit, about 175 mAh a day, same file `:249`, still open) dwarfs the
  rest.
- Disappears: raising `WAKE_INTERVAL_MAX_S = 3600`
  (`server/device_policy.py:198`), a separate photo-mode interval source, the
  battery-pin conflict (the pin is also 3600, `:206`), the permanent "No
  contact" of daily frames.
- Remains: one branch "photos on gives 3600 s" in `effective_wake_interval_s`
  (`server/wake.py:58`, next to the screen-off case) and in the frame-facing
  sleep base, and `device_status` (`companion/device_scope.py:287`) calling it
  instead of reading the config key. Still gated on the battery phases.
- Gives up: about 8 mAh a day. Nothing the owner can see.

Rejected: "a frame that has photos shows photos". Going back to planes would
mean deleting them. One piece of it is kept below (no photo means planes).

## 3. Recommendation: A + D, with five cuts

"Photos" is a third switch in Home's Frame group, the frame wakes hourly while
it is on, and the Photos page only manages photos. Cuts, each with its cheapest
honest version:

| Cut | Cheapest honest version |
|---|---|
| Pending state, Cancel, stamp | The existing save message with the clock time. Undo is the switch itself. |
| Zero-photo case, waiting screen | The server shows photos only if the switch is on **and** a photo exists; otherwise the plane path runs. The switch is not offered until one photo exists. Deleting the last photo says "the frame will show planes again". This is a small automatic fallback: said openly. |
| Banner on plane pages | None. Home's headline says "Showing photos". Plane settings saved meanwhile apply when Photos is turned off, as they do during quiet hours. |
| Photo on Home | In photos, Home's hero is a neutral card "Showing your photos" with a link, the same for every viewer. The current photo is on the Photos page only. No manager-only image on Home, no admin variant. |
| Order choice, drag crop | One order: shuffled, no repeat within a round. Adjust page: "Fill" or "Whole photo", and for Fill three positions (start, centre, end) with the server preview. Phase 64 already takes `pos_x`/`pos_y` and the fit mode (`server/photo/crop.py:29-32`); dragging can come later with no server change. |

Why: it reuses a pattern the owner already lives with; 2 states instead of 4;
one row and one page instead of a block, a box, a banner and a hero variant;
and the companion's one promise ("around HH:MM") stays true in every phase.

Phases 64 (pipeline) and 65 (store, quotas, deletion, manager-only access)
stay fully valid; nothing is thrown away. Roadmap:

- Phase 66 becomes "Photos switch and rotation". Keep: per-device key (default
  off, written only when on), photo as the lowest-priority hold with no ADS-B
  fetch and the heartbeat kept, no gallery write, quiet hours keep the photo
  on the glass. Drop: the waiting screen (MODE-03 is replaced by the fallback
  rule), the order option (MODE-02 keeps the interval only), the mode stamp.
- Phase 67 becomes smaller: Home row, headline and neutral hero card; one
  Photos menu entry for managers; Photos page (grid, quota, upload, delete,
  rotation interval); simple adjust page. No banner, no pending box, no
  Cancel, no admin photo variants.
- Phase 68 becomes "hourly wake while Photos is on": one constant and the two
  call sites in D. No ceiling change, no health redesign. Gate unchanged.
- Requirements to edit: MODE-01 (a switch, not a mode), MODE-02, MODE-03,
  MODE-04, UI-03. Sketches 010 and 011 are superseded; one small sketch of the
  Home row and the Photos page is enough.

Not verified here: that the screen-off switch shows nothing more than the save
message on the real app (read from code only), and the real battery figures.

## 4. Three questions only the owner can answer

1. **Is the Screen switch's level of feedback enough for Photos?** That is: the
   save message gives the time, Home says "Showing photos" at once, and nothing
   tracks whether the glass has caught up. Recommended: yes.
2. **Hourly wake while Photos is on, instead of following the rotation up to
   one day?** Changes arrive within the hour and Phase 68 nearly disappears,
   for about 8 mAh a day. Recommended: yes.
3. **Accept the cuts for v1.3?** No waiting screen (no photo, or last photo
   deleted, means planes), one shuffled order, three crop positions instead of
   dragging, no photo on Home. Recommended: yes; dragging and the order choice
   can come back later without touching the server.

Later, if wanted: "show photos during quiet hours" as an option of the same
switch, and a frame kind at pairing when a second device exists.

## Owner decisions of 2026-11-11 (after the real-companion demos)

Adopted:
- Photos is a segmented switch "Planes | Photos" in the Home page's Frame
  group (beside Screen and Quiet hours), saved at once with the existing
  "Applies at the next wake, around HH:MM" message. No pending state, no
  Cancel, no banner on plane pages, no waiting screen. The Photos option is
  offered only once the frame has a photo; deleting the last photo while it
  is on puts the frame back on planes.
- While Photos is on the frame wakes hourly, whatever the rotation.
- v1.3 cuts: one shuffled order, Fill / Whole photo plus three position
  choices instead of dragging, no photo on Home.
- Menu: the "Flight history" tab is removed from the menu and the bottom
  bar; the history stays reachable from the recent flights on Home (a
  "All flights" link). Phone bar becomes Home, Photos, Location and
  detection, Style; Airlines stays in More.

Proposed, not objected to (confirm when the screens are built):
- Quiet hours stay active and visible in photo mode (they still save the
  night wakes, roughly a quarter of the photo-mode wake cost, derived and not
  measured), with a caption: "In photo mode the frame sleeps through these
  hours and the photo stays on the glass." Not greyed, not hidden.

Findings from the demo to settle in the build (not yet decided):
- The "around HH:MM" time uses the new setting's interval, not the interval
  the frame is actually sleeping on; fixing it needs the last interval sent
  to the frame remembered.
- The fallback to planes after the last photo is deleted needs a visible
  explanation on Home, not only on the Photos page.
- Adjust page without scripts: saving without "Update preview" saves the
  previewed framing; prefer one form with two buttons.
- The Photos menu entry must be hidden for people who cannot open it (the
  administrator gets a 404 today in the demo).
