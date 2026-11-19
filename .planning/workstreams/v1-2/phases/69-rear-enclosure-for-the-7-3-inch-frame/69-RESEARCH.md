# Phase 69: Rear Enclosure for the 7.3 Inch Frame - Research

**Researched:** 2026-11-19
**Domain:** Owner-driven physical phase: FDM PETG enclosure (Bambu Lab printers) for a Seeed EE04 e-ink frame plus a 3.7 V LiPo, in an IKEA RÖDALM 13 x 18 cm frame. No code, no firmware, nothing deployed.
**Confidence:** MEDIUM on process and repository facts (HIGH, read from the repo); LOW to MEDIUM on every numeric tolerance (forum-level evidence only, no authoritative PETG/Bambu tolerance table exists; the first print will decide).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Every number that comes from the design record, the vendor drawings or the IKEA 3D model is written "design value, not measured" until the owner reports a measurement. Never claim a measurement, a print or a fit test happened unless the owner reports it, with date and method.
- **D-02:** Written artefacts are in English; answers to the owner are short and in French.
- **D-03 (owner, 2026-11-18):** Phase 69 is an owner-driven parallel track. Milestone v1.2 MAY CLOSE before Phase 69 is finished; an unfinished phase then carries into the next milestone.
- **D-04:** Screen first (outline about 170.2 x 111.2 x 0.91 mm and active area 160 x 96 mm per vendor drawings, to confirm on the real panel; the shim depends on it). Second: the RÖDALM frame (rebate about 133.4 x 183.4 mm, free depth 22.7 mm, mat thickness 1.2 mm assumed, metal tabs about 12.6 mm behind the screen). Third: ribbon length (24 mm assumed), battery cable length (under 105 mm per the owner, exact value unknown), masses of board and frame. Tool: calliper, no printer needed. Mat opening about 158 x 94 mm is cut by the owner. (Superseded in part by D-09, see divergences.)
- **D-05:** The parts are printed elsewhere (print service or fablab) for the first test print. No printer purchase for now. The Bambu Lab X2D Combo (749 EUR noted, Black Friday offer until 2026-12-01, to recheck) stays an option to revisit after the first fit result; the purchase is not decided and is the owner's. (Replaced by D-13 where different.)
- **D-13 (owner update 2026-11-18, replaces D-05, D-06 where different):** First print on the Bambu Lab X1 printers at the owner's workplace (no print service). PETG, any colour, nozzle 0.4 mm or another if needed, M2 self-tapping screws. Filament brand and build plate open.
- **D-06:** PETG, black (to match the black frame), 0.4 mm nozzle. Filament brand and build plate are left to the print provider / owner and recorded when known. Lid fixing: M2 self-tapping screws, pilot holes 1.7 mm, through holes 2.4 mm. Heat-set inserts stay a fallback if the printed threads wear.
- **D-07:** Wi-Fi comparison: same place, same orientation, same access point. At least 20 wakes without the enclosure, then at least 20 with it, using the `rssi` column of the frame's own health history (export `GET /api/export/battery-history`). Pass criterion proposed: median RSSI not worse by more than 3 dB (design value; the owner may adjust it when validating).
- **D-08 (owner, 2026-11-18):** The Blender design is not final and is to be reworked together. Claude cannot open Blender in the cloud session; redesign needs a local session on the owner's computer (or the owner applies changes described in writing).
- **D-09:** The mat keeps its 140 x 99 mm opening; the displayed image will be adapted to the visible window, not the mat recut. That image change is rendering work outside this phase.
- **D-10:** Metal tab depth is 8 mm (corrects the first report of 0.8 mm).
- **D-11:** The pack in the enclosure is the Kubii 3000 mAh (8 x 50 x 60 mm, vendor size; measured 8 x 60 x 50 mm, 49 g).
- **D-12:** Everything (shim, tray, lid, stand) is centred on the mat opening, not on the screen active area (owner, 2026-11-18).

### Claude's Discretion
- Structure of the plans, the measurement sheet and the assembly note; how to split owner steps into checkpoints; file names under `hardware/`.

### Deferred Ideas (OUT OF SCOPE)
- Printer purchase (X2D Combo): revisit after the first fit.
- Adapting the displayed image to the 140 x 99 mm mat window (server/rendering, not this phase; needs its own phase or seed).
- Identity label with device identifier / pairing code (SEED-014, v1.4).
- 13.3 inch enclosure, series production method and cost (SEED-015).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENC-01 | The second-hardware frame has a printed rear enclosure (tray, lid with wall hooks, loose stand plate, centring shim) that fits an IKEA RÖDALM 13 x 18 cm frame, hangs on a wall and stands on furniture, keeps USB-C, switch and buttons reachable, does not degrade the Wi-Fi signal, and is documented and validated by the owner. | Fit-clearance and coupon strategy (sections 1, 8); screw/insert and magnet findings (2, 3); battery safety checklist (4); Wi-Fi protocol with a defensible statistic (5); hook and stand tests (6); frame variation checklist (7); divergences and decisions (below). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Code, identifiers, comments, docstrings, docs and commit messages in English. (Hardware docs under `hardware/` follow this; owner-facing chat is French per D-02.)
- No plan, ticket, decision, review or phase IDs in code comments (`scripts/check_comment_history.py`). This phase touches no code, but the same rule is applied to the prose of the hardware documents: do not cite "D-07" or "Plan 04" inside `hardware/*.md` (the current plans already say "write in plain prose, no plan or decision IDs" for the validation document).
- GSD workflow enforcement: repository edits go through a GSD command. This research only writes the RESEARCH.md.
- Behaviour-over-source rule for tests: no pytest may read `.planning/`. This phase adds no tests; verification is by owner report. Plan `<automated>` greps are run by the GSD verifier, not pytest, but see Pitfall 9 about vacuous greps.
- `hardware/` documents keep the "measured vs design value" table style of `hardware/SECOND-HARDWARE-MEASUREMENTS.md`.

## Summary

The design is further along than the plans say. The owner reworked it in Blender on 2026-11-18/19 (one loose 20 degree stand plate, 132.0 x 182.0 mm plates, 1.0 mm shim, tab pads, screw lugs, notched landscape hook, battery pocket moved) and sliced it in Bambu Studio 2.9.1.70 for a P2S (PETG Basic, 0.20 mm, 3 walls, 20 % grid, textured PEI, no supports). Slicer figures (read by the owner): tray 56.29 g / 1 h 32, lid 51.56 g / 1 h 22, stand + shim 11.70 g / 29 min, about EUR 1.67 of filament in total. Nothing is printed. Plans 03 to 05 were written when the assumption was "send files to a print service, black PETG, hinged stand, 132.6 mm plates" and must be rewritten around a short, cheap, local print-measure-adjust loop on the owner's workplace printer.

What matters most for planning, in order: (1) the whole first set costs under two euros of filament and about three and a half hours of printer time, so the cheap move is not "coupons instead of parts" but "print the 1.0 mm shim first (same 132 x 182 footprint, about 15 to 20 minutes) and use it as the rebate/warp/shrinkage gauge on all five frames", then the tray, then the lid; small coupons are only needed for features that cannot be judged from the big parts (M2 pilot ladder, magnet pocket ladder, 0.4 mm hook ridges). (2) Three repository facts contradict the design assumptions: the IKEA frame is fibreboard with paper foil and a polystyrene front sheet (not wood and glass), so the screw lugs and the "wood edge" are model assumptions on a weaker material; the IKEA page lists a mount opening of 14 x 9 cm while the owner reads 140 x 99 mm (99 versus 90 needs a recheck because D-09 and D-12 centre everything on that opening); and heat-set inserts are not a drop-in fallback for the 4.0 mm standoffs and 3.2 mm lid walls. (3) The 20-wake / 3 dB Wi-Fi test is too weak as written: one integer RSSI snapshot per wake, no stated variance, a point-estimate comparison of two medians with a standard error of roughly 1 dB or more, and a confound (time drift). Replace it with an interleaved A-B-A-B design, a bootstrap confidence bound on the difference of medians, and run the baseline now, before the enclosure exists.

**Primary recommendation:** Keep five plans but rewrite 02 (close out and reconcile the decisions), 03 (a numbered print-measure-adjust loop starting with the shim gauge and three small coupons, with a clearance table that has a column per round), 04 (split mechanical/safety validation from a longer interleaved Wi-Fi run whose baseline starts immediately) and 05 (unchanged in intent, stale "cut the mat" and "glass" removed). Every number stays "design value, not measured" until the owner reports it.

## Architectural Responsibility Map

Physical project, so the "tiers" are mechanical and electrical owners rather than web tiers.

