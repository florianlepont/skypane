# Baseline capture index

Captured: 2026-09-24T08:51:35Z (UTC)
Python version: 3.11.15
euid: 0
Capture commit: 3655cc99f82529edc4d81977714df118dbbecfa8
PLAYWRIGHT_BROWSERS_PATH: /tmp/skypane-pw-browsers
Chromium executable path: /tmp/skypane-pw-browsers/chromium-1243/chrome-linux64/chrome

| Harness | Transcript | PASS | FAIL | Total | Exit code | Summary line |
| --- | --- | ---: | ---: | ---: | --- | --- |
| companion/test_contrast_check.py | `companion__test_contrast_check.txt` | 49 | 0 | 49 | 0 | contrast-check: 49/49 checks pass |
| companion/test_i18n.py | `companion__test_i18n.txt` | 24 | 0 | 24 | 0 | 24/24 checks pass |
| companion/test_view_pages.py | `companion__test_view_pages.txt` | 169 | 0 | 169 | 0 | view-pages: 169/169 checks pass |
| companion/test_config_page.py | `companion__test_config_page.txt` | 276 | 0 | 276 | 0 | config-page: 276/276 checks pass |
| companion/test_companion_app.py | `companion__test_companion_app.txt` | 318 | 2 | 320 | 1 | companion-app: 318/320 checks pass |
| companion/test_status_pages.py | `companion__test_status_pages.txt` | 316 | 1 | 317 | 1 | status-pages: 316/317 checks pass |
| companion/test_browser_ux_health_drawings.py | `companion__test_browser_ux_health_drawings.txt` | 11 | 0 | 11 | 0 | browser-ux-health-drawings: 11/11 checks pass |
| companion/test_browser_ux_quiet_wake.py | `companion__test_browser_ux_quiet_wake.txt` | 9 | 0 | 9 | 0 | browser-ux-quiet-wake: 9/9 checks pass |
| companion/test_browser_ux.py | `companion__test_browser_ux.txt` | 75 | 0 | 75 | 0 | browser-ux: 75/75 checks pass |

Grand total: 1250 checks across 9 harnesses

## Notes

**3 FAILs, all root-sandbox artifacts, none a regression** (this plan only captures the
baseline; it never modifies a harness — Rule 1/2/3 scope boundary):

- `companion/test_companion_app.py:10336,10344` and `:10386,10392` — the 2 WR-11 `os.chmod`
  checks (`add_entry()`/`delete_entry()` must fail cleanly when their state dir is read-only).
  This sandbox runs as `euid 0` (confirmed above), and root ignores a `chmod 0o500` read-only
  bit by design — the write the check expects to fail instead succeeds, so the check reports
  FAIL. Read at those exact line numbers: `os.chmod(manual_harness.tmpdir, 0o500)` /
  `os.chmod(manual_harness.tmpdir, 0o700)`, matching Phase 32's own precedent
  (`server/test_manual_resolutions.py`, `32-BASELINE/INDEX.md`) for the identical root-sandbox
  condition.
- `companion/test_status_pages.py:8201` — `health_page.anomaly_active("/nonexistent/definitely-not-here")`
  expected `False` for a non-existent `state_dir` path. Confirmed live this session: this call
  creates `/nonexistent/definitely-not-here` on the host filesystem (via
  `history_db.open_db()` → `os.makedirs(state_dir, exist_ok=True)`), and under root that
  `os.makedirs` succeeds where a non-root run would raise `PermissionError` on `/`. `ls -la
  /nonexistent` after this capture shows `drwxr-xr-x definitely-not-here`, owned by root,
  freshly created at capture time. It is empty and harmless; this session's own safety tooling
  blocks `rm -rf /nonexistent` ("critical system directory — requires explicit approval"), so
  it is left in place and flagged here rather than removed. TST-13's success criterion 4
  (nothing written outside `tmp_path`) is exactly what 33-25's migration of this check is
  expected to fix, by replacing the literal path with a `tmp_path`-scoped guaranteed-absent
  path.

Every other check in every other harness — including this file's and `test_companion_app.py`'s
remaining checks — passed cleanly (1247/1250 PASS overall).

**The +1 discrepancy between CONTEXT.md's expected 1249 (2018 − 769) and the measured 1250 is
traced to a commit:** `17d5bc7` (Phase 32 continuation, plan `32-11-PLAN.md` Task 1, TST-03)
added exactly one new `check(...)` call to `companion/test_companion_app.py` after the
2026-09-23 audit's baseline was measured — "the first poll trigger's run_once() was served by
the fake ADS-B providers (adsbfi and adsblol called, no live network)" — bumping that file's
`EXPECTED_CHECK_COUNT` from 319 to 320 (see the comment immediately above that assignment in
`companion/test_companion_app.py`, dated to that same plan). `git log --oneline
2808f8a..HEAD -- 'companion/test_*.py'` shows only two commits touched any companion test file
since the audit (`320a642` Phase 32's own initial landing, and `17d5bc7` the continuation
above); `git log -p` over that range shows exactly one added `check(` call, this one, and no
other companion harness's `EXPECTED_CHECK_COUNT` changed in that window. audit expected
1249 = 2018 − 769; measured 1250; +1 from `17d5bc7` (32-11): "the first poll trigger's
run_once() was served by the fake ADS-B providers (adsbfi and adsblol called, no live
network)".

