# Replacement pack acceptance: Soldered 333290

Validation status: NOT RECEIVED (ordered 2026-10-22, owner-reported)

This is the acceptance checklist for the replacement battery pack. It is filled in by the owner when the pack arrives. Until then every Result and Date cell stays blank and nothing in it is a measurement. The step-by-step French instructions are in `hardware/FIELD-VALIDATION-FR.md` (Partie D). The evidence record is `hardware/FIELD-VALIDATION.md`.

## Pack facts

The pack facts are those of `hardware/BATTERY-MODEL.md`, section "Chosen replacement pack". They are not repeated in full here so that the two documents cannot drift apart. In short:

| Item | Value | Status |
|---|---|---|
| Pack | Soldered 333290, Li-Po Battery 10000mAh 3.7V | chosen and ordered by the owner, 2026-10-22 |
| Capacity | 10000 mAh | vendor rating, not measured |
| Size | 11 x 60 x 100 mm | vendor page, read 2026-10-22 |
| Free depth behind the screen | 18 mm, against a pack thickness of 11 mm | owner-reported, 2026-10-22 |
| Connector | standard JST-PH 2 mm female | vendor page; the board connector is JST 2.0 mm (`hardware/BOM.md`, Battery Connector Verification) |
| Wire polarity | not stated by the vendor page | to be checked by the owner (check 2) |

## Checklist

Do the checks in this order. Do not connect the pack to the frame until check 2 has passed.

| Check | How (summary; the French step is in FIELD-VALIDATION-FR.md, Partie D) | Pass criterion | Result | Date |
|---|---|---|---|---|
| 1. Reference on the pack | Read the reference printed on the pack label and compare it with the order. | The label reads 333290 and matches the order of 2026-10-22. | | |
| 2. Wire polarity, before the first connection | Multimeter in voltage mode on the pack connector, nothing connected to the frame. Same rule as `hardware/BOM.md`, Battery Connector Verification: on the board, the negative pin is the one nearest the USB-C port and the positive pin is the one farthest from it. This is the polarity check, not the current measurement the owner declined. | The wire that reads positive on the red probe lands on the board's positive pin, with the connector oriented as the board expects. A mismatch means: do not connect, report it. A reversed pack destroys the board on first connection. | | |
| 3. Free area | Lay the pack flat behind the screen, in the frame, without pressure on the panel. | 60 x 100 mm lies flat in the free area and nothing presses on the panel. | | |
| 4. First charge | Connect the pack (only after checks 1 to 3 pass), plug in USB, watch the charge LED, and read the battery voltage on the Health page. Record the charge LED behaviour and the time taken to reach the plateau of 4058 to 4112 mV. A current meter is not required; record a current only if the owner volunteers one. | The first full charge completes without the pack or the board getting warm to the touch. If the board's charger current against a 10000 mAh pack is not documented, this check is recorded as `unverified` and the record says so. | | |

## Validation status values

| Status | Meaning |
|---|---|
| NOT RECEIVED | The pack has not arrived. Current value. |
| RECEIVED, CHECKS PENDING | The pack is in the owner's hands; at least one check is not done. |
| ACCEPTED | All four checks pass. |
| REJECTED (check N) | A check failed; the failing check is named. |
| ACCEPTED WITH OPEN ITEM (item) | Checks 1 to 3 pass and the open item (for example check 4 `unverified`) is named. |

## What this does not establish

- Real capacity: 10000 mAh is the vendor rating. It is not measured here and these checks do not measure it.
- Protection behaviour: the overcharge, undervoltage and short-circuit protection is a vendor statement. None of these checks tests it.