| Capability | Primary owner | Secondary | Rationale |
|------------|--------------|-----------|-----------|
| Centring the screen behind the mat | Shim (1.0 mm) | Tray outer size in the rebate | Shim locates the panel; tray locates the shim in the rebate; D-12 says centre on the mat opening |
| Carrying the frame mass on a wall | Lid hook rail (printed PETG) on a wall screw | Tab pads + friction on the four metal tabs hold frame to cassette | The hook hangs the cassette; the frame hangs from the cassette by tab friction (audit F-02, force unmeasured) |
| Holding the lid shut | Four M2 self-tapping screws into tray bosses | — | Only screw joint in the design; reopened for battery service |
| Holding the stand plate when stored | 2 x 2 magnet pairs (6 x 2 mm) | Stop walls and guides | Magnets only need to carry a plate of about 10 g |
| Wi-Fi reception | EE04 FPC antenna (2.4 GHz, bundled, 2.9 dBi per Seeed kit page) on a block 7 mm from the screen | Enclosure geometry (PETG 1.2 to 1.6 mm walls), distance to LiPo | Antenna moved above the board; behaviour unknown until measured |
| Battery safety | Protected pouch cell (vendor-stated protection, not verified here) | Free space in pocket (0.5 mm sides, 1.8 mm foam), non-sealed enclosure, owner checklist | Enclosure must not pinch, crush or hide a swollen cell |
| Evidence of results | Owner reports with date/method | `hardware/ENCLOSURE-*.md` tables | D-01 honesty rule |

## Standard Stack

No software packages are installed in this phase (**Package Legitimacy Audit: not applicable; no npm/pip/cargo packages**). The "stack" is hardware, process and records.

### Core
| Item | Value | Purpose | Status |
|------|-------|---------|--------|
| Printer / slicer | Bambu Lab P2S (slice) or X1 series (decision text); Bambu Studio 2.9.1.70 | Prints PETG parts | Slice settings read by owner 2026-11-19 (owner-reported). Which machine will physically print is not recorded. |
| Filament | Bambu PETG Basic profile, 0.20 mm Standard, 3 walls, 20 % grid, no supports | All four parts | Brand reference, colour and spool not yet recorded |
| Build plate | Textured PEI (as sliced) | PETG adhesion | Decisions table still says "open"; stale |
| Fasteners | M2 self-tapping pan-head, pilot 1.7 mm (vertical), through 2.4 mm | Lid, board standoffs | Assortment of 800 "ordered" per design record; arrival not reported |
| Magnets | 6 x 2 mm neodymium, pocket 6.2 x 2.2 mm | Stand storage | Lot of 100 "ordered" per design record (the brief says "to buy"); arrival not reported |
| Measuring tools | Tape measure only so far (resolution about 1 mm), kitchen scale, multimeter | Measurements so far | **A calliper has never been used on this project** (ENCLOSURE-MEASUREMENTS.md). Every fit decision below needs one. |

### Supporting
| Item | Purpose | When |
|------|---------|------|
| Calliper (0.02 to 0.05 mm) or borrowed workplace one | Plate size, rebate on 5 frames, hole diameters, magnet size, tab height | Before round 1 (blocking for a rigorous clearance strategy) |
| Phone inclinometer app / spirit level | Hanging tilt, stand tipping margin | Validation |
| Strip of paper, feeler-like shims (printer paper about 0.1 mm) | Shim/mat gap check | First fit |
| Cyanoacrylate glue (small bottle) | Magnet retention if press fit fails | Only after a pocket test (and never near the polystyrene front sheet: CA fumes can fog it, general knowledge [ASSUMED]) |
| Rubber/silicone foot pad | Stand foot slip | If the stand slides |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| M2 self-tapping into PETG | Heat-set inserts (M2 hole about 3.0 to 3.2 mm, range from suppliers) | **Not a drop-in fallback**: standoffs are 4.0 mm OD with 0.8 mm pilot floor, lid corner wall is about 3.2 mm around a 1.7 mm pilot. A 3.0 to 3.2 mm insert hole leaves no wall in a 4.0 mm boss. Needs boss redesign (about 5 to 6 mm OD; my rule of thumb, not from a source). |
| Screws in lid | Tool-free latch | Out of scope; battery is a service item, not a daily one |

**Installation:** none.

## Architecture Patterns

### System Architecture Diagram (process flow, not file listing)

```
Owner tools (calliper, tape, scale, multimeter)
   |  measure 5 frames: rebate L/W at 3 places/side, corner radius, depth, mat window, tab height
   v
ENCLOSURE-MEASUREMENTS.md  --(design value vs measured)-->  Blender model (owner's local session)
   |                                                           |
   |                                                           v  export STL per part, version-stamped
   |                                              Bambu Studio (P2S, PETG Basic, textured PEI)
   |                                                           |
   |        Round 1: shim (132x182x1.0) + coupon plate (M2 ladder, magnet ladder, hook ridge)  ~30-40 min
   |        Round 2: tray (1h32)  ->  Round 3: lid (1h22) + stand (29 min with shim)
   |                                                           v
   |                                            Printed parts -> owner measures (calliper)
   |                                                           v
   +--> ENCLOSURE-TEST-PRINT-LOG.md: clearance table, one column set per round, adjustment ledger
                                  |  fit result? --no--> adjust CAD (old->new->reason) -> re-export -> next round
                                  v yes
        Dry fit with battery UNPLUGGED -> lid-open electrical check -> connect battery
                                  v
   Validation: mechanical checklist  ||  Wi-Fi A-B-A-B (baseline A starts early, in parallel)
                                  v
   ENCLOSURE-ASSEMBLY.md + BOM.md + SEED-014 (owner-reported values only)
```

### Recommended file structure (no change in names)
```
hardware/
├── ENCLOSURE-3D-DESIGN.md        # design record (needs a stale-text sweep, see divergences)
├── ENCLOSURE-MEASUREMENTS.md     # owner readings
├── ENCLOSURE-PRINT-ORDER.md      # decisions, design changes, slice check
├── ENCLOSURE-AUDIT.md            # findings F-01..F-16
├── ENCLOSURE-TEST-PRINT-LOG.md   # NEW (plan 03): rounds, clearance table, adjustment ledger
├── ENCLOSURE-VALIDATION.md       # NEW (plan 04)
├── ENCLOSURE-ASSEMBLY.md         # NEW (plan 05)
└── cad/export/                   # skypane_{tray,lid,stand,shim}.stl (+ skypane_lid.3mf, unlisted)
```

### Pattern 1: Shim as fit gauge (recommended, my reasoning)
**What:** The shim (132.0 x 182.0 x 1.0 mm, 208 triangles, about 15 to 20 min of the 29 min "stand and shim" plate [estimate from slicer total]) shares the tray/lid footprint. Printing it alone first tests, for the price of a few grams: rebate fit in each frame, shrinkage, elephant foot, plate flatness, corner relief, the screen opening and the mat gap (paper strip).
**When to use:** Round 1, before tray and lid.
**Acceptance (design values; owner may adjust):** printed length and width measured at 3 places each; drops into the rebate of every one of the 5 frames without force; no rocking on a flat table beyond 0.5 mm at any corner (feeler of 2 to 5 sheets of paper); screen drops into its opening with visible, even margin.

### Pattern 2: Iteration ledger, one column set per round
**What:** The clearance table has columns `Round 1 measured | fit | Round 2 measured | fit ...` and a ledger `# | part | dimension | old | new | reason | round`. Each STL export gets a version stamp (`skypane_tray_r2.stl` or a date in the Files table) plus the Blender save date, so a printed part can be tied to the exact export.
**Why:** The current export lists "exported 2026-11-18" but the engraved board indications are dated 2026-11-19; nothing proves the STL matches the final blend. A version column removes the doubt.

### Pattern 3: Battery is the last thing connected
Dry fit (rounds 1 to 3) with the pack unplugged and, for the first closing, with the pack replaced by a dummy block of the same size (8 x 50 x 60 mm foam/cardboard, or the real pack unplugged and handled by its edges). Connect the battery only after the lid-open electrical check (polarity by multimeter, cable routing, nothing pinched).

### Anti-Patterns to Avoid
- **Filling a "measured" cell from a model value or from a calculation:** the slice table already mixes (thinnest wall computed in Blender, not read from Bambu Studio; the file says so, keep that note).
- **Using a tape measure to resolve 0.3 mm:** the tape has about 1 mm resolution against 0.4 to 0.5 mm design clearances.
- **One big print then one big adjustment:** change a limited number of dimensions per round so each fit result is attributable.
- **Changing filament/printer between rounds without recording it:** clearances are filament- and machine-specific (Bambu wiki: auto compensation tuned for Bambu filaments, drying matters).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hole-size compensation | A custom per-hole offset scheme in Blender | Bambu Studio "XY hole/contour compensation" (positive = looser, negative = tighter) after a ladder coupon | [CITED: wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation, via search summary; page itself returned HTTP 402 to a direct fetch] |
| Shrinkage compensation | Scaling STLs in Blender | Per-filament "Shrinkage" in Bambu Studio (default 100 %; community values for Bambu PETG about 99.6 to 99.8 %, forum/blog level) | Keeps CAD true to nominal; applies per spool |
| Magnet pocket sizing | Guess from datasheet | A pocket ladder (6.1 / 6.2 / 6.3 / 6.4 x 2.1 / 2.2 / 2.3) and a calliper reading of the real magnets (vendors state up to 0.4 mm dimensional error, forum claim) | Forum thread: [forum.bambulab.com/t/magnets-in-prints/76022] |
| Wi-Fi statistics | Eyeballing two medians | Bootstrap CI of the difference of medians (or Mann-Whitney / Hodges-Lehmann shift) in a throwaway local script, nothing committed | Snapshot RSSI is noisy (section 5) |
| Battery protection | Adding any circuit | The pack's own protection, verified by the owner's checks | Vendor-stated, "not independently checked" (BATTERY-MODEL.md) |

