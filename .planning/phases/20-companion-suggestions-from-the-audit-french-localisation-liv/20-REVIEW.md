---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
reviewed: 2026-09-12T04:03:12Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - companion/app.py
  - companion/auth.py
  - companion/prefs.py
  - companion/i18n.py
  - companion/i18n_fr/__init__.py
  - companion/i18n_fr/airlines.py
  - companion/i18n_fr/calendar_group.py
  - companion/i18n_fr/common.py
  - companion/i18n_fr/display.py
  - companion/i18n_fr/flights.py
  - companion/i18n_fr/health.py
  - companion/i18n_fr/home.py
  - companion/i18n_fr/nav.py
  - companion/i18n_fr/notifications.py
  - companion/i18n_fr/registry.py
  - companion/i18n_fr/rules.py
  - companion/layout.py
  - companion/screens.py
  - companion/theme_preview.py
  - companion/wake.py
  - companion/pages/home_page.py
  - companion/pages/config_page.py
  - companion/pages/health_page.py
  - companion/pages/airlines_page.py
  - companion/pages/history_page.py
  - companion/static/theme-preview.js
  - companion/static/copy-button.js
  - companion/static/dirty-state.js
  - companion/static/list-filter.js
  - companion/static/style.css
  - server/wake.py
  - server/notify.py
  - server/device_config.py
  - server/poll_loop.py
findings:
  critical: 1
  warning: 4
  info: 0
  total: 5
status: issues_found
---

# Phase 20: Code Review Report

**Reviewed:** 2026-09-12T04:03:12Z
**Depth:** standard
**Files Reviewed:** 24 (plus 10 static/JS files) against `git diff f5aef3d..HEAD`
**Status:** issues_found

## Summary

Reviewed the lines changed since `f5aef3d` across the companion service's new i18n/simple-mode layer, the new POST routes (`/ui-lang`, `/ui-mode`, `/settings/calendar/connect`, `/settings/notifications/test`, the relocated rule add/delete routes), `server/notify.py`, and the `server/poll_loop.py` notification-transition dedupe.

The session-gating, CSRF posture (SameSite=Strict + exact-membership `next`/Referer allowlists), the French i18n plumbing (per-request `contextvars`, catalogue completeness, `escape_html()`-after-`t()` discipline), and the settings-form `form="settings-form"` cross-DOM restructuring were all checked in detail and are sound — every new instant-action `<form>` (calendar connect/disconnect, rule add/delete, notifications test) is a documented sibling of `#settings-form`, never nested, and every scheduled field moved outside the form (Runway, Display, Quiet hours) carries an explicit `form="settings-form"` attribute. The `?live=1` theme-preview cache path is fully guarded (membership-tested `theme_id`, `int()`-coerced `live_event_id`, atomic write). The ES5 static scripts stay within the declared CSP (`script-src 'self'`, no inline handlers, no HTML-writing sinks).

One genuine security gap was found: `server/notify.py`'s transport does not disable HTTP redirect following, unlike `server/plane/calendar_rules.fetch_ics()` (which the module's own docstring claims parity with) — this reopens the SSRF gate the module claims to close. Four additional non-blocking issues (a monitoring gap, a benign but racy double-read, a latent unescaped-attribute helper, and a naming quality issue) are listed below.

## Critical Issues

### CR-01: `server/notify.py` SSRF gate is bypassed by automatic redirect following

**File:** `server/notify.py:96-113` (`default_notify_transport()`)
**Issue:** `send_notification()` validates `topic_url` once, up front, via `calendar_rules._url_is_safe(topic_url)` (scheme==https, hostname resolves to only public addresses). The module's own docstring explicitly claims this gives the topic URL "the exact scheme/hostname/private-IP gate `fetch_ics()` already applies ... re-applied per redirect hop" — but that claim is false for this module. `default_notify_transport()` calls `urllib.request.urlopen(request, timeout=timeout)` with no custom opener and no `follow_redirects=False`-equivalent. `urlopen()`'s default `OpenerDirector` includes `HTTPRedirectHandler`, which **automatically follows** 301/302/303/307 responses (including a `https`→`http` downgrade) with no re-invocation of `_url_is_safe()` on the redirect target.

Contrast with `server/plane/calendar_rules.fetch_ics()`, which the docstring says this reuses: that function explicitly disables automatic redirects (`allow_redirects=False` on the `requests` transport) and manually loops, re-validating every `Location` header against `_url_is_safe()` before following it.

Because a validated public HTTPS endpoint an attacker controls (or a compromised/malicious ntfy-compatible server the operator points this at) can freely respond with a 3xx to any internal address (e.g. `http://169.254.169.254/...`, `http://127.0.0.1:<port>/...`, an internal admin endpoint on the Hetzner VPS's private network), `urlopen()` will silently connect there — with the POST body (a notification title/body, not attacker-controlled but still an SSRF primitive: the response of the internal request is discarded but the request itself is fully attacker-directed to any URL of their choosing) — completely defeating the SSRF gate for this one call path. The initial scheme/host check only proves the *first* URL is safe; the actually-connected URL after redirect(s) is never checked.

**Fix:** Build a `urllib.request.OpenerDirector` with redirects disabled (a custom `HTTPRedirectHandler` subclass whose `redirect_request()` returns `None`, mirroring the stdlib idiom), or manually loop and re-validate each hop through `calendar_rules._url_is_safe()` exactly like `fetch_ics()` does, e.g.:

```python
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never follow — caller decides

_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)

def default_notify_transport(url, title, body, timeout):
    data = body.encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={...})
    return _NO_REDIRECT_OPENER.open(request, timeout=timeout)
```
A 3xx response then raises `urllib.error.HTTPError`, which `send_notification()`'s existing broad `except Exception` already turns into a logged, non-raising `False` — no further change needed to the caller.

## Warnings

### WR-01: Frame-silence notifications are unreachable for the entire duration of a hold state

**File:** `server/poll_loop.py:1035-1146` (early-return hold branch) and `1601-1626` (the one `_notify_silence_transition()` call site)
**Issue:** `_notify_silence_transition()` is called exactly once per `run_once()` invocation, after the shared code path following every non-hold branch. The hold branch (`if hold_kind is not None:`) `return`s before ever reaching that call site. The module's own docstring for `_notify_silence_transition()` acknowledges this is deliberate ("never inside the early-return hold branch further up, which has no 'this cycle's own check-in' to reason about the same way") — but a `display_off` hold, per `run_once()`'s own docstring, "has no scheduled end": an operator can leave the display off indefinitely. If the physical device dies (dead battery, hardware fault, disconnected from Wi-Fi) *while* the display is off, no `frame_silent` notification will ever fire, for as long as the hold lasts — potentially forever, since nothing ever re-checks staleness during a hold. This silently defeats the D-25/D-27 monitoring feature for exactly the scenario (a genuinely dead frame) it exists to catch, whenever that failure happens to coincide with a display-off (or quiet-hours) window.
**Fix:** Call `_notify_silence_transition()` (guarded by its own existing containment) from the hold branch too, using the same `history_db` connection already opened there for `_last_source_fault()`/`_record_history()` — staleness is a property of the device's last check-in row, independent of whether the panel itself is being repainted this cycle.

### WR-02: `_notify_battery_transition()` reads `battery_state.json` twice per transition, risking a body/decision mismatch

**File:** `server/poll_loop.py:1056-1060` and `1222-1227`
**Issue:** Both call sites compute `battery_low = apply_battery_hysteresis(load_battery_state(state_dir), was_battery_low)` and then, only `if battery_changed:`, call `_notify_battery_transition(state_dir, poll_state, battery_low, load_battery_state(state_dir), device_cfg)` — reading `battery_state.json` a *second* time to supply the `battery_mv` argument used to format the "Battery low — %s mV" notification body. `battery_state.json` is written concurrently by `stub-server/byos_server.py` on every device check-in with no lock between the two processes (the module's own docstring already documents this file as a read-only, externally-written input). Between the first read (which decided `battery_low`/`battery_changed`) and the second read (which formats the pushed message), the file can change, so the millivolt figure in the pushed notification can describe a different reading than the one that actually triggered the transition — a minor but real correctness gap, and an unnecessary duplicate file read either way.
**Fix:** Read `battery_state.json` once per cycle into a local (e.g. `battery_mv = load_battery_state(state_dir)`), and pass that same value to both `apply_battery_hysteresis()` and `_notify_battery_transition()` at both call sites.

### WR-03: `layout.section_intro_html()` does not escape its `section_id` argument

**File:** `companion/layout.py:1600-1622`
**Issue:** `section_intro_html(section_id, heading, description)` interpolates `heading` and `description` through `escape_html()` but writes `section_id` straight into `id="%s"` with no escaping at all:
```python
return (
    '<div class="section-intro">'
    '<h2 id="%s" class="text-heading">%s</h2>'
    '<p class="text-label section-caption">%s</p>'
    "</div>"
) % (section_id, escape_html(heading), escape_html(description))
```
Every current call site (`config_page.py`, `health_page.py`) passes a fixed module-level string constant, so this is not exploitable today. But this is a new shared helper (promoted this phase from a private per-page copy specifically so two page modules could share it), and every other builder in this file that accepts a string destined for an HTML attribute or text node escapes it unconditionally, with no "trust the caller" exception — this is the one new exception to that rule, in a helper explicitly designed to be reused more widely going forward.
**Fix:** Wrap `section_id` in `escape_html()` too, for defense in depth and to keep this file's "escape everything, unconditionally" invariant intact:
```python
) % (escape_html(section_id), escape_html(heading), escape_html(description))
```

### WR-04: Misleading constant reuse — `notify.TEST_NOTIFICATION_TITLE`/`TEST_NOTIFICATION_BODY` double as the generic push title for unrelated battery/silence transitions

**File:** `server/notify.py:51-55`, used at `server/poll_loop.py:545` and `609`
**Issue:** `TEST_NOTIFICATION_TITLE`/`TEST_NOTIFICATION_BODY` are documented as "The 'Send a test' button's own fixed title/body pair ... never templated" — i.e. named and scoped for one specific feature (`companion/app.py`'s `_handle_notifications_test_post()`). `poll_loop.py`'s `_notify_battery_transition()` and `_notify_silence_transition()` both reuse `notify.TEST_NOTIFICATION_TITLE` as the `title` argument for real battery-low/frame-silent pushes, which have nothing to do with the test button. This happens to be harmless today only because both features want the identical literal title text ("SkyPane"), but the naming actively misleads a future maintainer: renaming or changing `TEST_NOTIFICATION_TITLE`'s copy (e.g. to something test-specific like "SkyPane test") to improve the test-button UX would silently also change the title on every real battery/silence alert, and nothing in either call site's own code makes that coupling visible.
**Fix:** Introduce a separate, honestly-named constant (e.g. `notify.PUSH_TITLE = "SkyPane"`) for the shared branding title, and reserve `TEST_NOTIFICATION_TITLE` for the test button alone — even if both currently hold the same string.

---

_Reviewed: 2026-09-12T04:03:12Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
