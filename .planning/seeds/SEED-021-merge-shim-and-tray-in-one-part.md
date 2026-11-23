---
id: SEED-021
status: promoted
planted: 2026-11-23
planted_during: "v1.2, Phase 69 (rear enclosure), owner's question during the first fit trials"
trigger_when: "After the first fit results of the 7.3 inch enclosure (the shim and the tray both fit by feel in PLA on 2026-11-23), or when the enclosure is redesigned for a series or for another screen"
scope: small
---

# SEED-021: Merge the centring shim and the tray in one printed part

## Why This Matters

The 7.3 inch enclosure has four printed parts: tray, lid, stand plate and a
1.0 mm centring shim (cale) around the screen. The owner asked why the shim and
the tray are not one part. The design record gives no written reason for the
split, and the owner does not remember one. A single part would mean one part
fewer, one fit step fewer and no loose shim to lose. Owner idea of 2026-11-23;
not decided.

## Update of 2026-11-23

The owner decided that the shim and the tray must be one single part, for the
assembly ("il faut vraiment"), after the first fit of the printed tray. The
change goes into the next tray reprint of the 7.3 inch enclosure, together with
the longer ribbon slot and the longer battery pocket, recorded in the print
order. Risk to check first in the slicer: the screen-side face of the merged
part has a rim around the screen (the former shim) while the tray floor sits
behind the screen, so the part may need supports or an awkward print
orientation, and a support-marked floor would face the screen. The owner checks
this in Bambu Studio after the Blender change; nothing has been checked yet.

## When to Surface

**Trigger:** after the first fit round of Phase 69 has shown how the shim and
the tray behave in the frames, or at any redesign of the tray (series
production, another screen size).

## Scope Estimate

**Small.** A change to the tray in Blender by the owner, one reprint of the
tray, and a new fit trial. Claude cannot edit the Blender file.

## Trade-offs to weigh

- Lost: the 15 to 20 minute shim print used as a cheap fit gauge before the
  1 h 30 tray print.
- Lost: a failed print would lose the whole part.
- Lost: a different screen would mean reprinting the whole tray, not only the
  shim (the 0.5 mm clearance around the screen sits in the shim).
- To check: the assembly order with the fragile screen and its ribbon must
  still work (screen placed first, ribbon through the slot, then the tray).
- Possible reasons for the split, inferred by the assistant and not stated by
  the owner: the cheap early fit gauge; screen handling; independent
  tolerances around the screen.

## Breadcrumbs

- `hardware/ENCLOSURE-3D-DESIGN.md`: the four parts, the shim at 1.0 mm.
- `hardware/ENCLOSURE-TEST-PRINT-LOG.md`: fit trials by feel, PLA.
- `hardware/ENCLOSURE-PRINT-ORDER.md`: slice of the shim and the tray.
- SEED-014 (the enclosure and the administrator tool).

## Notes

Captured on 2026-11-23 at the owner's request. Nothing was measured or printed
for this idea.
