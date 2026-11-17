---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 13
subsystem: release
tags: [firmware-release, signing, typed-assets, hw2]
requirements: [HW2-03]
key-files:
  modified: [.github/workflows/firmware-release.yml]
completed: 2026-11-15
---

# Phase 64 Plan 13: Second board in the release workflow Summary

firmware-release.yml now builds, signs, verifies and manifests the second board in the same single job, publishing `skypane-seeed-ee04-7in3-spectra6-<tag>.bin` and `release-seeed-ee04-7in3-spectra6.json` next to the unchanged live-frame assets.

## Task 1 checkpoint results (owner answers, quoted)
1. The Phase 57 release is published (GitHub release fw-v1.1.0, live-frame installation recorded in main commit b7653298, #415) and firmware-release.yml is unchanged on main since #344.
2. One job that builds, signs and verifies both boards, as recommended in the plan.

## Task 2: baseline
- `git diff --exit-code fw-v1.1.0 -- .github/workflows/firmware-release.yml` printed nothing (the file equals the Phase 57 release version). SHA-256 of the pre-edit file: 45a6b42228a89fe52027fc5639e32d26afc842b6a10e2b4d13bdee0bccb48178.
- Live assets staged: skypane-<tag>.bin, bootloader-<tag>.bin, partition-table-<tag>.bin, ota_data_initial-<tag>.bin, release.json (plus notes.md as notes file). The key is used only by "Sign the release image" (env FW_SIGNING_KEY, 0600 file in RUNNER_TEMP) and shredded by "Remove the signing key" (`if: always()`).
- Section-level identity proof of the legacy ee02 image (58-05-SUMMARY.md procedure): NOT RUN, Docker is unavailable here. To be proven by CI or the owner before the first typed release is tagged.

## Task 3: edit (commit 6d11d4ae)
Added steps/lines only; zero lines removed relative to fw-v1.1.0 (`git diff fw-v1.1.0` has no `-` lines, so the gh release create list only gained lines):
- build second board (env SKYPANE_BOARD=second, SKYPANE_RELEASE_TAG from `github.ref_name` via env), built-mode check `check_production_config.sh built firmware/build-second second`, placed after the log-contract check and before signing so the key lifetime is single;
- second `espsecure.py sign_data` invocation appended inside the existing sign step (same digest-pinned container, `--network none`, same key file); first invocation text untouched;
- second `verify_signature` appended in the existing verify step; `--check-only` and manifest steps with `--hardware-type seeed-ee04-7in3-spectra6` from firmware/build-second only;
- stage typed image; extend gh release create with the typed image and manifest.
- ci.yml dispatch is still the last step (line 277); `build-second` appears 10 times; key shred is still `if: always()`; no `${{ }}` added in any run: block.

## Tests
- `server/.venv/bin/python3 -m pytest deploy/tests -q`: 306 passed, 1 skipped (pre-existing openssl backdate skip). Includes test_ci_secrets, test_release_manifest, test_release_assets.
- YAML parses.

## Unproven
- ee02 section-level identity proof and any firmware build (no Docker here): to be proven by CI or the owner.
- The workflow itself has never run: no tag pushed, workflow not triggered, no deploy triggered, no draft PR opened (no push).
- Task 4 (human verify): owner reads the diff, approves the firmware-signing environment run when tagging the next release, and confirms both boards' assets plus live names skypane-<tag>.bin / release.json.

## Deviations from Plan
None beyond: the draft PR was not created (no push allowed). The second board's build and check steps sit before the signing step (not after the live-frame steps) so that both signatures share one key lifetime without changing the first signing invocation.

## Known Stubs
None.

## Self-Check: PASSED
