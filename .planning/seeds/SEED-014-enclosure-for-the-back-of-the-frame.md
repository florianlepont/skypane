---
id: SEED-014
status: dormant
planted: 2026-11-14
planted_during: "v1.2, owner's roadmap discussion after the photo mode exploration"
trigger_when: "Milestone v1.4 (hardware) — the owner planned it on 2026-11-14 to follow v1.3; surface it at /gsd-new-milestone, or earlier if a hardware type is frozen."
target_milestone: v1.4
scope: medium
---

# SEED-014: A proper enclosure for the back of the frame

## Why This Matters

Today the frame is a bare e-ink panel with its driver board and a LiPo pack.
`hardware/BOM.md` says plainly that no enclosure exists ("no confirmed public
EE02 enclosure design exists yet"). A clean rear enclosure is what turns the
prototype into something hangable on a wall or standable on a desk, hides the
battery and the wiring, and is a prerequisite for putting a frame in front of
anyone else, including the later go-to-market study (SEED-015).

## When to Surface

**Trigger:** milestone v1.4, planned by the owner after v1.3. It depends on the
hardware types being settled, so surface it when Phase 58 (second hardware) is
done and the types to be supported are known.

## Scope Estimate

**Medium, and mostly physical rather than software.** The deliverables are a
design, prototypes and tests, not code. Points to settle at milestone start:

- **Which frames:** the 13.3 inch EE02 and the 7.3 inch EE04 (if retained), each
  in portrait and landscape (see SEED-013 on orientation): one family of
  enclosures or two.
- **Mechanical interface:** how the enclosure attaches to the panel and its
  bezel or frame; wall hook, stand for the desk, or both.
- **Battery:** a protected LiPo pack with the correct polarity, how it is held
  and kept from being pinched, whether the owner can swap it, and the
  autonomy target set in v1.1 (about six months).
- **Access:** USB-C for charging and flashing, any button, reset, a status
  light, and the serial pins used for provisioning.
- **Radio:** the enclosure must not block the ESP32 Wi-Fi antenna; materials and
  placement to be tested with measured signal strength.
- **Making it:** 3D printing for prototypes; what a small series would use
  (print, laser cut, injection) and the cost of each, which feeds the bill of
  materials of SEED-015.
- **Identity:** a place for a label with the device identifier or a code for
  pairing (the pairing by code exists since Phase 55).

## Breadcrumbs

- `hardware/BOM.md` (bill of materials; the enclosure is listed as not included)
- `hardware/SECOND-HARDWARE.md` (second hardware candidate and its dimensions)
- `hardware/BRINGUP-LOG.md` (how the first frame was assembled)
- `hardware/BATTERY-MODEL.md` (battery and autonomy figures)
- `firmware/provision.sh` (provisioning needs access to the serial port)

## Notes

Not a software milestone: GSD phases for it would track decisions, prototypes
and test results (photos, measurements) rather than code. The v1.3 photo mode
does not depend on it, and it does not depend on v1.3.
