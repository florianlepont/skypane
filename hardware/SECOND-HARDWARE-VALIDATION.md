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
  Decided on 2026-11-14: the owner will mount the unit with the cable tail at the
  bottom of the frame, so the picture reads as designed and the scan direction of
  the driver is not changed. Only that mounting is supported; the same panel
  mounted tail-up shows the picture upside down.
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
| Floor refusal | `fw-v1.0.7-bench5`, above the server's floor and below the unit's (`fw-v1.0.8`) | Refused without a download: no `GET /fw/...` line and no updating screen, and the next poll carried `X-Ota-Result=fail-floor;fw-v1.0.7-bench5` with the unit still on `fw-v1.0.9-bench4`, still polling. The token was resent at each following wake until the bench server stopped offering it, as the firmware does until a poll answers. The refusal happened at a reading of 4176 mV, above the 3500 mV battery refusal that comes first |
| Wrong hardware | The live frame's image | **Not done on the panel, by the owner's decision (2026-11-14).** Shown on the server side instead, see below |

The pass conditions written in SIGNING.md (the correctly signed image installs and
the unit keeps polling; the wrongly signed image is rejected with `fail-image` and
the running firmware is kept) were observed, and so was the floor refusal. The
wrong-hardware check, a further criterion of the phase, is shown on the server side
only.

Wrong-hardware check, decided: the live frame's firmware and the unit's share the chip
and the project name, so the unit's own checks would accept that image and run the
13.3 inch panel driver on the 7.3 inch panel, which could damage it. On 2026-11-14 the
owner decided not to do it on the panel. What was shown instead, in a scratch server
state directory with no panel involved:

- A legacy-type image (a build of the live frame's profile, signed with a throwaway key)
  was published to the legacy registry and scheduled there.
- The unit was registered as the evaluation type and polled four times: three polls
  announcing its own type, one announcing the legacy type. Every answer carried
  `firmware: null`. The server never offered the live frame's image to this unit.
- The legacy registry file was byte-identical before and after the polls, and no
  registry document of the evaluation type was created by them.

This shows that the server withholds a legacy image from this unit. It does not show
what the unit would do if it were given one: that device-side behaviour is not tested,
by choice, and the server's separation is what protects it.

Phase 57 does not start its release gating before the SIGNING.md table shows a pass,
and the unit takes no fleet role (no pairing, no production registry entry) before it.

## Battery readings seen (2026-11-14)

With no battery connected, `X-Battery-Mv` read between 3630 and 4180 mV and changed
from one wake to the next. These come from an input that floats without a battery and
are not measurements of a cell. The unit refuses an OTA at 3500 mV or less, so a
floating reading that falls under that value would make it answer `deferred-battery`
instead of the expected token. A real battery is needed for the battery work.

## Native layout (partly recorded)

Observed on 2026-11-14 on the physical panel, mounted flat on the bench: the six-colour
test frame (see above), the pairing screen and the retired screen were displayed at
the panel's own size. The owner reported the pairing code readable and unambiguous from
4 metres, the pairing screen legible, and the retired screen shown as designed.

Not recorded, so not claimed: whether any screen was cropped, offset or rotated beyond
the 180 degree turn explained above, whether "legible" also covers the small instruction
text under the code and from how far, the refresh time measured on the panel, and any
difference between the previews and the glass. The plane screens (flight screens) were not shown on
the unit in this session.

## Pairing test on the panel (2026-11-14)

The four checks were run on the unit against a throwaway fleet database, never the
production fleet, with the pairing screen as merged in pull request #397 (the status
charter composition: the glyph, a label, a giant `PAIR` and the code as the second
giant line). Each is recorded under its own heading.

### Code legible

Passed. The 8-symbol code on the panel was read from 4 metres, the screen was legible
and no symbol was ambiguous, according to the owner. It was then typed and accepted by the claim, which
confirms it was read correctly.

### Claimed

Passed. The frame was claimed with the code shown on the panel and the claim returned
the new device and its owner. Two earlier claim attempts were refused: one for a reason
that was not established (it is not known whether the real code was typed) and one
because the script was run with its placeholder text instead of the code. The refusal
message is the same for every cause, so it does not say which. The screen shown on the
panel after the claim was not recorded; a white panel is what the bench server sends a
claimed frame.

### Retired

Passed. After the frame was retired, the panel showed the retired screen (FRAME RETIRED)
at the next wake.

### Re-activated

Passed. After the frame was re-activated, the panel showed the pairing screen again with
a new code (`M9FPRVY7`), different from the first (`XNSE-SKZD`).

The server side of this sequence (register as pending, serve the 192000-byte pairing
frame, claim with a typed code in any case, retire, re-activate) was run in a
scratch directory without the panel and behaved as the runbook describes.
