# Ledger: server/test_dither.py

Baseline: 32-BASELINE/server__test_dither.txt (6 checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded | ported | server/test_dither.py::test_panel_palette_image_is_unpadded |
| 2 | dither_to_full_panel_palette() on a hue-rich synthetic image yields indices that are a subset of {0,1,2,3,4,5} | ported | server/test_dither.py::test_full_palette_dither_stays_within_legal_indices |
| 3 | a flat single-color RGB source quantizes to exactly that color's own index | ported | server/test_dither.py::test_flat_source_quantizes_to_single_index |
| 4 | dither_to_full_panel_palette() is deterministic for the same input image | ported | server/test_dither.py::test_dither_to_full_panel_palette_is_deterministic_for_the_same_input_image |
| 5 | write_calibration_preview() writes exactly one palette-swatch PNG and returns its path | ported | server/test_dither.py::test_calibration_preview_writes_exactly_one_palette_swatch_png_and_returns_its_path |
| 6 | build_mood_background() no longer exists on server.plane.dither (D-21 retirement) | ported | server/test_dither.py::test_build_mood_background_no_longer_exists_on_server_plane_dither |
