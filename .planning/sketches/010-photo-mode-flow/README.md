---
sketch: 010
name: photo-mode-flow
question: "Does the whole photo-mode flow hold together in the companion: menu that follows the frame mode, Photos page, upload, crop and preview, refusals, and the way back to planes (v1.3)?"
winner: null
tags: [photos, navigation, mode, flow, mobile, desktop, i18n, v1.3]
---

> Superseded on 2026-11-13 by `.planning/notes/photo-frame-types.md` for the mode switch and the menu. Kept as history.

# Sketch 010: Photo-mode flow (clickable)

One self-contained file, `index.html` (all CSS and JS inline, no network). It
assembles the recommended variants into one clickable prototype: 007 A (grid,
quota meter, upload), 008 A (preview-first crop and bands, six-colour dithered
preview), 009 A (segmented mode, rotation and order), inside a faithful frame
of the companion shell (sidebar from 960 px; below it a floating tab bar with a
More sheet). Decisions come from `.planning/notes/photo-companion-navigation.md`.

## How to view
Open `index.html` in a browser; nothing else is needed. The dark top bar is
sketch chrome, not part of the app:
- Walkthrough chips 1 to 7 jump to a state (planes menu, Photos page in planes
  mode, switch to photos, add a photo, crop and preview, a refusal, back to planes).
- EN / FR, Light / Dark, and a viewport helper (Phone 390, Tablet 768, Desktop
  1280) that shows the app in a frame of that width; Auto uses the real window.
- Options: Photos position in the menu (last or second), Style visible or hidden
  in photo mode, and "Frame wakes now" (the frame catches up with the saved mode).
- URL parameters: `step=1..7`, `lang=fr`, `theme=dark`, `vp=phone|tablet|desktop`,
  `page=`, `mode=photos`, `shown=`, `photos=none|7|19|20`, `open=<photo>`,
  `refuse=big|quota|fmt|heic`, `pos=second`, `display=1`, `chrome=0`.
- Everything is clickable by hand too. On the Photos page a dashed "Sketch only"
  row simulates upload refusals; "Add photos" adds a drawn picture; at 20 photos
  it refuses with the quota message.

## What it shows
- Menu follows the saved frame mode. Planes: Home, Flight history, Location and
  detection, Style, Airlines, Photos. Photos: Home and Photos only (Style hidden
  by default). The phone bar holds the first four entries; the rest, with
  Account, theme and language, are in the More sheet.
- Home carries "Frame is showing: Planes / Photos" and, when the saved mode
  differs, a note that the change happens at the frame's next wake (about 4
  minutes, faked). The menu changes at once; the frame does not.
- Photos page, top to bottom: mode switch (Planes | Photos; Save bar; toast "Saved.
  The frame will switch at its next wake."), then in plane mode the "Photo mode is
  off" state with "Switch this frame to photo mode" (and a strip of kept photos);
  in photo mode rotation and order, the photo card (meters, upload, refusals,
  grid), the "No photo yet" waiting state, delete with a confirm, and the
  privacy line for owners versus administrators.
- Selecting a photo opens Adjust: portrait or landscape preview, fill or whole
  photo, crop position (drag, arrows, sliders), frame look versus original,
  Save / Cancel, Delete, and the six-colour note.

## Labels
The menu uses the shipped labels (`companion/ui_base.py`, `i18n_fr/nav.py`): the
page called "Display" in code is labelled "Style"; Flights is "Flight history"
(bar: "History" / "Vols"); Detection is "Location and detection" (bar: "Location"
/ "Lieu"). The new entry is "Photos" in both languages.

## What to look for
- Does the menu that shrinks to Home and Photos feel clear, or does the owner
  wonder where Flights went? Is the Home status line enough?
- Photos last (in More on a phone in plane mode) or second (always on the bar)?
- Switching: a Save bar for the segmented control, a direct button in the empty state.
- The wait for the next wake: is "about 4 minutes" explained well enough?
- Refusal wording and placement under the upload control, in both languages.
- Adjust as a page with Back, versus a sheet.

## Open questions
1. Does Style stay visible in photo mode? It is hidden here, as decided for this
   sketch. Parts of it (theme, layout) are about plane screens, but it may later
   hold options that also apply to photos. The Options toggle shows both.
2. Photos position: last (phone: in More while in plane mode) or second.
3. Hiding rule when the mode changes while another page is open (another tab, a
   co-manager): here the menu follows the saved setting at once and an open plane
   page falls back to Home. The real page would need a message.
4. Should Home show the next wake time in photo mode (rotation interval) instead
   of a fixed estimate?
5. Per-file size limit (8 MB here), HEIC handling and refusal wording are placeholders.

## Not verified
Real file picking and upload, the server's real render (the preview is a browser
approximation, as in 008), real devices and touch dragging, screen readers.
