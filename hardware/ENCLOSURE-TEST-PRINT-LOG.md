# Enclosure: test-print log

Log of the test prints of the rear enclosure for the 7.3 inch frame (shim,
tray, lid, stand). The design record is
[ENCLOSURE-3D-DESIGN.md](ENCLOSURE-3D-DESIGN.md); the print order and slice
check are in [ENCLOSURE-PRINT-ORDER.md](ENCLOSURE-PRINT-ORDER.md); the real
part measurements are in [ENCLOSURE-MEASUREMENTS.md](ENCLOSURE-MEASUREMENTS.md).

Rules for this log:

- Every result cell is filled only from the owner's report. A filled row
  carries a date and the words "reported by the owner" in its Source cell.
- A "pass" without a date in the same row counts as not done.
- Every design number is "design value, not measured" until the owner
  reports a reading.
- Acceptance figures are design values the owner may adjust. Any change is
  recorded with its date.
- An adjustment is recorded only when the owner changed the CAD.
- The tolerance evidence found (clearances for pilots, magnet pockets,
  press fits) is forum-level, not an authoritative table. All numbers are
  starting points for the first print.
- No device identifier, token or password goes in this file.

How fit is judged (owner decision, 2026-11-20 and 2026-11-23): the approach is
prototype-first. Fit is first judged by trying the printed parts: fits,
tight, loose, or does not fit. Calliper readings are optional and are taken
only where a part does not fit. The owner has no calliper yet (reported on
2026-11-23). Every reading says the tool used (calliper, tape measure, by
feel) in the Tool column or in its cell; a tape or by-feel reading is never
recorded as a calliper value.

## Print rounds and gates

- Round A: the 1.0 mm shim plus one coupon plate (about 30 to 40 minutes).
- Round B: the tray (1 h 32 per the slice).
- Round C: the lid plus the stand (1 h 22 plus 29 minutes).
- A round D needs a one-line reason.

Rounds A, B and C are printed together as a single run: the owner reported on
2026-11-23 that he is "already printing everything" (shim, tray, lid and
stand, apparently at once). Which parts, which machine, spool, plate and
settings, and the start date, are not stated yet. Each round's rows are still
filled separately from what the owner reports. The Print record rows for A,
B and C keep their machine, spool and plate cells empty until the owner
reports them.

Gates as designed (they no longer hold the print back, since everything is
printed at once; they now hold back the go or no-go decisions and any reprint):

- The tray is accepted only after round A's rebate fit, pilot and magnet
  readings are reported.
- The lid is accepted only after the tray's rebate fit and standoff results
  and the 24 hour hook coupon load result are reported.

## Print record

One row per round. The slice was made for a P2S profile. The machine that
physically prints is recorded here every round, as the owner reports it (for
example the Bambu model). The same filament brand and plate are kept every
round.

| Round | Parts | Printer machine (model as reported) | Date | Filament reference | Colour | Spool or batch | Dried (yes or no) | Plate | Nozzle | Layer height | Walls and infill | Slicer shrinkage | XY hole and contour compensation | Elephant foot compensation | Actual print time | Source |
|-------|-------|-------------------------------------|------|--------------------|--------|----------------|-------------------|-------|--------|--------------|------------------|------------------|----------------------------------|----------------------------|-------------------|--------|
| A | Shim, coupon plate | Bambu Lab X1 Carbon | 2026-11-23 (print date not stated) | PLA |  |  |  | PEI plate (smooth or textured not stated) |  |  |  |  |  |  |  | reported by the owner on 2026-11-23: all parts printed (coupon plate not mentioned); filament brand, colour, spool, settings and print date not stated |
| B | Tray | Bambu Lab X1 Carbon | 2026-11-23 (print date not stated) | PLA |  |  |  | PEI plate (smooth or textured not stated) |  |  |  |  |  |  |  | reported by the owner on 2026-11-23: all parts printed (coupon plate not mentioned); filament brand, colour, spool, settings and print date not stated |
| C | Lid, stand | Bambu Lab X1 Carbon | 2026-11-23 (print date not stated) | PLA |  |  |  | PEI plate (smooth or textured not stated) |  |  |  |  |  |  |  | reported by the owner on 2026-11-23: all parts printed; later the same day the owner said the lid print is still to be done (planned for 2026-11-24), so which of the lid and the stand exist is to be clarified; filament brand, colour, spool, settings and print date not stated |
| D | | | | | | | | | | | | | | | | |

## Export stamps

One row per file expected per round.

| Round | File | Export date | Blend save date | Source |
|-------|------|-------------|-----------------|--------|
| A | Shim | | | |
| A | Coupon plate | | | |
| B | Tray | Bambu Lab X1 Carbon | 2026-11-23 (print date not stated) | PLA |  |  |  | PEI plate (smooth or textured not stated) |  |  |  |  |  |  |  | reported by the owner on 2026-11-23: all parts printed (coupon plate not mentioned); filament brand, colour, spool, settings and print date not stated |
| C | Lid | | | |
| C | Stand | | | |
| D | | | | |

