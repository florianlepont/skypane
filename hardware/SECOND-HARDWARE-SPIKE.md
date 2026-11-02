# Second hardware: driver spike (7.3" Spectra 6, 800x480)

Candidates come from `hardware/SECOND-HARDWARE.md` ("Spike candidates", cost
ranked). The spike is paper-only: manufacturer sources were read with plain
HTTP GET, nothing was flashed, no hardware was used, no purchase, cart, login
or payment call was made. Trial code lives only in `firmware/spike-7in3/`.

## Stopwatch

- Box: 1 day maximum, no hardware.
- Started: 2026-11-01 21:42 UTC (session clock).
- Time spent: see the last section of this file (about 10 minutes of session clock, 21:42 to 21:52 UTC).

## Method and limits

- Fetched with GET only: `raw.githubusercontent.com` (readable), vendor wiki
  and product pages (readable). `github.com` HTML, the GitHub API and
  archives were denied by the session proxy ("GitHub access to this repository
  is not enabled for this session"), so no commit SHA could be read. Each
  source is therefore pinned by branch name, fetch date and the SHA-256 of the
  file as fetched (first 16 hex digits, full value is reproducible from the
  URL at that moment). This is weaker than a commit pin.
- Downloaded files were kept in the session scratchpad, one directory per
  vendor, read only, never executed or compiled. Only constants and the
  command order were re-typed into the trial driver.
- Evidence strength: "source read" means the file was opened and the lines
  quoted below exist; nothing was run against a panel, so no sequence is
  hardware verified by this spike.

## Verdict table

Verdict rule (D-07): PASS only if the controller is identified, the init and
refresh sequence is found, and the pin map is known. FAIL otherwise.

| Rank | Candidate | Controller | Init + refresh sequence found | Pin map | Source licence | Verdict |
|---|---|---|---|---|---|---|
| 1 | Seeed XIAO ePaper EE04 (board + 7.3") | ED2208 (Seeed_GFX2 catalogue) | yes, 20-command init, refresh, power-off | yes (EE04 board config) | MIT (Seeed_GFX2) | **PASS** |
| 2 | Waveshare ESP32-S3-PhotoPainter | same command set as ED2208 family, chip not named by Waveshare | yes, ESP-IDF source with the Waveshare 14-command init | yes (vendor guide) | no licence file found in the repo (code not reusable) | **PASS** (sequence PASS; no code reuse) |
| 3 | Waveshare 7.3" e-Paper (E) raw / HAT (E) (+ ESP32 driver board) | same command set as ED2208 family, chip not named | yes, C reference driver with 14-command init | panel side: HAT table known; ESP32 driver board: pins known but 7.3" (E) compatibility not stated | MIT-style notice in the file header | **PASS** for the panel sequence; driver-board route has an unresolved fit question (see risks) |
| 4 | Seeed reTerminal E1002 | ED2208 (Seeed_GFX2: "GDEP073E01 / ED2208") | yes (same driver as rank 1) | yes (E1001/E1002 V1.2 schematic note) | MIT (Seeed_GFX2) | **PASS** |
| 5 | Good Display GDEP073E01 bare panel | ED2208 (stated by Seeed_GFX2 for part GDEP073E01); Good Display page unreadable | yes, via Seeed_GFX2 and Waveshare sequences for the same 800x480 part | none of its own: a bare FPC panel takes the pin map of whichever driver board is used (EE04 map above would apply) | Good Display datasheet/demo not read; reuse via Seeed MIT code | **PASS (secondary evidence only)**; vendor page, price and seller unconfirmed |

No candidate FAILed the paper spike. The ranking is unchanged (cost first,
D-06). The two things that separate the candidates are code licence and fit
with the existing firmware, not controller identification.

## Candidate 1: Seeed XIAO ePaper EE04 + 7.3" Spectra 6

- Controller: **ED2208**. Evidence: `src/runtime/ProductCatalog.cpp` in
  https://github.com/Seeed-Studio/Seeed_GFX2 (raw, branch `main`, fetched
  2026-11-01) maps `Seeed_Product::Seeed_ePaper_7INCH3_C`
  ("7.3-inch ePaper Display (Spectra 6)", 800, 480, 4, Colorful) to
  `createConfigured<Board_XIAO_ePaper_EE04, Driver_ED2208, Panel_EPaper>`.
  The EE04 wiki lists the same panel, with the board jumper set to "50 Pin"
  for "7.3-inch Spectra6 ePaper": https://wiki.seeedstudio.com/epaper_ee04/
  (this closes the open "24 or 50 pin" question of the shortlist: 50-pin).
  Seeed_GFX2 `examples/README.md` ties the same pairing to
  `Seeed_ePaper_7INCH3_C`.
- Init and refresh sequence location:
  https://raw.githubusercontent.com/Seeed-Studio/Seeed_GFX2/main/src/driver/epaper/Driver_ED2208.cpp
  (sha256 7350cf3dc95d7116...). `init()`: reset via
  `hardwareReset(20, 10, 1)` (20 ms and 10 ms phases) for 800x480, then commands in order
  AA (6 data), 01 (6), 00 (2), 03 (4), 05 (4), 06 (4), 08 (4), 13 (2), 30 (1),
  41 (1), 50 (1), 60 (2), 61 (4: width and height big-endian), 82 (1), 84 (1),
  86 (1), E3 (1), E0 (1), E6 (1), then 04 power on and BUSY wait. That is 20
  commands. Refresh: write 4 bpp rows with command 10, then `update()` sends
  12 with data 00 and waits for BUSY. Power-off: 02 with data 00 and BUSY wait.
- Colour transfer codes: the driver remaps its internal 4-bit indices before
  sending (`colorGet`: 0F->0, 00->1, 0D->5, 02->6, 0B->2, 06->3). The sent
  values (0 black, 1 white, 2 yellow, 3 red, 5 blue, 6 green) match the
  Waveshare 7.3" (E) table below. 4 bits per pixel, two pixels per byte, high
  nibble first (`pushColors`: `(colorGet(hi) << 4) | colorGet(lo)`). 800x480 at
  4 bpp is 192000 bytes; single controller, one chip select.
- BUSY: ready level is high (`waitForReadyPin(pin, true, timeoutMs)`); the
  driver waits 10 ms before the first sample; default timeout 60000 ms
  (`busyWait(uint32_t timeoutMs = 60000)` in `Driver_ED2208.h`).
- Sleep: for GDEP073E01 the driver deliberately sends only POF (02 00) and
  does not enter deep sleep (07 A5); its comment says deep sleep discards the
  setup and the wake path sends only PON. The Waveshare reference does send
  07 A5 and re-runs the full init each refresh. The two sources disagree on
  what is safe between refreshes; this matters for battery life and is listed
  as a risk, not resolved here.
- Pin map (EE04 board), from
  https://raw.githubusercontent.com/Seeed-Studio/Seeed_GFX2/main/src/board/configs/XIAO_ePaper_Board_Configs.h
  (sha256 6e28ce93004d8f24...) and `BoardConfig.h` (field order cs, dc, rst,
  backlight, mosi, miso, sclk, touchCS, touchIRQ, busy, enable, cs2):
  `Config_XIAO_ePaper_EE04_Board::pins() = esp32DisplayPins(10, -1)` which is
  `BoardPinConfig(44, dc=10, 38, -1, D10, -1, D8, -1, -1, 4, 43)`.

  | Signal | GPIO | Source |
  |---|---|---|
  | SCK | 7 (D8) | `sclk = D8` |
  | MOSI | 9 (D10) | `mosi = D10` |
  | CS | 44 | `cs = 44` |
  | DC | 10 | `esp32DisplayPins(dc = 10, ...)` |
  | RST | 38 | `rst = 38` |
  | BUSY | 4 | `busy = 4` |
  | EN (panel supply) | 43 | `enable = 43` |

  The same numbers (SCK 7, MOSI 9, CS 44, DC 10, RST 38, BUSY 4, EN 43) are the
  EE02 values already committed in `firmware/sdkconfig.ee02.defaults`, which
  were validated on the real EE02. EE04 differs from EE02 by having no second
  chip select, and by the 50-pin jumper for this panel. SPI settings in the
  vendor config: write 10 MHz, mode 0, secondary host (HSPI) on ESP32-S3.
- Licence: https://raw.githubusercontent.com/Seeed-Studio/Seeed_GFX2/main/LICENSE
  begins "This library is original work by Seeed Studio." then "MIT License".
  Compatible with Apache-2.0 when the notice is kept. The trial driver
  re-types the command bytes only and cites the file; no code is copied.
- Board: XIAO ESP32-S3 Plus (the EE04 board), so the ESP-IDF target matches.
- Not found: Seeed publishes no ESP-IDF (C) driver for EE04, only this Arduino
  C++ library; ESP-IDF 5.3.1 behaviour of the port is untested on hardware.

## Candidate 2: Waveshare ESP32-S3-PhotoPainter

- Controller: not named by Waveshare. The ESP-IDF source uses the same
  command set and 800x480 4 bpp format as the 7.3" (E) demo
  (`0xAA` CMDH first, `0x61` = 03 20 01 E0), so it is the same controller
  family as candidate 1; the chip name ED2208 comes only from Seeed.
- Sources: https://github.com/wurongmin/ESP32-S3-PhotoPainter (linked from
  https://www.waveshare.com/wiki/ESP32-S3-PhotoPainter and
  https://docs.waveshare.com/ESP32-S3-PhotoPainter), raw `main`, fetched
  2026-11-01. Panel code: `01_Example/xiaozhi-esp32/components/port_bsp/display_bsp.cpp`
  (sha256 df897df0ba6b67be...): `EPD_Init`, `EPD_TurnOnDisplay` (04, wait,
  06 booster, 12 00, wait, 02 00, wait), same as Waveshare's C reference.
  SPI 40 MHz, mode 0, half duplex, CS driven by code, in IDF.
- Pin map: the repo's operating guide
  (`01_Example/xiaozhi-esp32-IDF6.1/代码分析与完整操作说明.md`, section 15.2)
  states "MOSI / SCLK / DC / CS / RST / BUSY = 11 / 10 / 8 / 9 / 12 / 13".
- Licence: no `LICENSE` or `LICENSE.md` at the repo root (both 404). The
  derived Xiaozhi project is a separate matter. Without a licence the code is
  not reusable; only the command facts (also published by Waveshare under
  MIT-style notice, candidate 3) are.
- ESP-IDF versions in that repo: 5.5.2 and 6.1, not 5.3.1 (the repo README
  says "Both modified versions were compiled in the original development
  workspace" and the copy "has not been rebuilt ... in its new location").
  The board is an ESP32-S3-WROOM-1 with a different pin map from the existing
  firmware, and it carries audio, SD, RTC and PMIC (AXP2101 at I2C 0x34) that
  the existing firmware does not use.
- Not found: Waveshare wiki does not list the panel controller name.

## Candidate 3: Waveshare 7.3" e-Paper (E) raw panel / HAT (E)

- Controller: not named. Sequence source:
  https://raw.githubusercontent.com/waveshareteam/e-Paper/master/RaspberryPi_JetsonNano/c/lib/e-Paper/EPD_7in3e.c
  and `EPD_7in3e.h` (sha256 of the .c: 9f82c8f6520a9304...), fetched
  2026-11-01. `EPD_7IN3E_Init`: reset (high 20 ms, low 2 ms, high 20 ms), wait
  BUSY, 30 ms, then AA (6), 01 (1: 3F), 00 (2: 5F 69), 03 (4), 05 (4), 06 (4),
  08 (4), 30 (1: 03), 50 (1: 3F), 60 (2), 61 (4: 03 20 01 E0), 84 (1: 01), E3
  (1: 2F), 04 and BUSY wait (14 commands). Refresh (`TurnOnDisplay`): 04, wait,
  06 (6F 1F 17 49), 12 00, wait, 02 00, wait. Sleep: 02 00, wait, 07 A5.
  BUSY: low is busy, high is idle, no timeout in the reference loop.
- The init differs from candidate 1 in a few values (for example command 01
  has one data byte here and six in Seeed's, 06 data 6F 1F 17 49 here and
  6F 1F 16 25 in Seeed's init, PLL 03 vs 02). Both target 800x480 Spectra 6;
  which set is the better one for a given production lot is something only a
  panel can answer.
- Colour codes in `EPD_7in3e.h`: black 0, white 1, yellow 2, red 3, blue 5,
  green 6.
- Pin map: the HAT/raw panel has the 8-pin interface (VCC, GND, DIN, CLK, CS,
  DC, RST, BUSY); the host pins are the host board's. Waveshare E-Paper ESP32
  Driver Board (https://www.waveshare.com/wiki/E-Paper_ESP32_Driver_Board):
  DIN P14, SCLK P13, CS P15, DC P27, RST P26, BUSY P25 ("board fixed
  connection"). That board is described only as "Onboard ESP32" (no S3 is
  stated); its wiki's panel list read for this spike does not include the
  7.3" (E) panel.
- Licence: the source file header carries a permission notice (use, copy,
  modify, merge, publish, distribute, sublicense and/or sell, notice must be
  kept). It is the same MIT-style notice already reproduced in
  `firmware/main/epd13in3e.c`. No separate `LICENSE` file was found at the
  paths tried (`LICENSE`, `LICENSE.md`, `LICENSE.txt`, `license`: all 404), so
  the file-level notice is the evidence.
- Not found: the Arduino/ESP-IDF example directory name for 7in3e in that
  repo (guessed `Arduino/epd7in3e/` returned 404); the C/Raspberry Pi
  library was used instead.

## Candidate 4: Seeed reTerminal E1002

- Controller: ED2208, `Config_reTerminal_E1002_ED2208` in
  https://raw.githubusercontent.com/Seeed-Studio/Seeed_GFX2/main/src/panel/configs/Seeed_Panel_Configs.h
  with the comment "panel/controller: GDEP073E01 / ED2208", 800x480, Spectra 6,
  no partial refresh. Same `Driver_ED2208.cpp` as candidate 1.
- Pin map (`reTerminal_ePaper_Board_Configs.h`, comment "E1001/E1002 V1.2
  schematics"): CS 10, DC 11, RST 12, BUSY 13, MOSI 9, MISO 8, SCK 7; the SD
  slot shares the SPI pins (SD CS GPIO14, SD power GPIO16).
- Licence: MIT (Seeed_GFX2).
- Exceeds the 100 EUR target (shortlist). Kept for completeness.

## Candidate 5: Good Display GDEP073E01 (bare panel)

- Good Display's own pages and datasheet could not be read:
  https://www.good-display.com/product/533.html and `/product/381.html`
  returned HTTP 404 (and the site root 404); a first attempt was reset. The
  other domain https://www.e-paper-display.com/products_detail/productId=533.html
  resolves to a different product (a 3.71" panel), so it was not used.
- Controller: Seeed_GFX2 `Driver_ED2208.cpp` header states the driver is
  "used by GDEP040E01 (400x600) and GDEP073E01 (800x480)" and the E1002 config
  names "GDEP073E01 / ED2208". That is a vendor statement by a third party
  (Seeed), not Good Display's datasheet.
- Sequence: as candidates 1 and 3.
- Pin map: none of its own. FPC pin count and pitch are unconfirmed; the 50-pin
  FPC of the Seeed 7.3" panel is the only connector evidence.
- Licence: no Good Display code read. Reuse only through candidates 1 and 3.

## Not found (and what was tried)

- Commit SHA of any vendor repository: GitHub API, github.com HTML and
  archives denied by the session proxy; raw file reads worked.
- Good Display datasheet, demo code, connector, price: see candidate 5.
- ESP-IDF driver published by Seeed for EE04: none found; Seeed_GFX2 is
  Arduino/C++.
- Waveshare controller name: not on the product page, wiki or source header.
- Waveshare repository `LICENSE` file: not found at four paths.
- PhotoPainter repository licence: not found.
- Waveshare ESP32 driver board support for the 7.3" (E): not stated on its wiki.
- Timeout for BUSY in the Waveshare reference: none (infinite loop).

## Trial driver and build evidence

Files (all new, under `firmware/spike-7in3/`): `main/epd7in3e_trial.h`,
`main/epd7in3e_trial.c`, `main/spike_main.c`, `main/CMakeLists.txt`,
`CMakeLists.txt`, `test_epd7in3e_trial.c`, `run-spike-host-test.sh`,
`build-spike.sh`. The driver implements the front-runner (candidate 1): the
20-command init table of the Seeed ED2208 driver, 800x480 at 4 bpp
(192000 bytes, single controller, one chip select, confirmed from the
sources above, unlike the dual-controller 960000-byte 13.3" buffer), a
validating pixel packer, pin tables for the EE04 and the PhotoPainter, and a
thin SPI/GPIO layer (init, blit, sleep) behind `ESP_PLATFORM`. The PhotoPainter
table is data only; no second code path exists.

Source reuse: only command bytes and their order were re-typed from the MIT
licensed Seeed_GFX2 `Driver_ED2208.cpp` (cited in the file header). Nothing
was copied from the PhotoPainter repository, which has no licence file. No
code was copied from the Waveshare reference.

### Host test (red then green)

- Red: the test was written first; running `run-spike-host-test.sh` before the
  driver existed failed (`epd7in3e_trial.c: No such file or directory`).
- Green: `sh firmware/spike-7in3/run-spike-host-test.sh` compiles with
  `cc -Wall -Wextra -std=c11` and prints `epd7in3e_trial: all cases pass`. It
  checks the packed size (192000 bytes, high nibble first), the init table
  order, lengths and the 800x480 resolution bytes, the refresh command,
  rejection of a wrong pixel count, a short output buffer, null pointers and
  out-of-range colour codes (including 4), that a rejected call writes
  nothing, and the pin tables (EE04 equals the committed EE02 values).

### Container build (ESP-IDF 5.3.1): PASS, with an image-provenance note

- Command: `SPIKE_BUILD_DIR=<scratchpad>/spike-build sh firmware/spike-7in3/build-spike.sh build`
  (the build directory is outside the repository; the source is mounted
  read-only; the script accepts only `build` and `clean`, never flashes).
- Result: exit 0, `Project build complete`, 1007/1007 steps, target
  `esp32s3`, `skypane_spike_7in3.bin` 0x3b460 bytes, no compiler warnings in
  the build log. `idf.py --version` inside the image reports `ESP-IDF v5.3.1`.
- Image provenance: `docker pull espressif/idf:v5.3.1` from Docker Hub failed
  with `unexpected status from HEAD request to
  https://registry-1.docker.io/v2/espressif/idf/manifests/v5.3.1: 429 Too Many
  Requests`; `ghcr.io/espressif/idf:v5.3.1` returned `denied`. The Docker
  daemon was not running at the start (`failed to connect to the docker API
  at unix:///var/run/docker.sock`) and was started by hand. The image was
  pulled from the Docker Hub mirror `mirror.gcr.io/espressif/idf:v5.3.1`
  (digest `sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d`,
  image id `55ab243e8758`) and tagged locally as `espressif/idf:v5.3.1`. The
  tag matches `firmware/build.sh`, but this run did not compare that digest
  with Docker Hub's own, because Docker Hub answered 429.
- What this proves: the trial component compiles and links against ESP-IDF
  5.3.1 for esp32s3. What it does not prove: any behaviour on a panel (SPI
  chip-select timing per row, the BUSY polarity and timing, the
  between-refresh power state, the 10 MHz clock) is untested.

### Checks that stay green

- `sh firmware/tests/run_host_tests.sh`: 14 suites passed.
- `server/.venv/bin/python3 -m pytest stub-server/test_phase47_freeze.py -n 0 --no-cov`: 21 passed.
- `python3 scripts/check_comment_history.py check`: exit 0.
- `git diff --quiet` over `firmware/main`, `firmware/CMakeLists.txt`,
  `firmware/build.sh`, `firmware/tests`, `firmware/sdkconfig.defaults`,
  `firmware/sdkconfig.ee02.defaults` and `hardware`: no tracked file modified;
  `git status` shows only new files under `firmware/spike-7in3/` plus this
  document. Nothing was flashed.

## Recommendation (cost first, D-06)

Recommended: **Seeed XIAO ePaper EE04 (board + 7.3" panel)**, cheapest
candidate that passed: at least 78.73 EUR TTC (delivery excluded), 98.73 EUR
with the delivery assumption of the shortlist, against the 100 EUR target.
Every unconfirmed shortlist item still applies (VAT treatment of the Seeed
price, delivery to France, battery stock at Kubii, which is currently out of
stock). Runner-up: **Waveshare ESP32-S3-PhotoPainter**, 90.48 EUR TTC at least
(105.48 with assumed delivery, above the target), not recommended first
because it costs more, carries unused parts (audio, SD, PMIC), and its only
published ESP-IDF code is unlicensed and for IDF 5.5.2/6.1.

## Risks

- The driver is paper-only: no panel, no oscilloscope, no refresh was ever
  seen. Two vendor init sets for the same 800x480 panel differ in several
  values; the right one for a given lot is unknown until a panel answers.
- Sleep behaviour is contested: Seeed keeps the controller powered-off but not
  in deep sleep for this panel, Waveshare sends deep sleep. This decides the
  standby current and therefore battery life (a battery sample is Part 2).
- 4 bpp codes 0,1,2,3,5,6 are sent as is; the mapping from the project's image
  container palette to these codes is not decided here (the packer takes
  controller codes, not container indices).
- Seeed publishes no ESP-IDF driver; the port from Arduino/C++ concentrates
  the risk in SPI chip-select handling and timing. A 60 s BUSY timeout comes
  from the vendor default and is also untested.
- Fit with the existing firmware: the panel seam (`fp_panel_draw` and the
  Kconfig pin overlay) is unchanged; a real port still needs a Kconfig overlay
  for EE04 and a second driver behind `panel.c`, plus the container reader of
  the image format. Not started and not in scope here.
- Shop risk (unchanged from the shortlist): Seeed shipping to France and total
  cost are unconfirmed; the Kubii battery is out of stock; the enclosure is
  not priced.
- Good Display is not purchasable evidence: its pages returned 404 to a plain
  GET, so price, seller and connector are unconfirmed.
- Waveshare driver-board route: ESP32 board without stated S3, 7.3" (E) not in
  the supported list, pins differ; building for esp32s3 would not be enough.
- Image-provenance caveat for the build evidence (digest not compared to
  Docker Hub).

## Time spent

- Session clock at the end of Task 2: 21:52 UTC, started 21:42 UTC, so about
  10 minutes elapsed of the 1-day box. Most of it was spent finding readable
  raw paths (the GitHub API and HTML were denied) and on the image pull and
  first build. No candidate was left unfinished.

Nothing was bought, carted, ordered or paid. The owner decision is pending
and not part of this spike.
