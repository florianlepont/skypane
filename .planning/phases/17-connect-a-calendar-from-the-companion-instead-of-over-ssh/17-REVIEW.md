---
phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh
reviewed: 2026-09-10T00:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - server/plane/calendar_rules.py
  - server/test_calendar_rules.py
  - server/test_poll_loop.py
  - companion/app.py
  - companion/pages/config_page.py
  - companion/test_config_page.py
  - companion/test_companion_app.py
  - deploy/skypane.env.example
findings:
  critical: 2
  warning: 1
  info: 1
  total: 4
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-09-10
**Depth:** deep
**Files Reviewed:** 8
**Status:** issues_found

## Summary

This review read all four plan summaries, the locked context (D-01..D-09 plus the two research
amendments and the two security corrections), and the full diff from `4d6cd96` to `HEAD`. The
0600-at-creation secret writer, the mode-drift guard, the disconnect checkbox's polarity, the
`submitted_calendar_signal()` resolver, and the no-URL-in-render/no-URL-in-flash discipline are all
implemented exactly as specced and match every claim in the plan summaries — I traced each one
against the actual source and could not fault them. The suite is genuinely green (92% coverage,
`ruff check .` clean) and I reproduced two of its own mutation-testing claims independently.

Two BLOCKERs were found by writing small scripts against the real module rather than trusting the
tests, both in territory the test suite's own harness cannot reach because it exercises one process:

1. **The save-triggered erase races the real, cross-process poll cycle** (`skypane-poll.service`,
   a separate systemd unit from `skypane-companion.service`) with no lock that can ever see both
   sides. D-09's reasoning explicitly assumes `_POLL_LOCK` closes this window; it cannot, because
   `_POLL_LOCK` is an in-process `threading.Lock` and the poll cycle that actually runs every 30
   seconds in production is a different OS process that never touches it. I reproduced the data
   loss (a "disconnected" calendar's flights reappearing on disk) with a two-thread script standing
   in for the two processes.
2. **`save_calendar_url()`'s clear branch reports success even when the secret file was not actually
   removed.** `except OSError: pass` swallows every removal failure, not just "the file was already
   gone" — I reproduced this on this machine (`chflags uchg`, the direct analogue of a permission
   fault a Linux `chattr +i` or a remount would produce) and confirmed the operator is told
   "Calendar disconnected" while `calendar_is_configured()` still returns `True` and the URL is
   still readable on disk.

One WARNING (a narrower variant of the same root cause on the erase-then-write ordering) and one
INFO round out the findings. I looked hard for problems in the secret-file-mode path (item 1 of the
brief) and the disconnect-resolver's input space (item 3) and did not find any — both are correct
and the tests that pin them are non-vacuous by mutation, which I spot-checked by reverting one of
the plan's own claimed mutations and watching it fail as documented.

## Critical Issues

### CR-01: The calendar registry's erase-on-disconnect/replace has no protection against the real, cross-process poll cycle — a settings save can be silently undone

**File:** `server/plane/calendar_rules.py:918-1008` (`save_calendar_url()`), consumed by
`companion/pages/config_page.py:2028-2037` (`handle_post()`), consumed by
`companion/app.py:2074-2103` (`_handle_settings_post()`)

**Issue:** D-09's stated fix for "two writers doing a read-modify-write on the registry" is
"the immediate sync reuses `_POLL_LOCK`... A save arriving during a running poll cycle gets the same
honest 'already running' answer `/poll-now` already gives instead of racing." That is true only for
races against *another companion HTTP request* (another `/poll-now`, or another concurrent
`/settings` POST) — `_POLL_LOCK` is a plain `threading.Lock()` living inside the `companion/app.py`
process's own memory.

It provides **zero** protection against the actual, continuously-running poll cycle, which is a
**separate OS process**: `deploy/skypane-poll.service` (`Type=oneshot`, `ExecStart=.../server/
poll_loop.py --once`) is fired every 30 seconds by `deploy/skypane-poll.timer`, and is explicitly
documented as "a distinct service" from the companion (`deploy/skypane-companion.service`'s own
comment: "Separate process (D-03): this is a distinct service from... skypane-poll.service"). That
poll process calls `calendar_rules.refresh_calendar_registry()` directly, with its own Python
interpreter, its own copy of `calendar_rules._WRITE_LOCK`, and no knowledge that `_POLL_LOCK` in
`companion/app.py`'s memory even exists.

