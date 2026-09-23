# Ledger: server/test_panel_preview.py

Baseline: 32-BASELINE/server__test_panel_preview.txt (11 checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | a drawn canvas, packed then unpacked, yields identical per-pixel index data | ported | server/test_panel_preview.py::test_a_drawn_canvas_packed_then_unpacked_yields_identical_per_pixel_index_data |
| 2 | a canvas containing all six legal indices, including a mixed odd/even column pair, round-trips exactly | ported | server/test_panel_preview.py::test_all_six_indices_with_mixed_pair_round_trips |
| 3 | unpack_panel() on wrong-length input raises PanelDecodeError, never AssertionError/IndexError | ported | server/test_panel_preview.py::test_wrong_length_raises_panel_decode_error |
| 4 | unpack_panel() on the one illegal nibble code raises PanelDecodeError naming the offending code | ported | server/test_panel_preview.py::test_illegal_nibble_raises_panel_decode_error_naming_the_offending_code |
| 5 | panel_png_bytes() returns real, Pillow-decodable PNG bytes at the expected dimensions | ported | server/test_panel_preview.py::test_panel_png_bytes_is_a_real_pillow_decodable_png_at_the_expected_dimensions |
| 6 | panel_png_bytes(max_width=240) returns a proportionally resized thumbnail | ported | server/test_panel_preview.py::test_thumbnail_is_proportionally_resized |
| 7 | read_panel_file() on a missing file returns None rather than raising | ported | server/test_panel_preview.py::test_read_panel_file_on_a_missing_file_returns_none_rather_than_raising |
| 8 | a row with two different legal indices at column 0 and column 1 round-trips without a high/low nibble swap | ported | server/test_panel_preview.py::test_mixed_pair_catches_nibble_transposition |
| 9 | the full getdata() sequence (not a sampled subset) matches exactly for an all-six-indices canvas | ported | server/test_panel_preview.py::test_full_getdata_sequence_matches_over_all_six_indices |
| 10 | a real production render.render_panel(None, 'empty') round-trips index-for-index against build_canvas() | ported | server/test_panel_preview.py::test_production_render_round_trips_exactly_against_build_canvas |
| 11 | the nearest-neighbour thumbnail's colour set is a strict subset of the full image's colour set | ported | server/test_panel_preview.py::test_thumbnail_colour_set_is_a_strict_subset_of_the_full_images_colour_set |
