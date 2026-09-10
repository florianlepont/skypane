---
phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh
plan: 04
subsystem: ui
tags: [python, stdlib-http, settings-form, calendar, ssrf-mitigation]

requires:
  - phase: 17-03
    provides: >-
      submitted_calendar_signal() (the single carry-forward/set/clear/invalid
      resolver), calendar_group()'s write-only field and disconnect checkbox,
      and the calendar_drift context key render() already reads
  - phase: 17-02
    provides: >-
      refresh_calendar_registry()'s min_interval_s throttle-bypass parameter,
      and the file-backed calendar_is_configured()/configured_calendar_url()
      accessors

provides:
  - "_handle_settings_post(): an app.py-owned handler replacing the inline POST /settings branch, choosing between saved/rejected/connected/disconnected/deferred/failed outcomes"
  - "The save-triggered immediate calendar sync (D-06): one refresh_calendar_registry() call with min_interval_s=0, inside the shared _POLL_LOCK's non-blocking acquire (D-09)"
  - "Four new flash keys (calendar_connected, calendar_sync_failed, calendar_disconnected, calendar_sync_deferred), their copy, their ARIA roles, and the connected key's on-disk-count resolver special case"
  - "calendar_drift threaded into page_context(), read fresh per request"

affects: []

tech-stack:
  added: []
  patterns:
    - "A call-shape spy (monkeypatching a module-level function to record its kwargs while still delegating to the real implementation) as the only way to prove an argument is passed explicitly when the surrounding architecture makes the argument's *effect* unobservable on that call path"
    - "An in-process ThreadingHTTPServer harness (_InProcessHarness), sibling to the existing subprocess Harness, used specifically when a check needs to monkeypatch a module the subprocess's separate interpreter could never see"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/app.py
    - companion/test_companion_app.py

key-decisions:
  - "The throttle-bypass check (plan Task 3 item 6) could not be proven by seeding a stale last_attempt_at and observing whether the transport was called, because config_page.handle_post()'s own save_calendar_url() (17-01) unconditionally erases the whole registry - including last_attempt_at, resetting it to None - on every successful set, BEFORE this handler's own refresh call ever runs. Since calendar_fetch_is_due() already returns True unconditionally whenever last_attempt_at is None, the fetch would run whether min_interval_s were 0, omitted, or anything else on this call path. Replaced the black-box transport-call assertion with a spy on refresh_calendar_registry() itself, which is the only technique that actually distinguishes the two."
  - "The connected message's two placeholders ({n}/{s}) are the third deliberate exception to 'FLASH_MESSAGES carries no runtime interpolation' (after poll_cooldown and rule_replaced) - widened the existing regression check in place rather than loosening it, mirroring Phase 15's own precedent for rule_replaced."
  - "FLASH_KEY_CALENDAR_SYNC_DEFERRED deliberately does NOT reuse FLASH_KEY_POLL_ALREADY_RUNNING's copy - that string says nothing about whether the save itself succeeded. The LOCK behaviour is reused (D-09); the copy is not."

patterns-established:
  - "A call-shape spy for proving an explicit-vs-default argument value when the callee's own architecture (here: an upstream write that resets the exact state the argument would otherwise matter for) makes the argument's runtime effect unobservable through the front door alone"

requirements-completed: []

coverage:
  - id: D1
    description: "Saving a calendar feed URL performs exactly one refresh call with the throttle bypassed (min_interval_s=0, not omitted), and the page reports the resulting flight count"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#saving a calendar feed with three in-window flights performs exactly one refresh call and the rendered banner names the plural flight count (D-06)"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#saving a calendar feed with exactly one in-window flight pins the singular form ('1 flight', never '1 flights')"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#a syntactically valid feed with nothing in the frame's window reports success with a 0 count, distinguishable from a failure"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#a save-triggered sync against a calendar with a 60s-old last_attempt_at still fetches and reports success, and refresh_calendar_registry() is called with min_interval_s=0 explicitly"
        status: pass
    human_judgment: false
  - id: D2
    description: "There is exactly one honest generic failure message, built from the classified result code and nothing else - no exception is caught, no exception's text is read"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#a failing fetch redirects with the single generic failure flash key, renders the exact failure copy, and the URL is saved regardless (D-06)"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#handler shape verify script: no 'except' substring in _handle_settings_post()'s body"
        status: pass
    human_judgment: false
  - id: D3
    description: "T-17-FLASH: a raised error whose message embeds the full URL never surfaces the token, host, path segment, query-parameter name, or whole URL anywhere in the response"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#T-17-FLASH: a raised error whose message embeds the full URL never surfaces the token, host, path segment, query-parameter name, or whole URL in the Location header or any served response body"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-09: a save arriving while the poll lock is held gets an honest deferred answer, never a race with a concurrent poll cycle's own refresh; the lock is released on every path including failure"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#a save arriving while the poll lock is already held redirects with the deferred flash key, performs no fetch, and still saves the URL (D-09)"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#after a save whose immediate fetch fails, the poll lock is still free - one failure never wedges a later manual poll trigger"
        status: pass
    human_judgment: false
  - id: D5
    description: "A settings save that touches no calendar field is byte-identical in behaviour to before this phase - no fetch, no lock acquisition, no change to the calendar; the manual poll cooldown stays independent"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#a settings save that changes only the theme, against an already-connected calendar, redirects with the ordinary saved key, performs no fetch, and leaves the calendar and its fetched entries untouched"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#a calendar save immediately followed by a manual poll trigger does not hit the poll cooldown - the two mechanisms are independent"
        status: pass
    human_judgment: false
  - id: D6
    description: "The disconnect checkbox reports both halves of what happened - disconnected, and the fetched flights actually deleted from disk"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#checking the disconnect box redirects with the disconnected flash key, and the calendar's previously-fetched flights are actually erased from disk (D-04)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Manual verification: the Calendar group reads truthfully in a real browser across all four states (not connected, connected, connected then disconnected, permissions widened)"
    verification: []
    human_judgment: true
    rationale: "17-VALIDATION.md's Manual-Only Verifications section requires a human to judge whether the rendered copy 'sounds truthful to someone who knows what the frame actually does' - not an assertion any automated check can make."

duration: ~60min
completed: 2026-09-10
status: complete
---

# Phase 17 Plan 04: The settings write handler, the immediate sync, and the outcome copy Summary

**A new `_handle_settings_post()` handler closes the loop D-06 opened: saving a calendar URL triggers one throttle-bypassed `refresh_calendar_registry()` call inside the shared poll lock, and four new flash keys report connected/failed/disconnected/deferred — with the failure path structurally forbidden from ever reading a caught exception's text.**

## Performance

- **Duration:** ~60 min
- **Completed:** 2026-09-10
- **Tasks:** 3/3
- **Files modified:** 3

## Accomplishments

- Four flash keys (`calendar_connected`, `calendar_sync_failed`, `calendar_disconnected`, `calendar_sync_deferred`) declared in `config_page.py` and rebound in `app.py`, with `calendar_sync_failed` alone taking the assertive ARIA role; a third special case in `_resolve_flash_text()` fills the connected message's flight count and pluralisation from a fresh on-disk registry read at render time — never carried through the redirect's query string
- `_handle_settings_post()` — a new `app.py`-owned handler, sibling of `_handle_poll_now()`: calls `config_page.handle_post()`, then consults `submitted_calendar_signal()` again (never re-derived) to decide whether the save touched the calendar at all, and if so whether it set or cleared it
- A valid new URL acquires `_POLL_LOCK` (D-09 — the same lock `/poll-now` uses, not a second one) with a non-blocking acquire, then calls `calendar_rules.refresh_calendar_registry()` directly with `min_interval_s=0` — never `poll_loop.run_once()`. No error handler wraps the call anywhere in the method; a static verify script asserts the literal substring `except` never appears in the method body
- `POST /settings`'s dispatcher now delegates to the new handler; the session gate is unchanged
- Twelve new checks in `companion/test_companion_app.py`, all driven through a real HTTP round trip via a new `_InProcessHarness` (a `ThreadingHTTPServer` running in the test process itself, not a `Harness` subprocess) — needed because these checks monkeypatch `calendar_rules.default_calendar_transport` and `socket.getaddrinfo`, which a subprocess's separate interpreter could never observe. Ledger 165 → 177

## Task Commits

1. **Task 1: Four flash keys, their copy, their roles, the count resolver and the drift context key** - `69f0aa2` (feat)
2. **Task 2: The settings write handler and the immediate sync** - `854c25c` (feat)
3. **Task 3: Pin the sync outcomes, the lock contention path, the unchanged save, and the leak** - `acade1c` (test)
4. **Task 3 follow-up: fix a vacuous throttle-bypass check found by mutation testing** - `7ac8fc1` (test)

**Plan metadata:** committed together with this summary.

## Files Created/Modified

