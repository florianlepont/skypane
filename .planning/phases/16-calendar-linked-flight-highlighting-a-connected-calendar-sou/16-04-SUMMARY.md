---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
plan: 04
subsystem: infra
tags: [ssrf, secrets, requests, ical, dns-rebinding, calendar]

# Dependency graph
requires:
  - phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou (waves 1-2, plans 16-01/16-03)
    provides: parse_ics_events(), the calendar_rules.json registry contract (load/write), select_window_entries(), calendar_fetch_is_due(), configured_calendar_url(), and the FETCH_* result-code constants
provides:
  - "_address_is_public()/_host_is_safe()/_url_is_safe(): resolved-address (not hostname-string) SSRF gate, closing the DNS-rebinding gap"
  - "default_calendar_transport()/fetch_ics(): streamed-size-capped, timeout-bounded, manually-redirected HTTPS fetch, re-validating every redirect hop"
  - "refresh_calendar_registry(state_dir, now, transport=None): the single once-per-cycle throttle/fetch/parse/window/persist entry point plan 16-07 will wire into poll_loop.py"
affects: [16-07 (poll_loop.py wiring), 16-06 (matcher, reads the registry this populates)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSRF gate resolves the hostname explicitly via socket.getaddrinfo() and classifies every returned address via ipaddress, rather than trusting the hostname string - closes DNS rebinding"
    - "Redirects followed manually (requests allow_redirects=False) with the identical scheme+address gate re-applied to every Location target before it is followed, hop count bounded"
    - "Response size capped by counting streamed bytes, never by trusting Content-Length"
    - "Logging discipline: only type(exc).__name__ is ever printed for a caught transport exception, never the exception's own string form - several requests.exceptions.* subclasses embed the request URL, which here carries a secret token"
    - "A failed fetch re-persists the existing entries unchanged, moving only last_attempt_at - last_synced_at moves only on a genuine successful parse"

key-files:
  created: []
  modified:
    - server/plane/calendar_rules.py
    - server/test_calendar_rules.py

key-decisions:
  - "fetch_ics()'s transport-call and body-read catches use a bare `except Exception`, not the narrower `(requests.RequestException, ValueError)` the plan's <action> text suggested - the plan's own <behavior> spec requires \"any exception raised by the transport returns nothing rather than propagating\", and Task 2's own verify script raises a plain Exception from a fake transport to prove it"
  - "Ad hoc verify commands embedded in the plan reference a bare hostname (feed.example.com) that does not resolve in any real DNS environment (no wildcard under example.com); re-ran the same assertions with socket.getaddrinfo() monkeypatched to a public IP for that hostname, matching Task 3's own committed-harness approach - the committed test_calendar_rules.py checks never depend on live DNS"
  - "Two pre-existing comments (one carried over from plan 16-03, one in this plan's own new docstring) used the literal string 'Content-Length', which fails the Task 1 acceptance criterion's exact-string grep; reworded both to 'declared-length header' without changing meaning"

requirements-completed: []

coverage:
  - id: D1
    description: "SSRF-hardened URL gate (_url_is_safe/_host_is_safe/_address_is_public) refuses non-https schemes, hostless URLs, every private/loopback/link-local/reserved address, unresolvable hostnames, and a hostname resolving to a mix of public+private addresses (DNS rebinding)"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#_url_is_safe() gate checks (32-37)"
        status: pass
    human_judgment: false
  - id: D2
    description: "fetch_ics() streams a bounded, timeout-bounded, redirect-bounded HTTPS body, re-validating every redirect hop, never trusting Content-Length"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#fetch_ics() redirect/size/status/timeout checks (38-46)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The calendar URL's token, host, path and query name never reach stderr across seven distinct failure paths (including a transport exception carrying the full secret URL) or the persisted registry"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#secret-containment checks (47-48)"
        status: pass
    human_judgment: false
  - id: D4
    description: "refresh_calendar_registry() performs no network I/O when unconfigured or throttled, fetches at most once per CALENDAR_FETCH_INTERVAL_S, preserves the existing window on failure, and never raises"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py#refresh orchestration checks (49-55)"
        status: pass
      - kind: integration
        ref: "scripts/run-all-tests.sh (55/55 calendar_rules checks, 93% total coverage, full suite PASS)"
        status: pass
    human_judgment: false

# Metrics
duration: 40min
completed: 2026-09-08
status: complete
---

# Phase 16 Plan 04: SSRF-hardened calendar fetch and once-per-cycle refresh Summary

**SSRF-hardened, size/timeout/redirect-bounded HTTPS fetch of the operator's iCal URL via `requests`, with a secret-safe logging discipline (exception type only, never the exception's own string form) and a single `refresh_calendar_registry()` throttle/fetch/parse/window/persist entry point for `poll_loop.py`.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-09-08T00:30:10+02:00
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `_address_is_public()` / `_host_is_safe()` / `_url_is_safe()`: validate the **resolved** address via `socket.getaddrinfo()` + `ipaddress`, not the hostname string, closing the DNS-rebinding gap; a hostname resolving to a mix of public and private addresses is refused even though a hostname-only check would pass it
- `default_calendar_transport()` / `fetch_ics()`: manual redirect following (`allow_redirects=False`) re-validating every `Location` hop through the identical gate, a hop-count bound, a streamed byte-count cap that never consults `Content-Length`, and a hard timeout - four independent bounds, none sufficient alone
- Logging discipline: the only path in `fetch_ics()` that logs at all prints `type(exc).__name__` and a fixed description, never the exception object itself - deliberately diverging from `detect.py`'s neighbouring `"%s: %s" % (type(exc).__name__, exc)` idiom, because several `requests.exceptions.*` subclasses embed the request URL (which here carries the calendar's access token) in their default string form
- `refresh_calendar_registry(state_dir, now, transport=None)`: the single per-cycle entry point - no network call when unconfigured or throttled, one bounded fetch otherwise, a failed fetch re-persists the existing entries unchanged (moving only `last_attempt_at`), a legitimately empty window on success is still success (distinguished from failure only by `last_synced_at` moving)
- Extended `server/test_calendar_rules.py` with 24 new checks (31 → 55), each of the three headline properties (DNS-rebinding refusal, secret-leak containment, throttle-holds-across-eleven-cycles) proven live via a targeted mutation that flips exactly that check and nothing else