Worse: `config_page.handle_post()` calls `calendar_rules.save_calendar_url()` — which does the
D-04/D-05 registry erase — **before `_handle_settings_post()` ever acquires `_POLL_LOCK`** (see
`companion/app.py:2075-2090`: `flash_key = config_page.handle_post(form, ctx)` runs first; the lock
is only acquired afterward, and only around the throttle-bypassed sync). So even a fix that made
`_POLL_LOCK` genuinely cross-process would still leave the erase itself unguarded.

**Demonstrated failure scenario** (ran directly against `server/plane/calendar_rules.py`, standing
one thread in for the companion process and one in for the separate poll process — the real
processes race the same way, just with an OS scheduler instead of the GIL):

1. Calendar A is connected. A poll cycle (thread P, standing in for `skypane-poll.service`) starts
   `refresh_calendar_registry()`: it reads the current registry and Calendar A's URL, passes the
   throttle, and is now blocked inside `fetch_ics()`'s network read (a real HTTPS fetch can easily
   take up to `CALENDAR_FETCH_TIMEOUT_S` = 10s; I used a slow fake transport to model this
   deterministically).
2. While P is still fetching, the operator disconnects the calendar via Settings. `save_calendar_url
   (state_dir, CLEAR_CALENDAR_URL)` runs to completion immediately: it erases the registry
   (`write_calendar_registry(state_dir, [], None, None, ...)`) and removes the secret file. The
   Settings page redirects with `"Calendar disconnected — the flights it supplied have been deleted
   from the server."` — true at this instant.
3. P finishes its fetch (using the URL it had already read in step 1, before the disconnect) and
   calls its own `write_calendar_registry(state_dir, windowed, now, last_synced_at, now=now)`,
   **overwriting the just-erased empty registry with Calendar A's freshly-fetched entries.**

Reproduction output (fabricated event `AB123 ORY-JFK`, `now` fixed inside its window):
```
disconnect_ok (mid-poll): True
poll result code: fetch_ok
RAW file on disk: {'entries': [{'airline_iata': 'AB', 'origin_iata': 'ORY',
  'destination_iata': 'JFK', 'start_at': 1788242400.0, 'end_at': 1788246000.0}], ...}
still configured after disconnect: False
```
The operator was told the calendar is disconnected and its flights are gone. `calendar_is_configured()`
does say `False` (the secret file really was removed), but the *flights* — a named person's
schedule, which D-04 exists specifically to guarantee is gone — are back on disk within the same
30-second window, and will keep colouring the frame's panel via `match_calendar_theme()` until the
next successful poll cycle happens to run with nothing pending. The identical race applies to D-05
(replacing calendar A with calendar B): P's stale write can land after B's connection, resurrecting
A's flights under a session that now shows "Connected" to a different calendar.

The reviewed test suite cannot catch this: `companion/test_companion_app.py`'s
`_calendar_sync_lock_contention_is_honest` (companion/test_companion_app.py:5098) only holds
`_POLL_LOCK` itself (simulating another *companion* request), which correctly proves the
in-process, single-server race is closed — but it never runs a second, independent
`refresh_calendar_registry()` call the way the real `skypane-poll.service` process does, so the
actual production race is untested and unguarded.

**Fix:** The registry's read-modify-write needs a lock that is visible to every process that can
write it — at minimum a file lock (`fcntl.flock()` on a dedicated lock file in `state_dir`, or
equivalent) acquired around the *entire* sequence in `refresh_calendar_registry()` (load → throttle
check → fetch → write) and around `save_calendar_url()`'s erase-then-write. A `threading.Lock`
cannot do this across `skypane-poll.service` and `skypane-companion.service`; something that lives
in the filesystem or another OS-level primitive shared by both processes is required. At minimum,
until a cross-process lock exists, the phase's own D-09 rationale is not actually true for the
topology this project runs, and 17-CONTEXT.md / the plan summaries should not claim this race is
closed.

### CR-02: `save_calendar_url()`'s disconnect path reports success even when the secret file could not actually be removed — "Disconnected" can be a lie

**File:** `server/plane/calendar_rules.py:971-976`

```python
if clearing:
    try:
        os.remove(path)
    except OSError:
        pass
    return True
```

**Issue:** The docstring says the clear branch "removes the file, tolerating its own absence" —
i.e. the intended tolerance is for `FileNotFoundError` (the file is already gone, which is a
success). The code instead catches the entire `OSError` hierarchy and returns `True` unconditionally,
regardless of *why* `os.remove()` failed. Every other failure path in this module (`write_calendar_
registry()`'s own `except Exception: ... return False`, and this same function's `set`/`replace`
branch a few lines below) returns `False` on a genuine failure; only this one branch converts any
failure into a reported success.

