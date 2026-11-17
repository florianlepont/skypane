# Second board: support guide

The second hardware type is the Seeed XIAO ePaper EE04 (XIAO ESP32-S3 Plus
with a 7.3" E Ink Spectra 6 panel, 800x480). Its server-side key is
`seeed-ee04-7in3-spectra6`. The live frame is the EE02
(`xiao-ee02-13in3-spectra6`) and is a different device; nothing in this
guide may be run against it.

The records of how the board was chosen and validated are
`hardware/SECOND-HARDWARE.md`, `SECOND-HARDWARE-VALIDATION.md`,
`SECOND-HARDWARE-BATTERY.md` and `SECOND-HARDWARE-BENCH-RUNBOOK.md`.
They are history and are not edited by this guide.

## Status

No typed release of this board has been published, and the production
switch is closed. The image has been built and size-checked in CI and has
never been run against a panel in this repository's records.

## Build and size gate

```bash
SKYPANE_BOARD=second firmware/build.sh
```

The output is `firmware/build-second` (`build-second-dev` with
`SKYPANE_PROFILE=dev`), separate from `firmware/build-ee02`. Check that
the build is the second board, then the size gate CI applies (the OTA slot
is 0x250000 bytes; the image must stay under 90 percent of it):

```bash
sh firmware/tests/check_production_config.sh built firmware/build-second second
size=$(stat -c %s firmware/build-second/skypane.bin)
limit=$(( 0x250000 * 90 / 100 ))
test "${size}" -le "${limit}" && echo "size ok: ${size} <= ${limit}"
```

Signing of a bench image follows `firmware/SIGNING.md` ("Local signing for
bench images"). There is one signing key for both boards.

## First flash

Declare the live frame once in your shell profile, so a wrong port or a
wrong chip is refused:

```bash
export SKYPANE_LIVE_FRAME_PORT=<serial-port-of-the-live-frame>
export SKYPANE_LIVE_FRAME_MAC=<mac-of-the-live-frame>
```

Then flash the evaluation unit with `firmware/flash-second.sh
<serial-port>`. The script prints the chip MAC before writing anything,
refuses a declared port or MAC, and needs the MAC typed back at an
interactive prompt.

## Provisioning

`firmware/provision.sh <serial-port> --wifi-ssid <ssid> --api-base <url>`
writes the per-device enrolment secret, Wi-Fi and API base into the
`secret` partition. It applies the same typed live-frame guard as
`flash-second.sh`:

- a port equal to `SKYPANE_LIVE_FRAME_PORT`, or a chip MAC equal to
  `SKYPANE_LIVE_FRAME_MAC` (case-insensitive), is refused with exit code 3
  before anything is written;
- outside `--dry-run`, the chip MAC is printed and must be typed back;
- `--dry-run <mac>` applies only the live-MAC refusal and never prompts.

Limit: the chip cannot tell its board type, so the guard knows the live
frame only through the two variables you declared. If they are unset, the
only protection left is the typed MAC. Unsetting them is the deliberate
override, and it is yours to make knowingly. Check the MAC against the
unit's label and against the record of the live frame before typing it.

## Enrolment and pairing

Enrolment and pairing are the same as for any frame (`deploy/README.md`,
"Device enrolment" and "Pairing, retiring and re-activating a frame"):
register the printed MAC and secret hash as pending with the hardware type
`seeed-ee04-7in3-spectra6`, power the frame, type the code it shows into
the Fleet page, and choose the owner. While the production switch is
closed the production server does not know this type, so do not expect
it to work there until the owner lifts the switch.

## Over-the-air updates

Updates use the typed registry `firmware/registry.seeed-ee04-7in3-spectra6.json`.
A release is published as `skypane-<key>-<tag>.bin` plus
`release-<key>.json` and imported by the reviewed deploy (`deploy/README.md`,
"Per-hardware-type releases"). After import it shows as available on the
companion Update page; nothing installs automatically. A typed release
published while the switch is closed is skipped with a notice and imported
by the first deploy after the switch is lifted.

## Measured and provisional values

| Value | State | Where it comes from |
|-------|-------|---------------------|
| Wake budget (`CONFIG_SKYPANE_WAKE_BUDGET_S` = 700 s) | provisional, derived by formula | The 190 s blit stage is a bounded estimate, not a measurement; see `firmware/sdkconfig.second.defaults` |
| Refresh spacing (`FP_MIN_REFRESH_SPACING_S`) | provisional, the firmware default of 60 s | Not tuned for this panel |
| Panel pins | provisional | Taken from the Seeed_GFX2 board configuration (see `firmware/VENDOR.md`) and the board profile `firmware/sdkconfig.second.defaults`; never driven on a bench |
| Battery profile | provisional, a copy | Registered with values copied from the live frame's profile, each marked provisional in `server/hardware.py`; the 800x480 unit has no discharge run |
| Panel init sequence | not measured | Re-typed from the vendor driver; see `firmware/VENDOR.md` |

Nothing in this table is a measured value for the second board. When the
owner's bench measurements land (`hardware/SECOND-HARDWARE-BENCH-RUNBOOK.md`),
they replace the provisional entries one by one and this table is updated
with the measurement and its date. Until then, do not quote a battery life
or a refresh time for this board as measured.