## Clearance table

Each Round cell has the format `value; fits or tight or loose or does not
fit; pass or fail; YYYY-MM-DD` and stays empty until the owner reports it.
Tool column: the tool the design expects; the owner's reading states the
tool actually used.

| # | Item | Design value (design value, not measured) | Tool | Acceptance (design value, owner may adjust) | Round A | Round B | Round C | Round D | Source |
|---|------|-------------------------------------------|------|---------------------------------------------|---------|---------|---------|---------|--------|
| 1 | Plate outer length and width: shim (round A), tray and lid (later) | 132.0 x 182.0 mm (design value, not measured) | Calliper, 3 readings per side (optional; by feel first) | Within 0.3 mm of nominal | | | | | |
| 2 | Plate flatness (rock on a flat table, paper-sheet feeler) | Flat within 0.5 mm (design value, not measured); lid and shim are the warp risk | Flat table, paper sheet | Flat within 0.5 mm | | | | | |
| 3 | First-layer flare (step between layer 1 and layer 5) | Under 0.2 mm (design value, not measured) | Calliper (optional) | Under 0.2 mm; chamfer or compensation decided in round A | | | | | |
| 4 | Rebate fit in each of the five frames | Drops in without force (design value, not measured) | By feel | Drops in without force | | | | | |
| 5 | Shim opening and screen margin | Opening to be read from the STL by the owner; previous record gave 112.2 x 171.2 mm, to confirm (design value, not measured) | By eye; STL | Screen drops into its opening with an even visible margin | | | | | |
| 6 | Shim to mat gap | Mat back 0.1 mm above the shim (design value, not measured) | Paper strip | A paper strip slides with slight drag | | | | | |
| 7 | M2 pilot, lid corner (four corners) | 1.7 mm vertical (design value, not measured) | The bought screws, by feel | Screws drive in with firm resistance, no cracking | | | | | |
| 8 | M2 pilot, board standoff (four standoffs) | 1.6 to 1.8 mm, 0.8 mm floor (design value, not measured) | The bought screws, by feel | Screws drive in with firm resistance, floor intact | | | | | |
| 9 | M2 through hole | 2.4 mm (design value, not measured) | The bought screws, by feel | Screw passes without catching | | | | | |
| 10 | Standoff engagement and pull test | Engagement at most about 3.2 mm, below the 4 mm usual guidance (design value, not measured) | Firm hand pull | Screw does not strip under a firm hand pull | | | | | |
| 11 | Lid screw reuse: five removal and insertion cycles per screw, four lid screws (not two) | Five cycles per screw, four screws (design value, not measured) | By feel; owner records the count reached | No loss of grip over five cycles on each of the four screws | | | | | |
| 12 | Magnet pocket | 6.2 x 2.2 mm for 6 x 2 mm magnets; ladder 6.1 to 6.4 x 2.1 to 2.3 (design value, not measured) | Real magnets and pockets; calliper optional | Magnet seats fully and stays in | | | | | |
| 13 | Magnet retention | Stays in its pocket over 10 plate pulls, or glued with cyanoacrylate kept away from the polystyrene front sheet (design value, not measured) | By feel | Magnet stays in its pocket over 10 plate pulls | | | | | |
| 14 | Stop walls and stand plate | 0.5 mm clearance each side, walls 2.4 mm (design value, not measured) | By feel | Plate drops in without binding, wobble under 1 mm | | | | | |
| 15 | Battery pocket | 0.5 mm sides, 1.8 mm foam (design value, not measured) | Cell or dummy block, by feel | Cell fits with foam, cable exits the corner, free space remains after the lid is closed | | | | | |
| 16 | Ribbon slot | 4 x 28 mm (design value, not measured) | By eye | Ribbon passes without a hard crease | | | | | |
| 17 | Antenna block and cable route | 40 x 20 mm at x 12 to 52, y 65 to 85; route 46 to 47 mm against a 50 mm cable (design value, not measured) | By eye | Antenna reaches without strain | | | | | |
| 18 | Lid to board clearance | 0.41 mm over the battery socket (design value, not measured) | Paper test | Lid sits flat with the plug mated | | | | | |
| 19 | Hook rail ridges and notches | 0.4 mm ridges, 0.6 mm deep, 2 mm pitch (design value, not measured) | Real wall screw; load about 1 kg for 24 hours, over a soft surface and away from feet | Intact after 30 lifts and about 1 kg for 24 hours on the coupon section | | | | | |
| 20 | Tab pad height and tab contact | Pad top 15.0 mm (design value, not measured) | By feel | The cassette does not slip when held vertical and shaken gently | | | | | |
| 21 | Screw lugs | 2.2 mm hole, 4.2 mm head recess (design value, not measured) | The bought screws, by feel | Screws start on the fibreboard edge; failure is recorded as "fibreboard strips" | | | | | |
| 22 | USB-C notch, buttons and switch notch, service bay | USB-C notch 13 mm, buttons and switch notch 47.5 mm, service bay 20 and 30 mm (design value, not measured) | Tool or finger | Tool or finger reaches each | | | | | |
| 23 | Engraved text | 0.4 mm deep, 0.7 mm lines (design value, not measured) | By eye or loupe | Legible by eye or loupe | | | | | |

