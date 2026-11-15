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

- [x] B2. Build dev-profile images with `SKYPANE_PROFILE=dev SKYPANE_FAULT=nvs ./build.sh` and with `SKYPANE_PROFILE=dev SKYPANE_FAULT=slow_wake ./build.sh`, each with a higher bench version, signed with the bench key, imported and scheduled to the bench unit only. Let the unit install each in turn, watching `firmware/monitor.sh`.
  - Expected observation: the new image boots but fails (nvs fault, then slow wake), goes to the failure sleep, never confirms, the bootloader rolls back across the deep sleep, the next poll carries `X-Ota-Result` reporting the rollback, and the old version is running again.
  - Result: PASS on the bench unit (seeed-ee04-7in3-spectra6, MAC 84:c7:bb:70:b2:7c), observed by the owner on the bench server telemetry; no serial log captured. Image A `fw-v1.0.10-bench6` (`SKYPANE_FAULT=nvs`): downloaded 09:50:50, the unit reported `fw-v1.0.9-bench4` with `X-Ota-Result=rollback;fw-v1.0.10-bench6` at 09:56:50. Image B `fw-v1.0.11-bench7` (`SKYPANE_FAULT=slow_wake`): downloaded 10:05:43, reported `fw-v1.0.9-bench4` with `X-Ota-Result=rollback;fw-v1.0.11-bench7` at 10:23:21, and was retried (second attempt 10:23:54). No boot loop in either case. Not observed: the trial boot itself (inferred from the rollback token and the version returning). Ticked by the assistant at the owner's explicit request on 2026-11-15, from the telemetry the owner pasted.
  - Date: 2026-11-15

### B3. Container wake

- [x] B3. Serve the bench unit a container image from a bench server using the combined build. Capture with `firmware/monitor.sh`.
  - Expected observation: the log shows `fp_diag image format=container status=0 crc_ms=<n>`, the picture on the panel is correct, and the next wake hash-skips (no redraw).
  - Result (crc_ms value): PASS for the serial log, crc_ms=21. Bench unit seeed-ee04-7in3-spectra6 (MAC 84:c7:bb:70:b2:7c) running the combined build `fw-v1.0.12-bench8` (installed through OTA: `trial` at 10:48:04, `installed` at 10:53:39). Serial capture of one wake after the served image was changed on the bench server: `fp_diag image format=container status=0 crc_ms=21`, `blit ok bytes=192000 sha256_ok=1`, `refreshed to sha256:4822139f…`, `poll ok sleep_s=300 hash_skip=0`, `wake timing total_ms=37176 download_ms=778 draw_ms=31204`. An earlier wake with the image unchanged logged `image unchanged, skipping download` and `hash_skip=1` (total_ms=4721 and 2056), which is the no-redraw half of this check. Not recorded here: the owner's visual check of the panel (the changed image has a red band at the top). Ticked by the assistant at the owner's explicit request on 2026-11-15.
  - Date: 2026-11-15

### B4. Legacy fallback

- [x] B4. Make the bench server serve a raw (legacy) image to the combined build.
  - Expected observation: the log shows `fp_diag image format=legacy` with a legacy-ok status, the image is drawn correctly, and no sticky flag is set.
  - Result: PASS on server evidence and the panel; the serial line `fp_diag image format=legacy` was not captured. Bench unit seeed-ee04-7in3-spectra6 (MAC 84:c7:bb:70:b2:7c) running `fw-v1.0.12-bench8`. With the bench server returning the raw image (type contradiction, see B5), the unit polled after a reset at 11:18:40, downloaded `/img/d_0f7b6d33/77f7ffbb…bin` and the panel showed the new picture (green band at the top). The sha256 of the bench `panel.bin` is `77f7ffbb6eb9d9082aa5295bf075038eda4244be579a4f2457352dd1901ba82b`, equal to the served digest, so the served body was the raw file, not a container. No sticky flag was involved. Ticked by the assistant at the owner's explicit request on 2026-11-15.
  - Date: 2026-11-15

### B5. Hardware claim

- [x] B5. With the unit's type matching its fleet record, poll and check the offer. Then change the type in the bench fleet record so it contradicts the unit's claimed type and poll again.
  - Expected observation: matching type is offered the container and any scheduled firmware; the contradiction yields the raw image and no firmware offer, and the frame still polls normally.
  - Result: PASS for the server side and the frame still polling; one direction only on the panel. Bench fleet record changed from `seeed-ee04-7in3-spectra6` to `sim-landscape-800x480` (same image size, 192000 bytes; server started with `SKYPANE_SIM_HARDWARE=1`) while the unit kept claiming `seeed-ee04-7in3-spectra6`. Server log: `ota: 84:c7:bb:70:b2:7c claim mismatch (seeed-ee04-7in3-spectra6); no firmware offer`; the poll was answered 200 with the raw image (see B4) and the unit kept polling every wake. Matching case: container served and scheduled firmware offered and installed (B3, and the OTA of `fw-v1.0.12-bench8` at 10:47-10:53). The first reset after the record change showed `image unchanged`: the unit had probably already fetched the raw image on an unobserved timer wake. The bench record was to be restored by the owner after the check (not confirmed here). Ticked by the assistant at the owner's explicit request on 2026-11-15.
  - Date: 2026-11-15

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
