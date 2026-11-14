# Second hardware: validation record

The evaluation unit: a Seeed XIAO ePaper Display Board EE04 (XIAO ESP32-S3 Plus)
with a 7.3 inch E Ink Spectra 6 panel, 800x480, from the EE04 DIY bundle. This
record holds observed results only, with the date they were observed. A check
that has not been run says so. Nothing here was run on the live frame, and the
unit has no fleet role and no production registry entry.

How each step was run, command by command, is in
[SECOND-HARDWARE-BENCH-RUNBOOK.md](SECOND-HARDWARE-BENCH-RUNBOOK.md). The battery
method is in [SECOND-HARDWARE-BATTERY.md](SECOND-HARDWARE-BATTERY.md).

## How the evidence was gathered

The owner ran the device-side commands and pasted what the bench server printed.
The evidence is therefore the server's telemetry lines (`X-Fw-Version`,
`X-Ota-Result`, `X-Boot-Reason`) and `firmware/device_report.json`, plus the
owner's description of the panel and photos. No serial log was captured: the
console is the chip's native USB, which disappears while the unit deep-sleeps,
so a log of a whole wake was never obtained. `hardware/second-hardware-logs/` was
not filled for that reason.

## Identity and connection (2026-11-14)

| Item | Observed |
|------|----------|
| MAC | 84:c7:bb:70:b2:7c |
| Chip | ESP32-S3 (QFN56), revision v0.2, 8 MB embedded PSRAM, USB-Serial/JTAG |
| Panel connector | 50-pin, jumper cap on the 50-pin side (the two positions next to the buttons), 50-pin extension cable, latches closed |
| Power | USB-C only; no battery connected during any step below |

## Cable flash and first refresh (2026-11-14)

- A signed dev-profile image (`fw-v1.0.4-68-ga3aea8a4-dev`) was cable-flashed with
  `firmware/flash-second.sh`. The script read back the written app (1118208
  bytes at 0x20000) and ended with SUCCESS.
- First boot: the panel refreshed and showed the NO CONNECTION screen. That is the
  expected screen for a unit with no Wi-Fi provisioned, and it shows the driver
  talked to the panel, sent a full frame and the panel refreshed.
- After provisioning (Wi-Fi, bench API base and enrolment secret written to the
  secret partition and read back byte for byte) the unit enrolled with the bench
  server and displayed what the server sent.

## Data path and colours (2026-11-14)

- The server's default frame for the unit (192000 bytes, all white) was displayed
  as a white panel.
- A six-colour test frame was then served: six vertical bands (black, white,
  yellow, red, blue, green) over the top 400 rows, the same bands in reverse order
  over the bottom 80 rows, a red 60x60 marker top-left and a blue one bottom-right.
- Observed: all six inks distinguishable (black reads dark violet, white reads
  grey-blue, green reads deep green: normal for Spectra 6). The picture was
  rotated by exactly 180 degrees as seen with the panel's cable tail at the top.
  A pure rotation, not a mirror: the strip order, the two markers and the band
  order all agree. With the tail at the bottom the picture reads as designed.
  Whether to turn the panel or reverse the scan direction in the driver is an
  owner decision tied to the mounting (open).
- No pixel-pair mix-up and no offset were visible in the photo.

## Defects found on the bench and fixed

