# Phase 31 — Timing Baseline

## Pre-split baseline (31-01-PLAN.md Task 1)

- **Commit SHA:** `4fb2593b7b6573b0230626aa48da2f72a2314f6d`
- **Host:** `os.cpu_count()` = 10 (Apple Silicon macOS, arm64) — pinned `JOBS=4` below to mirror the CI runner's own core count rather than this host's, per RESEARCH.md Pitfall 5.
- **Measurement command:** `JOBS=4 ./scripts/run-all-tests.sh` from the repository root, using `server/.venv/bin/python3`.

### Local proxy — per-harness timing (slowest first), JOBS=4

| Harness | Wall (s) | Status |
| --- | --- | --- |
| companion/test_browser_ux.py | 240.9 | FAIL* |
| companion/test_companion_app.py | 22.5 | PASS |
| server/test_render.py | 10.4 | PASS |
| server/test_poll_loop.py | 5.8 | PASS |
| companion/test_status_pages.py | 4.3 | PASS |
| stub-server/test_poll_cycle.py | 3.8 | PASS |
| server/test_pipeline_e2e.py | 1.7 | PASS |
| server/test_panel_preview.py | 1.1 | PASS |
| companion/test_config_page.py | 1.0 | PASS |
| companion/test_i18n.py | 0.9 | PASS |
| companion/test_view_pages.py | 0.9 | PASS |
| server/test_illustrations.py | 0.7 | PASS |
| server/test_calendar_rules.py | 0.5 | PASS |
| server/test_notify.py | 0.2 | PASS |
| server/test_manual_resolutions.py | 0.2 | PASS |
| server/test_colour_rules.py | 0.2 | PASS |
| server/test_plane_detection.py | 0.2 | PASS |
| server/test_enrich.py | 0.2 | PASS |
| server/test_config_history.py | 0.2 | PASS |
| server/test_dither.py | 0.1 | PASS |
| server/test_runway_config.py | 0.1 | PASS |
| companion/test_contrast_check.py | 0.1 | PASS |

**Total wall time: 240.9s (JOBS=4)** — all 22 current `HARNESSES` entries present.

\* `companion/test_browser_ux.py` reports FAIL on this specific host (Apple Silicon
macOS, arm64 Chromium) for reasons fully unrelated to the code under test — see
"Local-environment correctness caveat" below. The wall-time figure (240.9s) is
still a valid duration measurement: the harness ran essentially all 96 checks
before failing on one of the affected checks near the end of the file, so the
number is not meaningfully shortened by the failure. Comparability for plan 04's
delta calculation is preserved because the same environmental quirk is symmetric
— it will still be present, in the same shape, when the split files are
re-measured on this same host.

### Local-environment correctness caveat (does not affect the timing number above)

The per-check PASS/FAIL transcript in `31-BASELINE-CHECKS.txt` was **not** captured
from this same `JOBS=4` run, and deliberately so. A standalone
`server/.venv/bin/python3 companion/test_browser_ux.py` run on this host (native
macOS, arm64 Chromium) deterministically FAILs 3 of 96 checks across 3 repeated
attempts, for two distinct, fully environmental reasons — neither is a defect in
the application or the test file, and neither is touched by this plan:

1. Two checks (the leave-guard "stays armed through commit" check and the
   validation-rejection echo check) both use `page.keyboard.press("Control+A")` to
   select-all before typing a replacement value. Blink's `EditingBehavior` for
   `EditingMacBehavior` maps Ctrl+A to "move to beginning of line" (an
   intentional Emacs-style binding), not select-all — only `EditingUnixBehavior`
   (Linux, i.e. the actual `ubuntu-latest` CI runner) treats Ctrl+A as select-all.
   On arm64 macOS the keystroke is a no-op for selection, so the typed value is
   appended rather than substituted.
2. One check (the no-JS fallback-Save-persists check) hits an intermittent
   Playwright "element is not stable ... element was detached from the DOM"
   timeout on the native-form-submit navigation, reproducing deterministically on
   both native arm64 macOS Chromium and an arm64 Linux Docker container, but never
   on an **amd64**-emulated Linux container (`--platform linux/amd64`, matching
   the actual GitHub Actions `ubuntu-latest` runner architecture) or on 4/4 sampled
   real CI runs from this same repository (`gh run view <id> --log`, each showing
   `browser-ux: 96/96 checks pass`). This points to an arm64-Chromium-specific
   paint/compositor timing characteristic, not a code defect.

Verification: 3 standalone runs on native macOS arm64 (this host) and 2 on an
arm64 Linux Docker container all reproduced the same failure pattern (3 FAILs on
macOS: the two Ctrl+A checks above plus the DOM-detach check; 1 FAIL on arm64
Linux: the DOM-detach check only, since Linux's Ctrl+A select-all behavior fixes
the first two). A single run under `--platform linux/amd64` (Docker, matching
CI's own architecture) produced a clean **96/96, zero FAIL** transcript, matching
4/4 sampled real CI runs on this repository. That amd64-emulated transcript is
what `31-BASELINE-CHECKS.txt` contains — it is the correctness-representative
baseline; this file's `JOBS=4` number above is the performance-representative
baseline. No source file was edited to produce either artifact.

### D-01's own CI-recorded figures (for cross-reference, not re-measured here)

- Job average: ~5min40s
- `companion/test_browser_ux.py` across five separate CI runs: 300.9s, 318.7s,
  314.4s, 303.4s, 314.2s
- Real CI confirms this file dominates the job — consistent with the local proxy
  figure above (240.9s), allowing for real-runner-vs-local-host variance.

Plan 04 should compare its post-split delta against both the local proxy number
above and a fresh real CI run's `gh run view` timing, per D-05's established
measurement method.
