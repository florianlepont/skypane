---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
reviewed: 2026-09-11T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - companion/app.py
  - companion/auth.py
  - companion/battery.py
  - companion/layout.py
  - companion/pages/__init__.py
  - companion/pages/airlines_page.py
  - companion/pages/config_page.py
  - companion/pages/health_page.py
  - companion/pages/history_page.py
  - companion/pages/home_page.py
  - companion/static/confirm-submit.js
  - companion/static/copy-button.js
  - companion/static/dirty-state.js
  - companion/static/freshness.js
  - companion/static/poll-cooldown.js
  - companion/static/style.css
  - companion/wake.py
  - deploy/skypane.env.example
  - server/device_config.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-09-11
**Depth:** standard
**Files Reviewed:** 18 (diffed against `40656bd..HEAD`)
**Status:** issues_found

## Summary

This phase's diff adds the Content-Security-Policy header, session-token
revocation, the `Secure`-cookie opt-out, the calendar-disconnect
confirmation route, field-level validation errors on Settings, several
"next wake" / plain-language copy additions, and two new ES5 static
scripts (`confirm-submit.js`, `poll-cooldown.js`) that externalize the
last inline `<script>` elements.

I traced every new/changed POST route (`/settings/calendar/disconnect`,
the quick-action toggles, `/ui-theme`, `/logout`) and confirmed each is
gated by `require_session()` before its handler runs, and that the
calendar-disconnect two-step confirmation holds server-side (the
`confirm` field is compared with `!=`, not trusted from the client-side
`confirm()` dialog). I traced the CSP directives against the markup this
diff and the surrounding modules emit and found no inline `<script>`,
no inline event-handler attribute, and no `javascript:` URL that would
either violate the policy or need an `'unsafe-inline'`/nonce exception
beyond the one already declared and justified for `style-src` (a fixed,
non-user-controlled palette of `style="background:..."` swatches). I
audited every new server-rendered fragment that echoes a value back to
the browser (field-error paragraphs, the "next wake ≈ HH:MM" lines, the
gap strip, the radiogroup `aria-labelledby`/`aria-describedby`
plumbing, the calendar-disconnect confirmation page, the write-only
`calendar_url` field's non-repopulation) and found consistent use of
`escape_html()` at every interpolation site — no XSS regressions in
this diff's new markup. The two new static scripts stay within the
existing ES5-safe subset and touch no HTML-writing sink; `freshness.js`'s
larger fetch/DOMParser/swap rewrite (not itself in the requested file
list, but exercised by `health_page.py`'s new `REFRESH_SWAP_SELECTORS`
it must stay in sync with) uses `DOMParser` for the fetched document,
which never executes embedded `<script>` content, preserving the
project's standing markup-writing-sink ban.

I found no BLOCKER-level defects. Three WARNING-level gaps and two INFO
items are below — the most notable is that a crafted `screen_id` field
on `POST /settings` is validated and rejected (`FLASH_SAVE_FAILED`), but
the corresponding field-level error message is silently dropped from
the re-rendered page, leaving the operator with no visible feedback
that anything was rejected.

## Warnings

### WR-01: `screen_id` validation error is captured but never rendered

**File:** `companion/pages/config_page.py:2404-2444` (`_screen_selector_html()`), cross-referenced with `companion/pages/config_page.py:2818-2827` (`handle_post()`)
**Issue:** `handle_post()`'s new D-23 gate calls
`_note_error(errors, "screen_id", ERROR_INVALID_CHOICE)` and returns
`FLASH_SAVE_FAILED` when a submitted `screen_id` is not a member of
`screens.SCREEN_IDS`. `_handle_settings_post()` (`companion/app.py`)
sees `errors` is non-empty, so it takes the D-07 "re-render at 200 with
no flash banner, the message lives at the field" branch. However,
`_screen_selector_html()` — the only render call site for this field —
takes no `errors`/`submitted` parameter at all and never calls
`_field_error_html()`. The result: on a rejected save whose *only*
error is an invalid `screen_id`, the page re-renders at 200 with **no
flash banner and no field-level message anywhere** — a silent failure
that contradicts this same plan's own D-07 contract ("the message lives
at the field"). Every sibling field this plan touches
(`theme`, `tracked_runway`, `led_enabled`, `quiet_hours_*`,
`wake_interval_s`, `display_enabled`, `calendar_theme_id`,
`calendar_url`) has a matching `_field_error_html()` call; `screen_id`
is the one field that does not.
Currently unreachable through the live UI (`screens.SCREEN_IDS` is a
one-member tuple today, so `_screen_selector_html()` itself renders
`""` and the `<select>` never appears), so this is latent rather than
exploitable today — but it will silently regress the very next time a
second screen type is registered, and it is already reachable today by
a hand-crafted `POST /settings` body with a `screen_id` field.
**Fix:** Thread `errors` (and, for consistency with the other
membership-tested selects, no `submitted` repopulation is needed since
`current_screen_id` is already resolved elsewhere) into
`_screen_selector_html()` and append a
`_field_error_html(errors, "screen_id", SCREEN_SELECTOR_ID)` call after
the `<select>`, mirroring `calendar_group()`'s `calendar_theme_id`
handling:
```python
def _screen_selector_html(current_screen_id, errors=None):
    if len(screens.SCREEN_IDS) <= 1:
        return ""
    ...
    error_html = _field_error_html(errors, "screen_id", SCREEN_SELECTOR_ID)
    return (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<select name="screen_id" id="%s" form="%s">%s</select>'
        "%s"
    ) % (..., error_html)
```
and pass `errors=errors` from both `_screen_selector_html(screen_id)`
call sites in `render()`.

**Status:** fixed in 4ec97a3

### WR-02: Module docstring's D-02 exemption list is now stale for `/ui-theme`

**File:** `companion/app.py:8-16` (module docstring), cross-referenced with `companion/app.py:2517-2520` (`do_POST()`)
**Issue:** The file's own header states: "every route except the login
routes, the stylesheet, and the theme-toggle POST calls
`Handler.require_session()` ... This same exemption list also decides
the caching scope on byte-served responses ... the two lists are not
allowed to silently drift apart." This plan's own T-19-04 change (19-04-PLAN.md, D-18/A-35) added a `require_session()` gate to
`POST /ui-theme` specifically *because* it is a real state change for
an authenticated visitor — a correct and more secure change — but the
module docstring (and a second, matching comment at
`companion/app.py:1384-1387`, `_serve_stylesheet()`) was not updated to
drop "the theme-toggle POST" from the stated exemption list. The two
are now out of sync, in the direction this file's own docstring says
must never happen. This is not itself an access-control bug (the code
is more restrictive than the docs describe), but it is exactly the
"silent drift" the invariant exists to prevent, and a future
maintainer reading only the docstring could incorrectly conclude
`/ui-theme` is safe to leave unauthenticated or safe to serve from a
shared cache.
**Fix:** Update the docstring at `companion/app.py:8-16` to read "every
route except the login routes and the stylesheet calls
`Handler.require_session()`" (dropping the theme-toggle POST clause),
and adjust the exemption-list comment at line 1384-1387 to match.

**Status:** fixed in 12e4ff0

### WR-03: `LoginThrottle` failure/lockout counters are mutated without synchronization under `ThreadingHTTPServer`

**File:** `companion/auth.py:308-335` (`LoginThrottle`), cross-referenced with `companion/app.py:523` (`LOGIN_THROTTLE = auth.LoginThrottle()`) and `companion/app.py:2227-2238`
**Issue:** `LOGIN_THROTTLE` is a single process-global instance shared
across every request thread (`ThreadingHTTPServer` spawns one thread
per connection). This plan's own A-32/D-15 fix rewrote
`record_failure()`'s logic to reset `self._failures` once the previous
lockout has elapsed:
```python
def record_failure(self):
    if self._failures >= self._limit and time.time() >= self._locked_until:
        self._failures = 0
    self._failures += 1
    if self._failures >= self._limit:
        self._locked_until = time.time() + self._lockout_s
```
None of `record_failure()`/`record_success()`/`locked_out()`/
`seconds_remaining()` acquire any lock, and `self._failures`/
`self._locked_until` are read-then-written non-atomically. Two
concurrent failed-login requests arriving in the same instant can both
read the same `self._failures` value, both increment from it, and land
on `self._failures == old + 1` instead of `old + 2` — under-counting
failures and potentially delaying (or in a tighter race, skipping) the
lockout the five-strikes contract promises. This is a pre-existing gap
(the class was never locked), but this phase specifically touched and
relied on the correctness of this counter's reset semantics (A-32/D-15)
without adding the synchronization the new, more stateful logic now
needs more than the old logic did.
**Fix:** Guard `LoginThrottle`'s state with a `threading.Lock()`,
mirroring `_REVOKED_LOCK`'s own precedent added by this same plan two
functions away in the same file:
```python
def __init__(self, ...):
    ...
    self._lock = threading.Lock()

def record_failure(self):
    with self._lock:
        ...
```

**Status:** fixed in f1e1a89

## Info

### IN-01: `_battery_readout_block()`'s percentage estimate now duplicates two constant sets with an implicit equality requirement

**File:** `companion/battery.py:24-25`, cross-referenced with `companion/pages/health_page.py:3540-3549` (`SPARKLINE_Y_MIN_MV`/`SPARKLINE_Y_MAX_MV`)
**Issue:** `companion/battery.py` defines `BATTERY_FULL_MV = 4200` /
`BATTERY_EMPTY_MV = 3300` for the percentage estimate, while
`health_page.py`'s new fixed-range sparkline axis (D-04/A-22) defines a
*different* pair, `SPARKLINE_Y_MIN_MV = 3000` / `SPARKLINE_Y_MAX_MV =
4200`, for the chart's Y-axis. The two ranges are related (both model
the same single-cell LiPo) but are not identical (3300 vs 3000 at the
low end), and nothing pins them to agree or documents why the sparkline
axis is deliberately wider than the percentage-estimate range. This is
not a bug — the sparkline axis is allowed to show some margin below 0%
— but a future reader changing one constant set has no signal that the
other exists and might need reconsidering.
**Fix:** Add a short cross-reference comment in each module pointing at
the other's constants, or fold both into one canonical source (e.g.
`battery.py` exporting the sparkline's own margin explicitly) so the
relationship is discoverable by grep.

**Status:** skipped — out of the fix scope for this pass (a
documentation nit about two constant pairs, not a one-line comment
fix; scope was limited to WR-01, WR-02, WR-03, and IN-02).

### IN-02: `wake_interval_group()`'s rejected-save echo double-converts an already-string value

**File:** `companion/pages/config_page.py:1416-1418`
**Issue:**
```python
if submitted is not None and "wake_interval_s" in submitted:
    raw_submitted = submitted["wake_interval_s"]
    value_attr = ' value="%s"' % escape_html(str(raw_submitted)) if raw_submitted else ""
```
`submitted` is always `self.read_form()`'s dict, whose values are
already `str` (URL-decoded form values), so `str(raw_submitted)` is a
no-op wrapping an already-`str` value. Harmless, but it reads as if
`raw_submitted` might be a non-string, which it never is in this
codebase's `read_form()` contract, and could mislead a future reader
into thinking this function accepts richer input shapes than it does.
**Fix:** Drop the redundant `str()` call: `escape_html(raw_submitted)`.

**Status:** fixed in a924324

---

_Reviewed: 2026-09-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
