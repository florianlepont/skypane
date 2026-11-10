---
id: SEED-013
status: dormant
planted: 2026-11-10
planted_during: "Exploration session on branch explore/photo-mode-v1-3 (no production code changed)"
trigger_when: "Milestone v1.3 — the owner chose to open it after the concept discussion of 2026-11-10; surface it at /gsd-new-milestone."
target_milestone: v1.3
scope: large
---

# SEED-013: Photo display mode (user photos, then provided collections)

## Why This Matters

Today a frame only shows the plane screen. The owner wants a second mode in
which a frame shows still pictures: the user's own photos, then collections
supplied by the project. A still photo costs almost nothing on the panel (an
unchanged image is not redrawn) and the frame can wake much less often, so the
mode should also help battery life.

## When to Surface

**Trigger:** `/gsd-new-milestone` for v1.3. The decisions are already taken, so
the milestone can go straight to requirements and phases.

## Scope Estimate

**Large**, in two parts: v1.3 (own photos: upload, per-frame mode, rotation)
and v1.3.x (provided collections).

Full decisions, risks, visual trials and a five-phase outline are in
`.planning/notes/photo-mode-concept.md`. In short:

- One mode per frame, plane or photos, set in the companion.
- Crop to fill by default, with a per-photo crop-or-bands setting.
- Rotation per frame: hourly, 6 h, 12 h or daily; random without repeats or in
  upload order.
- Privacy rule: only the owner and co-managers see photos, never the admin.
  Reduced copies only, real deletion, a quota.
- Collections: public domain or CC0 only, plus one artist collection that needs
  a written agreement.

## Breadcrumbs

- `.planning/notes/photo-mode-concept.md` (the concept brief)
- `server/plane/dither.py`, `server/test_dither.py` (6-colour dithering)
- `server/panel_format.py` (palette and panel size)
- `companion/illustration_normalize.py`, `server/plane/illustrations.py` (upload and normalisation to reuse, not copy)
- `server/detection.py` (per-device mode as a model for a display mode)
- `stub-server/byos_server.py` (content-addressed image serving)
- `hardware/BATTERY-MODEL.md`, `hardware/SECOND-HARDWARE.md` (energy figures, landscape panel)

## Notes

Do not touch plane-mode rendering or `server/fixtures/golden`. Changing the
wake interval per mode must wait until the battery-measurement phases are
finished.
