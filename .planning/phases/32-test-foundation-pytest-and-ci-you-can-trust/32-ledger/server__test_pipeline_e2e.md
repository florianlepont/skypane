# Ledger: server/test_pipeline_e2e.py

Baseline: 32-BASELINE/server__test_pipeline_e2e.txt (7 checks)

All seven old checks shared one process-global state directory (setup ->
download -> empty-snapshot no-op -> battery poll -> battery-empty park and
recovery are a genuinely sequential scenario, each depending on state an
earlier check created - MR-4), so all seven map to the same single,
consolidated node id.

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | run_once(multi-aircraft fixture) writes panel.bin at exactly 960000 bytes | ported | server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol |
| 2 | panel.bin bytes decompose into only the six legal nibble codes | ported | server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol |
| 3 | byos_server.py setup->display returns a valid image_url and image_hash | ported | server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol |
| 4 | downloaded image is 960000 bytes and SHA-256-verifies against image_hash | ported | server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol |
| 5 | run_once(empty fixture) leaves panel.bin byte-identical (D-04) | ported | server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol |
| 6 | a real authenticated poll carrying X-Battery-Mv:3400, followed by a run_once() cycle, changes the served panel.bin only inside the icon's byte columns/rows, and the packed ink nibble at (1520,70) matches whichever state run_once() actually reported | ported | server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol |
| 7 | end to end through the real device protocol: a 3290 mV check-in followed by run_once() latches BATTERY EMPTY and serves its hash with sleep_s 3600; a second run_once() is a byte-identical hash-skip; a 4100 mV check-in's OWN reply anticipates recovery (sleep_s != 3600) before the next run_once() clears the park and serves a different hash | ported | server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol |
