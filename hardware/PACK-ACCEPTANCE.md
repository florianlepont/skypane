# Replacement pack acceptance: Soldered 333290

Validation status: ACCEPTED WITH OPEN ITEM (check 4 unverified under the check's own rule: the board's charger current against a 10000 mAh pack is not documented). Ordered 2026-10-22, received by 2026-11-11, connected 2026-11-11 22:55 Paris time with the old pack disconnected; checks 1 to 3 passed (owner-reported).

This is the acceptance checklist for the replacement battery pack. It is filled in from what the owner reports when the pack arrives. A Result cell stays blank until the owner has reported that check, and nothing in it is a measurement by Claude. The step-by-step French instructions are in `hardware/FIELD-VALIDATION-FR.md` (Partie D). The evidence record is `hardware/FIELD-VALIDATION.md`.

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
| 1. Reference on the pack | Read the reference printed on the pack label and compare it with the order. | The label reads 333290 and matches the order of 2026-10-22. | PASS on a photograph sent by the owner (owner-reported): the label reads 333290, `1x Li-Po Battery 10000mAh 3.7V 1160100 JST`, with the Soldered logo. | 2026-11-11 |
| 2. Wire polarity, before the first connection | Multimeter in voltage mode on the pack connector, nothing connected to the frame. Same rule as `hardware/BOM.md`, Battery Connector Verification: on the board, the negative pin is the one nearest the USB-C port and the positive pin is the one farthest from it. This is the polarity check, not the current measurement the owner declined. | The wire that reads positive on the red probe lands on the board's positive pin, with the connector oriented as the board expects. A mismatch means: do not connect, report it. A reversed pack destroys the board on first connection. | PASS by effect (owner-reported, 2026-11-11): pack alone read +3.88 V with the red probe on the red wire (red wire positive); the owner then connected the pack to the board with the old pack disconnected, and the frame booted (`boot_reason` power-on at 22:55:54 Paris time, 3900 mV, read in the export) and kept reporting. The separate visual check of the connector orientation against the board was not reported in words; the outcome is what is recorded. | 2026-11-11 |
| 3. Free area | Lay the pack flat behind the screen, in the frame, without pressure on the panel. | 60 x 100 mm lies flat in the free area and nothing presses on the panel. | PASS (owner-reported): the pack lies flat behind the screen. | 2026-11-11 |
| 4. First charge | Connect the pack (only after checks 1 to 3 pass), plug in USB, watch the charge LED, and read the battery voltage on the Health page. Record the charge LED behaviour and the time taken to reach the plateau of 4058 to 4112 mV. A current meter is not required; record a current only if the owner volunteers one. | The first full charge completes without the pack or the board getting warm to the touch. If the board's charger current against a 10000 mAh pack is not documented, this check is recorded as `unverified` and the record says so. | UNVERIFIED under the rule of this row, with observations (owner-reported and export, 2026-11-11 to 2026-11-12): USB plugged in just after 22:55 Paris time and kept plugged until 19:56 on 2026-11-12 (the owner confirmed it was the USB cable that was unplugged, not the battery); the frame read 3900 mV at 22:55, 4088 mV at 06:00 on 2026-11-12 and 4160 to 4180 mV during the day with the charger; charge LED steady green (the owner says the LED does not change); battery and board cold to the touch, nothing warm. After the USB was unplugged the readings fell from 4158 mV (19:48) to 4152 mV (20:04), then settled at 4144 to 4146 mV (20:20 to 20:51). The EE02 wiki says a solid green LED means charging and gives no fully-charged indication; it states no charge current (module pages: 50 or 100 mA, conflicting; a forum post: about 110 mA), so the rule of this row applies and the check is recorded as unverified. A multimeter reading of the pack at rest was not taken, so a full charge is not shown; the resting reading of about 4145 mV is above the 4030 to 4060 mV that the old pack read when fully charged, which suggests the new pack is well charged (not a measurement). | 2026-11-12 |

## Optional comparison: voltage across the pack connector (calibration)

Not a pass or fail check, and it does not change the status values below. Context: `hardware/BATTERY-MODEL.md`, section "Percentage calibration at the top of the curve". The frame reads a full pack off the charger at about 4030 to 4060 mV, which is lower than a Li-Po charged to 4.2 V normally rests at, and it is not known whether the frame reads low or the charger stops early.

When the multimeter is already out for check 2 (voltage mode only, nothing in series), also record:

- the voltage across the pack connector after the pack has been charged and unplugged for at least one hour, nothing connected to the frame;
- the battery voltage the frame reports for the same pack, read on the Health page, the same hour.

The difference between the two numbers is the frame's reading error; if it is small, the charger stops early instead. Record both numbers and the time in the Result column of check 4 or in a note. This is optional: it needs no current measurement and no opening of the frame beyond the pack connector.

Owner-reported, 2026-11-11: the pack alone read +3.88 V across its connector before any charge. This is not the comparison described above, which needs a full charge and an hour of rest; it only records the state in which the pack arrived.

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