**Key insight:** The only parts of this phase that need engineering judgement are fit tolerance and Wi-Fi/battery risk. Everything else is bookkeeping; the plans should spend their words on the ladder coupons, the ledger and the acceptance criteria, not on new designs.

## 1. FDM PETG tolerances and the 132.0 x 182.0 plate strategy

**Evidence quality:** forum and maker-site level only. No authoritative PETG/Bambu tolerance table exists in what I could reach. Say so in the plans.

- **No verified clearance number.** Searches found no source giving a verified 0.2 to 0.5 mm per side for PETG on Bambu printers; a MakerWorld tolerance test (hex fits 0.00 to 0.40 mm) exists and its instructions say to adjust XY compensation from the result [CITED: makerworld.com/en/models/2236614-tolerance-test, search summary, LOW]. Bambu wiki: XY hole/contour compensation exists; positive = looser, negative = tighter; the Auto Circle feature is tuned for Bambu filaments and drying affects it [CITED: wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation, MEDIUM via search summary; direct fetch returned 402]. A Bambu forum thread on PETG HF dimensional accuracy says XY compensation "doesn't cut it" for all hole sizes and suggests separate shrinkage calibration [CITED: forum.bambulab.com/t/improving-dimensional-accuracy-on-bambu-lab-h2d-with-petg-hf/159931, LOW].
- **Shrinkage.** Published PETG shrinkage figures disagree: 0.3 to 0.8 % (forum), 0.8 % (3dprinterly), Bambu PETG community measurements 0.2 to 0.4 % (99.6 to 99.8 % in a blog) [CITED: forum.bambulab.com/t/dimensions-are-incorrect/87066; 3dprinterly.com/pla-abs-petg-shrinkage-compensation-in-3d-printing/; stacksheriff.com/3d-printing/bambu-studio-shrinkage-compensation/; LOW]. A forum user reports a 300 mm PETG part at 299 mm. My arithmetic on the design plate: 0.2 to 0.4 % gives 0.26 to 0.53 mm on 132 mm and 0.36 to 0.73 mm on 182 mm; 0.8 % would give 1.06 and 1.46 mm. So shrinkage makes the plates smaller than nominal (more clearance), while first-layer flare (elephant foot) makes the bottom edge larger. Expect both in the same part.
- **Warp.** Large flat PETG parts lift at corners; a forum report says a first-layer peel of 0.1 mm grows to 5 mm or more at the end (P2S thread) and suggests slow first layers, glue stick, brim ears [CITED: forum.bambulab.com/t/p2s-warping-issue-from-first-print/212662; 3dprinterly.com/9-ways-how-to-fix-petg-warping-or-lifting-on-bed/; LOW]. Audit F-12 already notes this. The 1.0 mm shim and the 1.5 mm lid are the most warp-prone (thin, large). Check flatness on a flat table; a lid that rocks will not sit on the tray walls.
- **Elephant foot.** Slicer compensation values of 0.1 to 0.2 mm are suggested; check the current value first because a Bambu forum user had it already at +0.15 and it hurt [CITED: 3dprintingspace.com article via search summary; LOW]. Alternative that needs no slicer change: a 0.2 to 0.4 mm 45 degree chamfer on the first-layer outer edge of the plates in CAD (audit F-01 already lists this "first-layer compensation or small chamfer"; it is **not recorded as done**).
- **Textured PEI** gives a rough bottom skin; lid underside (printed face down) and tray floor will be textured. The lid underside has only 0.41 mm clearance to the board's tallest part (audit F-08), and surface roughness can eat part of it. [ASSUMED effect size; verify at fit.]
- **Is 132.0 x 182.0 inside about 133 x 183 a sane strategy?** Yes as a first guess, with one caveat. Nominal clearance is 0.5 mm per side against the tape reading (133 x 183) and 0.7 per side against the IKEA model (133.4 x 183.4). The tape has about 1 mm resolution and the project has measured exactly one frame, so the real worst case across five frames could be about 0 mm (rebate 132.0) to over 1 mm per side. Shrinkage helps (smaller plate), flare hurts. My recommendation (design value, not a source): after a calliper survey of the five rebates, set plate size = smallest measured rebate at its narrowest point minus 0.8 mm (0.4 per side), then verify on the printed shim. If the survey shows the rebate varies more than about 1 mm frame to frame, the plate cannot be both snug and universal; then accept a loose fit and let the tab pads and screw lugs locate it. Also add about 1 mm corner relief on the plate corners because the rebate corner radius of the real frame has not been measured.
- **Cheap coupon strategy** (print time is about 30 to 40 min for all):
  1. Shim alone (gauge, see Pattern 1).
  2. One coupon plate (about 60 x 60 mm, 3 to 4 mm tall, vertical holes as in the real parts): M2 pilot ladder 1.6 / 1.7 / 1.8 / 1.9 mm in a 4.0 mm boss (and one with a 0.8 mm floor), magnet pocket ladder (see 3), and a 15 mm section of the hook rail with the 0.4 mm ridges and a real wall screw.
  3. Then tray, then lid.
  A coupon is cheaper than a full lid only in time (about 15 min versus 1 h 22), not in material (a full lid costs about EUR 0.72 per the slicer). Say that plainly; do not over-engineer.

**Confidence:** LOW to MEDIUM. All numbers are starting points for the ladder, not specs.

## 2. M2 self-tapping screws in printed PETG

- **Pilot diameter.** The Bambu forum screw-hole guide gives, for Bambu's own BT2 self-tapping screws (pitch diameter 1.62 mm), PETG Basic: 1.65 mm vertical, 2.00 mm horizontal; PETG HF: 1.60 vertical, 1.95 horizontal. For plain M2 machine screws it gives PETG Basic 1.74 mm vertical and 2.10 mm horizontal [CITED: forum.bambulab.com/t/how-to-design-screw-holes-for-3d-printing/217352, fetched 2026-11-19]. The design's 1.7 mm vertical pilot is consistent with this (MEDIUM). **Orientation matters**: a hole that is horizontal in the print comes out noticeably larger (about 0.3 mm) than a vertical one in that guide. The 2.2 mm "horizontal hole" in the screw lugs is a through hole for a screw into the frame edge, so that is a different case (clearance, not a thread).
- **Engagement and torque.** Same source: BT2 (M2-class) wants at least 4.0 mm engagement and about 0.15 N·m; chamfer the hole entry 45 degrees; wall modifier about 0.8 mm wider than the hole; 2 walls default, 3 walls for the larger screw; do not overtighten by hand [CITED: same, MEDIUM, a Bambu-community post not Bambu engineering]. Design check: lid corners have a 7 mm pilot (good, above 4 mm). Board standoffs: M2 x 4 mm at most with a 0.8 mm pilot floor, so engagement is at most about 3.2 mm: **below the 4 mm guidance**. Plan a pull/strip test on a standoff coupon (a board that is rarely removed tolerates this).
- **Boss wall.** The guide gives no wall in millimetres; Hubs says "minimum wall around a threaded hole should match the fastener diameter" (M5 needs 5 mm wall; an M2 reading would be 2 mm) [CITED: hubs.com/knowledge-base/how-assemble-3d-printed-parts-threaded-fasteners/, MEDIUM]. The design has lid corner wall 3.2 mm (passes) and standoffs 4.0 mm OD with 1.15 mm wall around a 1.6 to 1.8 mm pilot (fails this rule of thumb; one forum rule gives OD at least 2 x screw, i.e. 4 mm, borderline). Flag; the ladder coupon should include the real standoff geometry.
- **Re-use.** Hubs: self-tapping is "not suited for applications where parts will regularly be assembled/disassembled" [CITED: Hubs, MEDIUM]; Bambu sells BT2 and says its screws can be installed and removed multiple times (vendor claim, no count) [CITED: eu.store.bambulab.com BT2 pages, search summary, LOW]; McMaster says thread-forming M2 screws can be reused "a few times" [CITED: mcmaster.com listing, search summary, LOW]. **There is no published cycle count for M2 in PETG.** Recommend a design-value acceptance of 5 remove/insert cycles per lid screw with no loss of grip (owner may adjust), recorded as a count by the owner.
- **Which screws are bought.** The design record says "M2 self-tapping pan-head, assortment 4 to 20 mm" (800 pieces ordered). Generic sheet-metal-type tapping screws have a coarser thread than Bambu BT2; the pilot ladder must use **the bought screws**, not BT2 data. [ASSUMED thread form until the owner reads the label.]
- **Heat-set insert alternative.** CNC Kitchen: iron 10 to 20 degrees above print temperature (about 245 degrees C for PETG), blind hole about 1 mm deeper than the insert, melt to about 90 % depth then press the rest [CITED: cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey, fetched]. M2 hole sizes from suppliers conflict (2.6 mm for a 2.8 mm OD insert; 3.0 to 3.2 mm typical; 3.15 mm in one table) [CITED: accu-components.com insert chart, Prusa/Albany pages, search summary, LOW]. Test the real insert; holes print smaller than CAD [CITED: CNC Kitchen]. **Conclusion for planning:** keep self-tapping screws for rounds 1 to 3; record that inserts need a boss redesign, so "insert fallback" in D-06 is a redesign, not a swap. Decide after the cycle-count result.