- `companion/pages/config_page.py` — Four new flash-key constants (`FLASH_CALENDAR_CONNECTED`/`SYNC_FAILED`/`DISCONNECTED`/`SYNC_DEFERRED`), defined once for `app.py` to rebind, matching every other flash-key module boundary already established in this file
- `companion/app.py` — The four keys rebound and given copy/ARIA roles in `FLASH_MESSAGES`/`FLASH_ROLES`; a third `_resolve_flash_text()` special case for the connected key's count interpolation; `calendar_drift` added to `page_context()`; the new `_handle_settings_post()` handler (replacing the inline `POST /settings` branch in `do_POST()`)
- `companion/test_companion_app.py` — `_InProcessHarness`, `_FakeCalendarResponse`, `_make_calendar_transport`, `_stubbed_calendar_transport`, `_fake_public_hostname`, and `_ics_body()` fixture helpers; twelve new checks covering every outcome D-06/D-09 define; the existing "no FLASH_MESSAGES value carries a runtime placeholder" regression check widened to except `calendar_connected`; ledger 165 → 177

## Decisions Made

- **The throttle-bypass check needed a call-shape spy, not a black-box transport-call assertion.** Mutation testing (dropping `min_interval_s=0`) revealed that `config_page.handle_post()`'s own call to `calendar_rules.save_calendar_url()` (shipped in plan 17-01) unconditionally erases the *whole* registry — including `last_attempt_at`, resetting it to `None` — on every successful `set`, before `_handle_settings_post()`'s own refresh call ever runs. Since `calendar_fetch_is_due()` already returns `True` unconditionally whenever `last_attempt_at is None`, seeding a stale attempt and observing "was the transport called" cannot distinguish `min_interval_s=0` from an omitted argument on this specific call path — the fetch runs either way. The committed check now monkeypatches `refresh_calendar_registry()` itself to record the `min_interval_s` it was actually called with, which does distinguish the two (confirmed failing when the argument is dropped, passing when restored). This is documented inline in the check's own docstring and in `<architecture-note>`-equivalent commentary so a future reader does not "simplify" the spy back into a transport-call assertion.
- **`FLASH_KEY_CALENDAR_SYNC_DEFERRED` deliberately does not reuse `FLASH_KEY_POLL_ALREADY_RUNNING`'s copy**, per the plan's own explicit instruction: that string says nothing about whether the save itself succeeded, which would leave the operator unsure whether their URL was even stored. The lock *behaviour* is reused (D-09); the copy is not.
- **The connected message's copy avoids any verb-agreement construction** ("Connected — {n} flight{s} from this calendar in the frame's current window") so the same template reads correctly for 0, 1, and N without a second singular/plural branch on a verb.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, discovered via mutation testing] The throttle-bypass check was vacuous as first written**
- **Found during:** Task 3's own `<verify_your_own_work>` mutation pass (dropping `min_interval_s` from the sync call)
- **Issue:** The check seeded a stale `last_attempt_at` and asserted the transport stub was called after a settings save. This passed identically whether `min_interval_s=0` was present or dropped, because `config_page.handle_post()`'s own `save_calendar_url()` call already resets `last_attempt_at` to `None` on every successful `set`, and `calendar_fetch_is_due()` treats `None` as always-due regardless of the interval argument.
- **Fix:** Replaced the transport-call assertion with a spy on `calendar_rules.refresh_calendar_registry()` itself, capturing the exact `min_interval_s` value it was called with. Confirmed by mutation: fails (`got [None]`) with the argument dropped, passes (`got [0]`) with it restored.
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** Re-ran the full mutation cycle (drop → fails; restore → 177/177 pass)
- **Committed in:** `7ac8fc1` (separate follow-up commit, after `acade1c`)

**2. [Rule 1 - Bug] An existing regression check needed widening for the new interpolated key**
- **Found during:** Task 2's own verification, immediately after wiring `FLASH_KEY_CALENDAR_CONNECTED`
- **Issue:** A pre-existing check in `test_companion_app.py` asserts no `FLASH_MESSAGES` value carries `%`/`{` except the cooldown and `rule_replaced` keys (Phase 15's own precedent). `FLASH_KEY_CALENDAR_CONNECTED`'s `{n}`/`{s}` correctly tripped this guard.
- **Fix:** Widened the check's exception list in place, mirroring exactly how Phase 15 widened it for `rule_replaced` — not loosened, a third named exception with the same justification (server-computed value, never client-supplied).
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** Full suite green (165/165 before Task 3's ledger bump, then 177/177 after)
- **Committed in:** `854c25c` (part of Task 2's commit, since it was required to keep the suite green after Task 2's change)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs discovered and fixed in the executor's own test code, not in the shipped feature)
**Impact on plan:** No scope creep; both fixes are within Task 3's own mandate to prove the checks non-vacuous.

## Issues Encountered

- **The failure copy's apostrophe escapes to `&#x27;` on render** (`layout.escape_html()`), the identical surprise plan 17-02 recorded for `CALENDAR_STATUS_NOT_CONFIGURED`. The failure-message test compares against `layout.escape_html(expected_text)`, not the raw `FLASH_MESSAGES` string.
- **`_InProcessHarness` needed its own `SKYPANE_COMPANION_PASSWORD` env-var lifecycle.** By the time Section 3/4 of `test_companion_app.py` run, the file's own outer setup has already restored the parent process's environment (every `Harness` subprocess check sets the variable in its own child `env` dict instead). Since `_InProcessHarness` runs `companion.app.Handler` in-process, it now sets and restores `auth.PASSWORD_ENV_VAR` itself in `__init__`/`stop()`.

## Mutation Testing Results (`<verify_your_own_work>`)

Both required mutations were run and reverted; `git diff` against `companion/app.py` shows zero net change after both cycles.

| # | Mutation | Effect | Which check(s) caught it |
|---|---|---|---|
| 1 | Drop `min_interval_s=0` from the `refresh_calendar_registry()` call | `176/177` — the spy-based throttle-wiring check fails (`got [None]`, expected `[0]`) | `a save-triggered sync ... refresh_calendar_registry() is called with min_interval_s=0 explicitly` |
| 2 | Wrap the `refresh_calendar_registry()` call in `except Exception as exc:` and interpolate `str(exc)` into the redirect's `detail=` query param | Task 2's own **static** verify script fails immediately (`AssertionError: no error handler may appear in this method`) — the dynamic suite still passes 177/177 unchanged, because `refresh_calendar_registry()` is genuinely never-raising in production, so the added `except` branch is unreachable through any real HTTP request | Task 2's structural verify (`assert 'except' not in body`) |

**Supplementary proof for mutation 2 (ad hoc, not committed):** since the mutated `except` branch is unreachable through the real call path, I additionally monkeypatched `calendar_rules.refresh_calendar_registry` to raise directly (simulating a violated never-raising contract) against the same mutated handler. Result: the distinctive token `LEAKTOKEN99999` and the full URL appeared verbatim in the redirect's `Location` header (`&detail=Failed%20to%20resolve%20https%3A//leak-check-host.example/...`). This confirms the "no except clause anywhere in this method" rule is load-bearing — not defense-in-depth against a scenario that already can't happen, but the single barrier standing between the never-raising contract and a real leak if that contract were ever violated by a future refactor.

Both mutations were reverted; `git diff --stat companion/app.py` is empty relative to the committed state, and the full suite (`bash scripts/run-all-tests.sh`) passes at 92% coverage with `ruff check .` clean.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

This is the last plan of Phase 17. Everything the phase set out to build is now shipped:

- The URL lives in a `0600` file, never the environment (17-01/17-02)
- The write-only field, disconnect checkbox, and drift status render in the companion (17-03)
- Saving a URL syncs immediately, bypassing the throttle, and reports connected/failed/disconnected/deferred outcomes without ever risking the URL in a rendered message (17-04, this plan)

**Remaining before the phase can close:**
- `17-VALIDATION.md`'s Manual-Only Verifications: a human must read the Calendar group in a real browser across all four states (not connected, connected, connected then disconnected, permissions widened) and judge whether the copy still sounds truthful
- `/gsd-secure-phase 17` — the closing audit listed in `17-04-PLAN.md`'s own `<verification>` section, checking the permission-bits/guard-order/no-env-read/no-URL-in-render/single-resolver/no-caught-exception properties across all four plans at once

No blockers. `bash scripts/run-all-tests.sh` is green (92% coverage), `server/.venv/bin/ruff check .` is clean, and both required mutations were run and reverted cleanly.

---
*Phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh*
*Completed: 2026-09-10*

## Self-Check: PASSED

Verified on disk and in git history after writing this summary:
- `companion/pages/config_page.py` — FOUND
- `companion/app.py` — FOUND
- `companion/test_companion_app.py` — FOUND
- This summary file — FOUND
- Commits `69f0aa2`, `854c25c`, `acade1c`, `7ac8fc1` — all FOUND in `git log --oneline --all`