| Date | Defect | Cause | Fix |
|------|--------|-------|-----|
| 2026-11-14 | A scheduled OTA offer was never served to the unit | The second profile announced the live frame's hardware key, so the server withheld every offer as a claim mismatch | `sdkconfig.second.defaults` sets the evaluation key; `check_hw_type_key.sh` requires it (PR #394) |
| 2026-11-14 | The unit never downloaded an offered image | The firmware validated the offer URL as https-only even with the dev http override, and the bench server answers over http | The offer URL follows the same dev-only override as the API base; a production image is unchanged, shown by identical code and data sections (PR #395) |

## OTA and signing bench (firmware/SIGNING.md, steps 3 to 7)

All images are dev-profile builds of one commit; versions below are what the unit
reported.

| Step | What was offered | Observed (2026-11-14) |
|------|------------------|-----------------------|
| Base | Cable-flashed `fw-v1.0.4-71-gd495d240-dev`, signed with a throwaway bench key kept outside the repository | Unit reported that version |
| Correct signature | `fw-v1.0.6-bench1`, same bench key | Downloaded, the updating screen showed, the unit rebooted and reported `fw-v1.0.6-bench1` with `X-Ota-Result=trial;fw-v1.0.6-bench1`, and at the next wake `installed;fw-v1.0.6-bench1`. The test frame was displayed again |
| Wrong signature | `fw-v1.0.7-bench2`, signed with a second throwaway key | Downloaded, then rejected: the unit kept reporting `fw-v1.0.6-bench1` and the next poll carried `X-Ota-Result=fail-image;fw-v1.0.7-bench2`. It did not install, did not boot-loop, and kept polling |
| Unsigned image | The unsigned build of `fw-v1.0.7-bench2` | Refused by the server: `firmware_cli: signature: image is not signed`, exit 1, nothing published. A first attempt with a wrong file was refused for a version mismatch instead; that is not counted as evidence |
| Raised floor | `fw-v1.0.9-bench4` built with a raised compiled floor `fw-v1.0.8` (dev-only `SKYPANE_BENCH_FLOOR`) | Installed and confirmed: `installed;fw-v1.0.9-bench4` |
| Floor refusal | `fw-v1.0.7-bench5`, above the server's floor and below the unit's | **Not run yet.** The image was prepared; the expected result is `fail-floor;fw-v1.0.7-bench5` with no download and the version unchanged |
| Wrong hardware | The live frame's image offered to the unit | **Not run.** Open owner decision, see below |

The pass conditions written in SIGNING.md (the correctly signed image installs and
the unit keeps polling; the wrongly signed image is rejected with `fail-image` and
the running firmware is kept) were observed. The floor refusal and the wrong-hardware
check are further criteria of the phase and are still open.

Wrong-hardware check, open: the live frame's firmware and the unit's share the chip
and the project name, so the unit's own checks would accept that image and run the
13.3 inch panel driver on the 7.3 inch panel, which could damage it. The proposal is
not to do it on the panel and instead to show on the server side that the live frame's
image is never offered to this unit's type, which tests already cover. The owner has
not decided.

Phase 57 does not start its release gating before the SIGNING.md table shows a pass,
and the unit takes no fleet role (no pairing, no production registry entry) before it.

## Battery readings seen (2026-11-14)

With no battery connected, `X-Battery-Mv` read between 3630 and 4180 mV and changed
from one wake to the next. These come from an input that floats without a battery and
are not measurements of a cell. The unit refuses an OTA at 3500 mV or less, so a
floating reading that falls under that value would make it answer `deferred-battery`
instead of the expected token. A real battery is needed for the battery work.

## Native layout (open)

Not yet observed on the physical panel. Before the pairing screen was reworked, a
preview of the portrait composition scaled to the landscape panel had a code about 8
mm tall and instruction text about 2 mm tall. The pairing screen of both
orientations was reworked to follow the status-screen charter (pull request #397, not
merged at the time of writing). To record here: whether the text, the plane screens and the status screens are
legible and not cropped or rotated on the glass, the refresh time measured on the
panel, and any difference between preview and panel.

## Pairing test on the panel (open)

The four checks are run on the unit against a throwaway fleet database, never the
production fleet. Each is recorded under its own heading with the date.

### Code legible

Open. Read the 8-symbol code from wall-reading distance (state the distance) and note
any ambiguous symbol.

### Claimed

Open. Claim the frame with the code and record the screen seen after the claim.

### Retired

Open. Retire the frame and record the retired screen seen on the panel.

### Re-activated

Open. Re-activate the frame and record the screen seen, which must show a new code.

The server side of this sequence (register as pending, serve the 192000-byte pairing
frame, claim with a typed code in any case, retire, re-activate) was run in a
scratch directory without the panel and behaved as the runbook describes.