## Fit trials by feel

First trials of the printed parts, judged by trying them, without a calliper
(prototype-first). Each row carries the date, the tool ("by feel" when nothing
was measured) and "reported by the owner". The material is PLA, so a result
holds for PLA only.

| Part | Test | Frame (number or "not stated") | Result (fits, tight, loose, does not fit) | Tool | Date | Source |
|------|------|--------------------------------|-------------------------------------------|------|------|--------|
| Tray | Tray in the frame rebate | not stated | fits ("parfait", the owner's word) | by feel | 2026-11-23 | reported by the owner on 2026-11-23 |
| Shim | Shim in the frame rebate | not stated | fits ("rentre bien", the owner's words) | by feel | 2026-11-23 | reported by the owner on 2026-11-23 |
| Tray | Board on the four standoffs with M2 screws | not applicable | fits ("j'ai pu visser proprement la carte", the owner's words); screw length not stated | by feel | 2026-11-23 | reported by the owner on 2026-11-23 |
| Tray | All components placed in the tray | not applicable | fits ("j'ai pu mettre l'ensemble des composants", the owner's words); the list of components, the battery connection and any pinch of the cable or the ribbon are not stated | by feel | 2026-11-23 | reported by the owner on 2026-11-23 |
| Lid | Lid on the tray | | | | | |
| Lid | Lid with screws and magnets | | | | | |
| Stand | Stand plate in its stop walls | | | | | |

## Adjustment ledger

Rule: change a limited number of dimensions per round so each result is
attributable. Recorded only when the owner changed the CAD.

| # | Round | Part | Dimension | Old value | New value | Reason | Reprint needed | Date | Source |
|---|-------|------|-----------|-----------|-----------|--------|----------------|------|--------|
| | | | | | | | | | |

## Coupon plate specification

What the owner builds in Blender for round A: roughly 60 x 60 mm, 3 to 4 mm
tall, printed flat with vertical holes like the real parts.

- M2 pilot ladder 1.6, 1.7, 1.8 and 1.9 mm in 4.0 mm bosses, plus one boss
  with the 0.8 mm pilot floor of the real standoffs.
- Magnet pocket ladder 6.1, 6.2, 6.3 and 6.4 mm diameter by 2.1, 2.2 and
  2.3 mm deep.
- A 15 mm section of the landscape hook rail with the 0.4 mm ridges and the
  real notch geometry.

Notes:

- The pilot ladder is used with the screws actually bought, not with a vendor
  datasheet (the thread form is unknown until the label is read).
- A coupon saves time (about 15 minutes against 1 h 22 for a lid), not
  material.
- The coupon is part of the prototype-first approach but optional: if the
  owner prints all parts at once and they fit, it can be skipped.

## Battery checklist

Filled in the tray and lid work. Every row starts "not done".

| Row | Check | Method | Result (pass or fail or not done) | Date | Note | Source |
|-----|-------|--------|-----------------------------------|------|------|--------|
| BAT1 | Pack label read (capacity, protection mention) and compared with the order | Read the label | not done | | | |
| BAT2 | Polarity correct, checked before any connection | Multimeter on the extension cable, before any connection | done (the owner said the check was done; the result and the tool are not stated; the owner then connected the battery) | 2026-11-23 | The battery is connected to the board in the tray; the other rows (pinch, lid-open voltage, expansion room) are not reported yet | reported by the owner on 2026-11-23 |
| BAT3 | Dry fit with the plug disconnected | Dummy block of 8 x 50 x 60 mm | not done | | | |
| BAT4 | No part of the cell touches a screw tip, standoff, sharp print edge or the lid underside | By eye | done (the owner said nothing touches the battery; by eye, the lid is not closed yet so the lid underside is not covered) | 2026-11-23 | | reported by the owner on 2026-11-23 |
| BAT5 | Cables not pinched by lid or rebate, JST socket not loaded sideways, routing photographed (photo kept by the owner) | By eye, photo | partly done (the owner said the battery cable is not pinched; the screen ribbon, the JST socket and the photo are not reported) | 2026-11-23 | | reported by the owner on 2026-11-23 |
| BAT6 | Lid-open power-on check, voltage plausible | Multimeter | not done | | | |
| BAT7 | Cell free to expand 1 to 2 mm after closing | By eye, feeler | not done | | | |
| BAT8 | First full charge attended, board and cell not warm to the touch | By hand | not done | | | |
| BAT9 | Power switch and its position known | By eye | not done | | | |
| BAT10 | First swelling check date and next due date | By eye | not done | | | |

## Go or no-go by round

| Round | Decision | Date | Source |
|-------|----------|------|--------|
| A | | | |
| B | | | |
| C | | | |
