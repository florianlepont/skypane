---
sketch: 007
name: photo-list-and-upload
question: "How should a frame's photo list, upload, quota meter, delete confirmation and refusal messages be laid out in the companion?"
winner: null
tags: [photos, upload, quota, list, mobile, desktop, i18n, v1.3]
---

# Sketch 007: Photo list and upload

## Design Question
A frame in photo mode keeps up to 20 photos (about 1 MB each, 20 MB per frame). Where do the quota meter and the upload control go, how is the list shown (thumbnails or rows), how does a delete get confirmed, and how are the refusals worded and placed (file too big, not an image, unsupported format, HEIC, animated, too small, quota reached, server full, disk low)?

## How to View
open .planning/sketches/007-photo-list-and-upload/index.html

Params: `?v=a|b|c&lang=fr&theme=dark&state=populated|almost|full|empty&msgs=too_large,heic_unsupported&chrome=0`.
Real files can be chosen with the buttons to try the real client-side checks (they stay in the browser); the "simulate" row shows every server refusal.

## Theme
Links `../themes/companion-current.css` and `../themes/photo-shell.css` / `photo-shell.js` (new, shared by 007-009). They carry the LIVE `companion/static/style.css` tokens (graphite accent, glass cards, system sans, solid-accent segmented controls, docked toasts, 44 px targets, sidebar from 960 px and floating tab bar below). `default.css` is a pre-redesign snapshot (serif, orange accent) and is left untouched.

## Variants
- **A: Grid** — three cards: quota meters, a large drop zone (button only on touch), then a 2/4-column thumbnail grid with Adjust and Delete under each photo. Delete opens a confirm dialog.
- **B: List rows** — one card; Add photos in the card header, both meters as a compact strip, 72 px thumbnails in rows with icon actions. Delete confirms inline inside the row. The whole card is the drop target.
- **C: Hybrid grid + select** — grid whose first tile is "Add photos"; tapping a tile opens Adjust (sketch 008); a Select mode with checkboxes and a bulk Delete (one confirm for N photos) for clearing space when the quota is reached.

## Common
- Meters: photos "7 of 20" and storage "6.2 of 20 MB" (role `meter`); warning amber from 80 %, error at 100 %, always with words ("Almost full" / "Full: delete a photo to add another"), never colour alone.
- Refusals are persistent docked toasts under the upload control (title + detail, dismissible, `role=alert` for errors). File problems are error tone; `frame_count` / `frame_bytes` are warning; `server_bytes` / `disk_low` are error but worded as "not your photos".
- Empty state, the "On the frame" badge, a delete warning when the current photo is deleted, and EN/FR strings throughout.

## What to Look For
- Is the quota visible enough at 19 of 20 and 20 of 20 without being noisy at 7 of 20?
- Does the grid or the row list make Delete feel safe on a phone (44 px targets, confirm)?
- Is the select mode worth its extra concept, or is per-photo Delete enough?
- Refusal wording, in both languages, and whether a docked message under the control is found at once on a phone.
- Open: where the Photos page lives in the navigation (a new destination is assumed here).
