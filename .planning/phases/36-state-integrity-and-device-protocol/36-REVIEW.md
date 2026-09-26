---
phase: 36-state-integrity-and-device-protocol
reviewed: 2026-09-26T11:22:03Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - server/atomic_io.py
  - server/http_fetch.py
  - stub-server/byos_server.py
  - server/device_config.py
  - server/plane/calendar_rules.py
  - server/plane/colour_rules.py
  - server/plane/manual_resolutions.py
  - server/plane/detect.py
  - server/plane/enrich.py
  - server/notify.py
  - server/history_db.py
  - server/poll_loop.py
  - companion/app.py
  - companion/theme_preview.py
  - companion/illustration_normalize.py
  - deploy/backup/backup_gate.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 36: Code Review Report

**Reviewed:** 2026-09-26T11:22:03Z
**Depth:** standard
**Files Reviewed:** 16 (plus `deploy/skypane-poll.service` and the corresponding test files, read for cross-checking but not separately findings-bearing)
**Status:** issues_found

## Summary

Reviewed every production source file `git diff 7cd0380..HEAD` touched for Phase 36, against the locked decisions in `36-CONTEXT.md` (lock ordering, atomic-write contract, TLS pinning, byos request hardening, deadline enforcement, adsbdb cache TTL/LRU). Most of the work is solid and matches its own documented contract closely: `atomic_io.py`'s mkstemp-then-`os.replace()` writer and `exclusive_lock()` are correct (mode set before any byte is written, temp cleaned up on every failure path, lock always released in `finally`); `device_config.py`, `colour_rules.py`, `manual_resolutions.py` and `calendar_rules.py` all follow the same load-validate-lock-write discipline and the documented lock order (in-process `threading.Lock` → file lock, `device_config.lock` never nested inside another file lock); `poll_loop.py` correctly threads `detected=flight is not None` into the held branch for INT-13; `history_db.py`'s Caddy tailer matches INT-09's partial-line/offset-reset contract; `enrich.py`'s adsbdb cache TTL/LRU matches INT-08 exactly; `byos_server.py`'s Content-Length bounding, constant-time bearer compare, and content-addressed image publishing all match INT-05/INT-06.

