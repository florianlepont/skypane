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
was initially BLOCKED**, then diagnosed and resolved — see
`## First-Boot Capture: Diagnosis (resolved)` below.

## First-Boot Capture: Diagnosis (resolved)

**Symptom as reported:** the device "appears quickly in the USB list and
then disappears" repeatedly. Across several sessions this looked exactly
like a boot loop — a possible brownout during panel power-up, or a
firmware panic, given the EE02 profile's own authors never drove this
board on real hardware (see `## Board Profile Verification` below).

**Investigation method.** Plain `ls /dev/cu.*` polling was too coarse to
catch a connection window measured in single-digit seconds. Three
independent evidence sources were used together instead of guessing:

1. **macOS kernel-level USB log** (`/usr/bin/log show --predicate
   'eventMessage contains "303a" ...'` — note: `log` is a zsh builtin
   that shadows `/usr/bin/log`; the full path must be used). This
   surfaced every `IOUSBHostFamily` enumerate/terminate event for the
   board's native VID/PID (`0x303a/1001`, "USB JTAG/serial debug unit"),
   with real timestamps, independent of whether any capture script
   happened to be polling at that instant.
2. **The stub server's own request log**
   (`/private/tmp/inkframe-bringup/byos_server.log`, already running
   with stdout redirected there from an earlier session). This showed
   `/device/v1/setup` enrollment for the real device MAC
   (`<device-mac>` — matching the MAC esptool reports), followed by
   repeated authenticated `/device/v1/display` polls carrying real
   telemetry (`X-Boot-Reason`, `X-Rssi` between -42 and -64 dBm,
   `X-Fw-Version=0.1.0-p1`) — proof Wi-Fi and HTTP were working, well
   before any console bytes were ever captured.
3. **A race-capture script** (`ls /dev/cu.usbmodem*` polled every
   ~150 ms; the instant the port appeared, a background `cat` was
   attached and teed to a scratch file) — the fallback that finally
   caught real serial text once the timing/tooling issues below were
   fixed.

**Two tooling bugs found and fixed along the way (Rule 3):**
- `timeout` (GNU coreutils) is not present on stock macOS; a background
  `cat <port> &` + poll-and-`kill` loop was used instead in the
  race-capture script.
- `log` used bare is a zsh builtin (a math/logarithm command), not
  `/usr/bin/log` — commands must invoke `/usr/bin/log` explicitly.

**Finding: this was never a boot loop.** The very first real console
capture (during a hash-skip cycle, no download needed) read, in full:

```
I (6001) fp_wifi: clock set via SNTP
I (6571) inkframe: image unchanged, skipping download
I (6571) inkframe: poll ok sleep_s=300 hash_skip=1
I (6581) wifi:state: run -> init (0x0)
...
I (6631) inkframe: sleep enter sleep_s=300
```

No panic, no `Brownout detector was triggered`, no `Guru Meditation
Error` — the device printed a clean "poll ok" / "sleep enter" pair and
then the USB connection dropped, because `esp_deep_sleep_start()`
powers off the USB Serial/JTAG peripheral along with everything else
outside the RTC domain. **"Appears then disappears" is the device
correctly finishing its wake cycle and cutting power for deep sleep —
by design, not a fault.** The kernel log's `terminateDevice: ...
hardware connection lost` line is simply what a clean power-off looks
like from the host's side; it is indistinguishable at that layer from
an actual crash, which is why direct serial capture (not USB
enumeration events alone) was necessary to close this out.

The mixture of `X-Boot-Reason=power-on` and `X-Boot-Reason=rtc` visible
across the stub server's historical log lines is fully explained by the
several rounds of manual reflash/reconnect troubleshooting in earlier
sessions (each reflash forces a fresh power-on-reason boot); it does not
indicate repeated uncontrolled resets.

**Forcing and capturing a real (non-hash-skip) cycle.** Because NVS
already held the palette image's hash from an earlier successful blit,
a later poll would hash-skip and never reach the blit path this task's
acceptance criteria needs literal log text for. `/tmp/panel.bin` (the
file the stub server re-reads on every request) was temporarily swapped
to the repository's own `quadrants` test pattern via
`stub-server/make_test_panel.py --pattern quadrants` — a different,
still-valid 960,000-byte image with a different hash, existing
specifically for this purpose per that script's own docstring
("Used as the second distinct test image for the stub server's
hash-change check"). `firmware/flash.sh` was re-run (same
already-verified binary; this also forces an immediate fresh boot) and
the console was captured live. Result, captured in full to
`hardware/logs/first-light.log`:

```
I (746) inkframe: wake reason=power-on boot_count=17
...
I (986) wifi:connected with [home network], aid = 6, channel 6, BW20, ...
I (986) wifi:security: WPA2-PSK, phy: bgn, rssi: -48
...
I (43516) epd13in3e: refresh complete
I (43616) inkframe: blit ok bytes=960000 sha256_ok=1
I (43626) inkframe: refreshed to sha256:f7581d2c607ed6d5...
I (43626) inkframe: poll ok sleep_s=300 hash_skip=0
I (43626) inkframe: sleep enter sleep_s=300
```

The real blit (GPIO configure -> panel power-on -> refresh) took from
t=+11976ms to t=+43516ms, roughly **31.5 seconds** — comfortably inside
`epd13in3e.c`'s 60-second `DRF` busy-wait timeout, and a first real
measurement of this panel's full-refresh duration (see
`## Panel Observations` in Task 3's section below). No brownout, no
panic, across this or the two-earlier-download boot recorded in the
stub server's log.

`/tmp/panel.bin` was restored to the `palette` pattern immediately
after this capture (`make_test_panel.py --pattern palette`, hash
`62360cd7...`, matching the original), and the device was woken again
(another `firmware/flash.sh` reflash) so the panel redraws the correct
six-band image before the Task 3 human visual check — the quadrants
image was a diagnostic-only detour and never the intended first-light
picture.

**Conclusion:** no hardware defect, no firmware bug, no EE02 profile
correction needed for this finding. The board profile's pin values
drove a real 31.5-second refresh end to end without incident. The only
artifacts of this investigation are the two tooling fixes above and this
written record, so a future session does not have to re-discover that
"appears then disappears" is expected deep-sleep behavior.

---
*Log opened: 2026-08-25, Task 1 of plan 01-06. Task 2 flash+verify
recorded 2026-08-25 21:38 UTC; first-boot capture diagnosed and resolved
2026-08-25 22:1x UTC (see `## First-Boot Capture: Diagnosis (resolved)`
above) — root cause was the device's own correct deep-sleep USB
power-off, not a fault.*