**Demonstrated failure scenario** (reproduced directly against the module; `chflags uchg` on macOS
is the direct analogue of a `chattr +i` file, a restrictive SELinux/AppArmor policy, or a read-only
remount on the Linux VPS this ships to — none of which touch the *directory's* writability, so
`write_calendar_registry()`'s own erase, which happens first, succeeds normally):

```
clear() result while file is immutable: True
secret file still present: True
content still on disk: https://calendar-immutable.example/feed.ics
mode still safe (0600): 0o600
calendar_is_configured() after 'successful' clear: True
calendar_secret_mode_is_unsafe(): False
```

`calendar_secret_mode_is_unsafe()` — D-02's drift guard — does **not** catch this: the file's mode
bits are untouched (still `0600`), so nothing here trips the "off *because* of drift" status either.
`handle_post()` sees `save_calendar_url()` return `True` and returns `FLASH_SAVED`;
`_handle_settings_post()` then unconditionally redirects with `FLASH_KEY_CALENDAR_DISCONNECTED`
("Calendar disconnected — the flights it supplied have been deleted from the server."). The second
half of that sentence is true (the registry erase, a separate write to a different file, did
succeed); the first half is false — the calendar is still configured, and the very next poll cycle
(30s later, in production) will fetch it again and repopulate the panel with the person's schedule
the operator just tried to remove. This is exactly the outcome D-04 exists to prevent: *"'Disconnected'
must mean what the word promises: nothing of a named person's schedule remains on the server."*

**Fix:** Only tolerate the file already being absent; treat every other `OSError` as a real failure:

```python
if clearing:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return True
```

## Warnings

### WR-01: A secret-write failure after a successful erase silently wipes a still-connected calendar's flights without changing its URL

**File:** `server/plane/calendar_rules.py:918-1008` (`save_calendar_url()`)

**Issue:** On the `set`/`replace` branch, the registry erase (`write_calendar_registry(...)`) runs
and succeeds *before* the new secret file is written. If the subsequent `os.open()`/`os.fdopen()`/
`os.replace()` sequence then fails (disk full, `state_dir` briefly unwritable, etc.), `save_calendar_
url()` correctly returns `False` and `handle_post()` correctly maps that to `FLASH_SAVE_FAILED` — no
lie is told. But the **previous** URL's secret file is untouched (the failed write never reached
`os.replace()`), so the calendar is still configured with the *old* URL, while its previously-fetched
registry has already been erased. The operator sees a generic failure message, but the practical
effect is that a previously-working, still-connected calendar has just had its flights wiped for no
reason it can act on (retrying the *same* save is the only recovery, and nothing tells them that's
what's needed). This is a narrower instance of the same erase-before-write ordering CR-01 flags, but
triggered by a local write failure rather than a race, and is called out explicitly as an accepted
trade-off only for the *device-config* write ordering in `handle_post()`'s own docstring — it is not
discussed for this specific secret-write failure mode.

**Fix:** Either accept this as a known, documented trade-off (the same one `handle_post()`'s
docstring already accepts for the device-config write, extended explicitly to this case), or write
the new secret to a *different* temp path and verify the write before calling `write_calendar_
registry()`'s erase, so a failed write never costs an already-working calendar its data.

## Info

### IN-01: `refresh_calendar_registry()`'s failure-path comment about `T-17-FLASH` safety would benefit from naming the cross-process risk it does not cover

**File:** `server/plane/calendar_rules.py:1401-1407`

**Issue:** The section banner above `refresh_calendar_registry()` states "The single function
`poll_loop.py` (plan 16-07) calls once per cycle," which is accurate, but nothing in this module (or
in `companion/app.py`'s D-09 comment block at `companion/app.py:2026-2035`) flags that this same
function is now also called from a second, independent process (the companion, via `/poll-now` and
the Settings-triggered sync) with no shared locking primitive between the two. A future reader
fixing CR-01 will need to touch both call sites; a one-line pointer here would save them from
re-discovering the topology from scratch.

**Fix:** A short comment note near `_WRITE_LOCK`'s definition (`server/plane/calendar_rules.py:190-197`)
stating plainly that, as of Phase 17, this lock does **not** serialize against the companion
process's calls into this module, would prevent the next contributor from assuming it does (the
existing comment there already discusses the "single writer" assumption becoming false — it stops
one sentence short of saying what replaces it).

---

## Fix Outcomes (2026-09-10)

Three atomic commits, applied and verified in this order. Each new regression check was proved to
FAIL against the unfixed code (via a temporary `git stash` of the source change alone, harness
re-run, then restore) before being committed alongside its fix — see each commit's own diff for the
before/after.

### CR-02 — FIXED

**Commit:** `1e1ca83` — `fix(17): CR-02 report failure, not false success, when the secret file
cannot be removed`

**Files:** `server/plane/calendar_rules.py`, `server/test_calendar_rules.py`

`save_calendar_url()`'s clear branch now tolerates only `FileNotFoundError` (the file already
gone); every other `OSError` (permission denied, an immutable/read-only filesystem, ...) returns
`False` instead of being swallowed into a reported success — exactly the review's suggested patch.
Traced the call site as instructed: `config_page.handle_post()` (lines ~2028-2035) already branches
on `save_calendar_url()`'s return value and maps `False` to `FLASH_SAVE_FAILED` before
`_handle_settings_post()` ever reaches the `FLASH_KEY_CALENDAR_DISCONNECTED` redirect, so no
call-site change was needed — the source-function fix alone closes the lie end to end.

**Regression check:** `server/test_calendar_rules.py` —
`_clear_branch_reports_failure_when_removal_actually_fails` (EXPECTED_CHECK_COUNT 101→102).
Monkeypatches `os.remove()` to raise `PermissionError` for the secret path only (the portable
analogue of the review's `chflags uchg` reproduction) and asserts `save_calendar_url(CLEAR_CALENDAR_
URL)` returns `False`, the file is still present, and `calendar_is_configured()` is still `True`.
Confirmed FAILING against the unfixed code (`got True`) before the fix; confirmed PASSING after.

### CR-01 — FIXED

**Commit:** `5f55096` — `fix(17): CR-01 add a cross-process lock so a companion disconnect can't be
undone by a concurrent poll cycle`

**Files:** `server/plane/calendar_rules.py`, `server/test_calendar_rules.py`, `companion/app.py`

Added `calendar_rules._calendar_registry_lock()`, a `contextlib.contextmanager` over
`fcntl.flock()` on a new dedicated file (`calendar_rules.lock`, distinct from both
`calendar_rules.json` and the secret file) in `state_dir`. `fcntl` is imported defensively
(`try/except ImportError`, falling back to no locking with a documented comment) since it is
POSIX-only; this project's two real targets (Linux production, macOS development) both have it.
Acquisition is bounded — polls every 0.05s up to `CALENDAR_REGISTRY_LOCK_TIMEOUT_S` (15.0s, chosen
above `CALENDAR_FETCH_TIMEOUT_S`'s 10.0s) — then raises `TimeoutError`, which both call sites catch
and degrade to their existing failure contract (never blocking a poll cycle or an HTTP request
indefinitely, never proceeding unlocked past the timeout). The lock is acquired around the ENTIRE
load→throttle→fetch→write sequence in `refresh_calendar_registry()` and around the entire
erase/write sequence in `save_calendar_url()` — not merely the final write, which would still admit
the interleaving the review found. `_WRITE_LOCK` (in-process `threading.Lock`) is untouched and
still guards the final tmp-write against same-process callers, as before.

Also corrected the two false rationales the review named: the comment block above `_WRITE_LOCK` in
`calendar_rules.py` now states plainly that it does not serialize against
`skypane-poll.service`'s separate process (this doubles as the IN-01 fix — see below), and D-09's
bullet 5 in `companion/app.py`'s `_handle_settings_post()` docstring — which previously claimed
`_POLL_LOCK` closes the race against "a poll cycle's own calendar refresh" — now states the true
property: `_POLL_LOCK` only ever serializes this call against another concurrent request in the SAME
companion process, and the actual cross-process protection is `calendar_rules._calendar_registry_
lock()`.

**Regression check:** `server/test_calendar_rules.py` —
`_cross_process_lock_closes_the_disconnect_race` (EXPECTED_CHECK_COUNT 102→103). Two threads stand
in for the two real, separate OS processes: thread P runs `refresh_calendar_registry()` against a
transport that blocks mid-fetch on a `threading.Event` (simulating the network read
`skypane-poll.service` would be doing); the main test thread runs `save_calendar_url(CLEAR_
CALENDAR_URL)` concurrently, simulating the companion's disconnect request arriving mid-poll-cycle.
Asserts the final on-disk registry is empty (the erase, the chronologically last-completed
operation, is what the final state reflects) rather than repopulated by P's later write.
**This simulates two OS processes with two threads**, stated explicitly per the task's guidance:
the lock it exercises, `_calendar_registry_lock()`, is implemented with `fcntl.flock()` — a
kernel-level primitive keyed on the lock FILE itself, not on anything in either caller's memory —
so its exclusion behaviour is identical whether the two acquirers are two threads in one process or
two real OS processes; the check deliberately never touches `_WRITE_LOCK` or `_POLL_LOCK` (both
plain `threading.Lock`s, invisible across processes), only the lock that actually closes this race.
Confirmed FAILING against the unfixed code (disconnect's erase overwritten by the poll cycle's
write — 4 fixture entries reappeared) before the fix; confirmed PASSING after.

### WR-01 — FIXED

**Commit:** `60bfce7` — `fix(17): WR-01 verify the new calendar secret's write before erasing the
previous calendar's flights`

