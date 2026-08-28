# Deferred Items — Phase 06.5

Out-of-scope discoveries logged during execution, per the executor's scope-boundary rule (only auto-fix issues directly caused by the current task's changes).

## 1. Pre-existing `server/test_poll_loop.py` digest-pin failure

- **Found during:** 06.5-01 Task 1, running `scripts/run-all-tests.sh` to verify the task's changes.
- **Symptom:** `FAIL a default config against the FLIGHT1 fixture reproduces the pinned pre-06-10 panel.bin digest - panel.bin digest 44fe835ed0b509411bbc491d46f22d832250c1dcea810758cea0edaad66ea955 != pinned 49b8ba45f16b017e630bebf3c4b2f48a14d57ebbf932820eee9576502759d822`
- **Why out of scope:** This phase's Task 1 only touches `companion/static/battery-trend.js` (new file) and `companion/static/style.css`. Neither file is imported by, or has any code path into, `server/plane/render.py` or the panel-rendering pipeline `server/test_poll_loop.py` exercises. The failing check compares a byte-for-byte pinned image digest — unrelated to any change in this plan. Not fixed here; left for a separate investigation (likely environment-specific rendering drift, e.g. font/illustration asset differences).
- **Verified pre-existing:** confirmed the working tree at the time of this run contained only the two files listed above (`git status --short`); no Python source, font, or illustration asset was touched.
