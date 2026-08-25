# Ink Frame — Hardware Bring-Up Log

This log records the physical assembly, first flash, and first-light
verification of the XIAO ESP32-S3 Plus + EE02 driver board + 13.3" Spectra 6
panel, per plan `01-06-PLAN.md`.

## Arrival

Both packages physically arrived the week of **2026-08-17 to 2026-08-23**
(the calendar week before this log entry, 2026-08-25) — the developer did
not track the exact day within that week. This falls within
`hardware/BOM.md`'s estimated delivery windows for both orders (Seeed EE02
kit: 2026-08-14 to 2026-08-26; Kubii battery+cable order: estimated
2026-08-08, so that order likely arrived earlier in the window than the
EE02 kit did) — no delivery-window overrun to flag.

| Item | Order | Arrived on |
|---|---|---|
| XIAO ePaper DIY Kit EE02 (board + panel bundle) | Seeed order <seeed-order-ref> | Week of 2026-08-17 to 2026-08-23 (exact day not tracked) |
| LiPo battery pack + USB-C data cable | Kubii order <kubii-order-ref> | Week of 2026-08-17 to 2026-08-23 (exact day not tracked) |

`hardware/BOM.md`'s `## Order Tracking` table is updated to match (see that
file's own note on elapsed lead time).

## Assembly

The XIAO ESP32-S3 Plus module seated cleanly onto the EE02 driver board,
and the 13.3" panel's flat-flex cable seated into its connector without
issue. No deviation from Seeed's documented assembly steps for the EE02
kit was needed — no crooked seating, no latch that had to be reopened, no
missing part.

## USB Connection

The USB-C cable used is the one purchased specifically for this project
and recorded in `hardware/BOM.md`'s `## Required Now` table — "USB-C data
cable (USB 3, carries data — not power-only)", Kubii SKU "Cable USB 3
Type-C vers USB-A", part of order <kubii-order-ref>. This is a data-capable cable
by the vendor's own listing (explicitly not a charge-only cable), matching
the BOM's own warning that a charge-only cable is the most common cause of
"the board does not appear at all."

## Serial Device Path

Before plugging in, `ls /dev/cu.*` was run and the existing device list
noted. After plugging the board in via the cable above, the same command
was re-run and the newly appeared entry was identified as the board:

```
/dev/cu.usbmodem1301
```

This exact path — no wildcard — is what `firmware/flash.sh` (Task 2) is
invoked against. This connection has been observed to be flaky across
sessions (dropped once already), so the path is re-verified with a fresh
`ls /dev/cu.*` immediately before every flash attempt rather than trusted
from this log alone.

## Battery

The battery pack (Kubii "Batterie 3000mAh Li-Po", JST-PH 2.0mm 2-pin) is
physically present and has **not** been connected to the board. Per this
plan's own instructions ("Do not plug it in during this task; plan 01-08
does that"), no connection is made in this plan — first bring-up runs on
USB power only, exactly as designed.

**Polarity check status:** the visual polarity check against the board's
silkscreen (JST connector, negative pin nearest the USB-C port per
`hardware/BOM.md`'s `## Battery Connector Verification` section) has
**not yet been performed**. This plan's acceptance criteria for Task 1
only requires the battery to be "recorded as present and not yet
connected" — it does not require the polarity check to happen in this
plan, and the plan's own how-to-verify text assigns the actual connection
event to plan 01-08, not this one. The polarity check is therefore
explicitly deferred and tracked here as a **blocking prerequisite for plan
01-08**: before 01-08 connects the battery for the first time, the
JST housing orientation must be visually confirmed against the board's
silkscreen marking (and per BOM.md's own fallback, checked with a
multimeter if there is any doubt), since a reversed-polarity connection
destroys the board and is not recoverable.

## Board Profile Verification

**Status: PENDING**

The EE02 board profile's eight panel pin values, vendored verbatim from
upstream in plan 01-05 (`firmware/sdkconfig.ee02.defaults`), have never
been driven against real hardware by their own authors. A wrong
chip-select or power-enable value on this board does not fail cleanly —
it drives the panel incorrectly, so the symptom is a wrong-looking picture
on the glass rather than an error message.

What a wrong pin value would look like on the glass, per the plan's own
diagnostic framing:

- **Wrong colour order** — a swapped nibble packing or palette mapping
  shows the six bands in the wrong left-to-right order or with wrong
  colours entirely.
- **A visible seam discontinuity** — the panel's two controllers each
  drive one 600px-wide half; a wrong master/slave chip-select assignment
  shows as an offset, a duplication, or a blank/stale half at the vertical
  midline.
- **Partial refresh** — some rows updated and others not, pointing at the
  busy or reset line.
- **Wrong orientation** — bands running horizontally instead of vertically
  would mean a row-order or rotation problem, since the image is authored
  portrait for a portrait-native panel.
- **No console output at all** — on this board, the panel's master
  chip-select and power-enable signals share GPIOs with UART0, so the
  profile deliberately routes the console to USB Serial/JTOG instead; a
  silent console points at that routing rather than a dead board.

Tasks 2 and 3 of this plan resolve this section from `PENDING` to
`VERIFIED` (or, if a correction is needed, document the divergence here
and in `firmware/VENDOR.md`).

---
*Log opened: 2026-08-25, Task 1 of plan 01-06.*