**Confidence:** MEDIUM for the pilot size (agrees with the design), LOW for reuse and boss walls.

## 3. Magnets in printed pockets (6 x 2 mm neodymium)

- **Pocket size.** Forum and maker sources add 0.15 to 0.4 mm to the magnet diameter and thickness (6.3 x 2.3 suggested in one guide; 6.2 mm for a 6 x 3 mm in another) [CITED: forum.bambulab.com/t/magnets-in-prints/76022; kingroon.com/blogs/3d-printing-guides/how-to-embed-magnets-into-3d-prints, via search summary, LOW]. The design pocket 6.2 x 2.2 mm is inside this range. A forum poster warns stated magnet size can be off by up to 0.4 mm, so measure the real magnets [CITED: Bambu forum thread above, fetched]. Print a ladder (6.1 to 6.4 diameter, 2.1 to 2.3 depth), vertical axis.
- **Glue versus press fit.** One 6 x 2 mm user press-fit without glue; another needed glue because a magnet nearby can pull it out; another advises embedding rather than adhesive [CITED: Bambu forum thread, fetched, LOW]. Use cyanoacrylate if glue is needed; manufacturers' guide says avoid "plastic-specific" glues (search summary). For this application (a 10 g plate, stored loose) the retention requirement is small. Design acceptance (design value): the magnet stays in its pocket when the plate is pulled off 10 times by hand.
- **Skin thickness / pull force.** Forum advice: keep at least 3 layers over an embedded magnet; thicker walls weaken the hold, stay under about 1.5 mm. The design's 0.8 mm skin (3 mm boss minus 2.2 mm pocket) is 4 layers at 0.2 mm. **No source gives a pull force for a 6 x 2 mm magnet through a printed skin; I found none.** The strength-only unknown does not matter here (10 g plate) but the owner should note the observed hold on the first stand.
- **Polarity marking.** Design record says "stick each pair face to face first". Add: mark the exposed face of each magnet with a permanent marker dot before gluing, and keep the two bosses and the two plate pockets in the same orientation (a reversed magnet cannot be reversed after glue). Verify attract, not repel, with the plate in its stored position before gluing the second magnet of the pair.
- **Effect on the electronics (flag as unknown, low risk).**
  - The original ESP32 hall sensor was removed from ESP-IDF 5.0 support [CITED: docs.espressif.com migration guide 5.x peripherals, via search summary]. I found no statement that the ESP32-S3 has one; I believe it does not [ASSUMED]. The firmware (ESP-IDF 5.3.1) is not claimed to read any hall input.
  - EE04 has no reed switch or hall sensor listed on the pages I reached (search results); not confirmed from the schematic [UNVERIFIED].
  - Static magnet effect on Spectra 6 e-ink, pouch cell or its protection board: I found no source in either direction. My expectation is none for a 6 x 2 mm magnet at a few millimetres, but that is [ASSUMED]. Cheap check: with the board powered, hold a magnet on the lid back at the storage position and trigger a refresh; look for a changed image or reset. The stand storage bosses are at x = 31 mm, y = 11 and 39 mm on the lid back, which may sit over the battery pocket (centre y = -11.65, 60 mm long if the 60 mm side runs along y: spans about -41.7 to +18.4); the coordinate frames of tray and lid were not cross-checked here. [UNVERIFIED]
- Neodymium loses strength above about 80 degrees C (maker sources); irrelevant at room temperature.

**Confidence:** LOW to MEDIUM; unknowns stated.

## 4. LiPo (3.7 V 3000 mAh, 8 x 50 x 60 mm pouch) in a closed enclosure

What is known (and what is not):

- **Repository facts (HIGH):** pack is the Kubii 3000 mAh, listing says protected, "Not independently checked" (BATTERY-MODEL.md line 167), Kubii page showed "Rupture de stock" on 2026-11-01, so the owner's pack may not be re-orderable (SECOND-HARDWARE.md). The EE04 charges over USB-C with an on-board charger and a JST 2.0 power switch (Seeed wiki) [CITED: wiki.seeedstudio.com/epaper_ee04/, search summary]. Its charge current is not documented in the repo (the EE02 pages conflict: 50 or 100 mA, a forum says about 110 mA, PACK-ACCEPTANCE.md). At 100 mA against 3000 mAh the charge is about C/30 (my arithmetic), which is gentle.
- **Pouch cells and swelling (MEDIUM):** Battery University: swelling pressure "can crack a battery cover open and in some cases break the display or electronic circuit"; designers should "make provision for some expansion", lay cells flat, shield from physical strain, keep the compartment free of sharp points; do not puncture a swollen cell near fire or heat [CITED: batteryuniversity.com/article/pouch-cell-small-but-not-trouble-free, fetched]. Swelling that appears later is attributed mostly to faulty manufacturing there. Pouch cells themselves lack CID/PTC devices; the protection board does overcharge, over-discharge and short-circuit protection (patent texts via search, LOW).
- **What I did not find:** a source for "do not pinch", crush limits or unattended-charging rules. Standards exist for cells and packs (for example IEC 62133, UL 2054 were mentioned in search results) but they certify the vendor's pack; I have no content from them and cite none here. Do not invent numbers.
- **Design observations (from the repo):** pocket has 0.5 mm side clearance and a 1.8 mm foam layer (design values); lid clearance to the cell is 1.75 mm; the service bay and the USB-C notch are open on the wall side, so the enclosure is **not sealed**: gas from a failing cell has a route out. The foam is "adhesive foam" (to confirm what the owner uses).
- **Heat:** in deep sleep nothing active produces meaningful heat; the only heat source is USB charging. [ASSUMED]; PETG glass transition is about 80 degrees C [ASSUMED], so a charged-while-hanging frame is far from it unless in direct sun behind glass.
- **Prudent owner checklist (what I recommend the plan puts in; each item is owner-reported, never Claude-marked):**
  1. Before first fit: read the pack label (capacity, protection mention), compare with the order; polarity by multimeter on the extension cable (already in audit F-07 and PACK-ACCEPTANCE.md).
  2. Dry fit with the plug disconnected; no part of the cell touches a screw tip, standoff, sharp print edge or the lid underside under load; cables not pinched by the lid or the rebate; JST socket not loaded sideways. Photograph the routing.
  3. Lid-open power-on check before closing (does the board boot; is the battery voltage plausible).
  4. Check the cell visually and by pressing the cell face gently with a finger (not tools) through the lid-open tray for any puffiness every time the lid is opened and at a fixed interval (design value: monthly at first, owner may adjust). Swelling means: disconnect, do not charge, do not puncture, take it out (Battery University advice above).
  5. Leave the cell free to expand about 1 to 2 mm in thickness (the 1.8 mm foam and 1.75 mm lid gap are design values; confirm there is still room after closing).
  6. First full charge in the enclosure: attended, and check the board/cell is not warm to the touch (same as PACK-ACCEPTANCE check 4; charge current stays "unverified" in the record).
  7. Know where the power switch is (service bay) so the battery can be cut without a tool.
- **Tool-free opening?** Recommendation: **no tool-free lid for v1.** The lid is a service item, the power switch and USB-C port are reachable through the service bay without opening it, and a tool-free latch would be a redesign. The checklist above only needs the lid opened with a PH0/PH00 driver. Reconsider only if the owner finds the pack must be swapped often. This is the planner's call and the owner's; stated as a recommendation.

## 5. Wi-Fi through the enclosure, and a better test than 20 + 20 / 3 dB

**What is known (LOW to MEDIUM, no PETG measurement found):**
- I found **no measured dB figure for PETG at 2.4 GHz**. One BLE chamber test found ABS added about 0 dB [CITED: novelbits.io RF chamber episode, via search summary, LOW]; an RF design post says ABS is slightly worse than PETG and recommends 5 to 8 mm clearance between antenna and plastic and notes a few millimetres of plastic in the near field can shift resonance [CITED: community.aisler.net co-design thread, LOW]. Batteries, large PCBs and metal near an antenna detune it (nextpcb guide, LOW).
- Relevant geometry: antenna block 7 mm from the screen (a conductive stack), antenna 2.2 mm under the lid, near the LiPo pocket, with the metal tabs and a wall behind. The signal path is mostly out the lid/wall side. I could not find a prediction; **measure it**.
- The frame's own RSSI: `fp_wifi_rssi()` returns the AP RSSI from `esp_wifi_sta_get_ap_info` as an integer dBm, or **0 on failure**, and it is sent as `X-Rssi` on every display call (firmware/main/wifi.c line 241, api_client.c lines 246 to 259). So: one integer snapshot per wake, 1 dB resolution, and zeros are failures, not data.

