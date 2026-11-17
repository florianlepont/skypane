# Second hardware: measurement sheet

Unit: Seeed XIAO ePaper EE04 (XIAO ESP32-S3 Plus, 7.3 inch E Ink Spectra 6,
800x480), MAC 84:c7:bb:70:b2:7c (as recorded in
[SECOND-HARDWARE-VALIDATION.md](SECOND-HARDWARE-VALIDATION.md)).

Rules for this sheet:

- Nothing in the values table may be estimated, derived from a formula, or
  copied from the 13.3 inch board (EE02). Only a reading taken on this unit
  goes in.
- An empty row means the item stays **provisional**: the repository keeps the
  value it has today and says it is provisional.
- Every filled row needs the date, the unit MAC, the method actually used and
  the status `measured`. If you could not take the reading the way described,
  write the method you really used, or leave the row empty.
- Battery numbers (divider, discharge, battery life) are only final with a
  real cell connected; see
  [SECOND-HARDWARE-BATTERY.md](SECOND-HARDWARE-BATTERY.md). Without a
  measurement the battery profile stays provisional.

How the bench is set up (flash, provisioning, bench server) is in
[SECOND-HARDWARE-BENCH-RUNBOOK.md](SECOND-HARDWARE-BENCH-RUNBOOK.md).

Note on logs: the console is the chip's native USB Serial/JTAG, which
disappears while the unit deep-sleeps, and the 7.3 inch driver
(`firmware/main/epd7in3e.c`) prints no per-stage timing lines. Timing is
therefore best taken on the BUSY line (GPIO4) with a logic analyser or
oscilloscope, or with a stopwatch on the panel, or with a throwaway
instrumented build kept out of the repository. Say which one you used.

## Measurements and the repository value each one replaces

| # | Item | How to take it | Replaces |
|---|------|----------------|----------|
| 1 | Full refresh time (command that starts the refresh to BUSY back to idle) | Over at least five full refreshes, record min, median and max in seconds. Preferred: BUSY (GPIO4, idle high) on a logic analyser, measuring the low time after the refresh command. Fallback: stopwatch from the panel starting to flash to it going still. | Refresh spacing `FP_MIN_REFRESH_SPACING_S` (firmware default 60 s, not tuned for this panel) in `firmware/sdkconfig.second.defaults`; the Kconfig help text; the 190 s blit stage in `firmware/main/wake_deadline.h` |
| 2 | Busy wait after the init sequence (power-on) | Same five wakes. BUSY low time after the init table ends with power-on: min, median, max in seconds | `BUSY_TIMEOUT_MS` (60000) in `firmware/main/epd7in3e.c`, the blit stage in `wake_deadline.h`, `CONFIG_SKYPANE_WAKE_BUDGET_S` (700) |
| 3 | Busy wait after the refresh command | Same five wakes: min, median, max in seconds (this is item 1 seen from the driver) | Same as item 2 |
| 4 | Busy wait after the power-off command | Same five wakes: BUSY low time after power-off: min, median, max in seconds | Same as item 2 |
| 5 | Flash size | `esptool.py --port <port> flash_id` (also reports the chip and MAC to confirm the unit); record the "Detected flash size" line | The flash-size assumption of the second board's partition table and sdkconfig profile |
| 6 | Battery sense: GPIO and divider ratio | With a charged cell on the battery connector, read the cell voltage with a multimeter at the connector, then compare with `X-Battery-Mv` of the same wake on the bench server (runbook and battery method). Record both readings and the ratio. Floating readings with no battery do not count | `CONFIG_FP_PIN_BATTERY_ADC` (1) and the sense scaling, today copied from the EE02 |
| 7 | Battery ADC enable pin | Multimeter on the enable pin or the divider during a wake: record which GPIO goes active and its level while sampling | `CONFIG_FP_PIN_BATTERY_ADC_EN` (6), copied from the EE02 |
| 8 | User LED pin and polarity | Make the LED light with a known pin level (visual check, with the level seen in a log or on a meter); record the GPIO and whether low or high lights it | `CONFIG_FP_PIN_LED` (21) and `CONFIG_FP_LED_ACTIVE_LOW` (y), copied from the EE02 |
| 9 | KEY0, KEY1, KEY2 GPIOs | Press each key in turn while a log or a meter shows which GPIO changes and its idle and pressed level | `CONFIG_FP_PIN_KEY0` (5), `CONFIG_FP_PIN_KEY1` (3), `CONFIG_FP_PIN_KEY2` (2), copied from the EE02 |
| 10 | Battery discharge profile (optional) | Only from the battery work in [SECOND-HARDWARE-BATTERY.md](SECOND-HARDWARE-BATTERY.md) with a real cell: voltage against time | The battery profile in `server/hardware.py`, a provisional copy of the live frame's; it becomes final only with a source that says it was measured |

## Values table

Filled by the owner. Leave a row empty if the item was not measured.

| Item | Value | Date | Unit MAC | Method | Status (measured or provisional) |
|------|-------|------|----------|--------|----------------------------------|
| 1 Refresh time (min / median / max) | 25 s / 27 s / 27 s (five refreshes: 25, 27, 27, 27, 27) | 2026-11-15 | 84:c7:bb:70:b2:7c | Stopwatch from the panel starting to flash to it going fully still, on the bench server with a changing image at every wake (firmware fw-v1.0.12-bench8, dev profile, solid-colour test images) | measured |
| 2 Busy wait after init (min / median / max) | | | | | |
| 3 Busy wait after refresh (min / median / max) | | | | | |
| 4 Busy wait after power-off (min / median / max) | | | | | |
| 5 Flash size | 16 MB (quad, 3.3 V, manufacturer 0x85, device 0x2018); chip ESP32-S3 (QFN56) v0.2, 8 MB embedded PSRAM | 2026-11-15 | 84:c7:bb:70:b2:7c | `esptool --chip esp32s3 --port /dev/cu.usbmodem101 flash-id` (esptool v5.4.0), "Detected flash size" line | measured |
| 6 Battery sense GPIO and ratio | | | | | |
| 7 Battery ADC enable pin | | | | | |
| 8 LED pin and polarity | | | | | |
| 9a KEY0 GPIO | | | | | |
| 9b KEY1 GPIO | | | | | |
| 9c KEY2 GPIO | | | | | |
| 10 Battery discharge profile | | | | | |