The one finding rising to Critical is in the new `server/http_fetch.py` module (INT-07/INT-14's pinned-connection primitive): DNS resolution is not bounded by, or counted against, the "total wall-clock deadline" the module's own docstring and INT-07 both promise. Two Warnings cover a related contract gap in the same module (a raised exception on a request-write/read failure is not always a `requests.RequestException` as documented, confirmed by the module's own test suite) and a `settimeout(0)` misuse when the deadline has already elapsed before a connection attempt. One Info item notes a benign but slightly misleading module-docstring claim.

## Critical Issues

### CR-01: `pinned_request()`'s DNS resolution is not bounded by `deadline_s`, defeating the "total wall-clock deadline" guarantee INT-07/INT-14 require

**File:** `server/http_fetch.py:152-187` (`resolve_public_addresses()`), called from `pinned_request()` at `server/http_fetch.py:309`

**Issue:** `resolve_public_addresses()` calls `socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)` (or an injected `resolver`) with no timeout at all, and this call happens *before* `pinned_request()`'s own deadline arithmetic is applied to anything else. The module's docstring states the primitive "resolves a hostname once ... and connects only to an address it already checked", and INT-07 (locked) requires "every outbound HTTP call has a total wall-clock deadline, not only per-read timeouts", tested/documented elsewhere in this same phase as "deadline + one read timeout". A slow or non-responding DNS resolver (the operator's calendar feed host, or the ntfy topic host, going through a captive/broken resolver) can block this call for the platform's full default resolver timeout (which can be tens of seconds to indefinite, depending on `/etc/resolv.conf` and glibc's own retry/timeout behaviour) with **no bound at all** from this module — the `deadline_s` clock (`deadline = clock() + deadline_s` at line 297) is computed before this call but never checked until *after* it returns.

This is a direct violation of the invariant this same module exists to add (its own docstring: "adds a total wall-clock deadline ... on top of `timeout`'s own per-connect/per-read bound"). In production the only backstop is systemd's `TimeoutStartSec=90s` on `skypane-poll.service`, which will eventually kill a stuck poll cycle — but that means a single slow calendar DNS lookup can turn an intended ~10s-bounded calendar fetch (`CALENDAR_FETCH_DEADLINE_S=10.0`) into a cycle that runs up to 90s before being killed, violating the module's own "worst case is deadline + one read timeout" claim and the phase's stated boundary ("no single bad input or slow upstream can hang or fail a poll cycle" — here it *does* hang, up to the systemd kill). For the companion's synchronous "Save calendar URL" / "Send a test notification" HTTP handlers (`companion/app.py`'s `_handle_settings_post()`, notification test button), there is no such backstop at all: the request-handling thread blocks on the unbounded resolver call for as long as the OS/resolver takes.

**Fix:** Bound the resolution call by the same deadline as the rest of the request. `socket.getaddrinfo` has no first-class timeout parameter, so either run it in a way that can be interrupted at the deadline (e.g. a short-lived thread joined with a timeout, raising `DeadlineExceeded` if it doesn't return in time), or, at minimum, check `clock() > deadline` immediately before *and* after the resolution call and raise `DeadlineExceeded`/`UnsafeDestination` if the budget is already exhausted, rather than only starting the deadline clock at line 297 without ever consulting it around the resolve step:

```python
def resolve_public_addresses(hostname, port, resolver=None, deadline=None, clock=None):
    getaddrinfo = resolver or socket.getaddrinfo
    clock = clock or time.monotonic
    if deadline is not None and clock() > deadline:
        raise DeadlineExceeded("resolve_public_addresses: deadline already exceeded")
    # Run getaddrinfo on a worker thread, join(timeout=deadline - clock()),
    # and raise DeadlineExceeded if the thread is still alive afterward.
    ...
```

## Warnings

### WR-01: `pinned_request()` can raise a raw, un-wrapped `OSError` (e.g. `BlockingIOError`) instead of a `requests.RequestException`, contradicting the module's own documented contract

**File:** `server/http_fetch.py:24-30` (docstring), `:317-359` (`pinned_request()`'s connect/send/receive path), demonstrated by `server/test_http_fetch.py:594-614` (`test_pinned_request_closes_connection_on_request_failure`, which explicitly asserts a raw `BrokenPipeError` propagates)

**Issue:** The module docstring states: "Both primitives raise exceptions that are also `requests.exceptions.RequestException` ... so every existing `except requests.RequestException` / `except requests.Timeout` handler in this codebase keeps working unchanged once a caller migrates onto these primitives." This is not actually true for `pinned_request()`: a socket failure during `sendall()` (via `conn.putrequest()`/`conn.endheaders()`) or during `conn.getresponse()` propagates as a raw `OSError` subclass (the existing test proves this for `BrokenPipeError`), never wrapped into `UnsafeDestination` or any other `RequestException` subclass. Additionally, when `deadline_s` has already elapsed before a connect/send/receive step, the code computes `connect_timeout = 0` (`http_fetch.py:319`) and calls `sock.settimeout(0)` (`:348`, `:355`), which puts the socket into **non-blocking mode**, not "time out immediately" — this can itself surface as a raw `BlockingIOError` (an `OSError` subclass) from `sendall()`/`getresponse()`, again bypassing the documented `DeadlineExceeded` contract entirely.

Today every caller of `pinned_request()` (`calendar_rules.fetch_ics()`'s transport-call `except Exception as exc:` at `calendar_rules.py:1081`, and `notify.send_notification()`'s `except Exception as exc:` at `notify.py:120`) wraps the call broadly enough to swallow this regardless of exception type, so no cycle currently crashes because of it. But the documented contract is false, the failure is misclassified (a deadline overrun surfaces as a raw socket error rather than `DeadlineExceeded`, making the "deadline + one read timeout" bound unverifiable from the exception type alone), and a future caller written against the documented contract (`except requests.RequestException`) would not catch it.

**Fix:** Either (a) narrow the docstring to say what is actually guaranteed today (only `resolve_public_addresses()`'s failures, and only certain paths, are guaranteed `RequestException` subclasses), or (b) wrap the connect/send/receive block in `try/except OSError` and re-raise as `UnsafeDestination`/`DeadlineExceeded` as appropriate, and stop passing `timeout=0` to a blocking socket call — check the deadline explicitly and raise `DeadlineExceeded` before attempting the connect/send/receive rather than degrading to non-blocking mode:

```python
time_left = deadline - clock()
if time_left <= 0:
    conn.close()
    raise DeadlineExceeded("pinned_request: deadline exceeded before send/receive")
conn.sock.settimeout(min(timeout, time_left))
```

### WR-02: byos_server.py's `_atomic_write()` is a hand-copied duplicate of `atomic_io.atomic_write()` with no shared implementation, only a behaviour-parity test

**File:** `stub-server/byos_server.py:98-178`

**Issue:** This is called out and accepted in `36-CONTEXT.md` ("byos ... gets one local `_atomic_write` with the same contract ... SUMMARY records the copy as a Phase 39 ARC-05 input"), so it is not a new defect introduced against the plan — flagged here only because the duplication is real and any future edit to `atomic_io.atomic_write()`'s contract (e.g. a new failure-handling branch) will silently not apply to byos unless the parity test (`stub-server/test_byos_hardening.py`) is remembered and re-run. No action needed this phase; recorded so it is not lost track of before Phase 39 retires the copy.

**Fix:** None required now (deferred to Phase 39 per the locked decision). Confirm the parity test stays in CI until the duplicate is retired.

## Info

### IN-01: `http_fetch.py` module docstring overstates DNS-rebinding protection strength given CR-01

**File:** `server/http_fetch.py:11-22`

**Issue:** The docstring's claim — "resolves a hostname once ... refuses the whole host if any answer is not a public unicast address, and connects only to an address it already checked — closing the gap where `requests`/`urllib` re-resolve the hostname again at connect time" — is true for the *connect* step, but the missing deadline bound on the resolution step itself (CR-01) means the "one small stdlib primitive" is not actually deadline-safe end-to-end yet, only rebinding-safe. Once CR-01 is fixed, this note is resolved for free; recorded separately since it's a documentation precision issue distinct from the behavioural gap.

**Fix:** Update the docstring once CR-01 is fixed to state the resolution step's own bound explicitly, so a future reader doesn't have to re-derive it from the code.

---

_Reviewed: 2026-09-26T11:22:03Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Resolution (2026-09-26, orchestrator)

- **CR-01 fixed:** `resolve_public_addresses(..., timeout_s=)` runs `getaddrinfo` on a daemon thread bounded by the caller's remaining deadline and raises `DeadlineExceeded` when the resolver stalls; `pinned_request` passes its remaining time. Test: `test_pinned_request_raises_deadline_exceeded_when_dns_stalls`.
- **WR-01 fixed:** an elapsed deadline raises `DeadlineExceeded` before resolving, connecting, sending or reading the response (no more `settimeout(0)`); a raw `OSError`/`http.client.HTTPException` during the request is re-raised as `requests.exceptions.ConnectionError` (a socket timeout as `ReadTimeout`). Tests: `test_pinned_request_closes_connection_on_request_failure` (now asserts the wrapped type), `test_pinned_request_raises_deadline_exceeded_when_deadline_already_spent`.
- **WR-02:** accepted as designed (byos vendor boundary, removed by Phase 39 ARC-05).
- Full suite after the fixes: 2723 passed, 133 skipped (sandbox browser/root skips), coverage 93.79%.