**Why 20 + 20 and 3 dB is weak (my analysis):**
- One snapshot per wake, fading and AP behaviour make wake-to-wake spread of about 2 to 4 dB plausible [ASSUMED; measure it]. With SD 3 dB and n = 20 per arm, the standard error of a difference of means is about 0.95 dB and of medians roughly 1.2 dB. A "median not worse than 3 dB" rule on point estimates then passes a true 3 to 4 dB loss often and fails a true 0 dB change sometimes. My arithmetic, to be re-run with the real SD.
- Runs in sequence are confounded by time of day, other users on the AP, channel changes, temperature and battery state. Moving the frame to fit the enclosure changes position slightly.
- Snapshots are autocorrelated and not Gaussian; ANOVA assumes independence [CITED: MDPI Applied Sciences 13(6) 3900 via search summary, LOW]. A median plus bootstrap avoids the Gaussian assumption.
- Quantisation at 1 dB limits resolution; a 1 dB difference is inside the noise anyway.

**Recommended protocol (plans 04):**
1. **Run the baseline now.** The bare frame can be measured today, before any print exists, at the exact spot and orientation where it will later hang. Record the spot with tape marks and a photo, the access point name, and whether USB is plugged. Repeat the baseline once after the enclosure runs (A2) to expose access-point drift.
2. **Interleave:** A (no enclosure), B (enclosure), A, B (or B, A, B), each block at least 15 wakes, same time of day, same battery state class (say how it was charged; RSSI at the receiver is not directly a function of TX battery voltage but a low battery could change behaviour; keep it fixed anyway [ASSUMED]). At the 300 s cadence of the live frame this is about 75 minutes per block (the second hardware's cadence is set on the server and is not recorded in the files I read; confirm it); total about 5 hours for four blocks of 15.
3. **Discard** the first wake after moving the frame, and every row with `rssi == 0`. Report n kept, min, median, IQR, max per block.
4. **Verdict:** compute the difference of medians (all B minus all A) and a bootstrap 95 % interval in a throwaway local script (not committed). Rule (design value): pass if the lower end of the one-sided interval is above -3 dB, which means the observed difference has to be about no worse than -1 dB for an SD of 3 dB at n = 30 per arm (my arithmetic: -3 + 1.645 x 1.2 about -1 dB). If the owner wants the weaker original rule (point medians within 3 dB), keep it as a second line but report the interval as well. Say which was applied.
5. **Isolate the cause only if it fails:** an extra block "enclosure open, lid off" separates PETG from the antenna move/LiPo; a U.FL extension is already the documented fallback (audit F-06).
6. Do not extrapolate or fill wakes; fewer than the planned n means "not done".
7. Use the header `X-Rssi` only; do not write the export token or access point password into any file (existing threat T-69-07).

**Optional:** a phone Wi-Fi analyser app reading at the frame's spot gives a sanity floor on the access point strength; it does not measure the frame's antenna.

## 6. Wall hanging and stand stability

- **Load.** From the owner's masses (frame 173 g, screen 36 g, battery 49 g, board 20 g) plus printed parts, the design check gives 328 to 403 g total, about 3.2 to 4.0 N (my arithmetic; weight = mass x 9.81). The audit's F-02 text quotes "5.8 N" for the hook roof load; that is about 590 g and is not reconciled with 328 to 403 g (maybe a safety factor). Ask the owner to say which.
- **Wall screw/nail head.** The design record gives screw head up to 9.5 mm, shank 3.0 to 4.3 mm, 2.1 mm or more under the head. The wall type is unknown, so no load rating can be stated; a 400 g load on a properly plugged screw is small, but I cannot give a rating without the wall. IKEA's own product page recommends an ALFTA adhesive hook for this frame family (the stock frame package is 0.25 kg) [CITED: ikea.com/gb/en/p/roedalm-frame-black-10548872/, fetched]; the assembled cassette weighs more than the stock frame, so check the chosen hook's rating independently. A single hanging point also means the frame can swing; the notched rail is the level adjustment.
- **0.4 mm ridges in PETG.** The 12 V notches (2 mm pitch, 0.6 mm deep, 0.4 mm ridges) are one extrusion line wide with the design's 0.42-ish line width, so they are at the slicer's thin-wall limit; the slice check lists 0.4 as the lid's thinnest wall. Risks: the slicer may drop or merge them, layer lines are loaded across, repeated lifting wears them. [ASSUMED mechanism.] Test on a coupon section with the real wall screw: hang a mass of about 1 kg (about 2.5 times the frame, design value) for 24 hours, then check by calliper that the notch bottom has not moved and the ridges are intact; lift one notch and drop back 30 times.
- **Creep.** I found **no published long-term creep dataset for a PETG hook at room temperature.** What exists: academic work on printed PETG creep modelled by time-temperature superposition and showing infill and nozzle temperature matter (UTS studies, via search summary), a vendor blog (Qidi) saying PETG hooks hold better than PLA, a forum thread saying all FDM materials creep (LOW) [CITED: opus.lib.uts.edu.au; qidi3d.com/blogs/print-lab/pla-petg-heavy-wall-hook-material-guide; forum.bambulab.com/t/pla-vs-petg-hf-deformation-under-load/212834]. Recommended approach: measure, not predict. Mark the hook with a pencil line against the screw head and photograph/calliper it before and after a week hanging (design value; owner decides). If the wall is warm (radiator or sun), say so.
- **Screw lugs and fibreboard.** IKEA lists the frame as "fibreboard with paper foil", the front as polystyrene, the mat as acid-free paper [CITED: ikea.com/gb/en/p/roedalm-frame-black-10548872/, fetched]. The design (audit, print order) says "wood", assumes a vertical rebate wall between z 14 and 22 mm and screws "about 10 mm into the wood". A 2 mm screw into a fibreboard edge holds poorly versus solid wood (general knowledge [ASSUMED]). Treat the lugs as an anti-shift aid, not a load path; the real security is the tab friction test (audit F-02) before hanging with the frame's glazing.
- **Stand tilt test the owner can do.** Frame on the stand plate on a plank. Raise the back edge of the plank slowly while a phone inclinometer reads the plank angle; note the angle at which the frame starts to tip forward. The model predicted margins of 7.5 degrees (landscape) and 10.5 degrees (portrait), or 5.4 and 8.9 if the mass centre is 3 mm deep (audit F-10, all model values). Acceptance (design value): tips only at 5 degrees or more of plank tilt, does not slide at 5 degrees on the owner's actual surface, and survives a gentle finger tap on the top edge. Add a foot pad if it slides. Pulling the USB cable can topple it: mention in the assembly note.

## 7. IKEA RÖDALM 13 x 18 cm: what is known publicly

[CITED: ikea.com/gb/en/p/roedalm-frame-black-10548872/ (fetched; the product number shown there is the white 105.488.72, same family), and ikea.gr / islas.ikea.es listings via search]
- Frame 20 cm high x 15 cm wide x 3 cm deep; mount (mat) opening 14 cm high x 9 cm wide; picture with mat 15 x 10 cm; without mat 18 x 13 cm. Materials: frame fibreboard with paper foil, front protection and inner frame polystyrene plastic, mat acid-free paper. Package 0.25 kg.
- **Not published:** rebate size and depth, tolerance, corner radius, tab strength, spring force, front-sheet thickness. IKEA instructions PDF exists on the page; I did not read it (a PDF might give a profile drawing; recommend the owner or the next session reads it).
- **Discrepancy to settle:** IKEA says the mat opening is 14 high x 9 wide (landscape: 140 x 90 mm); the IKEA 3D model gives 141.8 x 91.8 mm; the owner's tape reading is 140 x 99 mm (D-09). 99 versus 90 may be a reading or transposition error, or the owner may have recut the mat. Active area is 160 x 96 mm (vendor), so a 99 mm window shows 1.5 mm of border above and below while a 90 mm window crops 3 mm top and bottom; D-09 and D-12 depend on this number. Re-measure the window with a calliper before the image-adaptation work is specified.
- **Frame-to-frame variation:** no public data. Fibreboard frames with a paper foil vary in rebate width and in the thickness of the foil; the owner already expects variation (ENCLOSURE-MEASUREMENTS.md notes). **Survey of 5 frames (calliper):** rebate length and width at both ends and middle of each side; rebate corner radius or mitre gap; free depth to the wooden/fibreboard edge at four corners; tab count, height behind the back of the screen, width and position along each side (the audit says positions and a 15 mm height are reported by the owner for one frame); front sheet thickness; mat thickness and window size; outer size (audit F-15 says unmeasured); mass of the empty frame. Record all in one table with one column per frame and the design value in the first column.
- Also check that the frames are the same colour/series (black 105.488.67 per the design record) because the IKEA page shows other colours that may differ.

## 8. Process: a sensible physical-phase plan shape

**Principles (my recommendation):**
1. Replace "send files to a provider" with a **round** concept: Round N = print set, measure, fit, adjust, decide go/no-go. Maximum three rounds planned; a fourth needs a note.
2. Each round has a **pre-registered acceptance list** with numbers (all design values until the owner adjusts), a **measurement table**, and an **adjustment ledger** with old value, new value, reason, round.
3. Round order by cost of failure: (a) shim + coupon plate, (b) tray, (c) lid + stand. Gate each: do not print the lid until the tray's rebate fit and the standoff fits are reported.
4. One change set per Blender session; one STL export stamped with date and round; one commit per export so "which STL was printed" is traceable. (Right now the export commit and the design rework are in the same commit, and the files list says exported 2026-11-18; the engraved board indications are dated 2026-11-19. Ask the owner to confirm that the exported STL matches the final blend and that the slice used these files.)
5. Battery last.

**Clearance table to measure (design values, not measured; add "round 1/2/3" columns):**

| Item | Nominal (design value) | Tool | Acceptance (design value, owner may adjust) |
|------|-----------------------|------|-----------------------------------|
| Plate outer length x width (tray, lid, shim) | 132.0 x 182.0 | calliper, 3 readings per side | within 0.3 mm of nominal, flat within 0.5 mm; fits all 5 rebates, drop-in without force |
| Elephant foot / chamfer | 0 to 0.4 mm chamfer not in CAD | calliper at first layer vs layer 5 | step under 0.2 mm |
| M2 pilot in lid corner / standoff | 1.7 mm (vertical) | calliper, pin gauges or drill shanks | real screw drives in with firm resistance, no cracking, grips after 5 cycles |
| M2 through hole | 2.4 mm | calliper | screw passes without catching |
| Magnet pocket | 6.2 x 2.2 mm | calliper on real magnets and pockets | magnet pressed in by hand, stays on 10 plate pulls, or glued |
| Stop walls and stand plate | 0.5 mm clearance each side, walls 2.4 mm | calliper | plate drops in without binding, no wobble beyond 1 mm |
| Battery pocket | 0.5 mm sides, 1.8 mm foam thick | calliper, cell | cell in with foam, cable exits corner, free space after lid closed |
| Ribbon slot | 4 x 28 mm | ribbon trial | ribbon passes, no hard crease |
| Antenna block | 40 x 20 mm at x 12 to 52, y 65 to 85 | trial | cable reaches (46 to 47 mm route versus 50 mm cable), no strain |
| Lid to board clearance | 0.41 mm over battery socket | feeler or paper test | lid sits flat with mated plug |
| Shim to mat gap | mat back 0.1 mm above shim | strip of paper | paper slides with slight drag |
| Hook rail ridges and notches | 0.4 mm ridges, 0.6 mm deep, 2 mm pitch | calliper, loupe | ridges intact after 30 lifts and 1 kg load for 24 h |
| Tab pad height and tab contact | 15.0 mm design pad top, tab underside 15.0 to 15.4 | shake test | cassette does not slip when held vertical and shaken gently (audit F-02, F-04) |
| Screw lugs | 2.2 mm hole, head recess 4.2 mm | trial on 5 frames | screws start; mark failure as "fibreboard strips" |
| Engraved text 0.4 mm | 0.7 mm line | eye / loupe | legible |

**Round structure for the plans (recommendation):**
- 69-02 (rewrite as a short closeout): record decisions that are stale, reconcile the print order Decisions table, confirm STL vs blend freshness, add the calliper to the tools list, decide first-layer chamfer or elephant foot setting, record which printer will actually print. Owner checkpoints are replies, not work.
- 69-03: Round 1 (shim + coupon plate), Round 2 (tray), Round 3 (lid + stand). One log, one column set per round. Includes the five-frame survey as the first task (calliper). Includes the battery dry-fit rules.
- 69-04: split into (a) mechanical and safety checklist (cover hanging, stand tilt test, tab shake, lid cycles, USB/switch/buttons, battery checklist), and (b) Wi-Fi interleaved test with the baseline taken early (can run in parallel to 03).
- 69-05: as is, with "glass" replaced by "polystyrene front sheet", "cut the mat" replaced by "mat kept at its current opening" (D-09), and the BOM including foam, JST extension, magnets, screws, wall fixing, calliper if bought.

## Common Pitfalls

### Pitfall 1: Believing a tape-measure rebate to 0.5 mm clearance
**What goes wrong:** Plates jam in one of five frames or rattle in another.
**Why:** The tape has about 1 mm resolution; one frame measured; fibreboard frames vary.
**Avoid:** Calliper survey of 5 frames; print the shim first; set plate size from the smallest rebate.
**Warning signs:** The shim fits frame 1 but not frame 3.

### Pitfall 2: Shrinkage and elephant foot cancel in the middle and add at the edge
**What goes wrong:** Bottom edge flared, top smaller; measured size "correct" but the fit binds on the first layer.
**Avoid:** Measure at layer 1 and at height; chamfer first layer or tune elephant-foot compensation; avoid high elephant-foot compensation with a tight brim gap [CITED: 3dprintingspace.com, search summary].

### Pitfall 3: A printed pilot hole that is 0.1 to 0.2 mm small
**What goes wrong:** Screw binds or cracks the boss.
**Avoid:** Ladder coupon with the bought screws; drill to size after printing is more accurate than a printed hole (Hubs, search summary); chamfer the entry.

### Pitfall 4: Inserts as a fallback that cannot fit
**What goes wrong:** Threads wear, inserts needed, bosses too thin.
**Avoid:** Say in the plan that the fallback is a boss redesign (about 5 to 6 mm OD is my rule of thumb); decide after the cycle test.

### Pitfall 5: Magnets reversed or loose
**Avoid:** Mark polarity; verify attract before glue; pocket ladder; keep CA glue away from the polystyrene front sheet.

### Pitfall 6: Battery pinched by the lid or rubbing a screw tip
**Avoid:** Dry fit unplugged, photograph routing, foam, no screw tip in the cell zone, lid-open power-on check before closing.

### Pitfall 7: Wi-Fi verdict from two sequential 20-wake runs
**Avoid:** Interleaved blocks, zero filter, bootstrap bound, baseline early (section 5).

### Pitfall 8: Hook ridges drop out of the slice or wear
**Avoid:** Coupon test with the real wall screw; consider widening ridges to 0.8 mm only if the coupon fails.

### Pitfall 9: Vacuous automated checks in the plans
**What goes wrong:** Plan 04 Task 2 verifies `grep -c 'pass' ... -ge 1` and plan 03 Task 3 greps `fits|tight|loose|does not fit`. The template header text already contains those words, so the check passes on an empty file.
**Avoid:** Check for populated rows instead (for example a row with a date `20[0-9]{2}-` in the Date column and a non-empty Value), or check that no cell still reads "not done"/empty in rows the owner reported.

### Pitfall 10: Stale statements spreading through documents
**What goes wrong:** `ENCLOSURE-3D-DESIGN.md` still says printer "X2D recommended", "Material ... not formally decided", "Slicer ... not used yet", "Tests: no part sliced", "Nothing has been printed or sliced yet" and the "Open questions" list begins with "check that the Blender file is saved" (done). The Status paragraph at the top says the opposite.
**Avoid:** A stale-text sweep task in the closeout plan.

## Code Examples

None (no code in this phase). Throwaway analysis, to be run locally by Claude on pasted rows, never committed (project rule: tests/commits stay clean):

```python
# Throwaway: difference of medians with a bootstrap interval (not committed).
import random, statistics
def diff_ci(a, b, n=5000, seed=1):
    rnd = random.Random(seed)
    d = []
    for _ in range(n):
        ra = [rnd.choice(a) for _ in a]
        rb = [rnd.choice(b) for _ in b]
        d.append(statistics.median(rb) - statistics.median(ra))
    d.sort()
    return statistics.median(b) - statistics.median(a), d[int(0.05 * n)], d[int(0.95 * n)]
```

## State of the Art

| Old approach | Current approach | Impact |
|--------------|------------------|--------|
| Hand-tuned hole offsets in CAD | Slicer hole/contour compensation and per-filament shrinkage (Bambu Studio) | Keep CAD at nominal, tune in the slicer per filament |
| Press fit / glue magnets only | Pause-and-embed (printer pauses to insert the magnet) | More complex; not needed for a 10 g plate; mentioned in the Bambu forum thread |
| Self-tapping into raw print | Bambu BT-series screws or heat-set inserts for repeated assembly | Reuse count unpublished; decide by test |

**Deprecated/outdated:** the ESP32 hall sensor API was dropped in ESP-IDF 5.0 (irrelevant to magnets here; stated for completeness).

## Divergences: plans 69-02 to 69-05 versus the real state

| # | Plan / document | What it says | Real state | Fix |
|---|-----------------|--------------|------------|-----|
| 1 | 69-02 SUMMARY frontmatter and body | `status: incomplete`; "the slice check by the owner is not [done]"; "Masses, thinnest wall and slot, and any slicer warning were not reported; no print yet" | ENCLOSURE-PRINT-ORDER.md "Slice check" has times, masses, settings, a warning note; thinnest wall/slot are Blender values (not from Bambu Studio) | Rewrite the summary as complete, keep the "no print" and "thinnest values are model values" notes; ROADMAP still shows `[ ] 69-02` |
| 2 | 69-02 PLAN, Decisions | "first print elsewhere by a print service or fablab"; "PETG black"; Bambu X2D as option | Workplace Bambu printers; PETG any colour; slice made for a P2S; build plate textured PEI, filament "PETG Basic" | Update the Decisions table: printer (P2S slice vs "X1 series to confirm"), build plate, filament reference |
| 3 | 69-02 must_haves | "PETG black" | "any colour" (owner, 2026-11-18) | Edit |
| 4 | 69-03 PLAN Task 2 and "Print record" | Provider, order date, receipt date, cost per part, "provider changed anything" | Own printer, no provider, cost EUR 1.67 total per slicer | Rewrite as rounds on the workplace printer: machine, date, spool, plate, settings per round |
| 5 | 69-03 PLAN Task 1 clearance list | 10 listed rows | Missing: screw lugs, tab-pad contact and shake test, hook ridges, board standoff engagement, lid to board 0.41 mm, antenna cable route, plate flatness, first-layer flare, JST extension | Add rows (table above) |
| 6 | 69-03 PLAN | "Two M2 screws" for lid dry fit | Four lid corner lugs/bosses; lugs are for the frame, not lid | Four screws; note lugs separately |
| 7 | 69-04 PLAN, Wi-Fi | "20 wakes without, then 20 with, median within 3 dB" | Weak statistic and confounds (section 5) | Replace with interleaved A-B-A-B, interval, early baseline |
| 8 | 69-04 PLAN checklist row 6 | "Buttons (KEY0, KEY1, KEY2)" | Design also has RESET (fourth button) with engraved indications and ON/OFF | Add RESET and the power switch positions |
| 9 | 69-04 PLAN | No battery-safety, magnet, tab-shake, hook-load or stand-tilt method | Design findings F-02, F-04, F-10 explicitly leave these open | Add them (sections 4, 6) |
| 10 | 69-04 PLAN, row 1 | "Screen sits centred behind the mat" | D-12 centres on the mat opening; D-09 says the image will be adapted later; mat window height 99 versus IKEA 90 | Record visible margins against the mat window; recheck 99 mm |
| 11 | 69-05 PLAN Task 2 | Assembly step "cut mat" and cost "mat cut" | D-09: mat keeps its 140 x 99 mm opening | Remove the cut step, keep "mat as is" |
| 12 | 69-05 PLAN | "glass" | IKEA: front protection is polystyrene plastic | Say "front sheet" |
| 13 | 69-05 PLAN | "IKEA ... article 105.488.67" | The design record says black is 105.488.67; the IKEA page fetched was white 105.488.72 | Confirm article of the frames actually bought |
| 14 | 69-01 PLAN rows 4 to 7 and CONTEXT D-04 | "mat opening about 158 x 94 mm cut by the owner" | D-09 overrides: 140 x 99 mm kept | Note superseded (plan 01 already complete) |
| 15 | ENCLOSURE-3D-DESIGN.md | Multiple stale statements (see Pitfall 10); stated "exported 2026-11-18" vs 2026-11-19 rework | `hardware/cad/export/skypane_lid.3mf` also exists and is not in any file list | Sweep; list or remove the 3MF |
| 16 | ENCLOSURE-PRINT-ORDER.md Print-order spec table | Two rows (Material, Nozzle) carry four cells in a two-column table | Table formatting bug (extra "decided by the owner / date" cells) | Fix columns |
| 17 | ENCLOSURE-PRINT-ORDER.md "Build plate: open"; "Filament: Bambu Lab filament (reference to confirm)" | Slice states textured PEI and PETG Basic | Same document contradicts itself | Update the Decisions rows |
| 18 | ENCLOSURE-AUDIT F-01 "Still to do: first-layer compensation or a small chamfer" | Not recorded as done or decided | Open | Decide in round 1 |
| 19 | BOM / "To buy" in design record | "Magnets ... to buy"(brief) | Design record says a lot of 100 magnets, 20 JST extensions and 800 screws were ordered; no arrival reported | Ask the owner to confirm arrival |
| 20 | BATTERY-MODEL.md | Kubii 3000 mAh "out of stock" on 2026-11-01 | The enclosure is sized to it; frame in production uses the 10000 mAh Soldered pack (11 x 60 x 100 mm) that does not fit this pocket | Record that enclosure pack choice is the owner's single 3000 mAh unit; spare/replacement may differ |
| 21 | Audit F-02/F-15, design record | "wood" edge, "glass" | IKEA: fibreboard with paper foil, polystyrene front | Update terms; screw lugs hold less than assumed |
| 22 | Audit F-02 hook load | 5.8 N hook roof load | 328 to 403 g is 3.2 to 4.0 N | Reconcile |

## Open Decisions: recommendations

| Decision | Status in repo | Recommendation |
|----------|---------------|----------------|
| Printer X1 versus P2S | D-13 says X1 series (to confirm); slice was for a P2S | Record "sliced for P2S, printed on <machine>, owner to confirm"; both are Bambu CoreXY machines, but record the machine per round because tolerances differ by machine. |
| Build plate | "open" in the Decisions table; slice says textured PEI | Record textured PEI as decided (owner-reported slice); expect rough underside; keep the same plate every round. Forum reports say PETG should use glue stick or textured PEI to avoid over-adhesion on smooth PEI [LOW]; textured is the safer choice for adhesion on a 132 x 182 mm plate. |
| Filament reference | "Bambu Lab filament (reference to confirm)" | Record "Bambu PETG Basic", colour, and spool/batch per round. Do not change brand between rounds. Dry the spool if it has been open for long (Bambu wiki says drying affects fit). |
| Screws vs inserts | Screws decided; inserts "fallback" | Keep screws; replace "fallback" by "redesign if the 5-cycle test fails"; plan only the test. |
| Magnets | Ordered per design record | Confirm arrival; measure with calliper; ladder coupon; mark polarity. |
| Wi-Fi baseline timing | After the enclosure exists | Start now (A block) while prints run; repeat A2 after. |
| Printer purchase (X2D) | Deferred; offer ends 2026-12-01 | Stay deferred; the first fit result will arrive after that date; the owner's call. I did not re-check the price or the product. |
| Calliper | None owned | Buy or borrow before round 1 (blocking for the survey). Price [ASSUMED] about EUR 10 to 25; I did not check. |
| Lid tool-free | Not discussed | No (see section 4). |
| Frames to survey | One measured, four planned | Survey all 5 before round 2. |

## Risks the owner has not decided yet

1. **Fibreboard and polystyrene** (not wood and glass): lugs and tab friction; handling of the front sheet.
2. **Mat window 99 mm versus IKEA 90 mm** (D-09/D-12 depend on it).
3. **Tab grip unmeasured** (spring force and friction); a frame with glazing could drop.
4. **Wall type unknown** and hook fixing not chosen; single hanging point.
5. **Hook ridge durability and creep** unknown; test or accept.
6. **Battery: protection unverified, pack out of stock at vendor, swelling provision, charge current unknown, no tool-free cut-off other than the switch.**
7. **Wi-Fi unknown** until measured; fallback documented (U.FL).
8. **Stand tipping** margin small (5.4 to 10.5 degrees, model); slip on varnished surfaces; USB cable pull.
9. **Lid to board 0.41 mm** clearance and textured underside.
10. **Reuse count of M2 screws** unknown; insert fallback is a redesign.
11. **Printer availability** at the workplace and the time of day when it is free is not recorded.
12. **Design source is a binary blend** with French names in the script (audit F-13); not reviewable as text.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | PETG glass transition about 80 degrees C | 4 | Low; only matters in direct sun |
| A2 | Wake-to-wake RSSI SD about 2 to 4 dB | 5 | Test power calculation off; the plan measures SD from the data |
| A3 | ESP32-S3 has no hall sensor; EE04 no reed/hall | 3 | Magnet near board could trigger something; mitigated by the refresh test |
| A4 | Static magnet effect on Spectra 6, pouch cell and protection board is none at these distances | 3 | Unknown artifacts; owner check |
| A5 | CA glue fumes can fog polystyrene | Supporting | Minor |
| A6 | Screw into fibreboard edge holds poorly versus wood | 6 | Lugs may be adequate; test on 5 frames |
| A7 | Bought M2 screw thread form is a coarse sheet-metal type | 2 | Pilot ladder will show |
| A8 | About 5 to 6 mm boss OD for M2 inserts | Alternatives | Redesign effort wrong size |
| A9 | Calliper price about EUR 10 to 25 | Open decisions | Trivial |
| A10 | A closed lid does not trap gas because the service bay and USB notch are open | 4 | If the bay is covered later, venting changes |

## Open Questions (RESOLVED)

1. **Which printer physically prints?** Known: P2S slice, X1 in the decision text. Recommendation: owner reports per round. RESOLVED: routed to plan 03 task 3 and plan 04 tasks 1 and 2 (print record per round, machine reported each round; owner answer pending).
2. **Does the exported STL match the final blend?** Both were committed together; the Files table says 2026-11-18 but design changes are dated 2026-11-19. Recommendation: owner re-exports or confirms. RESOLVED: routed to plan 02 task 2 (owner answer pending).
3. **What is the real mat window height (90 or 99 mm)?** Recommendation: calliper before any image-adaptation decision. RESOLVED: routed to plan 02 task 2 (owner answer pending); calliper value in plan 03 task 2 survey.
4. **Second hardware wake cadence** for the Wi-Fi test is not recorded in the files read (live frame 300 s). Recommendation: record the server `sleep_s` used. RESOLVED: routed to plan 05 task 2 (owner answer pending).
5. **Is the 5.8 N hook load a safety-factor number?** Recommendation: reconcile. RESOLVED: routed to plan 02 task 1 (reconciled in prose, no owner question).
6. **Do any of the five frames differ in tab geometry?** Unknown until surveyed. RESOLVED: routed to plan 03 task 2, calliper survey of five frames (owner answer pending).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Bambu Lab P2S / X1 at workplace | All prints | Owner access stated (D-13); machine not recorded | — | Print later or use another Bambu machine, note it |
| Bambu Studio | Slicing | Yes (owner used 2.9.1.70) | 2.9.1.70 | — |
| Blender with owner's file | Any CAD change | Owner's computer only; **not available in this cloud session** | — | Owner applies written changes (D-08) |
| Calliper | Survey, fit | **No** (tape only so far) | — | Borrow at workplace; none otherwise (tape cannot resolve 0.3 mm) |
| Multimeter | Polarity, voltage | Yes (used in earlier records) | — | — |
| 0.1 g scale | Masses | Kitchen scale used | — | Good enough |
| M2 screws, magnets, JST extension | Fit, lid, stand | Ordered per design record; arrival not reported | — | Local shop |
| Frames (5) | Survey | One measured; four planned | — | — |
| Python (throwaway) | Wi-Fi stats | Available in this session | — | spreadsheet |
| `GET /api/export/battery-history` + export token | RSSI | Existing route (plan 04 states it needs `SKYPANE_EXPORT_TOKEN`); token never written to files | — | — |

**Missing with no fallback:** none blocking Wave 1 except a calliper for the rigorous survey.
**Not checked:** slopcheck is irrelevant (no packages).

## Validation Architecture

`workflow.nyquist_validation` is true (absent keys treated as enabled; config has it true).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None for this phase. The project's pytest/ruff gates are unaffected; no code is touched. Acceptance is by owner report in `hardware/*.md` tables. |
| Config file | none |
| Quick run command | `git diff --stat -- hardware/` (docs only); optional `grep` populated-row checks |
| Full suite command | `./scripts/run-all-tests.sh` (unchanged; must stay green, nothing in this phase changes it) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENC-01 | Parts fit frame, screws/magnets/battery bay fit | manual (owner, calliper) | Populated-row grep on `hardware/ENCLOSURE-TEST-PRINT-LOG.md` (rows with dates) | Wave 0 (created by plan 03) |
| ENC-01 | Hangs and stands | manual (owner, tilt test) | none | Wave 0 (plan 04) |
| ENC-01 | USB-C, switch, buttons reachable | manual | none | Wave 0 |
| ENC-01 | Wi-Fi not degraded | manual + throwaway script on exported rows | none committed | Wave 0 |
| ENC-01 | Documented, BOM, SEED-014 | doc check | `test -f` and `grep` for section headings | Wave 0 |

### Sampling Rate
- Per round: owner fills the clearance table before the next print.
- Per phase gate: all rows pass/fail/not done with dates; the verifier reads owner-reported rows only.

### Wave 0 Gaps
- [ ] Replace the vacuous greps (Pitfall 9) with populated-row checks.
- [ ] A rule that "pass" cells must have a date in the same row.

## Security Domain

`security_enforcement` true, ASVS level 1. There is no code, authentication or deployed change.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | — |
| V6 Cryptography | no | — |
| V8/V14 data protection (config) | marginal | Do not write `SKYPANE_EXPORT_TOKEN`, access point password, device MAC/secret or enrolment code into any hardware file or message (existing T-69-03, T-69-07, T-69-10) |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Secret leaked into RSSI export notes | Information disclosure | Record counts/medians and the AP name only |
| Reversed battery polarity destroys board | Denial of service | Multimeter before connection (F-07) |
| Cell pinched/punctured/swollen in a closed case | Denial of service / safety | Checklist in section 4 |
| Frame falls from the wall | Safety | Tab grip test and hook load test before hanging with glazing |
| Verdict spoofed by Claude | Tampering | Only owner reports (D-01) |

## Sources

### Primary (HIGH, read in this session)
- Repository: `69-CONTEXT.md`, `69-DISCUSSION-LOG.md`, `69-01..05-PLAN.md`, `69-01/02-SUMMARY.md`, `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md`, `hardware/ENCLOSURE-3D-DESIGN.md`, `ENCLOSURE-MEASUREMENTS.md`, `ENCLOSURE-PRINT-ORDER.md`, `ENCLOSURE-AUDIT.md`, `BOM.md`, `BATTERY-MODEL.md`, `PACK-ACCEPTANCE.md`, `SECOND-HARDWARE*.md` (grep only), `firmware/main/wifi.c`, `api_client.c`, `hardware/cad/export/` file names.
- IKEA UK RÖDALM 13x18 page [ikea.com/gb/en/p/roedalm-frame-black-10548872/](https://www.ikea.com/gb/en/p/roedalm-frame-black-10548872/) (fetched).
- Bambu forum screw-hole design guide [forum.bambulab.com/t/how-to-design-screw-holes-for-3d-printing/217352](https://forum.bambulab.com/t/how-to-design-screw-holes-for-3d-printing/217352) (fetched; community post, MEDIUM).
- CNC Kitchen heat-set inserts [cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey](https://www.cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey) (fetched).
- Hubs fasteners [hubs.com/knowledge-base/how-assemble-3d-printed-parts-threaded-fasteners/](https://www.hubs.com/knowledge-base/how-assemble-3d-printed-parts-threaded-fasteners/) (fetched).
- Battery University pouch cells [batteryuniversity.com/article/pouch-cell-small-but-not-trouble-free](https://batteryuniversity.com/article/pouch-cell-small-but-not-trouble-free) (fetched).
- Bambu forum magnets thread [forum.bambulab.com/t/magnets-in-prints/76022](https://forum.bambulab.com/t/magnets-in-prints/76022) (fetched; forum level).

### Secondary (MEDIUM/LOW, web search summaries only, not opened)
- Bambu wiki XY hole/contour compensation [wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation](https://wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation) (direct fetch returned HTTP 402).
- Bambu wiki shrinkage [wiki.bambulab.com/en/knowledge-sharing/3d-prints-shrinkage](https://wiki.bambulab.com/en/knowledge-sharing/3d-prints-shrinkage); Bambu forum threads on PETG dimensional accuracy, dimensions, P2S warping: [159931](https://forum.bambulab.com/t/improving-dimensional-accuracy-on-bambu-lab-h2d-with-petg-hf/159931), [87066](https://forum.bambulab.com/t/dimensions-are-incorrect/87066), [212662](https://forum.bambulab.com/t/p2s-warping-issue-from-first-print/212662).
- [stacksheriff.com Bambu Studio shrinkage](https://stacksheriff.com/3d-printing/bambu-studio-shrinkage-compensation/); [3dprinterly PETG shrinkage](https://3dprinterly.com/pla-abs-petg-shrinkage-compensation-in-3d-printing/); [3dprinterly PETG warping](https://3dprinterly.com/9-ways-how-to-fix-petg-warping-or-lifting-on-bed/).
- [MakerWorld tolerance test](https://makerworld.com/en/models/2236614-tolerance-test); [accu-components insert chart](https://accu-components.com/p/488-threaded-insert-hole-size-charts-for-3d-printing-pla-petg-resin).
- RF: [aisler co-design thread](https://community.aisler.net/t/co-design-of-pcb-antennas-and-3d-printed-enclosures-practical-rf-insights/5518), [novelbits RF chamber](https://novelbits.io/rf-chamber-episode-1-material-attenuation-public/), [MDPI Appl. Sci. 13(6) 3900](https://www.mdpi.com/2076-3417/13/6/3900).
- Creep: [Qidi hook guide](https://qidi3d.com/blogs/print-lab/pla-petg-heavy-wall-hook-material-guide), [Bambu forum 212834](https://forum.bambulab.com/t/pla-vs-petg-hf-deformation-under-load/212834), UTS studies (opus.lib.uts.edu.au).
- Seeed EE04 wiki [wiki.seeedstudio.com/epaper_ee04/](https://wiki.seeedstudio.com/epaper_ee04/); Espressif migration guide [docs.espressif.com/projects/esp-idf/en/v5.3/esp32s3/migration-guides/release-5.x/5.0/peripherals.html](https://docs.espressif.com/projects/esp-idf/en/v5.3/esp32s3/migration-guides/release-5.x/5.0/peripherals.html).

### Tertiary
- None beyond the above; every [ASSUMED] item is in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Repository facts and divergences: HIGH (read directly).
- Standard stack: MEDIUM (hardware and process; no packages).
- Tolerances, shrinkage, screw reuse, magnets, creep: LOW to MEDIUM (forum-level, no authoritative table).
- Battery safety: MEDIUM for swelling advice, LOW for specifics; no standards content used.
- Wi-Fi: LOW for expected attenuation (none found), MEDIUM for the statistical critique (my arithmetic).
- Pitfalls: MEDIUM.

**Research date:** 2026-11-19
**Valid until:** about 2026-12-19 for process; re-check the X2D price/date separately (not verified here).
