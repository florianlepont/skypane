---
sketch: 011
name: mode-switch-on-home
question: "Does the new workflow hold together: the Planes | Photos switch on Home, a pending state with a clock time, a menu that never changes, a banner on plane pages in photo mode, and a Photos page that only manages photos?"
winner: null
tags: [photos, navigation, mode, home, pending, banner, mobile, desktop, i18n, v1.3]
---

# Sketch 011: Mode switch on Home, stable menu (clickable)

Rebuild of 010 for the workflow in `.planning/notes/photo-mode-workflow.md` (4 states, "Decisions of 2026-11-11"). One self-contained `index.html`, inline CSS/JS, no network, procedural art only. 010 is untouched. Photo adjust page (crop, bands, dithered preview), refusals (12 MB per file), delete confirm and privacy line are carried over from 010.

## How to view
Open `index.html`. The dark top bar is sketch chrome: EN/FR, Light/Dark, viewport helper, a fake clock readout, "Frame wakes now" (completes a pending change, advances the clock to the frame's wake) and chips 1 to 7:
1 Planes; 2 Switch to Photos (pending); 3 Frame wakes (photos); 4 Plane page in photo mode (banner); 5 Photos page; 6 Switch back (pending); 7 Zero photos case (pending; press "Frame wakes now" to see the waiting screen).
URL parameters: `step=1..7`, `lang=fr`, `theme=dark`, `vp=phone|tablet|desktop`, `chrome=0`; also `mode=photos`, `page=photos|flights|...`.

## What it shows
- Home: block "This frame shows: Planes | Photos" (radiogroup, arrow keys switch, one explicit target value). Pending: "Applies at the next wake, around 14:32", "still showing planes until then", Cancel link. Zero photos: allowed, inline note and "Add photos" (opens Photos page on the upload button).
- Home in photo mode: current photo, "Next photo about 02:00 tomorrow" (follows the rotation setting), quiet-hours line (photo stays on the glass).
- Menu identical in every state: Home, Flight history, Location and detection, Style, Airlines, Photos (last; in More on a phone).
- Plane pages in photo mode: docked info banner with a "Go to Home" link only.
- Photos page: read-only "This frame shows: X" with "Change on Home"; in plane mode "Not shown on the frame while it shows planes."; rotation and order (Save bar), photo grid and quota, upload, adjust page, delete.

## What to look for
- Is the block on Home prominent enough, and is one tap with a visible Cancel the right amount of ceremony (no confirm, no Save bar)?
- Does the pending box say clearly what the frame shows now versus later?
- Does a stable menu plus banner feel better than 010's shrinking menu?
- Photos page without the switch: is "Change on Home" enough of a pointer?

## Open points
1. Banner timing: it follows the saved mode, so during pending-to-photos it already shows (worded "is switching to photos"). During pending-to-planes it is gone while the frame still shows photos. Alternative: follow the shown mode.
2. Wake cadence: the sketch fakes a wake every 4 minutes in both modes. In photo mode the real frame may wake only for rotation (Phase 68), so switching back could wait much longer than the pending line says.
3. Arrow keys on the segmented control switch immediately (radiogroup convention) and so save a change; a stray key press is undone with Cancel.
4. Home hero in photo mode is shown to managers only; admin variant not drawn.
5. Rotation changes still use a Save bar; the mode switch does not. Intentional difference to judge.

## Not verified
Real upload, server render, real devices and touch dragging, screen readers, admin and co-manager views.
