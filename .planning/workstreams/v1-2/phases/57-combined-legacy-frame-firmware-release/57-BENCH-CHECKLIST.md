# Phase 57 EE04 bench checklist

Status: not run, waiting for the Seeed EE04 unit.

No box in this file may be ticked by an automated agent. Only the owner ticks a box, after observing the result on the bench unit, and fills in the Result and Date fields by hand. An agent that finds a box ticked without an owner-written result must treat it as not done.

## Dependency

Every item needs the Phase 58 evaluation unit (plan 58-03 cable-flashes it) and a firmware build that runs on its panel. It is not verified whether an EE02-profile image runs its OTA mechanics on the EE04 unit. If it does not, the affected checkpoints stay open and the owner decides how to proceed (for example waiting for an EE04 profile). An earlier spare ESP32-S3 board is acceptable for B1, B2 and B6 to B8 only if the owner says so in the Result field.

## Safety rules

- The target is the bench unit only. Nothing here touches the live frame (`xiao-ee02-13in3-spectra6`).
- Use a throwaway bench key kept outside the repository, never the release key.
- Fault builds (`SKYPANE_FAULT=...`) are dev-profile only (`build.sh` refuses them otherwise). Sign them with the bench key, import them with `server.firmware_cli import-bench --allow-foreign-key` and schedule them to the bench unit only.
- No `fw-v*` tag, no publish, no production registry import before B9 is signed off.

## Checkpoints

### B1. SIGNING.md bench

- [ ] B1. Run every step and every pass/fail row of "Bench procedure" in `firmware/SIGNING.md` as written there (do not rewrite it here): correctly signed image accepted and the new version reported; wrongly signed image refused with the previous firmware kept and `X-Ota-Result: fail-image;<version>` on the next poll; unsigned image refused (server side); fail-floor token round trip.
  - Expected observation: the Pass-when conditions of SIGNING.md, and none of its Fail-when conditions.
  - Result:
  - Date:

### B2. Unconfirmed-trial rollback

- [ ] B2. Build dev-profile images with `SKYPANE_PROFILE=dev SKYPANE_FAULT=nvs ./build.sh` and with `SKYPANE_PROFILE=dev SKYPANE_FAULT=slow_wake ./build.sh`, each with a higher bench version, signed with the bench key, imported and scheduled to the bench unit only. Let the unit install each in turn, watching `firmware/monitor.sh`.
  - Expected observation: the new image boots but fails (nvs fault, then slow wake), goes to the failure sleep, never confirms, the bootloader rolls back across the deep sleep, the next poll carries `X-Ota-Result` reporting the rollback, and the old version is running again.
  - Result:
  - Date:

### B3. Container wake

- [ ] B3. Serve the bench unit a container image from a bench server using the combined build. Capture with `firmware/monitor.sh`.
  - Expected observation: the log shows `fp_diag image format=container status=0 crc_ms=<n>`, the picture on the panel is correct, and the next wake hash-skips (no redraw).
  - Result (crc_ms value):
  - Date:

### B4. Legacy fallback

- [ ] B4. Make the bench server serve a raw (legacy) image to the combined build.
  - Expected observation: the log shows `fp_diag image format=legacy` with a legacy-ok status, the image is drawn correctly, and no sticky flag is set.
  - Result:
  - Date:

### B5. Hardware claim

- [ ] B5. With the unit's type matching its fleet record, poll and check the offer. Then change the type in the bench fleet record so it contradicts the unit's claimed type and poll again.
  - Expected observation: matching type is offered the container and any scheduled firmware; the contradiction yields the raw image and no firmware offer, and the frame still polls normally.
  - Result:
  - Date:

### B6. 401 loop

- [ ] B6. Revoke the bench unit's token on the server and watch several wakes.
  - Expected observation: the token is erased, the unit re-enrols on the next wake, repeated failures space out at 5, 10, 20 minutes (growth), the last image stays on the panel, and no NO CONNECTION screen is drawn.
  - Result:
  - Date:

### B7. Sticky fallback

- [ ] B7. From a bench server, force one invalid container (for example a corrupted CRC) and let the unit wake twice more.
  - Expected observation: the first wake keeps the last image, sets the `imgfmt_bad` NVS flag and backs off without writing the hash; the next wake does not send `X-Img-Fmt`; the raw image is then accepted and drawn.
  - Result:
  - Date:

### B8. Size and wake time

- [ ] B8. On a container wake, record the image size against the slot size and the total wake duration (monitor log timestamps).
  - Expected observation: the image fits its slot with margin; wake duration is within the battery profile budget.
  - Result (image size, slot size, wake seconds):
  - Date:

### B9. Owner sign-off

- [ ] B9. The `firmware/SIGNING.md` "Bench results" table is filled with observed results (not "deferred"), and B1 to B8 are ticked by the owner. Only then may the instructions in `57-RELEASE-INSTRUCTIONS.md` be started.
  - Result:
  - Date:
