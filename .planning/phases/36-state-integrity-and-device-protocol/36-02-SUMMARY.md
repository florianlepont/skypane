---
phase: 36-state-integrity-and-device-protocol
plan: 02
subsystem: infra
tags: [http, requests, ssrf, dns-rebinding, tls, http.client, stdlib]

# Dependency graph
requires:
  - phase: 36-01
    provides: "server/atomic_io.py (not used directly by this plan; same wave, disjoint files)"
provides:
  - "server/http_fetch.py: bounded_get(url, *, headers=None, timeout, deadline_s, max_bytes, clock=None) -> FetchResult"
  - "server/http_fetch.py: pinned_request(method, url, *, headers=None, body=None, timeout, deadline_s, resolver=None, create_connection=None, ssl_context=None, clock=None) -> PinnedResponse"
  - "server/http_fetch.py: address_is_public(ip_text), resolve_public_addresses(hostname, port, resolver=None)"
  - "server/http_fetch.py: DeadlineExceeded, ResponseTooLarge, UnsafeDestination, FetchResult"
  - "test-support/skypane_test_support.py FakeResponse: iter_content/content/close (streaming surface)"
  - "deploy/skypane-poll.service: TimeoutStartSec=90s"
affects: [36-05, 36-06, 36-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "bounded_get: a streamed requests.get() checked against a monotonic total deadline between chunks and a running byte count that never trusts Content-Length, raising a requests.Timeout/RequestException subclass so existing except-RequestException handlers keep working"
    - "pinned_request: one getaddrinfo call, every answer checked public, connect only to a checked address via an http.client.HTTPSConnection subclass whose connect() never re-resolves; TLS verified against the hostname via an unmodified ssl.create_default_context()"

key-files:
  created: [server/http_fetch.py, server/test_http_fetch.py]
  modified: [test-support/skypane_test_support.py, deploy/skypane-poll.service, deploy/tests/test_units.py]

key-decisions:
  - "G-35 gate re-verified independently before any edit: 23 35-*-SUMMARY.md on origin/main, 35-VERIFICATION.md status passed on HEAD, ROADMAP Phase 35 fully checked, origin/main an ancestor of HEAD -- all four checks passed, no edits made by that task."
  - "pinned_request's tests drive real http.client.HTTPResponse parsing over a fake socket (io.BufferedReader wrapping a raw reader that returns exactly one byte per readinto call) rather than a hand-rolled response stub, so the status-line/header parser exercised is the same one production uses; PinnedResponse.iter_content's own deadline/settimeout-clamping timing test constructs PinnedResponse directly against a minimal fake body object instead, isolating that timing logic from response parsing so a deterministic 1-second-per-read fake clock is unambiguous."
  - "Added 6 tests beyond the plan's required behaviour list, closing gaps the plan's own verification step surfaced: bounded_get's pre-loop deadline check (an explicit interface bullet -- 'the deadline has passed when the response arrives' -- with no test), PinnedResponse.getcode()/close()/normal (non-exceptional) completion, pinned_request closing the connection when the request itself fails after connecting, a URL with no hostname, and every checked address refusing (not just the first). Coverage on server/http_fetch.py went from 94% to 100% (module fully covered); whole-repo coverage held at 93.2%, above the 93.0% floor. (Rule 1/2: closing an explicitly-documented but untested behaviour, and completing the module's own defensive branches, is correctness, not scope creep.)"

patterns-established:
  - "Pattern: bounded_get -- check the monotonic deadline once before consuming any content and again after every chunk; total byte count checked against max_bytes as chunks arrive, Content-Length never read; response.close() always in finally."
  - "Pattern: pinned_request -- resolve once via resolve_public_addresses (refuses the whole host on any non-public answer), try each checked address in order until one connects (a refusal is not a safety failure, just try the next), verify TLS via server_hostname on the real hostname, never follow a redirect, never read HTTP_PROXY/HTTPS_PROXY."

requirements-completed: []

# Metrics
duration: 20min
completed: 2026-09-26
---

# Phase 36 Plan 02: Bounded outbound HTTP (deadline + pinned TLS) Summary

**`server/http_fetch.py`: a streamed GET with a total wall-clock deadline and byte cap (`bounded_get`, INT-07), and a pinned HTTPS request that resolves a hostname exactly once and connects only to an address it already checked (`pinned_request`, INT-14) -- both proven by 32 tests against fake sockets/resolvers/SSL contexts, no real network; `skypane-poll.service` now carries `TimeoutStartSec=90s`.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-26T07:47:00Z (approx., first read of the plan)
- **Completed:** 2026-09-26T08:06:24Z
- **Tasks:** 3 (1 gate check, 2 TDD)
- **Files modified:** 5 (2 created: `server/http_fetch.py`, `server/test_http_fetch.py`; 3 modified: `test-support/skypane_test_support.py`, `deploy/skypane-poll.service`, `deploy/tests/test_units.py`)

## Accomplishments
- Confirmed Phase 35 is complete on `main` (gate G-35, re-verified independently of 36-01's own check) before making any edit.
- Landed `bounded_get`: a streamed `requests.get()` bound by a total wall-clock deadline (checked before any content and after every chunk) in addition to `timeout`'s own per-read bound, and by a running byte cap that never trusts a declared `Content-Length`. Raises `DeadlineExceeded` (a `requests.Timeout` subclass) or `ResponseTooLarge` (a `RequestException` subclass), so an existing `except requests.RequestException` handler needs no change to keep working once 36-05/36-06 migrate their callers onto it.
- Extended the shared `FakeResponse` test fake with `iter_content`/`content`/`close`, so every fake-provider test that streams a response (present and future) keeps working, proven end-to-end by streaming `bounded_get` through `fake_providers` itself.
- Added `TimeoutStartSec=90s` to `skypane-poll.service`: a oneshot's default start timeout is infinity, and every outbound call the cycle now makes is individually bounded, so 90s catches a genuinely stuck process without masking normal runs (a normal cycle is a few seconds; the documented bound per call is deadline + one read timeout).
- Landed `pinned_request` (INT-14, the decided pin -- not just a docstring correction): `resolve_public_addresses` resolves a hostname exactly once and refuses the whole host if any answer is not a public unicast address (`address_is_public`, the same classification `calendar_rules._address_is_public` already uses); a private `http.client.HTTPSConnection` subclass (`_PinnedHTTPSConnection`) connects only to an address already checked, never re-resolving; TLS is verified against the hostname via an unmodified `ssl.create_default_context()` (`check_hostname=True`, `CERT_REQUIRED`). `PinnedResponse` gives `fetch_ics`/`send_notification` the surface they need (`status_code`, `headers.get(...)`, `iter_content`, `close`, plus `is_redirect`/`getcode()`), with `iter_content` clamping the socket's timeout to `min(timeout, time left)` before every read and raising `DeadlineExceeded` once no time is left. Never follows a redirect itself and never reads an environment proxy.
- 32 tests total, none opening a real socket: a fake resolver, a fake socket whose `makefile("rb")` wraps a raw one-byte-per-`readinto` reader (so the response is parsed through `http.client`'s own real status-line/header parser), and a fake SSL context recording `wrap_socket` calls. Covers first-address success, falling through to a second address on a refused connection, refusal on any private DNS answer (with the resolver proven called exactly once), refusal on a resolution failure or empty answer, refusal of a non-`https` URL and a URL with no hostname, an unfollowed 302 redirect, a POST body with `Content-Length`, `address_is_public`'s classification for 7 representative addresses, and `PinnedResponse.iter_content`'s deadline/settimeout-clamping timing (isolated from response parsing via a direct `PinnedResponse` construction against a minimal fake body).

## Task Commits

Each task was committed atomically (Task 1 made no changes, so it has no commit):

1. **Task 1: Gate G-35 (Phase 35 complete on main)** - no commit (read-only check; all four automated checks passed, `git status --porcelain` empty)
2. **Task 2: bounded_get + streaming FakeResponse + poll unit start timeout (INT-07)** - `33ad9f8` (test, RED) + `6eede69` (feat, GREEN)
3. **Task 3: pinned_request, address checks and PinnedResponse (INT-14)** - `803707c` (test, RED) + `9da3d5b` (feat, GREEN, includes the added coverage-completion tests)

_TDD tasks: each is a test → feat pair (RED then GREEN); no refactor commit was needed._

## Files Created/Modified
- `server/http_fetch.py` - `DeadlineExceeded`, `ResponseTooLarge`, `UnsafeDestination`, `FetchResult`, `bounded_get`, `address_is_public`, `resolve_public_addresses`, `_default_ssl_context`, `PinnedResponse`, `_PinnedHTTPSConnection`, `pinned_request`; module docstring documents the deadline bound, the pinning rationale, and that redirects/proxies are never followed/read
- `server/test_http_fetch.py` - 32 behaviour tests: 11 for `bounded_get` (including a fake-provider streaming round trip), 21 for `pinned_request`/`PinnedResponse`/`address_is_public`
- `test-support/skypane_test_support.py` - `FakeResponse` gains `iter_content`, `content`, `close` (and a `closed` flag), so the fake still stands in for a `requests.Response` once a caller streams it
- `deploy/skypane-poll.service` - `TimeoutStartSec=90s` with a why-comment (bound = deadline + one read timeout per call, normal cycle a few seconds, no torn state on a kill since every write is atomic and flock releases with the process)
- `deploy/tests/test_units.py` - one new assertion pinning `skypane-poll.service`'s `TimeoutStartSec` to `90s`

## Decisions Made
See `key-decisions` in the frontmatter for the test-isolation strategy (real `http.client` parsing for the connect/request round trip, a direct minimal fake for `PinnedResponse`'s own timing) and the coverage-completion additions; both are elaborated in Deviations below since the latter is Rule 1/2 auto-fixed work not in the plan's task list.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/2 - Behaviour and coverage completeness] Added 6 tests closing an explicit interface gap and the module's remaining defensive branches**
- **Found during:** Task 3, after the GREEN implementation, running `./scripts/run-all-tests.sh` per the plan's own verification step
- **Issue:** `server/http_fetch.py` landed at 94% coverage. One gap was a real miss against the plan's own `<interfaces>` text -- `bounded_get` "raises `DeadlineExceeded` if the deadline has passed when the response arrives **or** after any chunk" -- only the "after any chunk" half had a test; the "when the response arrives" (pre-loop) branch was untested. The rest were the module's own defensive/completeness branches with no dedicated test: `PinnedResponse.getcode()`/`close()`/normal (non-exceptional) completion of `iter_content`, `pinned_request` closing the connection when the request itself fails after a successful connect, a URL with no hostname, and the case where every checked address refuses (not just the first, which was already covered).
- **Fix:** Added `test_bounded_get_raises_deadline_exceeded_before_any_content_is_read`, `test_pinned_response_getcode_and_close_and_normal_completion`, `test_pinned_request_closes_connection_on_request_failure`, `test_pinned_request_refuses_url_with_no_hostname`, and `test_pinned_request_refuses_when_every_checked_address_refuses` to `server/test_http_fetch.py` -- all behaviour tests against the existing fakes, no production code change was needed (every branch was already correct, just untested).
- **Files modified:** `server/test_http_fetch.py` (tests only)
- **Verification:** `server/http_fetch.py` coverage went from 94% (9 lines missing) to 100% (module fully covered, no longer listed in the coverage report's per-file table -- it moved into "files skipped due to complete coverage"). `./scripts/run-all-tests.sh` reports `Required test coverage of 93.0% reached. Total coverage: 93.21%`, exit 0, 2630 passed / 132 skipped (all Playwright-Chromium or root-euid skips, pre-existing and expected in this sandbox).
- **Committed in:** `9da3d5b` (Task 3's GREEN commit)

**2. [Rule 1 - Comment-guard fix] Removed a phase-ID reference from a module docstring**
- **Found during:** Task 3, running `scripts/check_comment_history.py check` per the plan's own verification step
- **Issue:** The module docstring's forward-looking note ("a later phase (ARC-03) is expected to absorb it...") tripped the comment guard's `prefix-id` check (`server/http_fetch.py:32: prefix-id: ARC-03`), which forbids plan/ticket/phase IDs in comments and docstrings.
- **Fix:** Reworded to "a future refactor is expected to absorb it, plus `calendar_rules._url_is_safe`, into a shared `net/safe_fetch.py`" -- same information (this module is deliberately small and expected to be absorbed later), no ID.
- **Files modified:** `server/http_fetch.py` (docstring only, part of Task 3's GREEN implementation, not a separate commit)
- **Verification:** `scripts/check_comment_history.py check` exits 0 with no output.
- **Committed in:** `9da3d5b` (Task 3's GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 behaviour/coverage completeness, Rule 1/2; 1 comment-guard fix, Rule 1)
**Impact on plan:** No scope creep on the interface contract -- `bounded_get` and `pinned_request` match `<interfaces>` exactly; the fixes are test-only (deviation 1) and a docstring reword (deviation 2), both closing gaps the plan's own verification steps surfaced.

## Issues Encountered
None beyond the two deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/http_fetch.py` is ready for 36-05 (`calendar_rules`, `notify`) and 36-06 (`detect`, `enrich`, adsbdb) to migrate their `requests.get`/`urllib` calls onto `bounded_get`/`pinned_request`. `fetch_ics`'s redirect-following loop and `send_notification`'s single POST both get the `PinnedResponse` surface they already expect (`status_code`, `headers.get(...)`, `iter_content`, `close`).
- `skypane-poll.service` now has a start timeout; no other unit needed one per this plan's scope.
- Per this plan's requirements-completed note: INT-07 and INT-14 are left **Pending** in REQUIREMENTS.md, not Complete -- this plan lands the primitives, but neither requirement is delivered end-to-end until 36-05/36-06/36-07 wire their callers onto them (per the environment notes for this plan).
- Kept as one small module for now (both `bounded_get` and `pinned_request` together); a future refactor is expected to absorb it, plus `calendar_rules._url_is_safe`, into a shared `net/safe_fetch.py`.
- No blockers for wave 2 (36-03..36-06).

## Self-Check: PASSED

- FOUND: server/http_fetch.py
- FOUND: server/test_http_fetch.py
- FOUND commit 33ad9f8 (test RED, Task 2)
- FOUND commit 6eede69 (feat GREEN, Task 2)
- FOUND commit 803707c (test RED, Task 3)
- FOUND commit 9da3d5b (feat GREEN, Task 3)

## TDD Gate Compliance

Both TDD tasks show the required RED -> GREEN sequence in git log:
- Task 2: `33ad9f8 test(36-02): ...` then `6eede69 feat(36-02): ...`
- Task 3: `803707c test(36-02): ...` then `9da3d5b feat(36-02): ...`

No REFACTOR commit was needed for either task.

---
*Phase: 36-state-integrity-and-device-protocol*
*Completed: 2026-09-26*
