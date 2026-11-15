# Combined legacy-frame firmware release: owner instructions

Every command below is written for the owner to run later. Nothing in this
document has been executed by the phase.

## 1. Status

Prepared, not published. The phase delivered code, tests and documents on the
branch `firmware/phase-57-combined-release`. The phase never did any of these:

- created or pushed a tag (no `fw-v*` tag exists because of this work)
- published a GitHub Release or triggered `firmware-release.yml`
- scheduled anything for a frame, or imported anything into the production
  registry
- merged anything to `main`, or called `publish_release`
- flashed a device or ran a bench session

The C changes in `firmware/main/api_client.c`, `api_client.h` and
`state_machine.c` were not compiled locally (no ESP-IDF build was available).
The first compile happens in `.github/workflows/firmware.yml` on the pull
request, and the first run on glass is the bench in `57-BENCH-CHECKLIST.md`.

## 2. Preconditions

None of these is ticked. Tick each one yourself, in order, before section 4.

- [ ] Phase 47 allows the release (owner statement; the 47.1 measurement
      window decision in section 3 is made).
- [ ] The signing bench in `firmware/SIGNING.md` ("Bench procedure") passed on
      the EE04 unit, with the observed results written into its "Bench results"
      table and into `57-BENCH-CHECKLIST.md`. The table records a pass on
      2026-11-14 (one EE04 unit, dev images signed with throwaway keys, no
      serial log); confirm that this is enough for you, and that items B1 to
      B8 of the checklist are ticked and B9 is yours to sign.
- [ ] The firmware code is merged to `main` with CI green, including the
      firmware compile and size step (done: merged in #391; re-check that
      nothing newer touched `firmware/` since).
- [ ] The server release containing the hardware-claim rule is deployed first.
      It is safe for frames that send no `X-Hw-Type` header, so deploying it
      ahead of the firmware changes nothing for the live frame.
- [ ] The live frame's running version and install date are read with
      `firmware_cli list` (command in section 4) and written down.
- [ ] The live frame's fleet type equals `xiao-ee02-13in3-spectra6` (check in
      the companion; a frame typed otherwise gets no offer and no container).
- [ ] You have given the explicit go-ahead to publish a release that reaches
      the live frame.

## 3. Contents and effect on the live frame

- The image reader: after the download and before the panel draw, the frame
  validates the body (legacy raw or container, CRC-32 checked). A body it
  rejects keeps the last image, sets a sticky flag and the frame asks for the
  raw image from then on.
- Two request headers on the display request only: `X-Img-Fmt: 1` (while the
  sticky flag is clear) and `X-Hw-Type: xiao-ee02-13in3-spectra6`. The server
  withdraws the offer and the container if the claim contradicts the assigned
  type.
- A 401/403 (`auth`, `enrol`) no longer draws the NO CONNECTION screen. The
  frame keeps the last image and backs off along 300 s, then growing, up to a
  6 h cap (21600 s); one successful poll resets it.
- One extra redraw: the first wake that downloads a container changes the
  served hash, so the panel refreshes once; later wakes hash-skip again.
- Restart of the 14-day measurement window: installing a release changes the
  firmware under test, so the 47.1 baseline window restarts. Decide this
  before section 4 (it is the 47.1 window decision in section 2).
- The 47.2 work needs its own later release; this one does not include it.

## 4. Procedure (owner actions)

Everything in this section is run by the owner. The version name is a
recommendation only: `fw-v1.1.0` is proposed because the first OTA-capable
release is `fw-v1.0.0` and this adds behaviour without changing the device
protocol. Choose the tag yourself; it must match `fw-vMAJOR.MINOR.PATCH` and
be above the floor. `firmware/SIGNING.md` and the workflow guard enforce the
shape and that the tagged commit is on `main`.

1. Read what is published and what the frame runs now (owner action):
   ```
   ssh ubuntu@<vps-ip> "sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec /opt/skypane/venv/bin/python3 -m server.firmware_cli --state-dir /opt/skypane/state list'"
   ```
