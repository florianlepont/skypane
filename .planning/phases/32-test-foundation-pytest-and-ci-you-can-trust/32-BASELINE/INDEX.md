# Baseline capture index

Captured: 2026-09-23T14:12:45Z (UTC)
Python version: 3.11.15
euid: 0
Capture commit: 3a6665c924df8077166e67923d31bca0177214b2

| Harness | Transcript | PASS | FAIL | Total | Exit code | Summary line |
| --- | --- | ---: | ---: | ---: | --- | --- |
| server/test_calendar_rules.py | `server__test_calendar_rules.txt` | 113 | 0 | 113 | 0 | calendar_rules: 113/113 checks pass |
| server/test_colour_rules.py | `server__test_colour_rules.txt` | 33 | 0 | 33 | 0 | colour_rules: 33/33 checks pass |
| server/test_config_history.py | `server__test_config_history.txt` | 90 | 0 | 90 | 0 | config-history: 90/90 checks pass |
| server/test_dither.py | `server__test_dither.txt` | 6 | 0 | 6 | 0 | dither: 6/6 checks pass |
| server/test_enrich.py | `server__test_enrich.txt` | 60 | 0 | 60 | 0 | enrich: 60/60 checks pass |
| server/test_illustrations.py | `server__test_illustrations.txt` | 60 | 0 | 60 | 0 | illustrations: 60/60 checks pass |
| server/test_manual_resolutions.py | `server__test_manual_resolutions.txt` | 21 | 2 | 23 | 1 | manual_resolutions: 21/23 checks pass |
| server/test_notify.py | `server__test_notify.txt` | 8 | 0 | 8 | 0 | notify: 8/8 checks pass |
| server/test_panel_preview.py | `server__test_panel_preview.txt` | 11 | 0 | 11 | 0 | panel-preview: 11/11 checks pass |
| server/test_pipeline_e2e.py | `server__test_pipeline_e2e.txt` | 7 | 0 | 7 | 0 | pipeline-e2e: 7/7 checks pass |
| server/test_plane_detection.py | `server__test_plane_detection.txt` | 47 | 0 | 47 | 0 | plane-detection: 47/47 checks pass |
| server/test_poll_loop.py | `server__test_poll_loop.txt` | 110 | 0 | 110 | 0 | poll-loop: 110/110 checks pass |
| server/test_render.py | `server__test_render.txt` | 140 | 0 | 140 | 0 | render: 140/140 checks pass |
| server/test_runway_config.py | `server__test_runway_config.txt` | 15 | 0 | 15 | 0 | runway-config: 15/15 checks pass |
| stub-server/test_poll_cycle.py | `stub-server__test_poll_cycle.txt` | 46 | 0 | 46 | 0 | poll-cycle: 46/46 checks pass |

Grand total: 769 checks across 15 harnesses

## Notes

`server/test_manual_resolutions.py` printed 2 FAIL lines (21/23). Both are root-sandbox
environment failures, not regressions, and are **not** auto-fixed by this plan (Rule 1/2/3
scope boundary: this plan only captures the baseline, it never modifies a harness):

- `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created because
  the parent directory is read-only — CR-01's exact reproduction case (WR-11)` (source:
  `server/test_manual_resolutions.py:434-450`, `os.chmod(parent, 0o500)` at line 439)
- `delete_entry() returns False (never raises) when the state dir goes read-only mid-write...
  (WR-11)` (source: `server/test_manual_resolutions.py:452-476`, `os.chmod(tmp, 0o500)` at
  line 461)

Both checks assert that a chmod-0o500 (read-only) directory actually blocks a write. This
sandbox executes as `euid 0` (root, confirmed above), and root ignores read-only directory
permission bits by design — the chmod has no effect, the write succeeds, and the check that
expected it to fail reports FAIL. This is the same root-sandbox condition
`.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-01-SUMMARY.md` and
`.planning/STATE.md`'s own session history document repeatedly (session baseline: "4×WR-11,
1×`anomaly_active()`" under root — 2 of those 4 WR-11 checks live in this file; the other 2
and the `anomaly_active()` check are in `companion/test_*.py`, out of this phase's scope).
Every other check in every other harness — including this file's remaining 21 — passed
cleanly. 32-RESEARCH.md's own root-safety pattern (`requires_non_root` /
`pytest.mark.skipif(os.geteuid() == 0, ...)`) is exactly what `server/test_manual_resolutions.py`'s
own migration plan (32-04) is expected to apply to these two checks when it ports them; this
baseline capture records the pre-migration FAIL faithfully rather than "fixing" it, per this
plan's own scope (capture only, no harness rewritten).