**Files:** `server/plane/calendar_rules.py`, `server/test_calendar_rules.py`

Took the review's second offered option (reorder + verify, not merely documenting the trade-off),
per the task's explicit "fix it with the same ordering/atomicity work" instruction. On the
set/replace branch only, `save_calendar_url()` now builds and verifies the new secret in a temp
file FIRST; only once that write succeeds does the previous calendar's registry get erased; only
once THAT succeeds does the final `os.replace()` make the new URL live. A failure at the temp-file
write (disk full, a briefly unwritable `state_dir`) now touches neither the old secret nor the old
registry — the call returns `False` having done nothing observable, matching every other
rejected/failed path in this function. D-05's guarantee (no window with a new calendar's URL
configured beside the previous calendar's flights) still holds, for two reasons: the erase still
runs before the atomic rename that makes the new URL live, and — new as of the CR-01 fix — the
entire function now runs under the cross-process registry lock, so no other reader or writer can
observe any intermediate state during the whole call regardless of internal ordering. The clear
branch's ordering (erase-then-remove) is unchanged, since that ordering was already correct for
D-04.

**Regression check:** `server/test_calendar_rules.py` —
`_write_failure_before_erase_preserves_the_previous_calendars_flights` (EXPECTED_CHECK_COUNT
103→104). Seeds a connected calendar with real fetched entries, then monkeypatches `os.fdopen()` to
raise `OSError(28, "No space left on device")` during the new secret's write, and asserts: the
call returns `False`; the previously-fetched entries are still on disk (`ORY` origin, unchanged);
and `configured_calendar_url()` still reports the OLD URL. Confirmed FAILING against the unfixed
(pre-reorder) code (seeded entries erased despite the write never succeeding) before the fix;
confirmed PASSING after.

### IN-01 — FIXED (folded into the CR-01 commit)

**Commit:** `5f55096` (same commit as CR-01 — the two are the same edit: the corrected comment near
`_WRITE_LOCK` IS the documentation gap IN-01 asked for)

Added the note IN-01 requested near `_WRITE_LOCK`'s definition
(`server/plane/calendar_rules.py`), stating plainly that this lock does not serialize against
`skypane-poll.service`'s separate process, and pointing at `_calendar_registry_lock()` as the lock
that actually does. No test added — this is a documentation-only fix; there is no runtime behaviour
to regress-test, and the CR-01 regression check already proves the underlying cross-process race is
closed.

### Suite state after all three fixes