2. Merge the reviewed firmware pull request to `main` (owner action).
3. Tag the merge commit and push the tag (owner action; the tag name is yours
   to pick, `fw-v1.1.0` below is only the recommendation):
   ```
   git checkout main && git pull --ff-only
   git tag fw-v1.1.0
   git push origin fw-v1.1.0
   ```
4. In GitHub Actions, open the `Firmware release` run. The `guard` job checks
   the tag shape and that the commit is an ancestor of `origin/main`. Approve
   the `firmware-signing` environment for the `release` job (you are the
   required reviewer). Never paste or copy the signing key anywhere.
5. Wait for the `release` job. It builds with the tag as the exact version,
   checks the production configuration and log contract, signs, verifies the
   signature against the committed public key, checks the image descriptor,
   generates `release.json` and publishes the GitHub Release.
6. Verify the signature and hash yourself (section 5) on the downloaded
   assets before anything is scheduled.
7. The workflow's last step dispatches `ci.yml` on `main`. Approve the
   `production` environment there; the deploy downloads every `fw-v*`
   release and imports it with `firmware_cli import-dir`. A release whose
   bytes do not match its manifest fails activation before the swap.
8. Confirm the import with the `list` command from step 1. The release is now
   only available; nothing is installed automatically.
9. Schedule it to the legacy type from the companion Update page, choosing the
   frame typed `xiao-ee02-13in3-spectra6` (owner action in the UI; the exact
   button labels were not re-checked against the running companion).

## 5. Signature verification

Run on your own machine, on the files downloaded from the GitHub Release
(`skypane-<tag>.bin`, `release.json`). Use the public key committed at
`firmware/signing/skypane-signing-pubkey.pem`. `espsecure.py` comes from the
`esptool` package, or run it in the pinned `espressif/idf:v5.3.1` container as
the workflow does.

```
espsecure.py verify_signature --version 2 \
    --keyfile firmware/signing/skypane-signing-pubkey.pem \
    skypane-fw-v1.1.0.bin
sha256sum skypane-fw-v1.1.0.bin
```

Compare the printed digest with the `sha256` field of `release.json`, and the
file size with its `size` field. Both must match exactly. The workflow already
ran the signature check once; this repeats it independently. A server-side
`check-image` (see `deploy/README.md`) additionally compares the embedded key
modulus, but never verifies the signature itself.

## 6. Rollback and abort

- Abort before the offer: cancel the schedule in the companion Update page
  before the frame next wakes. Once the frame has received the offer it will
  attempt the install on that wake (not confirmed how late a cancel can still
  win; cancel as early as possible).
- Automatic rollback of a bad trial: the new image boots on trial and is
  confirmed only after its first successful poll, just before deep sleep. A
  crash, watchdog, brownout or failed poll leaves it unconfirmed and the
  bootloader returns to the previous slot. The server counts failed attempts;
  after 3 (`MAX_ATTEMPTS`) the schedule is marked failed and stops offering.
- Voluntary rollback: schedule an older, already-published release that is at
  or above the version floor (`fw-v1.0.0`). `firmware/SIGNING.md` states this
  stays allowed; the lower-build refusal applies at publish time only.
