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
| 2 Busy wait after init (min / median / max) | 0.17 s / 0.17 s / 0.17 s | 2026-11-17 | 84:c7:bb:70:b2:7c | Throwaway instrumented build kept out of the repository (ESP-IDF v5.3.1, the production driver `firmware/main/epd7in3e.c` copied with one change: the BUSY wait logs its duration with `esp_timer`, polling every 1 ms after a 10 ms pause; the figure runs from the command to BUSY idle and includes that 10 ms pause). Bench program only: awake, USB-C only, no battery, no Wi-Fi; five cycles (init, draw plus refresh, power-off) with solid black, white, red, blue, green (n=5) | measured |
| 3 Busy wait after refresh (min / median / max) | 30.35 s / 30.36 s / 30.62 s | 2026-11-17 | 84:c7:bb:70:b2:7c | Same instrumented build and five cycles as item 2; BUSY wait after the refresh command | measured |
| 4 Busy wait after power-off (min / median / max) | 0.15 s / 0.15 s / 0.15 s | 2026-11-17 | 84:c7:bb:70:b2:7c | Same instrumented build and five cycles as item 2; BUSY wait after the power-off command | measured |
| 5 Flash size | 16 MB (quad, 3.3 V, manufacturer 0x85, device 0x2018); chip ESP32-S3 (QFN56) v0.2, 8 MB embedded PSRAM | 2026-11-15 | 84:c7:bb:70:b2:7c | `esptool --chip esp32s3 --port /dev/cu.usbmodem101 flash-id` (esptool v5.4.0), "Detected flash size" line | measured |
| 6 Battery sense GPIO and ratio | | | | | |
| 7 Battery ADC enable pin | | | | | |
| 8 LED pin and polarity | GPIO21, lit when the pin is LOW (active low) | 2026-11-17 | 84:c7:bb:70:b2:7c | Visual check on the unit with the pin level printed in the log (same throwaway bench build) | measured |
| 9a KEY0 GPIO | GPIO5 (right arrow key); idle high, pressed low | 2026-11-17 | 84:c7:bb:70:b2:7c | Pressed the three keys in turn, left to right, with the log showing each GPIO going 1 -> 0 then 0 -> 1 (internal pull-up, idle high). Silkscreen symbols read by the owner, left to right: circular arrow, left arrow, right arrow | measured |
| 9b KEY1 GPIO | GPIO3 (left arrow key); idle high, pressed low | 2026-11-17 | 84:c7:bb:70:b2:7c | Same key test as 9a | measured |
| 9c KEY2 GPIO | GPIO2 (circular arrow key); idle high, pressed low | 2026-11-17 | 84:c7:bb:70:b2:7c | Same key test as 9a | measured |
| 10 Battery discharge profile | | | | | |

## Notes on the 2026-11-17 readings

- Unit MAC: the instrumented build did not print the MAC. The owner reports
  that the only EE04 plugged in was the unit of the rows above, so the MAC is
  recorded as reported by the owner, not read from this run.
- Items 2 to 4 are bench readings (awake, USB-C only, no battery, no Wi-Fi,
  no image download). They measure the driver's BUSY waits, not a full wake.
- Item 3 (30.35 / 30.36 / 30.62 s) and item 1 (25 / 27 / 27 s, stopwatch,
  2026-11-15) are both kept. They are different measurements: BUSY covers the
  whole refresh command, including the panel's power ramp before the visible
  flashing, while the stopwatch covers only the visible part.
- The measured waits (0.17 s, 30.62 s at most, 0.15 s) are far below
  `BUSY_TIMEOUT_MS` (60000) and within the current 190 s blit stage and 700 s
  wake budget. Applying or tightening any of these values, or setting
  `FP_MIN_REFRESH_SPACING_S`, is a separate firmware decision (a new release)
  and is not done here. The 190 s and 700 s figures are still not measured as
  a full wake.
- Items 8 and 9 equal the repository values (`CONFIG_FP_PIN_LED=21`,
  `CONFIG_FP_LED_ACTIVE_LOW=y`, `CONFIG_FP_PIN_KEY0=5`, `CONFIG_FP_PIN_KEY1=3`,
  `CONFIG_FP_PIN_KEY2=2`): they are confirmed unchanged. A stray GPIO1 change
  during the key test was the floating battery sense pin with no cell and is
  not a key.
- Items 6, 7 and 10 are not measured and stay provisional.
