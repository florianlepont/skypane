# Phase 69: Rear Enclosure for the 7.3 Inch Frame - Context

**Gathered:** 2026-11-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A printed rear enclosure (tray, lid with wall hooks and hinge, folding stand, centring shim) for the Seeed EE04 frame (7.3 inch Spectra 6) that fits an IKEA RÖDALM 13 x 18 cm black frame; requirement ENC-01. It is owner-driven physical work: the planner writes plans, checklists and record templates; the owner measures, designs, prints and tests. No code, no firmware, no server change, nothing deployed.

Not in this phase: the administrator flashing tool (SEED-014, v1.4), a 13.3 inch enclosure, series production (SEED-015), battery discharge (SEED-019).

</domain>

<decisions>
## Implementation Decisions

### Honesty rules for every artefact
- **D-01:** Every number that comes from the design record, the vendor drawings or the IKEA 3D model is written "design value, not measured" until the owner reports a measurement. Never claim a measurement, a print or a fit test happened unless the owner reports it, with date and method.
- **D-02:** Written artefacts are in English; answers to the owner are short and in French.

### Milestone relationship
- **D-03 (owner, 2026-11-18):** Phase 69 is an owner-driven parallel track. Milestone v1.2 MAY CLOSE before Phase 69 is finished; an unfinished phase then carries into the next milestone. Recorded in the roadmap's open decisions and in STATE.md.

### Order of measurements
- **D-04:** Screen first (outline about 170.2 x 111.2 x 0.91 mm and active area 160 x 96 mm per vendor drawings, to confirm on the real panel; the shim depends on it). Second: the RÖDALM frame (rebate about 133.4 x 183.4 mm, free depth 22.7 mm, mat thickness 1.2 mm assumed, metal tabs about 12.6 mm behind the screen). Third: ribbon length (24 mm assumed), battery cable length (under 105 mm per the owner, exact value unknown), masses of board and frame. Tool: calliper, no printer needed. Mat opening about 158 x 94 mm is cut by the owner.

### Printing
- **D-05:** The parts are printed elsewhere (print service or fablab) for the first test print. No printer purchase for now. The Bambu Lab X2D Combo (749 EUR noted, Black Friday offer until 2026-12-01, to recheck) stays an option to revisit after the first fit result; the purchase is not decided and is the owner's.

### Owner update 2026-11-18 (replaces D-05, D-06 where different)
- **D-13:** First print on the Bambu Lab X1 printers at the owner's workplace (no print service). PETG, any colour, nozzle 0.4 mm or another if needed, M2 self-tapping screws. Filament brand and build plate open.

### Material and fixing
- **D-06:** PETG, black (to match the black frame), 0.4 mm nozzle. Filament brand and build plate are left to the print provider / owner and recorded when known. Lid fixing: M2 self-tapping screws, pilot holes 1.7 mm, through holes 2.4 mm. Heat-set inserts stay a fallback if the printed threads wear.

### Wi-Fi comparison
- **D-07:** Same place, same orientation, same access point. At least 20 wakes without the enclosure, then at least 20 with it, using the `rssi` column of the frame's own health history (export `GET /api/export/battery-history`, as in `hardware/SECOND-HARDWARE-MEASUREMENTS.md`). Pass criterion proposed: median RSSI not worse by more than 3 dB (design value; the owner may adjust it when validating).

### Mat, tabs and battery (owner, 2026-11-18)
- **D-09:** The mat keeps its 140 x 99 mm opening; the displayed image will be adapted to the visible window, not the mat recut. That image change is rendering work outside this phase.
- **D-10:** Metal tab depth is 8 mm (corrects the first report of 0.8 mm).
- **D-12:** Everything (shim, tray, lid, stand) is centred on the mat opening, not on the screen active area (owner, 2026-11-18).
- **D-11:** The pack in the enclosure is the Kubii 3000 mAh (8 x 50 x 60 mm, vendor size; measured 8 x 60 x 50 mm, 49 g).

### Blender work
- **D-08 (owner, 2026-11-18):** The Blender design is not final and is to be reworked together. Claude cannot open Blender in the cloud session, so the redesign needs a local session on the owner's computer (or the owner applies changes described in writing).

### Claude's Discretion
- Structure of the plans, the measurement sheet and the assembly note; how to split owner steps into checkpoints; file names under `hardware/`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Enclosure design
- `hardware/ENCLOSURE-3D-DESIGN.md` — owner's design record: four parts, dimensions, clearances, decisions, open questions
- `hardware/cad/skypane_cassette.blend` — Blender file with the generating script (cannot be opened here; owner must confirm it is saved and current)
- `hardware/cad/ee04_board.stl` — board model
- `hardware/cad/ikea_rodalm_13x18_noir.glb` — IKEA frame model
- `.planning/seeds/SEED-014-enclosure-for-the-back-of-the-frame.md` — origin, split of 2026-11-18

### Hardware
- `hardware/SECOND-HARDWARE.md` — EE04 candidate and dimensions
- `hardware/BOM.md` — to be updated with added parts and cost
- `hardware/SECOND-HARDWARE-MEASUREMENTS.md` — EE04 pins, buttons, LED measured in Phase 64
- `hardware/BATTERY-MODEL.md`, `hardware/PACK-ACCEPTANCE.md` — battery facts used by the design

### Planning
- `.planning/workstreams/v1-2/ROADMAP.md` — Phase 69 section and success criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — ENC-01

</canonical_refs>

<code_context>
## Existing Code Insights

No code is touched. Existing hardware records follow a "measured vs provisional" table style (see `hardware/SECOND-HARDWARE-MEASUREMENTS.md`: date, unit, method, status); reuse it for the Phase 69 measurement sheet. The RSSI source already exists (`device_health.rssi`, battery-history export).

</code_context>

<specifics>
## Specific Ideas

Landscape is the base format (board at the bottom), portrait secondary; wall on battery, furniture possibly on USB power. Design checks already on the model (closed meshes, no support, wall >= 0.8 mm, centre of gravity) used estimated masses and must be redone after the real masses are measured.

</specifics>

<deferred>
## Deferred Ideas

- Printer purchase (X2D Combo): revisit after the first fit.
- Adapting the displayed image to the 140 x 99 mm mat window (server/rendering, not this phase; needs its own phase or seed).
- Identity label with device identifier / pairing code (SEED-014, v1.4).
- 13.3 inch enclosure, series production method and cost (SEED-015).

</deferred>

---

*Phase: 69-rear-enclosure-for-the-7-3-inch-frame*
*Context gathered: 2026-11-18*