- Last resort: a USB flash of a signed release over the cable. This needs
  physical access to the frame. The sequence below is the one used on the live
  frame on 2026-09-29 (`hardware/BRINGUP-LOG.md`, H42-04), adapted to a
  recovery release; it has **not** been re-run for a recent tag, so re-derive
  the offsets first (step 2) and read the cautions at the end.

  What it does not touch: the `secret` partition (the enrolment secret and
  Wi-Fi credentials) is not written by this flash, and neither is the main
  `nvs` partition (bearer token, image hash).

  1. Download the five assets of the release to flash back to (the last
     known good one, for example `fw-v1.0.4`) and check the image before
     anything is written. An unsigned or wrongly signed image aborts at every
     boot and can then only be fixed by another USB flash:
     ```
     REL=~/skypane-recovery/rel-fw-v1.0.4
     mkdir -p "$REL" && gh release download fw-v1.0.4 --dir "$REL"
     espsecure.py verify_signature --version 2 --keyfile firmware/signing/skypane-signing-pubkey.pem "$REL/skypane-fw-v1.0.4.bin"
     shasum -a 256 "$REL/skypane-fw-v1.0.4.bin"
     python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['sha256'])" "$REL/release.json"
     ```
     The signature must verify and the two SHA-256 values must match
     (ignoring a `sha256:` prefix).
  2. Re-derive the offsets from the partition table before writing:
     ```
     awk -F, '/^[a-z_0-9]+,/ {gsub(/ /,""); print $1, $4, $5}' firmware/partitions.csv
     ```
     At the time of writing: `otadata` 0xf000, `factory` 0x20000 (size
     0x250000), `ota_0` right after `factory` at 0x270000. The bootloader is
     at 0x0 and the partition table at 0x8000.
  3. Find the port (`ls /dev/cu.*` before and after plugging in the cable),
     then write the five files. The same app image goes into `factory` and
     `ota_0`:
     ```
     PORT=/dev/cu.usbmodemXXXX
     esptool --chip esp32s3 --port "$PORT" write-flash \
         --flash-mode dio --flash-freq 80m --flash-size keep \
         0x0      "$REL/bootloader-fw-v1.0.4.bin" \
         0x8000   "$REL/partition-table-fw-v1.0.4.bin" \
         0xf000   "$REL/ota_data_initial-fw-v1.0.4.bin" \
         0x20000  "$REL/skypane-fw-v1.0.4.bin" \
         0x270000 "$REL/skypane-fw-v1.0.4.bin"
     ```
  4. Read both app regions back and compare them with the image, then reset
     so the firmware runs:
     ```
     SIZE=$(stat -f%z "$REL/skypane-fw-v1.0.4.bin")
     for OFF in 0x20000 0x270000; do
         esptool --chip esp32s3 --port "$PORT" --after no-reset read-flash $OFF $SIZE /tmp/readback.bin &&
         cmp /tmp/readback.bin "$REL/skypane-fw-v1.0.4.bin" && echo "$OFF matches"
     done
     esptool --chip esp32s3 --port "$PORT" --after hard-reset read-mac
     ```
     Both offsets must print `matches`.
  5. Check that the frame polls: the companion Update page (or the bench or
     production telemetry) must show `X-Fw-Version` equal to the flashed tag
     and the next wake on the usual cadence.

  Cautions: (a) the frame's USB port exists only while it is awake, because
  deep sleep powers it off; press RESET, then start the command at once, and
  retry if esptool reports no port. This is from the bring-up notes, not
  re-verified here. (b) Do not use `firmware/flash.sh` for this: it flashes the
  local build directory, not release assets. (c) Never burn an eFuse; no step
  here needs one. (d) If the frame was running the combined release and its
  sticky `imgfmt_bad` flag is set, a USB flash does not clear it; erasing the
  main `nvs` partition does (`esptool --chip esp32s3 --port "$PORT"
  erase-region 0x9000 0x6000`), after which the frame re-enrols with its own
  secret.

## 7. Post-install checks

- [ ] The device reports the new `X-Fw-Version` (companion Update page, or
      `firmware_cli list` plus the device report).
- [ ] An `installed` event is recorded for the frame.
- [ ] The next wake arrives on the usual cadence.
- [ ] The first container wake redraws once; the wake after that hash-skips
      (`poll ok ... hash_skip=1` on a serial capture, if one is attached).
- [ ] `device_report.json` shows no `rollback` and no `fail-*` result.
- [ ] The battery reading is plausible.

## 8. Known residual risks

- Rollback of an unconfirmed trial across deep sleep has not been seen on a
  device.
- A Wi-Fi outage during the trial makes the first poll fail, so a healthy
  image can be rolled back. The retry limit then ends the schedule.
- The sticky `imgfmt_bad` flag is cleared only by an NVS erase or a later
  release; until then the frame receives raw images (functional, just no
  container).
- The C changes were first compiled in CI, not locally. They have run on one
  EE04 bench unit (checklist items B1 to B8, 2026-11-14 and 2026-11-15), not
  on the live frame, which is a different board.
- The wrong-signature rejection was seen on one EE04 bench unit with
  throwaway keys, without a serial log (`firmware/SIGNING.md` bench results:
  pass of 2026-11-14), and not on the live frame itself.