`server/test_calendar_rules.py`: 101 → **104** (+3: CR-02, CR-01, WR-01).
`server/test_poll_loop.py`: **81** (unchanged — `refresh_calendar_registry()`'s public signature
and behaviour are unchanged from its callers' perspective; the new lock is internal).
`companion/test_config_page.py`: **138** (unchanged — `config_page.handle_post()` already branched
correctly on `save_calendar_url()`'s return value; no call-site change was needed for CR-02).
`companion/test_companion_app.py`: **177** (unchanged — the D-09 docstring correction in `app.py` is
documentation-only; `_POLL_LOCK`'s actual behaviour, which the existing
`_calendar_sync_lock_contention_is_honest` check already pins, is unchanged).

`bash scripts/run-all-tests.sh`: **PASS** (all 19 harnesses, 92% coverage, threshold met).
`server/.venv/bin/ruff check .`: **clean** (verified before every commit above).

---

_Reviewed: 2026-09-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

---

_Fixes applied: 2026-09-10_
_Fixer: Claude (gsd-code-fixer)_

---

## UAT Finding (2026-09-10) — webcal:// calendar feed URLs refused

### UAT-01 — FIXED

**Reported by:** UAT, against a real developer subscription URL (never printed or logged): the
orchestrator confirmed `_url_is_safe(<the configured webcal:// URL>)` returned `False` while the
same URL with `https://` substituted for `webcal://` returned `True`.

**Commit:** `a51c15d` —
`fix(17): normalise webcal:// calendar URLs to https:// before the safety gate`

**Files:** `server/plane/calendar_rules.py`, `server/test_calendar_rules.py`

**The defect:** `_url_is_safe()` refuses any scheme other than exactly `https`. Apple Calendar's own
"Public Calendar" share links — the exact source this feature was built for — use `webcal://`, not
`https://`. Every operator pasting the URL Apple Calendar itself hands them therefore failed at the
gate and saw only the generic "couldn't sync that calendar right now — check the URL" message, which
sends them hunting for a problem in a URL that was correct all along.

**The fix:** `webcal://` is not a distinct transport; it is the de-facto convention meaning
"subscribe to this iCal feed over HTTPS" — the fetch itself is an ordinary HTTPS request. Added
`_normalise_calendar_url()`, a scheme REWRITE (`webcal` → `https`, case-insensitive; every other
scheme, and anything `urlparse()` cannot parse, including `None`, passes through completely
unchanged) that runs strictly BEFORE `_url_is_safe()`. `_url_is_safe()`'s own comparison
(`parsed.scheme != "https"`) is untouched — the gate stays the single, unweakened arbiter of what is
safe to fetch; normalisation happens upstream of it, never inside it. `_normalise_calendar_url()`
never maps `webcal` to plain `http` — there is no legitimate `webcal` → `http` mapping, and doing so
would silently downgrade a request that frequently carries an access token in its query string.

Two call sites apply it, both deliberate:
- `fetch_ics()` normalises its `url` argument once, before the redirect loop starts — the single
  choke point both the companion's save-time sync and `poll_loop.py`'s regular cycle already share
  via `refresh_calendar_registry()`, so this one call covers both without either caller needing its
  own copy of the rewrite. Redirect targets discovered inside the loop are deliberately NOT
  separately normalised — a `Location` header names a live HTTP response's own next hop, never a
  calendar-client convention, so there is no legitimate `webcal://` shape to expect there.
- `save_calendar_url()` normalises before writing the SET/replace branch's secret, so the file
  stores the `https://` form, not whatever scheme the operator pasted. Chosen deliberately over
  storing verbatim: `config_page.calendar_group()`'s own docstring already documents this field as
  write-only — the stored value is never rendered back to the operator in any of its four status
  states — so there is no UI cost to the two differing, and every future reader of
  `configured_calendar_url()` gets one canonical scheme rather than needing its own webcal-awareness.
  `fetch_ics()`'s own normalisation still runs regardless, as a second, independent line of defence
  for a `calendar_rules.json`-adjacent secret file a human hand-edited directly on the VPS (state_dir
  is operator-inspectable) without ever going through `save_calendar_url()`.

**Explicitly decided against:** adding an early, save-time scheme/shape check ahead of
`_url_is_safe()` (raised as a live option in 17-CONTEXT.md's Claude's Discretion section). Not
added, because `config_page.calendar_group()`'s docstring already records a locked decision from
plan 17-03 that "the single arbiter of acceptability stays `calendar_rules._url_is_safe()` and the
fetch itself" — introducing a second definition now would be exactly the drift that decision, and
this task's own guidance, warn against. The actual UAT defect was a missing scheme normalisation,
not a missing early validator, so the fix stays scoped to that.

**Regression checks:** `server/test_calendar_rules.py`, six checks added under the `17-REVIEW.md UAT
fix (webcal:// scheme)` banner (EXPECTED_CHECK_COUNT 104→110):
- `_normalise_calendar_url() rewrites a webcal scheme (any case) to https, leaves every other scheme
  and an unparseable value unchanged, and never raises on None (UAT)`
- `fetch_ics() accepts a webcal:// URL - Apple Calendar's own share-link scheme - and the transport
  observes an https:// request (UAT)`
- `the webcal:// rewrite does not weaken the address gate - fetch_ics() still refuses a webcal://
  URL pointing at a private address, at loopback (literal IP and "localhost"), and at the cloud
  metadata address (UAT)`
- `fetch_ics() still refuses a plain http:// URL - there is no webcal -> http downgrade path (UAT)`
- `a redirect discovered while fetching a webcal:// URL (normalised to https:// first) is still
  re-validated per hop, refusing a Location that targets a loopback address (UAT)`
- `save_calendar_url() stores a webcal:// value already rewritten to its https:// form, so the
  secret file never holds a webcal:// string (UAT)`

**Non-vacuity proof:** reverted `server/plane/calendar_rules.py` only (via `git stash`), re-ran the
harness. Four of the six new checks failed against the unfixed code exactly as expected — the
`_normalise_calendar_url` rewrite check (`AttributeError`, the function didn't exist yet), the
`fetch_ics()` webcal-acceptance check (`None` instead of the fetched body), the redirect
re-validation check (zero transport calls — `fetch_ics()` refused the un-normalised `webcal://` URL
before ever reaching the loop), and the stored-form check (`b'webcal://...'` on disk instead of the
normalised `https://` form) — 106/110. The other two new checks (the address-gate-non-weakening and
http-still-refused checks) passed even before the fix, as expected: they guard against a *future*
regression in this same area rather than pinning the specific defect fixed here. Restored the fix
(`git stash pop`) and confirmed 110/110 again.

**Suite state after this fix:**
`server/test_calendar_rules.py`: 104 → **110** (+6, all UAT).
`server/test_poll_loop.py`: **81** (unchanged — `fetch_ics()`'s and `refresh_calendar_registry()`'s
public signatures and call-site behaviour are unchanged from `poll_loop.py`'s perspective).
`companion/test_config_page.py`: **138** (unchanged — no `config_page.py` change was needed; the
fix lives entirely in `calendar_rules.py`).
`companion/test_companion_app.py`: **177** (unchanged — no `companion/app.py` change was needed).

`bash scripts/run-all-tests.sh`: **PASS** (all 19 harnesses, 92% coverage, threshold met).
`server/.venv/bin/ruff check .`: **clean**.

---

_UAT fix applied: 2026-09-10_
_Fixer: Claude (gsd-code-fixer)_

---

## UAT Finding (2026-09-10) — cap-before-window discards every future flight on a real feed [BLOCKER]

### UAT-02 — FIXED

**Reported by:** UAT, against the developer's own real Apple Calendar subscription feed (1958
VEVENTs, 1074 with `CATEGORIES:FLT`, spanning 2025-04 to 2026-09): with the 200-entry cap applied
before D-03's retention window, the surviving 200 entries were feed positions `0..199` — the oldest
200 — while every future flight sat at positions `1066..1073`. The window then had nothing future
left to keep: `0 of 8` future events survived. The feature was structurally incapable of ever
colouring a flight for this user, not "sometimes misses" — never.

**Commit:** `94154cc` —
`fix(17): UAT-02 apply the retention window before the entry cap`

**Files:** `server/plane/calendar_rules.py`, `server/test_calendar_rules.py`

**The defect, and a scope note:** the finding as reported named `_rebuild_capped_entries()` — its
loop stopped the instant `CALENDAR_MAX_ENTRIES` survivors had accumulated, in raw `raw_entries` list
order, and only afterward called `select_window_entries()`. Investigating the actual live-fetch call
graph (`refresh_calendar_registry()` → `parse_ics_events()` → `select_window_entries()` →
`write_calendar_registry()`) found the IDENTICAL cap-before-window pattern already live in
`parse_ics_events()` itself, at its own `CALENDAR_MAX_ENTRIES`-keyed accumulation stop — and proved
by direct reproduction (a synthetic feed: 250 historical VEVENTs followed by 5 in-window ones, run
through the real `parse_ics_events()` + `select_window_entries()`, no other code involved) that THIS
is the site the real fetch path actually hits: `write_calendar_registry()` always receives an
already-windowed, already-≤200 list from `select_window_entries()`, so `_rebuild_capped_entries()`'s
own instance of the bug is reachable only via a hand-edited `calendar_rules.json` (T-16-INPUT),
never via a live fetch. Fixing only the function named in the report would have left the reported
UAT blocker unresolved on re-test. Both sites were fixed.

**The fix:** in both `parse_ics_events()` and `_rebuild_capped_entries()`, raw-candidate examination
is now bounded by a new, generous, DoS-only ceiling — `CALENDAR_MAX_RAW_EXAMINED` (5000; the real
feed's 1074 candidates sit comfortably inside it) — instead of by the much smaller
`CALENDAR_MAX_ENTRIES`. Every candidate within that ceiling is normalised, THEN windowed via a new
shared helper, `_window_filtered_entries()` (the exact edge-computation `select_window_entries()`
already used, factored out so nothing recomputes the day-start edge, the forward edge, or
`CALENDAR_WINDOW_FORWARD_S`), and only the windowed survivors are capped at `CALENDAR_MAX_ENTRIES`.
`select_window_entries()`'s own signature, contract and sort guarantee are unchanged — it now calls
`_window_filtered_entries()` internally and slices the result, byte-identical to its prior output for
every existing caller. The cap is still fully enforced: a file or feed with more than
`CALENDAR_MAX_ENTRIES` entries genuinely inside the window is still truncated to the cap — it now
just bounds the windowed survivors rather than raw feed/file position.

The drop-count warning in `_rebuild_capped_entries()` stays truthful after the reorder: it now fires
for malformed/unsafe entries, raw entries beyond the `CALENDAR_MAX_RAW_EXAMINED` examination ceiling,
or well-formed in-window entries still cut by the `CALENDAR_MAX_ENTRIES` cap — never for entries
merely outside the window, which is this feature's ordinary, designed steady state (a calendar
containing history) and must never print a scary warning on every companion page render.

**UF-16-05 also closed:** `_resolve_retention_now()` previously accepted any `math.isfinite()` value
as a safe `now`, but a finite-but-absurd value (`1e300`) still overflows
`datetime.fromtimestamp()` one layer down inside the window logic, which degrades to `[]` there —
silently ERASING a populated registry rather than merely failing to trim it, exactly the failure
mode the function exists to prevent for `None`/`NaN`/`+-Infinity`. `_resolve_retention_now()` now
proves convertibility directly (the same `datetime.fromtimestamp(now, tz=timezone.utc)` call) rather
than trusting `isfinite()` as a proxy for it, so `1e300` now resolves to real current time exactly
like the other hostile shapes already did.

**Regression checks:** `server/test_calendar_rules.py`, three checks added under the `17-REVIEW.md
UAT-02 fix` banner (EXPECTED_CHECK_COUNT 110→113), plus one pre-existing check renamed and
re-targeted at the new ceiling rather than removed:
- *(renamed, not new)* `parse_ics_events() on a body with more VEVENT blocks than
  CALENDAR_MAX_RAW_EXAMINED returns exactly CALENDAR_MAX_RAW_EXAMINED entries` — was keyed to
  `CALENDAR_MAX_ENTRIES`; re-targeted at the new, larger ceiling now that `CALENDAR_MAX_ENTRIES`
  itself is enforced downstream, after the window.
- `UAT-02: a feed listing more than CALENDAR_MAX_ENTRIES historical VEVENTs before a small number of
  in-window ones still surfaces every in-window entry through parse_ics_events() +
  select_window_entries() - the exact real-world failure reproduced` — the decisive check: 258
  synthetic VEVENTs (250 historical, 8 in-window, in that order), asserting all 8 survive.
- `UAT-02: load_calendar_registry() on a raw entries list holding more than CALENDAR_MAX_ENTRIES
  out-of-window entries before a small number of in-window ones still surfaces every in-window entry
  - the exact real-world failure reproduced at the registry layer` — the same decisive shape, at the
  `_rebuild_capped_entries()` layer via a hand-written `calendar_rules.json`.
- `UF-16-05 closure: _resolve_retention_now() resolves None, a bool, a non-numeric value,
  NaN/+-Infinity, and a finite-but-absurd value (1e300) all to a real convertible clock, so none of
  them can erase a populated registry through load_calendar_registry()`.

The pre-existing cap-still-enforced check (`load_calendar_registry() on a file holding more than
CALENDAR_MAX_ENTRIES well-formed entries returns exactly CALENDAR_MAX_ENTRIES of them and prints a
drop-count warning on stderr`) and the pre-existing loader/`select_window_entries()`
behavioural-equivalence anti-drift guard both continued to pass unmodified, pinning that the cap
enforcement and sort contract survived the reorder.

**Non-vacuity proof:** reverted `server/plane/calendar_rules.py` only (via `git stash`), re-ran the
harness. Four checks failed against the unfixed code exactly as expected — the renamed
`CALENDAR_MAX_RAW_EXAMINED` check (`AttributeError`, the constant didn't exist yet), both decisive
"history before window" checks (`got 0 survivors` in each case — the exact real-world failure,
reproduced), and the UF-16-05 closure check (`_resolve_retention_now(1e+300) let an absurd now erase
a populated registry — got 0`) — 109/113. Restored the fix (`git stash pop`) and confirmed 113/113
again.

**Suite state after this fix:**
`server/test_calendar_rules.py`: 110 → **113** (+3, all UAT-02).
`server/test_poll_loop.py`: **81** (unchanged — `parse_ics_events()`, `select_window_entries()`,
`load_calendar_registry()` and `write_calendar_registry()`'s public signatures and call-site
behaviour are unchanged from `poll_loop.py`'s perspective).
`companion/test_config_page.py`: **138** (unchanged — no `config_page.py` change was needed).
`companion/test_companion_app.py`: **177** (unchanged — no `companion/app.py` change was needed).

`bash scripts/run-all-tests.sh`: **PASS** (all 19 harnesses, 92% coverage, threshold met).
`server/.venv/bin/ruff check .`: **clean**.

---

_UAT fix applied: 2026-09-10_
_Fixer: Claude (gsd-code-fixer)_
