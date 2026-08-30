# Deferred items — out-of-scope discoveries

Logged per the executor's scope-boundary rule: issues not caused by the
current task's changes are logged here, not fixed.

## Plan 06.6-01

- **`server/test_poll_loop.py::"a default config against the FLIGHT1 fixture
  reproduces the pinned pre-06-10 panel.bin digest"` fails in this
  environment.** Confirmed pre-existing and unrelated to this plan: `git
  diff HEAD --stat` at the time of this run showed only
  `companion/pages/health_page.py` and `companion/test_status_pages.py`
  modified (companion/layout.py already committed in Task 1's commit,
  also unrelated to server/plane/render.py or server/test_poll_loop.py).
  Neither file this plan touches is imported by the rendering pipeline
  under test. Most likely cause: a font/Pillow-version rendering
  difference between this sandbox and the environment the digest was
  pinned against (commit `3a2a674 fix(07-01): re-pin default-config panel
  digest from CI's own output`) — not investigated further, out of this
  plan's scope (companion/layout.py, companion/pages/health_page.py,
  companion/test_status_pages.py only).