## Task Commits

1. **Task 1: Add the SSRF-hardened, bounded, secret-safe fetch** - `4ae9de5` (feat)
2. **Task 2: Add refresh_calendar_registry()** - `e0fb57c` (feat) - includes a Rule 1 bug fix discovered while verifying this task (see Deviations)
3. **Task 3: Extend server/test_calendar_rules.py** - `529eddc` (test)

**Plan metadata:** (this commit) `docs(16-04): complete SSRF-hardened calendar fetch plan`

## Files Created/Modified
- `server/plane/calendar_rules.py` - added `USER_AGENT`, `_address_is_public()`, `_host_is_safe()`, `_url_is_safe()`, `default_calendar_transport()`, `fetch_ics()`, `refresh_calendar_registry()`
- `server/test_calendar_rules.py` - 24 new checks covering the SSRF gate, redirect/size/status/timeout bounds, secret containment across seven failure paths, and refresh-orchestration behaviour; `EXPECTED_CHECK_COUNT` raised 31 → 55

## Decisions Made
- Broadened `fetch_ics()`'s transport-call and body-read exception catches from `(requests.RequestException, ValueError)` to a bare `Exception` - the plan's own `<behavior>` contract ("any exception raised by the transport returns nothing rather than propagating") and Task 2's own verify script (which raises a plain `Exception` from a fake transport) both require it; the logging discipline (type name only, never the exception's string form) is preserved regardless of which branch is hit
- The plan's ad hoc verify commands use a literal hostname (`feed.example.com`) that does not resolve under any real-world DNS resolver (no wildcard exists under `example.com`, confirmed against three independent hostnames); re-ran the equivalent assertions with `socket.getaddrinfo()` monkeypatched for that one hostname, exactly matching the approach Task 3 itself specifies for the committed harness. The committed `test_calendar_rules.py` checks never depend on live DNS - every SSRF-gate check either uses an IP literal (resolves offline) or an explicit monkeypatch, restored in a `finally`
- Reworded two comments (one inherited from plan 16-03, one in this plan's own new docstring) that used the literal string `Content-Length`, to satisfy Task 1's acceptance criterion asserting `grep -c 'Content-Length' server/plane/calendar_rules.py` returns `0` - the code never reads that header; only the prose mentioned its name

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `fetch_ics()`'s transport-call catch was too narrow, silently violating its own never-propagates contract**
- **Found during:** Task 2, while running its own verify script (`refresh_calendar_registry(d, later, transport=lambda u,t: (_ for _ in ()).throw(Exception('down')))`)
- **Issue:** Task 1's `<action>` text described catching only `(requests.RequestException, ValueError)` around the transport call. A plain `Exception` (not a `requests.RequestException` subclass) propagated straight through `fetch_ics()` into `refresh_calendar_registry()`'s outer safety `try/except`, which then returned the registry loaded from disk *before* this attempt rather than the intended in-memory result - silently reusing a stale `last_attempt_at` instead of advancing it to `now`. This directly contradicted the plan's own `<behavior>` line: "Any exception raised by the transport returns nothing rather than propagating."
- **Fix:** Broadened both the transport-call catch and the body-streaming catch in `fetch_ics()` to a bare `except Exception as exc:`, keeping the existing secret-safe logging (type name only, never `exc` interpolated).
- **Files modified:** `server/plane/calendar_rules.py`
- **Verification:** Re-ran Task 2's verify script (passed) and the full `test_calendar_rules.py` harness (55/55) plus `scripts/run-all-tests.sh` (PASS, 93% coverage).
- **Committed in:** `e0fb57c` (Task 2 commit)

**2. [Rule 3 - Blocking, environmental] Plan's ad hoc verify commands reference a non-resolving hostname**
- **Found during:** Task 1 and Task 2, running the exact `<verify>` command blocks as written
- **Issue:** Both plan-supplied verify scripts use `SECRET='https://feed.example.com/cal.ics?token=...'` and expect `_url_is_safe()` to accept it on a successful-fetch assertion. `feed.example.com` does not resolve under any real DNS resolver (confirmed: `example.com` itself resolves, but no wildcard subdomain exists - `sub.example.com`, `test.example.com`, and `feed.example.com` all return `NXDOMAIN`/`gaierror` identically). As written, the scripts would fail the very "success" case they assert, for reasons entirely external to the implementation.
- **Fix:** Re-ran the identical assertions with `socket.getaddrinfo()` monkeypatched (restored in a `finally`) to resolve that one hostname to a public IP, matching the DNS-independence approach Task 3 itself specifies for the permanent harness. No implementation code was weakened to accommodate this; the fix is entirely in how the ad hoc verification was run.
- **Files modified:** none (verification-only; the committed `test_calendar_rules.py` was written DNS-independent from the start, using IP literals or explicit monkeypatches)
- **Verification:** Both ad hoc scripts, adapted this way, printed `fetch OK` / `refresh OK` and exited 0.

**3. [Rule 1 - Bug/consistency] Two comments used the literal string the acceptance criteria forbid**
- **Found during:** Task 1, running its own acceptance criteria (`grep -c 'Content-Length' server/plane/calendar_rules.py` expected `0`)
- **Issue:** A pre-existing comment on `CALENDAR_MAX_RESPONSE_BYTES` (landed by plan 16-03, anticipating this plan) and this plan's own new `fetch_ics()` docstring both said "Content-Length header", tripping the exact-string grep even though no code ever reads that header.
- **Fix:** Reworded both to "declared-length header" / "response's own declared-length header", preserving the exact same meaning.
- **Files modified:** `server/plane/calendar_rules.py`
- **Verification:** `grep -c 'Content-Length' server/plane/calendar_rules.py` now returns `0`; the oversized-body-with-lying-Content-Length behaviour and its test are unchanged.
- **Committed in:** `4ae9de5` (Task 1 commit)

---

**Total deviations:** 3 (1 bug fix, 1 environmental/verification-only, 1 doc-comment wording fix for an exact-string acceptance criterion)
**Impact on plan:** The Rule 1 bug fix (#1) is a genuine correctness fix directly required by the plan's own stated behaviour contract - without it, a raising fake transport (or a future non-`requests` exception) would silently leave `last_attempt_at` stale, defeating the throttle's own safety property. #2 changed nothing about the shipped code. #3 is cosmetic. No scope creep.

## Issues Encountered
None beyond the deviations above.

## User Setup Required
None - no external service configuration required. `SKYPANE_CALENDAR_ICS_URL` wiring into the deployed environment file happens in a later plan of this phase; this plan only adds the module-level fetch/refresh functions.

## Next Phase Readiness
- `calendar_rules.fetch_ics()` and `calendar_rules.refresh_calendar_registry()` are ready for plan 16-07 to wire into `poll_loop.py`'s per-cycle priming block, following the exact call shape documented in this plan's `<read_first>` references (`poll_loop.py:735-755`).
- `server/requirements.txt`/`server/requirements-dev.txt` are untouched; `server/plane/render.py`, `server/plane/colour_rules.py`, `server/plane/detect.py`, `server/plane/enrich.py`, `server/poll_loop.py`, `server/device_config.py`, and `companion/` are all untouched by this plan's commits, confirmed via `git diff --stat`.
- No blockers for 16-05 (running in the same wave) or 16-06/16-07 (later waves).

---
*Phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou*
*Completed: 2026-09-08*

## Self-Check: PASSED
- FOUND: server/plane/calendar_rules.py
- FOUND: server/test_calendar_rules.py
- FOUND: commit 4ae9de5
- FOUND: commit e0fb57c
- FOUND: commit 529eddc
