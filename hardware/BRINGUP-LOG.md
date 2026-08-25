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

## Flashing Tooling

`esptool` was installed via Homebrew (not pip), keeping Phase 1's
zero-pip-install property intact:

```
esptool v5.3.1
```

(`brew install esptool`; binary at `/opt/homebrew/bin/esptool`, with the
deprecated `esptool.py` alias also present.)

## Console Routing Bug (Rule 3 deviation)

The first flash attempt in this plan's earlier session produced **no
console output at all** after boot. Per this plan's own diagnostic
framing (see `## Board Profile Verification` above), a silent console on
this board points at console routing rather than a dead board: the
panel's master chip-select and power-enable signals share GPIOs with
UART0, so the EE02 profile must route the console to USB Serial/JTAG
instead of the default UART console.

Root cause found: `firmware/build-ee02/sdkconfig` (the generated build
config) did not actually carry `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y`
despite `firmware/sdkconfig.ee02.defaults` specifying it — a stale
generated `sdkconfig` in the build directory did not pick up the defaults
file's routing on an incremental build. Fix: a clean rebuild (removing
`firmware/build-ee02` and re-running `firmware/build.sh`) regenerated
`sdkconfig` correctly. Confirmed post-fix:

```
$ grep -E 'CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG|CONFIG_ESP_CONSOLE_UART' firmware/build-ee02/sdkconfig
# CONFIG_ESP_CONSOLE_UART_DEFAULT is not set
CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y
# CONFIG_ESP_CONSOLE_UART_CUSTOM is not set
CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG_ENABLED=y
CONFIG_ESP_CONSOLE_UART_NUM=-1
# CONFIG_ESP_CONSOLE_UART_NONE is not set
```

This is a build-process gotcha, not a wrong value in
`sdkconfig.ee02.defaults` itself (that file was already correct — see
`firmware/VENDOR.md`'s vendored-file table, `Verbatim? = yes`). No
divergence from upstream was introduced; the fix is "rebuild clean when
`sdkconfig.ee02.defaults` changes and the build directory already
exists," which is generic ESP-IDF build hygiene rather than an EE02-
specific hardware fact. Logged here under Rule 3 (auto-fixed blocking
issue) rather than as a `firmware/VENDOR.md` divergence, since no
vendored file's content changed.

## Flash Attempt (Task 2)

**Working command** (device at `/dev/cu.usbmodem1301`):

```
firmware/flash.sh /dev/cu.usbmodem1301
```

**Attempts needed:** 1 successful flash + read-back verification, on the
first attempt of this session (following the clean rebuild above).

**Result:**

```
Writing '.../build-ee02/bootloader/bootloader.bin' at 0x00000000... Hash of data verified.
Writing '.../build-ee02/partition_table/partition-table.bin' at 0x00008000... Hash of data verified.
Writing '.../build-ee02/ota_data_initial.bin' at 0x0000f000... Hash of data verified.
Writing '.../build-ee02/inkframe.bin' at 0x00020000... Hash of data verified.
Verifying application region (offset=0x20000, size=1050368) against build-ee02/inkframe.bin ...
verify_flash: OK - flashed application region matches build-ee02/inkframe.bin byte-for-byte (1050368 bytes)
flash.sh: SUCCESS
```

Chip identified during flash: ESP32-S3 (QFN56) revision v0.2, 8MB
embedded PSRAM, MAC `<device-mac>`.

**Status: flash byte-verified successful. First-boot console capture
is BLOCKED** — the USB serial connection dropped again immediately
after the flash+verify completed and before `firmware/monitor.sh` could
capture any output (confirmed by `ls /dev/cu.*` losing the
`/dev/cu.usbmodem1301` entry entirely, twice, with waits of several
seconds in between). This is the same intermittent physical connection
this log already flagged above ("This connection has been observed to be
flaky across sessions") — not a firmware or flashing defect. The flashed
image itself is confirmed correct (byte-for-byte verified against
`build-ee02/inkframe.bin`); only observing it boot is blocked pending a
physical reconnection.

**Next action:** reseat/replace the USB-C cable connection (or the port)
and re-run `firmware/monitor.sh <port>` once `ls /dev/cu.*` shows the
device again — no re-flash is needed, the device already has the
verified image on it.

---
*Log opened: 2026-08-25, Task 1 of plan 01-06. Task 2 flash+verify
recorded 2026-08-25 21:38 UTC; first-boot capture pending physical
reconnection.*
