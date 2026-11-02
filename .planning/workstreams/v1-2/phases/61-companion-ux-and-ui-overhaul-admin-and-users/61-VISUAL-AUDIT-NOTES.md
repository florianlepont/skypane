# Phase 61 — visual audit notes (pre-walkthrough)

Source: 68 full-page captures of the current companion on fake data
(admin / user / login, 360 px and 1280 px, EN and FR). Script: scratchpad
`shoot.py` (provisioned_fleet fixture, loopback server, no network).

## Observed before any walkthrough (to confirm with the owner)

- **User view is one page.** A plain user gets 404 on `/`, `/display`,
  `/device`; the only page is `/account`, yet the phone tab bar shows
  Home / Flights / Display / Health / Account to them (tabs that lead to 404).
- **Fleet desktop table is clipped**: the Hardware column is cut and the
  actions column is off-screen (horizontal scroll inside the card).
- **Fleet phone cards**: Open / Reassign / Retire stacked per frame, long;
  the console section tabs (Fleet/Users/Locations/Audit/Releases) wrap onto
  two lines at 360 px.
- **Phone nav**: the admin console hides behind one "Admin" tab plus a
  "More" tab; admin concepts (Admin) sit beside everyday tabs.
- **Users phone**: email breaks mid-word, badge "INVITED" on already
  signed-in users, role select + "Save role" take a full row per user.
- **Pair a frame / Register a frame**: two forms always open, the rarely
  used raw MAC/secret form has the same weight as the pairing one.
- Fixed tab bar overlaps content in full-page captures (artefact of the
  capture, to be re-checked in a real viewport).

## Full page sweep (all 13 pages, mobile and desktop, EN and FR sampled)

Navigation and structure
- Desktop sidebar has 3 groups (everyday / Advanced / Administration) = 12
  entries; "Account" is not in the sidebar for an admin at all.
- Same destination, three names: Device / Update / Releases (FR: Appareil /
  Mise à jour / Versions); the Update page has its own title "Update" but
  its tab says "Releases".
- "Detection" appears on both Display and Device (two cards, same link).
- Phone: 5 tabs (Home, Display, Flights, Admin, More); Health, Device,
  Update, Account and Airlines hide behind "More"; the dot on "More" and on
  Health is an unexplained orange marker.
- Console section tabs wrap on two lines at 360 px on every admin page
  (the "Releases" tab alone on row two); the Audit page stacks a second
  wrapped filter row under it (two tab rows before any content).
- A "Frame" picker sits at the top of Home/Display/Flights/Health/Device
  even for a single frame.

Admin console
- Fleet and Users desktop tables are clipped inside their card (columns
  cut, actions off-screen); email and frame name rendered in large
  monospace, with the id/last-seen glued to it on the same line.
- Users: "Invited" badge on users who already signed in; "Last active
  administrator cannot be changed" text truncated on desktop.
- Locations: inputs/selects overflow the card width at 360 px (the time
  zone select pokes out of the card).
- Pair a frame and Register a frame are always-open forms below the list;
  the raw MAC/secret form has the same weight as pairing.
- Owner/co-manager actions live on Home (Co-managers card), far from
  Fleet where frames are managed.

Home / Display / Device / Health
- Home: a persistent "Something needs attention" bar leads to Health;
  empty states are large serif blocks; the Current frame card is empty
  of content when no image exists yet.
- Device: Diagnostic LED switch is drawn with an orange box around it.
- Health: "Frame connection" row says "Has not checked in" three ways.

User view
- A plain user can reach only /account (every other page is a 404), but
  the phone tab bar offers Home/Flights/Display/Health to them.
- Frames list shows serif name + hardware model side by side, "Open" link
  per frame; no frame state (battery, last image, problem) at a glance.

Login
- Login card is clean and short; error and invitation states still to be
  captured (unverified email, not invited).
