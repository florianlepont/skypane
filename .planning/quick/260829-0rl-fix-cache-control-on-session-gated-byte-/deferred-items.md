# Deferred Items — quick task 260829-0rl

## Pre-existing, out-of-scope test failure in `scripts/run-all-tests.sh`

**Found during:** Task 2 verification (full-suite run of `scripts/run-all-tests.sh`).

**Failure:**
```
FAIL a default config against the FLIGHT1 fixture reproduces the pinned
pre-06-10 panel.bin digest - panel.bin digest
44fe835ed0b509411bbc491d46f22d832250c1dcea810758cea0edaad66ea955 !=
pinned 49b8ba45f16b017e630bebf3c4b2f48a14d57ebbf932820eee9576502759d822
```
in `server/test_poll_loop.py` (`poll-loop: 42/43 checks pass`).

**Why out of scope:** This quick task's `files_modified` are `companion/app.py`
and `companion/test_companion_app.py` only. This failure is a pinned
render-output digest tied to `server/plane/render.py` / `server/poll_loop.py`,
neither of which this task touches. STATE.md's 2026-08-28 session entry
already documents render output moving twice recently (once during Phase 07's
on-glass Blue/Green darkening, once during a separate illustration-crop-text-
margin debug session merged the same day) and the digest needing re-pinning
each time — this looks like a third instance of the same drift, unrelated to
cache-control headers.

**Action taken:** None (per SCOPE BOUNDARY — only fix issues directly caused
by the current task's changes). Companion harnesses (the actual scope of this
task) are all green: `companion/test_companion_app.py` 52/52,
`companion/test_config_page.py` 23/23, `companion/test_view_pages.py` 19/19.
Coverage held at 90% (threshold 83), confirming this task's change did not
move coverage.

**Recommended follow-up:** Re-pin `server/test_poll_loop.py`'s
`_DEFAULT_CONFIG_DIGEST` (or equivalent pinned-digest constant) in a
dedicated quick task or as part of the next phase touching `render.py`,
verifying the new digest reflects only intentional/expected output.
