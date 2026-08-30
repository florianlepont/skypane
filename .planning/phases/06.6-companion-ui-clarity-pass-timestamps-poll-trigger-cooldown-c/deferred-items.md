# Deferred Items — Phase 06.6

Out-of-scope discoveries logged during plan execution, per the executor's
scope-boundary rule (do not fix issues unrelated to the current task's
files).

## From 06.6-02 execution (2026-08-30)

- **`server/test_poll_loop.py` — pinned panel.bin digest mismatch.**
  `scripts/run-all-tests.sh` reports 1 failing check: "a default config
  against the FLIGHT1 fixture reproduces the pinned pre-06-10 panel.bin
  digest." Digest produced in this environment
  (`44fe835ed0b509411bbc491d46f22d832250c1dcea810758cea0edaad66ea955`)
  does not match the pinned value
  (`49b8ba45f16b017e630bebf3c4b2f48a14d57ebbf932820eee9576502759d822`).
  This test exercises `server/plane/render.py`/`server/panel_format.py`
  image rendering, neither of which this plan (06.6-02, scoped to
  `companion/pages/config_page.py` and `companion/test_config_page.py`)
  touches. Git history shows the pinned digest was most recently updated
  by an unrelated, later-numbered phase (`fix(07-01): re-pin
  default-config panel digest from CI's own output`), suggesting this is
  environment-sensitive (likely font-rendering variance between the CI
  environment that pinned the digest and this local/worktree
  environment) rather than a regression introduced by 06.6-02. Deferred,
  not fixed, per the scope-boundary rule — all 37/37
  `companion/test_config_page.py` checks and all other 14 harnesses in
  `scripts/run-all-tests.sh` pass; this is the sole failing harness and
  it is orthogonal to this plan's files.
