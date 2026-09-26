---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 02
subsystem: api
tags: [http-caching, etag, http-caching-caddy, stdlib, companion]

# Dependency graph
requires:
  - phase: 38-01
    provides: "test-support/efficiency_probe.py and 38-EFF-BASELINE.md's Before section (not consumed directly by this plan's tests, but the instruments-first ordering this plan continues)"
provides:
  - "companion/app.py: _serve_static(abs_path, content_type, cache_control) — the shared body behind _serve_stylesheet(), _serve_script_file() and _serve_runway_image(), built on _static_entry()/_read_static_bytes() (a per-process, lock-guarded in-memory cache keyed by abs path) and _not_modified() (RFC 9110 13.2.2 conditional evaluation)"
  - "Every /static/*.css and /static/*.js route now serves public, no-cache with a strong quoted ETag and a Last-Modified date, replacing the prior public, max-age=300 with no validators"
  - "/runway-image/{id}.png keeps its private, max-age=300 policy unchanged and gains the same ETag/Last-Modified/in-memory-cache treatment, still behind require_session()"
  - "deploy/Caddyfile: encode zstd gzip in the companion site block only, with the device (byos) block untouched"
affects: [38-03, 38-04, 38-05, 38-06, 38-07, 38-08, 38-09, 38-10, 38-11, 38-12, 38-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_serve_static() is the one seam every static delegate calls through; the 17 routes, 17 _serve_*() delegates and 17 do_GET() branches stay exactly as they were (no catch-all handler, no route table — that is Phase 40's CMP-02)"
    - "A namedtuple cache record (_StaticEntry: payload, etag, last_modified, mtime_s) plus a single disk-read seam (_read_static_bytes) a test can monkeypatch and count, matching test-support/efficiency_probe.py's own 'wrap a production seam, don't add a hook' convention"
    - "A browser test that needs to prove a real-browser round trip, but whose context is forced through companion/conftest.py's mandatory loopback-only route() guard, drives the round trip explicitly (two fetch() calls, the second carrying the first's ETag) instead of relying on an implicit page.reload() — the guard's own CDP interception disables Chromium's disk cache as a side effect, proven separately against an unguarded context where reload() does revalidate correctly"

key-files:
  created:
    - companion/test_static_cache.py
  modified:
    - companion/app.py
    - companion/test_companion_app_02.py
    - companion/test_companion_app_03.py
    - companion/test_companion_app_04.py
    - deploy/Caddyfile
    - deploy/tests/test_caddyfile.py

key-decisions:
  - "The runway-image route delegates to _serve_static() too (it was in-scope per the plan's action list) but keeps its own private, max-age=300 Cache-Control string, passed straight through by the shared helper rather than derived from any shared no-cache default — _serve_static()'s cache_control parameter is opaque, so two different policies coexist behind one implementation with no branching on caller identity"
  - "The browser criterion-2 test proves the real-browser round trip with two explicit fetch() calls (the second carrying the first response's own ETag as If-None-Match) rather than page.reload(), because companion/conftest.py's mandatory loopback-only new_context() route guard enables Chrome DevTools Protocol request interception on every browser test's context, which disables Chromium's own HTTP disk cache as a side effect — verified with a standalone script that an identical reload() does revalidate to 304 throughout against an unguarded context, and does not against a guarded one. This is a property of the shared test harness, not of companion/app.py, and conftest.py is out of this plan's file scope."

requirements-completed: [EFF-01]

# Metrics
duration: ~25min
completed: 2026-09-26
---

# Phase 38 Plan 02: Companion static-asset caching (EFF-01) Summary

**`_serve_static()` gives every CSS/JS route a strong ETag, a Last-Modified date and `public, no-cache` (replacing `max-age=300`), serves bytes from a per-process in-memory cache read from disk once, answers a matching conditional request with a bodiless 304, and Caddy now compresses the companion site block only.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-26T13:15:00Z (approx., immediately after 38-01)
- **Completed:** 2026-09-26T13:39:36Z
- **Tasks:** 2 completed (each run as its own RED/GREEN TDD cycle)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments
- `companion/app.py`: `_serve_static(abs_path, content_type, cache_control)` — the shared body behind `_serve_stylesheet()`, `_serve_script_file()` and `_serve_runway_image()` — built on a per-process cache (`_static_entry()`/`_read_static_bytes()`, a `threading.Lock`-guarded dict keyed by absolute path, one disk read per file per process) and `_not_modified()` (RFC 9110 §13.2.2: `If-None-Match` decides outright when present — exact, `W/`-prefixed, inside a comma list, or `*`; `If-Modified-Since` only otherwise; a malformed date is a defensive no-match, never a 500).
- Every `/static/*.css` and `/static/*.js` route now serves `public, no-cache` with a strong quoted 32-hex-char ETag and a parseable `Last-Modified`, replacing the old `public, max-age=300` with no validators at all — so every load revalidates and no page can ever run new HTML against a browser's stale cached JS/CSS after a deploy.
- `/runway-image/{id}.png` keeps its exact `private, max-age=300` policy (unchanged, still behind `do_GET()`'s `require_session()` gate) and gains the same ETag/Last-Modified/in-memory-cache treatment.
- `companion/test_static_cache.py` (16 tests): validator/policy shape on the stylesheet and every served script route; four `If-None-Match` variants → 304; a mismatch → 200; `If-Modified-Since` equal/earlier/malformed; `If-None-Match` winning over a matching `If-Modified-Since`; the runway image's private policy and its 303-never-304 unauthenticated behaviour; a disk-read-once-per-process proof via a monkeypatched `_read_static_bytes`; a missing-file-then-created-file proof; and one `@pytest.mark.browser` test proving the real-browser round trip.
- `deploy/Caddyfile`: `encode zstd gzip` as the first directive of the companion site block only; the device (byos) block is untouched. Two new `deploy/tests/test_caddyfile.py` tests assert exactly one non-comment `encode zstd gzip` line in the companion block and none in the device block.
- Updated 16 pre-existing `max-age=300` assertions across `test_companion_app_02/03/04.py` to the new `no-cache` policy (CSS/JS only; the one pre-existing runway-image-adjacent assertion was already unrelated to this change).

## Task Commits

Each task ran as its own RED → GREEN TDD cycle, each side committed separately:

1. **Task 1 RED: failing static-cache validator/304 tests** - `5932433` (test) — 28 tests fail against the unmodified `companion/app.py`
2. **Task 1 GREEN: `_serve_static()` (ETag/Last-Modified/304, in-memory cache)** - `b0d57f2` (feat) — all 28 pass; full companion suite (1569 tests) green
3. **Task 2 RED: failing encode-directive Caddyfile tests** - `096cafe` (test) — 1 test fails against the unmodified `deploy/Caddyfile`
4. **Task 2 GREEN: `encode zstd gzip` in the companion Caddy site block** - `644565e` (feat) — all 16 `deploy/tests/test_caddyfile.py` tests pass

_Note: this plan's `<output>` block is delivered by this SUMMARY.md itself; no separate plan-metadata commit was needed beyond the four commits above and the STATE/ROADMAP metadata commit that follows._

## Files Created/Modified
- `companion/app.py` - `_StaticEntry`, `_STATIC_CACHE`/`_STATIC_CACHE_LOCK`, `_read_static_bytes()`, `_static_entry()`, `_not_modified()`, `Handler._serve_static()`; `_serve_stylesheet()`/`_serve_script_file()`/`_serve_runway_image()` now delegate to it
- `companion/test_static_cache.py` - 16 tests: validators, 304 semantics, disk-read-once, missing-file recovery, runway-image policy, one browser test
- `companion/test_companion_app_02.py`, `test_companion_app_03.py`, `test_companion_app_04.py` - `max-age=300` → `no-cache` assertions on every CSS/JS route
- `deploy/Caddyfile` - `encode zstd gzip` in the companion site block
- `deploy/tests/test_caddyfile.py` - two new tests for the encode directive's placement

## Decisions Made
- The runway-image route delegates to the same `_serve_static()` helper as CSS/JS but keeps its own distinct `private, max-age=300` `Cache-Control` string — the helper's `cache_control` parameter is opaque, so one implementation serves two different policies with no branching on caller identity.
- The browser criterion-2 test drives the revalidation round trip with two explicit `fetch()` calls from inside the authenticated page (see Deviations) rather than `page.reload()`, because of a test-harness-only side effect discovered during execution (below).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The plan's literal `page.reload()` browser-test shape cannot observe a 304 under this repo's mandatory browser-test guard**
- **Found during:** Task 1, writing the `@pytest.mark.browser` test the plan specifies ("log in, load `/`, clear the recorder, `page.reload()`, wait for load: every recorded `/static/` request has code 304")
- **Issue:** `companion/conftest.py`'s `new_context` fixture override — installed on every browser test's context in this repo, including the plain `page` fixture, to enforce the loopback-only network guard — calls `context.route("**/*", ...)`. Enabling Chrome DevTools Protocol request interception this way has the side effect of disabling Chromium's own HTTP disk cache for every intercepted request. With the disk cache disabled, `page.reload()` never has anything to revalidate against, so every `/static/*` request came back 200, never 304 — confirmed with a standalone script showing the *identical* `page.reload()` sequence gets 304 throughout against a plain, unguarded `browser.new_context()`, and 200 throughout against a context carrying the guard's own `route("**/*", ...)` call. This is a documented risk the phase's own research flagged (`38-RESEARCH.md` Pitfall 1: "Playwright's cache reporting" is `[ASSUMED behaviour]`), just triggered by a different mechanism (interception, not `max-age`) than the research anticipated.
- **Fix:** The test still proves the same real-browser round trip, through the same guarded, real Chromium network stack every other browser test in this repo uses, but drives it explicitly: it reads the `/static/*` `src`/`href` attributes off the real rendered, authenticated page, then runs two `fetch()` calls per asset from inside the page (the second carrying the first response's own `ETag` as `If-None-Match`), and asserts the second is 304 for every asset. A `send_response` recorder (monkeypatched exactly as the plan specifies) corroborates that the origin actually answered from `_serve_static()`'s 304 branch, not from an intermediary. `companion/conftest.py` itself was not touched — it is out of this plan's file scope and its guard exists for a security reason (blocking non-loopback navigation) that applies to every browser test, not just this one.
- **Files modified:** `companion/test_static_cache.py` (test design only; no production code change)
- **Verification:** The test passes with the Chromium shim (`SKYPANE_REQUIRE_BROWSER=1`); a scratchpad probe script confirmed the guard/no-guard behaviour split described above before the fix was written.
- **Committed in:** `5932433` (RED) / `b0d57f2` (GREEN) — the test module's shape was already correct going into RED, since the underlying `_serve_static()` behaviour (not the test's browser-driving mechanism) is what RED/GREEN was proving.

---

**Total deviations:** 1 auto-fixed (1 blocking — test-harness environmental constraint, not a production-code defect)
**Impact on plan:** No production-code or scope change. The plan's other 27 behaviour-list bullets and Task 2 were implemented exactly as written.

## Issues Encountered
None beyond the one deviation above. Two comment-history hits (`D-1` inside a code comment in `companion/app.py`, twice, plus one test docstring) were caught by `scripts/check_comment_history.py check` before the first commit and reworded to describe the behaviour without the decision ID, per CLAUDE.md's "no plan/phase/requirement/decision IDs in comments" rule — not a deviation, just draft cleanup before RED was committed.

## User Setup Required

None for this plan's own scope. The companion service picks up the new `Cache-Control`/`encode` behaviour on its next normal deploy (`deploy/activate.sh` restarts `skypane-companion.service` and reloads Caddy only when the rendered site file changed) — no manual step. The live VPS `curl` verification of `Content-Encoding` and transferred bytes (developer-only VPS access) stays deferred to the phase's final checkpoint, per `38-EFF-BASELINE.md`'s `## Live compression (VPS)` placeholder from 38-01.

## Next Phase Readiness

`_serve_static()` and the companion `encode` directive are in place and fully tested (HTTP-level: 15 tests; browser-level: 1 test; Caddy-config-level: 2 tests), plus the full companion suite (1569 tests) and the whole repo's test suite (2883 passed, 1 pre-existing unrelated local failure, coverage 94.04% against the 93.0% floor) both green. Plans 38-03 onward can proceed with EFF-02 through EFF-06 (per-page scripts, connection scoping, lazy context/freshness, `poll_state` write-once, parallel providers) independently of this plan's `companion/app.py` static-serving region. No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

All 5 named files found on disk; all 4 named commit hashes (`5932433`, `b0d57f2`, `096cafe`, `644565e`) found in `git log --oneline --all`.
