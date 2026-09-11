# Phase 20: Bilingual companion, Display regrouped, Home redesigned, live theme preview, notifications, simple mode — Pattern Map

**Mapped:** 2026-09-11
**Files analyzed:** 22 (5 new, 12 heavily modified production, 6 test harnesses — 1 file, `companion/test_config_page.py`, counted in both modified-production and test-harness sets since it is both)
**Analogs found:** 22 / 22 — every file lands inside an existing, already-precedented module, an existing sibling static asset, or a verbatim move of code that already exists elsewhere. There is no "no analog" bucket this phase, in the same shape phase 19's own pattern map found none.

This map reuses 19-PATTERNS.md's format verbatim (file classification table → pattern assignments → shared patterns → no-analog bucket) and its **six-touch-point static-script contract** unchanged — every new script this phase adds (`theme-preview.js`, and the small `rule-form.js` addition) follows it exactly as phase 19 defined it, restated in Shared Patterns below with this phase's own route names substituted in.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `companion/i18n.py` (new) | service (shared, non-page) | transform (per-request string lookup) | `companion/auth.py`'s module shape (stateless, page-independent, documented import boundary) + `companion/battery.py`'s "verbatim new shared module" precedent | role-match (genuinely new mechanism, well-precedented module *shape*) |
| `companion/i18n_fr.py` (new) | model/registry (static data) | CRUD-read | `server/device_config.py`'s `THEMES`/`RUNWAYS` — "one Python dict registry keyed by a stable id" idiom | exact (id here is the English string, not a short code, but the "plain dict, no framework" shape is identical) |
| `server/wake.py` (new) | utility (shared, non-page) | transform | `companion/wake.py` itself — a **verbatim move**, not a rewrite (already stdlib `os`/`datetime` + `server.device_config` only, confirmed by its own docstring's import-boundary statement) | exact (verbatim move) |
| `server/notify.py` (new) | service (outbound HTTP) | request-response (one-shot POST) | `server/plane/calendar_rules.py`'s `default_calendar_transport()` + `fetch_ics()` + `_url_is_safe()`/`_host_is_safe()` — the codebase's only existing outbound-HTTPS-with-SSRF-gate pattern | exact |
| `companion/static/theme-preview.js` (new) | static asset (browser behaviour) | event-driven (DOM) | `companion/static/battery-trend.js` (render-on-interaction, data-attribute-driven) / the six-touch-point contract phase 19's `poll-cooldown.js` established | exact |
| `companion/static/rule-form.js` (new, or native-radio CSS per UI-SPEC §F recommendation) | static asset (browser behaviour) | event-driven (DOM) | `companion/static/dirty-state.js`'s preset-button idiom (`data-preset-*` attributes read by an existing script) | exact |
| `companion/layout.py` | shared view helper / shell | transform (HTML assembly) | itself (`_theme_form_html()`, `stat_tile()`, `page_shell()`, `local_clock_text()`/`relative_age_text()`) | exact |
| `companion/app.py` | HTTP controller (`BaseHTTPRequestHandler`) | request-response + routing | itself (`_handle_theme_post()`/`THEME_ROUTE` for `/ui-lang`+`/ui-mode`; `_handle_calendar_disconnect_post()` for calendar-connect and notifications-test; `_serve_theme_preview_image()` for the `?live=1` branch) | exact |
| `companion/pages/config_page.py` | page module (request-response, form CRUD) | request-response (form CRUD) | itself — every new group/section is a sibling of an existing group builder in the same file | exact |
| `companion/pages/home_page.py` | page module | request-response (read) | itself (full rebuild against its own existing `_status_tiles_html()`/`_recent_flights_html()` shape) | exact |
| `companion/pages/airlines_page.py` | page module | request-response (read + resolve-write) | itself — the "Change pictures"/"Done" toggle reuses `config_page._edit_artwork_link_html()`'s exact markup shape, relocated | exact |
| `companion/screens.py` | registry / config module | CRUD-read (static data) | itself (`SCREEN_TYPES["everyday_groups"]`/`["advanced_groups"]` tuples — a one-line move, not a new shape) | exact |
| `companion/theme_preview.py` | service (render + disk cache) | transform + file-I/O | itself (`cache_path()`/`preview_signature()`/`cached_preview_bytes()` — extended with one new optional axis, not rebuilt) | exact |
| `companion/wake.py` | thin re-export shim (after the move) | transform | itself, reduced to `from server.wake import *`-equivalent | exact |
| `companion/static/copy-button.js` | static asset | event-driven (DOM + Clipboard API) | itself — one hardcoded literal (`FEEDBACK_TEXT`) becomes a `data-*` read, mirroring `freshness.js`'s own `data-pause-text` idiom | exact |
| `companion/static/dirty-state.js` | static asset | event-driven (DOM) | itself — the five connector-word literals in `updateBar()` become `data-*` reads, same idiom | exact |
| `companion/static/style.css` | config/presentation | transform | itself | exact |
| `server/device_config.py` | model / registry + persistence | CRUD | itself (`normalise_screen_id()` + `load_device_config()`/`save_device_config()`'s "membership test, raise on write, degrade on read" family — the `notifications` group is the first **dict-valued** field in this family, not a scalar, so it is a role-match, not byte-identical) | role-match |
| `server/poll_loop.py` | cron-like batch process | batch + event-driven (transition detection) | itself — both `battery_low_active` sites (`poll_loop.py:846-849`, `poll_loop.py:1011-1014`) are the two call sites the new notify hook attaches to | exact |
| `companion/test_view_pages.py` | test harness | batch (self-executing check list) | itself (`check()`, `EXPECTED_CHECK_COUNT`) — this is the file that owns every Home retarget (confirmed live: 13/13 `home_page.` references in this file, 0 in the other three harnesses) | exact |
| `companion/test_config_page.py` | test harness | batch | itself | exact |
| `companion/test_companion_app.py` | test harness | batch | itself | exact |
| `companion/test_status_pages.py` | test harness | batch | itself | exact |
| `server/test_config_history.py` | test harness | batch | itself | exact |
| `server/test_poll_loop.py` | test harness | batch | itself | exact |

**Live `EXPECTED_CHECK_COUNT` baseline (verified 2026-09-11, matches RESEARCH.md's own table):** `test_view_pages.py`=85, `test_config_page.py`=181, `test_companion_app.py`=221, `test_status_pages.py`=191, `server/test_config_history.py`=64, `server/test_poll_loop.py`=81.

## Pattern Assignments

### `companion/i18n.py` (new) — service, transform

**Analog:** `companion/auth.py`'s module-boundary docstring shape + `companion/wake.py`'s "shared, page-independent module" framing.

**Module docstring convention to copy** (`companion/wake.py:1-27`, `companion/auth.py:1-8`) — every shared non-page module in this codebase states, at the top: what it must never import, which other shared modules it sits beside, and why it exists as a separate file rather than living inside a page module:
```python
"""companion/i18n.py — the per-request language lookup for the SkyPane
companion service (D-01..D-09).

Sits beside auth.py, battery.py, layout.py, screens.py and wake.py in
this same package — a shared, page-independent module, never living
inside the per-tab pages package itself (companion/pages/__init__.py's
own rule: no page module imports another page module). Stdlib
`contextvars` only; imports nothing from companion.pages, nothing from
server/.
"""
```

**Per-request state shape** — Claude's Discretion names `contextvars.ContextVar` as the expected shape; there is no existing per-request-scalar precedent in this codebase to copy verbatim (this app's only "resolved once per request" values today are computed inline in `page_context()` and returned in `ctx`, not stashed in a module-global). The nearest structural cousin is `companion/auth.py`'s `LoginThrottle`/`_REVOKED_TOKENS`-style module-level mutable state guarded by explicit set/get functions — model `set_current_lang(lang)`/`current_lang()` on that same "one get, one set, no other mutation path" shape:
```python
import contextvars

_LANG_CTX = contextvars.ContextVar("skypane_lang", default="en")

def set_current_lang(lang):
    _LANG_CTX.set(lang if lang in ("en", "fr") else "en")

def current_lang():
    return _LANG_CTX.get()
```
`companion/app.py`'s `page_context()` (the sole caller with request-scoped knowledge — see its existing body at `app.py:1115-1170`) calls `i18n.set_current_lang(...)` once, before any page module's `render()`/`handle_post()` runs, exactly where it already computes `ctx["ui_theme"]`.

**Fallback-never-raises contract** — every normaliser in `server/device_config.py` (`normalise_screen_id()`, `normalise_led_enabled()`, etc., `device_config.py:542-604`) documents "never raises, degrades to a fixed default" as its own one-line docstring sentence; `t()` must carry the identical sentence for the identical reason (a missing catalogue key is not a bug that should crash a request):
```python
def t(text):
    """Return i18n_fr.CATALOG[text] when the current request language
    is French AND text is a key in that dict; otherwise return text
    unchanged. Never raises, never logs — a missing key degrades to
    the English source string exactly like a request in English would
    render, per D-04.
    """
    if current_lang() == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text


def t_lang(text, lang):
    """t()'s test-only sibling: look up `text` for an explicit `lang`
    without touching the ContextVar — companion/test_i18n.py's own
    round-trip checks use this so they never depend on set_current_lang()
    leaking state between checks in the same process.
    """
    if lang == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text
```

---

### `companion/i18n_fr.py` (new) — registry, CRUD-read

**Analog:** `server/device_config.py`'s `THEMES`/`RUNWAYS` dict-of-dicts registries (`device_config.py:416-432` for `RUNWAYS`'s exact shape) — here flattened to one dict since the "id" is the English string itself, not a short code.

```python
"""companion/i18n_fr.py — the French translation catalogue (D-01/D-04).

A plain dict, keyed by the exact English source string (including any
%s/%d placeholder), grouped by page module with a comment banner per
group — mirroring THEMES'/RUNWAYS' own "one registry, no framework"
convention in server/device_config.py, and RULE_KIND_LABELS' own
"small fixed dict, no database" idiom in
server/plane/colour_rules.py.

companion/i18n.py.t() is the ONLY reader of this dict; nothing else in
this codebase should import CATALOG directly (mirrors THEMES' own
single-consumer-module discipline where every other reader goes
through a helper: theme_label(), not THEMES[...] directly).
"""

# --- Home (home_page.py) ---
CATALOG = {
    "Next update ≈ %s": "Prochaine mise à jour ≈ %s",
    "Expected since %s": "Attendue depuis %s",
    ...
}
```
Every English key in the Copywriting Contract table (`20-UI-SPEC.md`'s Section A-K) becomes one entry; the completeness harness (D-08, below) is the mechanical proof no key is missing or orphaned, not a hand-kept checklist.

---

### `server/wake.py` (new) — utility, transform

**Analog:** `companion/wake.py` itself — this is a **verbatim move**, confirmed safe by direct read: the existing module (`companion/wake.py`, full file, 193 lines) already imports only `os`, `datetime`/`timedelta`/`timezone`, and `server.device_config` — it has *never* imported anything from `companion/pages/` or `companion/app.py`. Moving it to `server/wake.py` is a change of home, not of logic.

**Move mechanics:**
1. Copy `companion/wake.py`'s full body (constants `SLEEP_ENV_VAR`/`MISSED_WAKES_WARN`/`MISSED_WAKES_ERROR`/`STALE_WARN_FLOOR_S`/`STALE_ERROR_FLOOR_S`, functions `env_sleep_s()`/`effective_wake_interval_s()`/`device_staleness_thresholds()`/`next_wake_at_iso()`) into `server/wake.py` unchanged, updating only the module docstring's own path self-reference.
2. `companion/wake.py` becomes a 3-line re-export shim (RESEARCH.md's own recommended path, Open Question 3):
```python
"""companion/wake.py — thin re-export shim over server/wake.py (D-27).

Moved here in an earlier phase (19-05-PLAN.md); relocated to
server/wake.py this phase so server/poll_loop.py can import the same
arithmetic without ever importing anything under companion/ (D-27's
own "the server never imports the companion" constraint). Every
existing `companion.wake.*` call site (home_page.py, config_page.py)
and every existing pinned test importing `companion.wake` keeps
working unmodified against this shim.
"""
from server.wake import (  # noqa: F401
    env_sleep_s, effective_wake_interval_s, device_staleness_thresholds,
    next_wake_at_iso, MISSED_WAKES_WARN, MISSED_WAKES_ERROR,
    STALE_WARN_FLOOR_S, STALE_ERROR_FLOOR_S, SLEEP_ENV_VAR,
)
```
3. `server/poll_loop.py`'s new frame-silent check imports `from server import wake` directly (never `companion.wake`) — this is the whole point of the move.

---

### `server/notify.py` (new) — service, request-response (one-shot POST)

**Analog:** `server/plane/calendar_rules.py`'s `default_calendar_transport()` (`calendar_rules.py:1656-1676`), `fetch_ics()` (`:1679+`), `_url_is_safe()` (`:1626-1653`) — the codebase's only existing "outbound HTTPS with an SSRF gate and an injectable transport for tests" pattern.

**Transport + injection-seam idiom to copy verbatim** (`calendar_rules.py:1656-1676`):
```python
def default_calendar_transport(url, timeout):
    return requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=timeout,
        stream=True, allow_redirects=False)
```
`server/notify.py`'s `send_notification(topic_url, title, body, timeout=5, transport=None)` follows the identical shape: a `transport=None` keyword defaulting to a module-level `default_notify_transport(url, title, body, timeout)` (a thin `requests.post()`/`urllib.request` wrapper per D-25's stdlib-preference — RESEARCH.md's Don't-Hand-Roll table names `urllib.request.Request`/`urlopen` specifically, since this module has no existing `requests` dependency the way `calendar_rules.py` does), injectable exactly like `fetch_ics(transport=...)` already is for `server/test_calendar_rules.py`'s own hermetic fakes.

**SSRF gate — reuse, do not re-derive** (Security Domain, ASVS V5): `send_notification()`'s first line must be `if not calendar_rules._url_is_safe(topic_url): return False` (or a locally re-exported alias) — the exact function `fetch_ics()` already calls, never a second, independently-written scheme/hostname/private-IP check. This is the single most important line in the new file per the phase's own Security Domain table.

**Never-raise / 5s-timeout / one-attempt discipline** (D-27's own text, mirrored from `fetch_ics()`'s own docstring convention):
```python
def send_notification(topic_url, title, body, timeout=5, transport=None):
    """POST `body` to `topic_url` with a `Title: {title}` header — an
    ntfy-style push. Returns True on any 2xx response, False on any
    refusal (an unsafe URL, a non-2xx response, a timeout, or a
    transport exception) — never raises, matching fetch_ics()'s own
    contract. One attempt, no retry (D-27).
    """
    if not calendar_rules._url_is_safe(topic_url):
        return False
    send = transport or default_notify_transport
    try:
        response = send(topic_url, title, body, timeout)
    except Exception:
        return False
    return 200 <= getattr(response, "status_code", 0) < 300
```

**Logging discipline** (mirrors `fetch_ics()`'s own T-16-SECRET-shaped rule at `calendar_rules.py:1705-1714`): on any failure, log `type(exc).__name__` and a fixed description only — never the exception's own `str()`, since a topic URL is exactly as secret-shaped as a calendar feed URL and several `requests`/`urllib` exception types embed the request URL in their default string form.

---

### `companion/static/theme-preview.js` (new) — static asset, event-driven

**Analog:** the six-touch-point static-script contract, restated below in Shared Patterns; structurally closest sibling is `companion/static/battery-trend.js` (render-on-interaction, reads `data-*` attributes, no fetch/timer).

**Header-comment convention to copy** (`companion/static/copy-button.js:1-26`, `companion/static/dirty-state.js:1-59`): name the decision (D-22..D-24), the ES5-safe constraint, the exact `*_SCRIPT_ROUTE`, and the no-`innerHTML` standing constraint.

**Guard-clause idiom** (`companion/static/dirty-state.js:40-53`'s shape, reused verbatim): look up `.theme-live-preview img`, `return` immediately if absent — most pages carry no live preview at all.

**The behaviour to implement** — each chip's `<label>` (built by `_theme_chip_grid_html()`, `config_page.py:754-808`) gains a `data-preview-src="/theme-preview/{id}.png?live=1"` attribute (per D-24/`20-UI-SPEC.md` §H); the script listens for a `change` event on the grid's radio inputs (event delegation on the grid container, matching `dirty-state.js`'s own `form.addEventListener("change", ...)` idiom rather than one listener per chip) and rewrites `.theme-live-preview img`'s `src` to the clicked chip's `data-preview-src`. No-JS floor: the preview's initial `src` (server-rendered from the currently-saved theme) is the only state a no-JS browser ever sees — this is D-24's own explicit fallback, requiring zero script-side special-casing.

**Test harness pattern to extend** — `companion/test_companion_app.py`'s existing three-check family for a static script (`_static_script_public()`, the ES5-safe/no-HTML-write token-ban check, the route/src cross-file-agreement check — see Shared Patterns below) gets a fourth new triplet for this file, named identically to how phase 19 added `poll-cooldown.js`'s.

---

### `companion/static/rule-form.js` (new, if the segmented-control path is chosen over native radios)

**Analog:** `companion/static/dirty-state.js`'s Quiet-hours-preset idiom (`dirty-state.js:73+`, "D-14/S-04: Quiet hours presets... reading their data-preset-start/data-preset-end/data-preset-enabled attributes and writing into the same form's inputs") — the exact same "small script reads `data-*`, writes into a sibling native control, no server round-trip" shape D-15b's placeholder-swap needs.

`20-UI-SPEC.md`'s own Structural Note 5 recommends native radios styled as the segmented control instead (zero degraded state) — if the planner takes that path, no new `.js` file is needed at all and this file drops out of scope entirely; flag this choice explicitly in the plan, per the UI-SPEC's own instruction.

If the button-segment path ships anyway: toggle `.theme-option--active`, write the hidden `rule_kind` input, and rewrite the value input's `placeholder` on click — three plain `addEventListener("click", ...)` handlers, ES5-safe, no fetch/timer, following `copy-button.js`'s guard-clause-first shape.

---

### `companion/layout.py` — shared view helper

**D-02/D-03/D-29 — the language and simple-mode nav-footer switches.** `_theme_form_html()` (`layout.py:835-848`) is the exact idiom to copy twice:
```python
def _theme_form_html(resolved_theme):
    options = []
    for choice in UI_THEME_CHOICES:
        is_active = choice == resolved_theme
        css_class = ("theme-option theme-option--active" if is_active else "theme-option")
        options.append(
            '<button type="submit" name="ui_theme" value="%s" class="%s" aria-pressed="%s">%s</button>'
            % (escape_html(choice), css_class, "true" if is_active else "false",
               escape_html(choice.capitalize())))
    return '<form class="theme-form" method="post" action="/ui-theme">%s</form>' % "".join(options)
```
Two new sibling builders, `_lang_form_html(resolved_lang)` (options `"fr"`/`"en"`, action `/ui-lang`, labels "FR"/"EN" — untranslated identifiers per D-05) and `_mode_form_html(resolved_mode)` (options `"simple"`/`"full"`, action `/ui-mode`, labels `t("Simple")`/`t("Full")`) — both hard-code their own `action="/ui-lang"`/`action="/ui-mode"` literal for the identical reason `_theme_form_html()`'s own comment documents (`layout.py:857-861`: `companion/app.py` imports this module, so the reverse import would be a cycle). Per `20-UI-SPEC.md` §I, each `<form>` gains `aria-label="Language"`/`aria-label="Simple mode"` (the theme form gets `aria-label="Theme"` too, a one-line addition) to disambiguate the three now-identical-looking segmented groups.

**Footer assembly order** — `page_shell()`'s `sidebar_footer_html` (`layout.py:1058-1060`) and `_mobile_nav_html()`'s `footer_html` (`layout.py:928-930`) both currently concatenate `theme_form_html + _logout_form_html()`; both become `lang_form_html + theme_form_html + mode_form_html + _logout_form_html()` (the UI-SPEC's resolved order: language, theme, simple mode, Sign out) — **two call sites, must change together**, exactly the risk `_mobile_nav_html()`'s own docstring already calls out ("`theme_form_html` is taken as a parameter... so the two copies can never drift").

**D-03 `<html lang="...">`.** Both `page_shell()` (`layout.py:1095`, `'<html lang="en" data-ui-theme="%s">\n'`) and `login_shell()` (`layout.py:969`, identical literal) hard-code `lang="en"`. `page_shell()` gains a `lang="en"` keyword parameter (defaulted, so the existing ~40+ call sites across every page module stay unmodified) read from `ctx["lang"]` at each page module's own call site (mirroring how `ui_theme=` is already threaded through every `render()` today); `login_shell()`/404/etc. (routes with no authenticated `ctx`) read the `Accept-Language`-derived language the same way `page_context()`'s new helper resolves it pre-login.

**D-07 lang-aware dates.** `relative_age_text()` (`layout.py:565-578`) and `local_clock_text()`'s `_MONTH_ABBR` (`layout.py:31-32`) both need a French branch. Follow `_STATUS_DOT_CLASSES`'s own "fixed dict, membership lookup, documented fallback" shape for a `_MONTH_ABBR_FR` tuple parallel to `_MONTH_ABBR`, and thread `lang` through both functions as a new trailing keyword defaulted to `"en"` (never change the two functions' existing positional signature — dozens of existing call sites pass exactly `(parsed, now_parsed=...)`/`(age_seconds)`).

**D-21 `layout.status_row()` — the one new visual primitive.** Modelled directly on `stat_tile()` (`layout.py:1239-1296`, read in full above) for its "status maps to one of three fixed CSS classes, falls back to the neutral/warn class for anything unrecognised, `label`/`verdict`/`detail` are separate escaped slots" shape, and on `status_dot()` (`layout.py:1214-1236`) for the dot-plus-label idiom:
```python
def status_row(label, verdict, detail, state):
    """<div class="status-row status-row--ok|warn|error"> — D-21's one
    new shared primitive. `label` is optional: an empty string omits
    the <span> entirely (20-UI-SPEC.md §A), not merely its text — the
    calendar status row passes "" since its own <h2> already names the
    subject. `verdict`/`detail` are both escaped here; `state` maps
    through the SAME _STATUS_DOT_CLASSES/_DEFAULT_STATUS_DOT_CLASS
    fallback status_dot()/stat_tile() already use — a third consumer
    of that one dict, never a second copy of it.
    """
    dot_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    label_html = (
        '<span class="status-row__label text-label">%s</span>' % escape_html(label)
        if label else "")
    return (
        '<div class="status-row status-row--%s">'
        '<span class="dot %s"></span>%s'
        '<span class="status-row__verdict">%s</span>'
        '<span class="status-row__detail">%s</span>'
        "</div>"
    ) % (state, dot_class, label_html, escape_html(verdict), escape_html(detail))
```
Note `state` here maps through the SAME three-key whitelist `_STATUS_DOT_CLASSES` already enforces — do not accept an arbitrary `state` string into the outer `status-row--%s` class interpolation without the same membership discipline `card_status_class()` (`layout.py:1299+`) already documents for exactly this "status → CSS modifier" mapping; reuse `card_status_class("status-row", state)` for the outer class rather than hand-rolling a second `%s` interpolation of unvalidated input.

**§C — promoting `_section_intro_html()` to `layout.py`.** `health_page._section_intro_html()` (`health_page.py:1639-1666`, read in full above) is copied verbatim into `layout.py` as `layout.section_intro_html(section_id, heading, description)` — byte-identical markup and CSS class (`.section-intro`), only its module location changes (per `20-UI-SPEC.md` §C's own instruction: `companion/pages/__init__.py` forbids page-to-page imports, so a helper both `health_page.py` and `config_page.py` need must live in the shared layer). `health_page.py`'s own call sites become `layout.section_intro_html(...)`; `config_page.py`'s three new Display supersection headers (Look / What it watches / When it is on) call the same function.

---

### `companion/app.py` — HTTP controller

**D-02/D-29 — `/ui-lang` and `/ui-mode` routes.** `_handle_theme_post()` (`app.py:2479-2490`, read in full above) is the exact template:
```python
def _handle_theme_post(self):
    form = self.read_form()
    submitted = form.get("ui_theme")
    cookie_header = None
    if submitted in layout.UI_THEME_CHOICES:
        cookie_header = (
            "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
            % (auth.UI_THEME_COOKIE_NAME, submitted, auth.secure_cookie_flag(),
               THEME_COOKIE_MAX_AGE_S))
    return self.redirect(self._referring_tab(), set_cookie=cookie_header)
```
`_handle_lang_post()`/`_handle_mode_post()` are byte-for-byte the same shape, substituting `form.get("ui_lang")`/`auth.UI_LANG_COOKIE_NAME`/`("fr", "en")` and `form.get("ui_mode")`/`auth.UI_MODE_COOKIE_NAME`/`("simple", "full")` respectively. **Gating**: both new routes join `THEME_ROUTE`'s own gated dispatch shape in `do_POST()` (`app.py:2523-2526`):
```python
if path == THEME_ROUTE:
    if not self.require_session():
        return None
    return self._handle_theme_post()
```
— copy this exact `if not self.require_session(): return None` guard for `/ui-lang` and `/ui-mode`, per the Security Domain table's own instruction (never leave a state-changing route ungated, matching the comment phase 19 itself already left at `app.py:2519-2522` about exactly this class of route).

**Cookie constants** — `companion/auth.py`'s `UI_THEME_COOKIE_NAME = "sp_ui_theme"` (`auth.py:58`) plus `secure_cookie_flag()` (`auth.py:228-246`, read in full above) are the model: `UI_LANG_COOKIE_NAME = "sp_ui_lang"`, `UI_MODE_COOKIE_NAME = "sp_ui_mode"`, both routed through the SAME `secure_cookie_flag()` call — never a second Secure-flag scheme, per the Security Domain table.

**D-03 `Accept-Language` default.** `page_context()` (`app.py:1115-1170`, read in full above) is where `ctx["lang"]` is resolved — add a small `_lang_from_request(self)` helper mirroring `_resolved_ui_theme()`'s own "cookie first, environment-derived fallback second" shape (grep `_resolved_ui_theme()` at `app.py:1038` for its exact body before writing this), reading `self.headers.get("Accept-Language", "")` only when no `sp_ui_lang` cookie is present.

**D-14c — calendar-connect's own dedicated route.** `_handle_calendar_disconnect_post()` (`app.py:1986-2040`, read in full above) is the template: read the form, call the single existing writer function directly (`calendar_rules.save_calendar_url()` + — on success — `calendar_rules.refresh_calendar_registry()` under `_POLL_LOCK`, exactly like `_handle_settings_post()`'s own calendar-signal branch already does at `app.py:2390-2403`), redirect with a flash key — **never** through `config_page.handle_post()`'s scope/`in_scope` machinery (Pitfall 2). New `_handle_calendar_connect_post()` follows the identical gate-then-dispatch registration in `do_POST()`.

**D-26 — `POST /settings/notifications/test`.** Same dedicated-route shape again: read the form's already-saved `notifications.topic_url` from `device_config.load_device_config()` (never from the request — the field is write-only), call `notify.send_notification(topic_url, TEST_NOTIFICATION_TITLE, TEST_NOTIFICATION_BODY)`, redirect with a success/failure flash key mirroring `FLASH_KEY_CALENDAR_DISCONNECTED`/`FLASH_KEY_CALENDAR_SYNC_FAILED`'s own two-flash-key pattern.

**D-23 — `?live=1` on the theme-preview route.** `_serve_theme_preview_image(self, theme_id)` (`app.py:1572-1603`, read in full above) gains one new step: parse `?live=1` off `self.path` (the same `urlsplit`/`parse_qs` idiom `page_context()` already uses at `app.py:1119-1120`), and when present, fetch the single most recent runway event (`history_db.recent_runway_events(conn, limit=1)`, the exact call `home_page._recent_flights()` already makes) and pass it through to `theme_preview.cached_preview_bytes(state_dir, theme_id, live_event=row_or_none)`. The membership-test-before-any-path-construction discipline this function's own comment documents (`app.py:1579-1584`, "Membership test FIRST, before any path is ever constructed") is unchanged — the new `live_event` argument never itself becomes a path component (`theme_preview.py`'s own cache-key change folds only the event's integer `id`, never any string field, into the filename).

---

### `companion/pages/config_page.py` — the highest-touch-count file in the phase

**D-10/D-11 — group moves.** `scope_groups()` (`config_page.py:119-133`, read in full above) needs **no change** — it already reads `screen["everyday_groups"]`/`["advanced_groups"]` off `companion/screens.py`'s per-screen-type dict. The entire move is one edit in `companion/screens.py`: `SCREEN_TYPES["plane-frame"]["everyday_groups"]` gains `GROUP_RUNWAY` and `GROUP_CALENDAR`; `["advanced_groups"]` loses them, per `screens.py:50-52` (read in full above). `render()`'s `show_rules`/`show_calendar_disconnect` flags (`config_page.py:2313-2319`, currently set only in the `elif scope == SCOPE_DEVICE:` branch) move to the `if scope == SCOPE_DISPLAY:` branch; `calendar_disconnect_section()`'s own `return_to` (via `_scope_fields_html(scope, layout.DISPLAY_ROUTE)`, currently `layout.DEVICE_ROUTE` at `config_page.py:2312`) becomes `layout.DISPLAY_ROUTE`.

**D-12 — three supersections.** `render()`'s Display-scope groups_html assembly (`config_page.py:2286` builds one flat `groups_html` string today) needs restructuring into three `layout.section_intro_html(...)` calls interleaved with the relevant group builders' output, in the UI-SPEC's locked order (Theme/Flight-colours/Calendar, then Runway, then Screen/Quiet-hours). This is the one place `groups_html = "".join(builders[g]() for g in groups if g in builders)` (`config_page.py:2286`) cannot stay a single flat join for the Display scope — branch on `scope == SCOPE_DISPLAY` to build the three-section version, leaving the Device/SCOPE_ALL paths' flat join untouched.

**D-13/§D — the `<form>`-nesting fix for Screen on/off and Quiet hours.** This is the phase's Pitfall 1 (CRITICAL). `display_group()` (`config_page.py:1451-1513`, read in full above) and `quiet_hours_group()` (`config_page.py:1221-1356`, read in full above) both currently return one `<div class="theme-status">...</div>` string that `render()` concatenates INTO `groups_html`, which is emitted INSIDE `<form id="settings-form">`. The fix, following the exact `form="%s" % SETTINGS_FORM_ID` precedent already shipped for the dirty-bar's Save button (`config_page.py:2242`, read in full above) and the screen-type `<select>` (`config_page.py:2452-2456`, `'<select name="screen_id" id="%s" form="%s">%s</select>'`):
1. Both group builders' returned wrapper (`<div class="theme-status theme-status--nested">`) moves OUT of `groups_html` and renders as a **sibling** of `<form id="settings-form">` — the same slot `calendar_disconnect_section()` already occupies (immediately after `</form>` closes).
2. Every scheduled control inside (the `display_enabled` checkbox; the `quiet_hours_enabled` checkbox, the two `time` inputs) gains a literal `form="settings-form"` attribute — reuse `SETTINGS_FORM_ID`, never retype the string `"settings-form"`.
3. The new quick-action mini-`<form method="post" action="/quick/display">` (D-19) renders as a true, separate `<form>` at the top of that same non-form wrapper, using `home_page._toggle_form_html()`'s exact markup shape (`home_page.py:229-237`) relocated.

**D-14 — Calendar redesign.** `calendar_group()` (`config_page.py:1515-1687`, read in full above) is restructured, not rewritten from scratch — every piece it needs already exists somewhere in this file:
- The status sentence (`status_html`, currently `'<p class="calendar-status">%s</p>'`) becomes a `layout.status_row("", verdict, detail, state)` call (D-21) — `verdict`/`detail` split out of the existing four-branch `if drift / elif not configured / else usable / else pending` logic (`config_page.py:1608-1624`), which itself needs no change beyond returning two strings instead of one pre-joined one.
- The two-sentence disclaimer moves into a `<details><summary>How it works</summary>...</details>` block — no existing `<details>` precedent in this file to copy verbatim (RESEARCH.md confirms this codebase's first two-step server-rendered confirm flow was likewise "genuinely new," per Pitfall 2's own note); the closest structural cousin for a collapsed-by-default disclosure is the calendar disconnect confirm page's own `<form>`-based two-step gate, though `<details>` itself needs no JS analog — it is a native element.
- The `<select name="calendar_theme_id">` (`config_page.py:1667-1672`) is REPLACED by `_theme_chip_grid_html("calendar_theme_id", selected_calendar_theme_id, extra_class="theme-chip-grid--compact")` (`config_page.py:754-808`, read in full above — the SAME function `theme_fieldset()` already calls twice for departures/arrivals, now a third consumer) plus a new `.theme-chip--compact` CSS modifier (UI-SPEC §G, zero new selected-state logic — additive size-only rules on top of the existing chip).
- The write-only URL field's contract (`config_page.py:1563-1575`'s own docstring: "the field always renders with no value attribute... nothing derived from the stored URL") is UNCHANGED and must be preserved verbatim in whatever new markup renders the Connect/Replace form.

**D-14c — the Connect mini-form** is a NEW small form posting to `/settings/calendar/connect` (its own dedicated route, per app.py's section above and Pitfall 2) — model its markup on `_rule_add_form_html()`'s `<div class="rule-add-form__field">` field-wrapper shape (`config_page.py:1931-1946`) for the label+input+hint layout, and on `calendar_disconnect_section()`'s own sibling-of-the-form placement (`config_page.py:1690-1737`, read in full above) for WHERE it renders (immediately after the Calendar `.page-section`, never inside `<form id="settings-form">`).

**D-15 — Flight colours rebuild.** `_rule_add_form_html()` (`config_page.py:1894-1956`, read in full above), `_rule_row_html()` (`:1972-1996`), `_rules_table_html()`/`_rules_cards_html()` (`:1999+`) all get restructured, reusing pieces already in this file:
- The `<select name="rule_kind">` (`:1935`) becomes a segmented `role="radiogroup"` reusing `.theme-form`/`.theme-option` verbatim (`layout._theme_form_html()`'s exact button markup, `layout.py:842-845`) — the THIRD consumer of that component after the UI-theme picker and this same phase's language switch (UI-SPEC §F's own count).
- The `<select name="rule_theme_id">` (`:1945`) becomes `_theme_chip_grid_html("rule_theme_id", ..., extra_class="theme-chip-grid--compact")` — the calendar theme picker's own compact-chip call, a second consumer of the SAME new modifier class.
- `_rule_row_html()`'s `<tr>`/`<td>` cells (`:1972-1996`) become one `<li class="rule-row">` per row, reusing `_rule_theme_swatch_html()`'s existing swatch-plus-label helper (`:1959-1969`) but drawing it as `.theme-chip__swatches`' two dots (UI-SPEC §F) instead of the current single `.theme-swatch__chip`, and `_rule_delete_action()` (`:1875-1891`) unchanged — the delete form's `action` URL builder needs no edit.
- D-15e's suggested-chips read `history_db.recent_runway_events(conn, limit=5)` — the EXACT call `home_page._recent_flights()` already makes (`home_page.py:125-126`) — reuse that query shape, do not write a second one.

---

### `companion/pages/home_page.py` — full rebuild against its own existing shape

**Pitfall 3's exact fix (the duplicated verdict).** `_status_tiles_html()` (`home_page.py:166-226`, read in full above) currently builds `frame_body` from its OWN `FRAME_STATE_TEXT[device_state]` (`home_page.py:173-174`), then appends `health["device_html"]` verbatim as a second detail paragraph (`home_page.py:175-177`). `health["device_html"]` is produced by `health_page._device_section()` (`health_page.py:1669-1722`, read in full above), whose own `verdict = '<p class="text-body widget-verdict">%s</p>' % escape_html(DEVICE_STATE_TEXT.get(state, ...))` (`health_page.py:1718-1719`) is BYTE-IDENTICAL text to `home_page.py`'s own `FRAME_STATE_TEXT` dict (`home_page.py:99-103`) — confirmed by direct read, both dicts read `"Checking in normally"` / `"Has not checked in for a while"` / `"Has not checked in for a long time"`. The fix: add a detail-only sibling to `health_page.py`, e.g. `_device_timestamp_only(device_health, now)` returning ONLY `layout.concise_timestamp_html(ts, now)` (the second half of `_device_section()`'s return, `health_page.py:1720-1721`, with the `verdict` line dropped), and have `home_page.py`'s new `status_row()`-based Frame row call THAT instead of `health["device_html"]`.

**D-17 — hero row + status card, replacing `_status_tiles_html()`'s three `stat_tile()` calls with three `layout.status_row()` calls.** The new function keeps `_status_tiles_html()`'s existing state-resolution logic (`device_state`/`pipeline_state`/`battery_state` reads off `ctx["health_state"]`, `home_page.py:167-171`) and its existing `FRAME_STATE_TEXT`/`DATA_STATE_TEXT`/`BATTERY_STATE_TEXT` dicts verbatim — only the OUTPUT builder changes, `stat_tile(label, content_html, state, icon=...)` → `status_row(label, verdict, detail, state)`.

**The "Expected since" past-time fix** — `_status_tiles_html()`'s existing next-wake block (`home_page.py:184-192`) already computes `next_wake_clock` via `wake.next_wake_at_iso()` + `layout.local_clock_text()`; the ONLY new logic needed is one `is_past` branch comparing `next_wake_parsed` against `layout.parse_iso(now)` (both already in scope at that point) and choosing between `"Next update ≈ %s" % clock` and `"Expected since %s" % clock` — no new data source, purely a comparison on values already computed.

**D-16 — quick actions leave Home.** `_quick_actions_html()`/`_toggle_form_html()`/`QUICK_ACTIONS_HEADING`/etc. (`home_page.py:47-82, 229-311`) are DELETED from this file and their markup (the screen/quiet-hours widgets) is what `config_page.py`'s D-19 section above relocates — `_toggle_form_html()`'s exact `<form method="post" action="%s" class="quick-action__form">` shape (`home_page.py:229-237`) is the piece to copy into `config_page.py`, not reinvent.

**D-17.2 — recent-flights thumbnail.** `_recent_flights_html()` (`home_page.py:340-369`) gains one new call per row: `illustrations.normalise_airline_key(row.get("airline"))` (D-20's own named resolver, "reusing the Airlines page's own resolver" — confirmed at `airlines_page.py:657`, a pure string function with `if not key: return ""` gate, so a falsy key renders the placeholder span with no new query).

---

### `companion/pages/airlines_page.py` — D-36

**Analog:** `config_page.py`'s now-deleted `_edit_artwork_link_html()` (`config_page.py:2461-2483`, referenced but not fully read — its call site at `config_page.py:2306-2311` is the piece being relocated) — the SAME `.page-header__screen`/`.text-label.section-caption` markup shape, moved wholesale from Device's action-slot to the top of Airlines' own gallery section, per `20-UI-SPEC.md` §K's own instruction ("this is that exact function's markup, relocated").

`airlines_page.py`'s existing `?edit=1` gating (`airlines_page.py:1217-1219` per 19-PATTERNS.md's own D-22 entry) needs NO change — only the entry point (a styled anchor instead of Device's plain `<a>`) is new.

---

### `server/device_config.py` — the `notifications` group

**Analog:** `normalise_screen_id()` (`device_config.py:549-558`, read in full above) for the "membership/type test, degrade to default on read, raise on write" shape; `load_device_config()`/`save_device_config()` (`device_config.py:641-838`, read in full above) for the additive-key pattern `screen_id` itself used one phase ago.

**Genuinely new wrinkle, flagged for the planner:** every existing field in this registry is a scalar (string/bool/int) or `None`; `notifications` is the first **dict-valued** field (`{"topic_url": str|None, "battery_low": bool, "frame_silent": bool, "lang": "en"|"fr"}`). There is no existing multi-field-sub-dict precedent in `device_config.py` to copy verbatim — the closest structural cousin is `theme_arriving`'s own three-state write contract (`device_config.py:750-760`, `None`/`CLEAR_THEME_ARRIVING`-sentinel/a-THEMES-member), which demonstrates this module's convention for "a field whose write semantics differ from a plain scalar," even though `notifications` itself needs a nested-dict validator, not a sentinel:
```python
def normalise_notifications(value):
    """Return a well-formed notifications sub-dict — never raises,
    degrades to DEFAULT_NOTIFICATIONS wholesale for anything that
    isn't a dict, and per-field within it for anything malformed,
    mirroring normalise_screen_id()'s own "membership test on read,
    degrade to default" shape, applied once per sub-key.
    """
    if not isinstance(value, dict):
        return dict(DEFAULT_NOTIFICATIONS)
    return {
        "topic_url": value.get("topic_url") if isinstance(value.get("topic_url"), str) else None,
        "battery_low": value.get("battery_low") if isinstance(value.get("battery_low"), bool) else DEFAULT_NOTIFICATIONS["battery_low"],
        "frame_silent": value.get("frame_silent") if isinstance(value.get("frame_silent"), bool) else DEFAULT_NOTIFICATIONS["frame_silent"],
        "lang": value.get("lang") if value.get("lang") in ("en", "fr") else DEFAULT_NOTIFICATIONS["lang"],
    }
```
`save_device_config()` gains a `notifications=None` trailing keyword (placed LAST, per `screen_id`'s own precedent comment at `device_config.py:705-707`, "so every existing positional/keyword call site predating this plan is unaffected") — a non-None value that fails `normalise_notifications`'s own shape check raises `ValueError` naming the rejected value, matching every sibling field's raise-on-write message shape (`device_config.py:769-797`).

**`server/test_config_history.py`'s mechanical retarget.** Every dict-equality check in this file (RESEARCH.md: "multiple, e.g. lines ~100, 116, 131, 144, 193, 225" per `screen_id`'s own phase-19 retarget, the exact same mechanical shape) needs a `"notifications": {...DEFAULT_NOTIFICATIONS...}` key added to every expected literal — the single highest-count mechanical retarget in this section, identical in kind to `screen_id`'s own phase-19 retarget (19-PATTERNS.md's own closing section documents this exact grep-and-patch recipe).

---

### `server/poll_loop.py` — the notify hook

**Analog:** itself — both `battery_low_active` transition sites (`poll_loop.py:846-849` inside the hold branch, `poll_loop.py:1011-1014` in the main branch, both read in full above) are IDENTICAL three-line blocks:
```python
was_battery_low = bool(poll_state.get("battery_low_active", False))
battery_low = apply_battery_hysteresis(load_battery_state(state_dir), was_battery_low)
battery_changed = battery_low != was_battery_low
poll_state["battery_low_active"] = battery_low
```
Both sites already compute `battery_changed` — a new `_notify_battery_transition(state_dir, was_battery_low, battery_low, battery_mv, device_cfg)` call, gated on `if battery_changed:`, is a ONE-LINE addition immediately after each of the two blocks above, not a restructuring of either. The function itself reads `device_config.load_device_config(state_dir)["notifications"]`, checks `["battery_low"]` is true and `["topic_url"]` is set, and calls `notify.send_notification(...)` with the D-25/D-28 body text (from `20-UI-SPEC.md` §G) in the persisted `notifications.lang`.

**The new frame-silent check** has no existing call site to extend — it is genuinely new logic, but every piece it needs already exists: `history_db.latest_device_health(conn)` (the same function `home_page._latest_battery()`/`health_page.py`'s own device-freshness read already call), `server.wake.effective_wake_interval_s(device_cfg)` + `server.wake.device_staleness_thresholds(...)` (the moved module, this phase's own D-27 seam — the WARN threshold, `MISSED_WAKES_WARN = 3`, is D-27's own named multiplier, already the exact number Health's warn threshold uses, satisfying "must not be lower than Health's own warn threshold" by construction rather than by a second independently-tuned constant).

**`poll_state.json`'s new sub-dict** follows `load_poll_state()`'s own "missing key → documented default" convention already used throughout this file (the same convention `battery_low_active` itself already relies on via `poll_state.get("battery_low_active", False)` above) — `poll_state.setdefault("notifications", {"last_battery_sent": False, "last_silent_sent": False})`, no migration needed.

---

## Shared Patterns

### `check(name, fn)` test-harness convention
**Source:** `companion/test_companion_app.py:743-753` (verified live, byte-identical to 19-PATTERNS.md's own citation — this convention has not changed since phase 19):
```python
def check(name, fn):
    try:
        ok, reason = fn()
    except Exception as exc:
        ok, reason = False, "exception: %r" % (exc,)
    results.append((name, ok))
    if ok:
        print("PASS %s" % name)
    else:
        print("FAIL %s - %s" % (name, reason))
```
**Apply to:** every new/retargeted assertion in all 6 harnesses this phase touches, plus any new `companion/test_i18n.py`/`server/test_notify.py` file. Always `def _x(): ... return True/False, "reason"` immediately followed by `check("description", _x)` — never a bare `assert`.

### `EXPECTED_CHECK_COUNT` re-derivation
**Live baseline, verified 2026-09-11:** `companion/test_view_pages.py`=85, `companion/test_config_page.py`=181, `companion/test_companion_app.py`=221, `companion/test_status_pages.py`=191, `server/test_config_history.py`=64, `server/test_poll_loop.py`=81.
**Apply to:** after editing a harness, run it directly (`server/.venv/bin/python3 <file>.py`), read the printed `N/M checks pass` line, append a NEW `EXPECTED_CHECK_COUNT = M` assignment with a comment citing this phase's plan number — never edit an old comment's narration in place, never edit an old assignment's value.

### Home's test ownership (confirmed, not just assumed)
**Verified live (2026-09-11):** `grep -c "home_page\." companion/test_view_pages.py` → 13; the same grep against `test_config_page.py`/`test_companion_app.py`/`test_status_pages.py` → 0 each. `companion/test_view_pages.py` is Home's sole owner — every D-16..D-21 retarget lands there; no new `test_home_page.py` is needed (matches the CONTEXT.md orchestrator resolution verbatim).

### Duplicated-not-imported static-route contract (the six touch points)
**Source:** `companion/app.py:110-135`+`:1468-1479` (route+path constants, thin `_serve_*_script()` delegate), `companion/layout.py`'s mirrored `*_SCRIPT_SRC` constants + `page_shell()`'s script-tag list, `companion/test_companion_app.py`'s cross-file "route equals src" test family — unchanged since 19-PATTERNS.md's own citation of this exact contract, verified still current via the live `FLASH_CLEANUP_SCRIPT_ROUTE`/`_FLASH_CLEANUP_JS_PATH`/`_serve_flash_cleanup_script()` triplet (`app.py:168, 514, 1468-1474, 2136-2137`).
**Apply to:** `companion/static/theme-preview.js` (new) and `rule-form.js` (new, if that path is chosen): (1) a `THEME_PREVIEW_SCRIPT_ROUTE`/`_THEME_PREVIEW_JS_PATH` constant pair in `app.py`, alongside the existing seven; (2) a thin `_serve_theme_preview_script(self)` delegate onto `_serve_script_file()`; (3) one `elif path == THEME_PREVIEW_SCRIPT_ROUTE:` dispatch line in `do_GET()`; (4) a matching `THEME_PREVIEW_SCRIPT_SRC` constant in `layout.py`, carrying the same "duplicated rather than imported" comment every sibling already has; (5) `page_shell()`'s script-tag list/tuple grows by one; (6) a new cross-file route/src-agreement test in `companion/test_companion_app.py`. **Never** attempt to collapse the route string into one shared constant module — `companion/app.py` cannot import `companion/layout.py`'s constant without a cycle (`layout.py` imports nothing from `app.py`), and this codebase treats that duplication as a deliberate, tested design choice, not an oversight to fix.

### `form="settings-form"` — a form-associated control outside its `<form>`
**Source:** `companion/pages/config_page.py:2242` (dirty-bar Save button) and `:2452-2456` (screen-type `<select>`) — both already-shipped, already-tested precedents for "an element that submits into `<form id="settings-form">` despite not being a DOM descendant of it."
**Apply to:** every scheduled control inside the restructured Screen on/off and Quiet hours group wrappers (D-19/Pitfall 1) once those wrappers move to being siblings of the form.

### Universal escaping choke point
**Source:** `companion/layout.py`'s `escape_html()`, the single definition site every `companion/pages/*.py` module imports and calls — unchanged since 19-PATTERNS.md's own citation.
**Apply to:** every new dynamic markup builder this phase adds, INCLUDING the output of `t()` — `t()` returns plain text, never markup (per the Security Domain table's own explicit warning: "do not special-case translated strings as already safe"). Every `t(...)` call site still needs its own `escape_html(...)` wrap, exactly like any other string.

### Fixed-class-lookup-with-fallback (the `_STATUS_DOT_CLASSES`/`_STAT_TILE_BORDER_CLASSES` idiom)
**Source:** `companion/layout.py:151-156` (`_STATUS_DOT_CLASSES`/`_DEFAULT_STATUS_DOT_CLASS`), reused by `status_dot()`, `stat_tile()`, and now `status_row()` (D-21) and `card_status_class()` — a fourth/fifth consumer of ONE dict, never a duplicate.
**Apply to:** any new component this phase adds that carries a three-state (`ok`/`warn`/`error`) status colour — `status_row()` above, and the `.rule-row__kind` badge (D-15c) if it is ever given a status tint (the UI-SPEC's own instruction is that it should NOT be colour-coded, so this is a "do not add" flag as much as a reuse pointer).

## No Analog Found

None. Every file in this phase's scope lands inside an existing, already-precedented module or an existing sibling static asset, or is a verbatim move/extension of code that already exists elsewhere in the codebase (`server/wake.py` from `companion/wake.py`; `server/notify.py`'s transport/SSRF shape from `calendar_rules.py`; `companion/i18n.py`'s module-boundary shape from `companion/auth.py`/`companion/wake.py`).

## Metadata

**Analog search scope:** `companion/`, `companion/pages/`, `companion/static/`, `server/device_config.py`, `server/poll_loop.py`, `server/plane/calendar_rules.py`, `server/test_config_history.py`, `server/test_poll_loop.py`
**Files scanned (Read/Grep), 2026-09-11 (live, this session):** `companion/app.py` (targeted: `_handle_theme_post()`, `THEME_ROUTE`/`do_POST()` gating, `page_context()`, `_serve_theme_preview_image()`, `_handle_calendar_disconnect_post()`, the flash-cleanup six-touch-point triplet), `companion/auth.py` (targeted: `UI_THEME_COOKIE_NAME`, `secure_cookie_flag()`, cookie-header builders), `companion/layout.py` (targeted: module header, `NAV_GROUPS`, `relative_age_text()`/`local_clock_text()`/`_MONTH_ABBR`, `_nav_links()`/`sidebar_nav()`/`_theme_form_html()`/`_logout_form_html()`/`_mobile_nav_html()`, `login_shell()`/`page_shell()` incl. `<html lang>` literals and the sidebar-footer assembly, `status_dot()`/`stat_tile()`/`card_status_class()`), `companion/pages/config_page.py` (targeted: `scope_groups()`/`submitted_scope()`/`submitted_return_route()`, the checkbox-value constants, `_theme_chip_grid_html()`, `calendar_group()`/`calendar_disconnect_section()` in full, `quiet_hours_group()`/`display_group()` in full, `_rule_add_form_html()`/`_rule_row_html()`/`_rules_section_html()` in full, `render()` in full incl. the dirty-bar `form=` attribute and the SCOPE_DISPLAY/SCOPE_DEVICE branches), `companion/pages/home_page.py` (full read, 383 lines), `companion/pages/health_page.py` (targeted: `_section_intro_html()`, `_device_section()`, `DEVICE_STATE_TEXT`), `companion/screens.py` (full read, 88 lines), `companion/wake.py` (full read, 194 lines), `companion/theme_preview.py` (full read, 243 lines), `companion/static/copy-button.js`/`dirty-state.js` (targeted headers + the exact literal lines D-06 needs), `server/device_config.py` (targeted: every `normalise_*()` function, `load_device_config()`/`save_device_config()` in full), `server/poll_loop.py` (targeted: both `battery_low_active` sites), `server/plane/calendar_rules.py` (targeted: `_url_is_safe()`, `default_calendar_transport()`, `fetch_ics()` docstring), live `EXPECTED_CHECK_COUNT`/`home_page.` grep counts across all 6 harness files.
**Pattern extraction date:** 2026-09-11
