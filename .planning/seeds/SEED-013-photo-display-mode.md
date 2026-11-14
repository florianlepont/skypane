---
id: SEED-013
status: dormant
planted: 2026-11-10
planted_during: "Exploration session on branch explore/photo-mode-v1-3 (no production code changed)"
trigger_when: "Milestone v1.3 — the owner chose to open it after the concept discussion of 2026-11-10; surface it at /gsd-new-milestone."
target_milestone: v1.3
scope: large
---

# SEED-013: Photo display mode (user photos, provided collections, messages, orientation, getting-started wizard)

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

**Large.** The concept brief of 2026-11-10 split it into v1.3 (own photos:
upload, per-frame mode, rotation) and v1.3.x (provided collections). **The owner
widened v1.3 on 2026-11-14**; see "Owner update, 2026-11-14" below, which
supersedes that split.

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

## Owner update, 2026-11-14

The owner's plan for milestone v1.3 now contains all of the following:

1. **Photo frames with messages.** A frame in photo mode can show a short
   message with its pictures. This is the existing future requirement MSG-01
   ("the companion sends a short message to the frame"); how a message is laid
   over or beside a photo, and who may send one, are open questions.
2. **Portrait and landscape for both frame types.** Both hardware types (the
   13.3 inch portrait frame and the 7.3 inch landscape frame under study) can
   be used in portrait or landscape, in both configurations (plane or photo).
   Orientation becomes a per-frame setting. Open question: whether a server-side
   rotation of the rendered image is enough (the panel keeps its native size,
   so the firmware would not change) or whether the firmware or image format
   must carry an orientation. To be checked before planning.
3. **Two configurations per frame: plane or photo.** The existing decision
   stands: one mode per frame, chosen in the companion, no automatic switch.
4. **A getting-started wizard** in the companion: pair a frame, choose its
   mode and orientation, set its location or runway, and for photo mode add the
   first pictures. It builds on the pairing by code (Phase 55) and the
   refreshed companion (Phase 61). SEED-012 (an admin invite that also creates
   the Auth0 account) belongs next to it.
5. **A photo collection system, in v1.3, not v1.3.x.** Collections come from
   two kinds of source: **public** (public domain or CC0 only, as decided on
   2026-11-10) and **partnerships** (for example the artist collection that has
   a written agreement). Each image keeps source, author and licence; a
   partnership needs a written agreement kept with the tracking file. How
   collections are published, enabled per frame and credited on or beside the
   picture is open.
6. **A simplified Wi-Fi setup** (added by the owner on 2026-11-14). Today the
   Wi-Fi network name and password are written onto the frame **over a USB
   cable** by `firmware/provision.sh`, into the "secret" storage partition,
   together with the enrolment secret and the server address. Moving a frame to
   another network therefore needs a cable and a computer. The upstream
   firmware has options for an on-device re-provision hold and a pairing QR
   (`FP_REPROVISION_HOLD_MS` and the E1004 controls in
   `firmware/main/Kconfig.projbuild`), but nothing in this project's firmware
   uses them, and the XIAO boards of both frame types have no such buttons.
   Ways to evaluate: a setup mode where the frame opens its own temporary
   network and a phone enters the home network on a small page, a Bluetooth
   provisioning flow (the ESP32-S3 has Bluetooth), or both. Points to settle:
   how a frame enters setup mode without a button (for example after several
   failed connections, or on first boot when unprovisioned); what the e-ink
   panel shows during setup (instructions and a QR code to join the temporary
   network; each redraw takes 20 to 25 seconds); a timeout so setup mode cannot
   drain the battery; storing more than one network; and security: **the Wi-Fi
   password stays between the phone and the frame and is never sent to the
   server.** It fits the getting-started wizard (item 4) and the pairing code
   shown by an unclaimed frame (Phase 55). It is a firmware change, so it
   reaches existing frames only by an over-the-air update (see Prerequisites).

## Prerequisites to check at milestone start

- Phase 58 (second hardware) validated, since "both frame types" needs the
  7.3 inch type working on a real unit.
- Phase 47.1 (wake-energy measurement) finished before changing the wake
  interval per mode (see Notes).
- Phase 57 (combined firmware release) sequenced, if photo mode or the
  Wi-Fi setup needs any firmware change. The Wi-Fi setup certainly does.

## Breadcrumbs

- `.planning/notes/photo-mode-concept.md` (the concept brief)
- `server/plane/dither.py`, `server/test_dither.py` (6-colour dithering)
- `server/panel_format.py` (palette and panel size)
- `companion/illustration_normalize.py`, `server/plane/illustrations.py` (upload and normalisation to reuse, not copy)
- `server/detection.py` (per-device mode as a model for a display mode)
- `stub-server/byos_server.py` (content-addressed image serving)
- `hardware/BATTERY-MODEL.md`, `hardware/SECOND-HARDWARE.md` (energy figures, landscape panel)
- `firmware/provision.sh`, `firmware/main/enrol_secret.c` (how Wi-Fi and the enrolment secret are written today)
- `firmware/main/Kconfig.projbuild` (unused upstream re-provision and pairing-QR options)

## Notes

Do not touch plane-mode rendering or `server/fixtures/golden`. Changing the
wake interval per mode must wait until the battery-measurement phases are
finished.
