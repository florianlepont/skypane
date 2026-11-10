---
phase: 63-fast-ci
plan: 04
status: executed-pending-ci
requirements: [CIS-05, CIS-04]
---

# Plan 63-04 Summary

Cheaper slow non-browser tests, with nothing dropped and no assertion changed.

## Profile (measured, not assumed)

`cProfile` of `server/test_firmware_registry.py::test_legacy_size_bound_is_unchanged` (49 s): `skypane_fw_image._body` was called 947 times for two images (44.7 s of its own time in the per-byte checksum loop, 3.2 s hashing). `build_image` grew the segment in a loop that rebuilt the whole 2.4 MB image on every step. No production code is involved: the cost was entirely in the test helper.

## Change

- `test-support/skypane_fw_image.py`: the final segment length is found arithmetically (the image length depends only on the segment length), then the image is built once; the checksum XOR runs over the descriptor only, because the rest of the segment is zero bytes and XOR with zero changes nothing. No production file is touched.
- `test-support/test_fw_image_digests.py` (new): 124 builder outputs (sizes none, 5000, 0x250000, 0x250001, 1,118,208; signed and unsigned; every corruption; default and custom modulus; two versions) pinned by length and SHA-256. The digests were recorded from the builder before the change; the test passed before (125 tests, 151 s) and passes after (125 tests, 0.65 s), so the produced bytes are identical.
- `server/test_golden_giant_render.py`: the one looping test is now one test per golden case (84 cases, ids are the case names, rendered inside the test). The existing `test_manifest_case_names_equal_generator_case_names` already asserts the case set equals the manifest in both directions (84 = 84). The Pillow-version skip is kept per case; local Pillow equals the manifest's (13.0.0), so nothing skips here, and CI pins Pillow.

## Before / after (same machine, one run each)

| Test | Before | After |
|---|---|---|
| `test_legacy_size_bound_is_unchanged` | 49-52 s | 0.05 s |
| `test_size_bound_defaults_to_the_ota_slot_not_the_display_bound` | 47-51 s | under 0.05 s |
| `test_image_at_the_bound_passes_and_one_byte_over_fails[2424833-2]` | 51-53 s | 0.08 s |
| `test_every_case_is_legal_and_matches_the_manifest` (one test of 84 renders) | 22 s | 84 tests, 7 s for the file with 4 workers (largest case 0.85 s) |

## Checks

- Changing one hash in the giant manifest (reverted, not committed) made exactly one case fail.
- No assertion, expected value or parametrised case was changed or removed in the three firmware tests.
- Executed count rises by 124 + 1 (digest matrix and its coverage test) and 83 (golden cases minus the old single test); the floor only goes up.
- ruff, mypy, comment-history guard and the 713 tests of the touched areas pass.
