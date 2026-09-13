# Phase 26 — Pattern Map

Every file this phase creates or modifies, with the closest existing analog and
the excerpt that settles how it must be written. Read this instead of exploring
the codebase.

**Counting convention, established and easy to get wrong:** there are **16**
`.js` files in `companion/static/` today, but the pin at
`companion/test_companion_app.py:4398` counts **deferred `<script src=>` tags
before `</body>` on the authenticated shell**, which is **14**. Those are
different numbers on purpose — `login-card.js` is login-only and
`battery-trend.js` is page-scoped. `quick-switch.js`'s own comment
(`app.py:220-226`) says it plainly: "the fifteenth static script, and the
fourteenth emitted by `page_shell()`". Phase 25 moves the **shell** pin 14 → 15.
This phase moves it **15 → 16**, once, and re-derives it by RUNNING.

---

## 1. `companion/static/command-palette.js` — NEW (the phase's only new script)

### Closest analog for the file's shape: `companion/static/quick-switch.js` (23-07, the newest)

```js
// Source: companion/static/quick-switch.js:1-28 (abridged)
/*
 * SkyPane companion service — quick-switch.js.
 *
 * D2 (22-AUDIT.md's dynamism half, 23-07-PLAN.md Task 1/2, CFG-36).
 *
 * --- IT IS AN ENHANCEMENT, AND THE FLOOR IS STRUCTURAL ---------------
 *
 * This file creates no control. Every switch it touches is a <form>
 * that already works: ... Delete this file and every switch still posts,
 * still saves, and still lands back on its own page with the server's flash.
 *
 * role="switch" and aria-checked are rendered by the SERVER from the
 * saved value, so the accessible state is correct with scripts blocked
 * too. The role is not a promise this file keeps; it is a description of
 * what the button does either way.
 */
(function () {
  "use strict";
```

**What to copy:** the "IT IS AN ENHANCEMENT, AND THE FLOOR IS STRUCTURAL" section
and its argument form — *delete this file and X still works*. For the palette the
sentence is: **delete this file and every destination the palette offers is still
reachable from the nav, the tab bar and the page it lives on.** That sentence is
what 26-04's blocked-script check makes executable.

**What to copy structurally:** the IIFE + `"use strict"`, the ES5-safe subset (no
`let`/`const`/arrow functions/template literals/backticks — no transpiler is ever
introduced), and the **guard clause first**: look up the dialog, return if it is
absent, return if `showModal` is not a function. Fifteen of sixteen pages are the
"absent" case for most scripts and the guard-clause convention is what makes one
cached asset safe to serve everywhere.

### The `<dialog>` handling to reuse, not re-derive: `panel-lookup.js`

```js
// Source: companion/static/panel-lookup.js:56-62, :316-318
  // A browser with no native <dialog>/showModal() support degrades to no
  // lightbox at all, rather than to a JavaScript error ...
  if (typeof dialog.showModal !== "function") {
    return;
  }
  ...
  // the native <dialog> element already provides Escape-to-
  // close ... UI-SPEC §8.3 chose <dialog> over a hand-rolled overlay <div>.
  // Do not [hand-roll one].
```

**This is the phase's most important reuse.** `showModal()` supplies the focus
trap, the top layer, Escape, and focus restoration on close. A hand-rolled focus
trap in the palette would be re-deriving — badly — something this codebase already
decided and documented.

### The entrance to reuse: the existing `<dialog>` `@starting-style`

```css
/* Source: companion/static/style.css:6220-6299 (abridged) */
/* History lightbox (D-20, §8.3) — a native <dialog> element ...
 * A <dialog> promoted to the top layer via showModal() does [not inherit] ...
 * `@starting-style` is Baseline newly (2024-08-06: Chrome 117, ...) */
@starting-style { ... }
```

Phase 23 added `<dialog>` entrances via `@starting-style`. The palette reuses
**this** block's idiom; it must not invent a third entrance vocabulary beside
`@keyframes skypane-fade-in` / `.is-fading-in` and `skypane-bar-arrive`.

### The three taxes a new script owes (paid once, in 26-01)

```python
# Source: companion/app.py:219-226 — the pattern, repeated 16 times
RELATIVE_TIME_SCRIPT_ROUTE = "/static/relative-time.js"
# 23-07-PLAN.md Task 1 (D2/CFG-36): companion/layout.py's
# QUICK_SWITCH_SCRIPT_SRC must equal this exactly, mirroring every pair
# above — the fifteenth static script, and the fourteenth emitted by
# page_shell(). Pre-auth like every one of them; the file carries no
# session data of any kind and no-ops via its own guard clause ...
QUICK_SWITCH_SCRIPT_ROUTE = "/static/quick-switch.js"
```

```python
# Source: companion/layout.py:223-233 — the mirror constant
QUICK_SWITCH_SCRIPT_SRC = "/static/quick-switch.js"
```

The constant is **duplicated, not imported**, in both directions — that is the
recorded contract, and a harness asserts the two strings are equal. Tax 2 is a
French catalogue entry for every `var ALL_CAPS = "literal"` and `|| "literal"` in
the new file (`test_i18n.py:31-37`). Tax 3 is the public-route smoke check
(`test_companion_app.py:3723`, `_static_script_public`) plus the ES5/forbidden-sink
scan and route==src agreement.

### The `.js` gate — how a script-only affordance avoids rendering as a dead control

```js
// Source: companion/static/nav-dropdown.js:31 — unconditional, first script on the shell
  document.documentElement.className += " js";
```

```css
/* Source: companion/static/style.css:1078 */
.js .mobile-nav { ... }
```

Hide by default, **reveal under `.js`** — never the reverse, which flashes a dead
control on every load and leaves it visible forever when a script fails. The
palette trigger is gated exactly this way. This mechanism is **already shipped**;
this phase depends on the shipped `nav-dropdown.js:31`, not on Phase 25's
restatement of it.

---

## 2. `companion/layout.py` — MODIFIED (26-01 index + trigger + shell, 26-06 `empty_state()`, 26-09 theme-color)

### The ONE nav iteration the palette index must be fed by

```python
# Source: companion/layout.py:1399-1422 (abridged)
def _nav_links(active):
    """Return one (is_active, escaped_route, escaped_label, slug) tuple
    per NAV_TABS entry, in NAV_TABS order.

    This is the single place NAV_TABS is iterated and its route/label
    pair escaped; sidebar_nav() ... and _mobile_nav_html() ... both
    consume this (via _nav_groups() below) instead of re-iterating
    NAV_TABS and re-implementing the same escaping/active-state logic twice.
    """
```

```python
# Source: companion/layout.py:80-100
NAV_GROUPS = (
    ("", ((HOME_ROUTE, "Home"), (DISPLAY_ROUTE, "Display"),
          (FLIGHTS_ROUTE, "Flights"), (AIRLINES_ROUTE, "Airlines"))),
    (ADVANCED_GROUP_LABEL, ((HEALTH_ROUTE, "Health"), (DEVICE_ROUTE, "Device"))),
)
NAV_TABS = tuple(...)
```

22-14 made the bottom tab bar "a third nav rendering fed by the ONE shared
`_nav_links()` iteration". **The palette index is the fourth consumer of that same
iteration** — that is precisely why a palette command cannot point at a
destination the site does not otherwise have.

### The component-builder idiom every new renderer follows

```python
# Source: companion/layout.py:3629-3643 — empty_state(), in full
    if compact:
        return (
            '<div class="empty-state empty-state--compact">'
            '<p class="empty-state__heading text-body">%s</p>'
            '<p class="empty-state__body text-label section-caption">%s</p>'
            "</div>"
        ) % (escape_html(heading), escape_html(body))
    return (
        '<div class="empty-state">'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (escape_html(heading), escape_html(body))
```

`%s` placeholders only — never f-strings, never `.format()`; every caller-supplied
string through `escape_html()`.

### The byte-identity contract any new keyword parameter must honour

```python
# Source: companion/layout.py:3594-3603 (empty_state docstring, abridged)
    `compact` ... is a keyword-with-default whose falsy value returns
    markup that is BYTE-IDENTICAL to what this function returned before
    the parameter existed, matching `stat_tile()`'s own `caption_title`
    and `status_dot()`'s own `visually_hide_label` contract. Every
    full-card caller ... passes two positional arguments and is unaffected.
```

26-06's new `illustration`/`action` parameters take exactly this shape, and the
proof is the one 22-12 already used: capture the six existing call sites' output
before the change and diff it after.

### The already-escaped-markup passthrough contract, for the illustration parameter

```python
# Source: companion/layout.py, page_header() docstring (abridged)
    `freshness_html` and `action_html`, when truthy, are each the
    caller's own already-safe markup and are interpolated verbatim —
    no call to escape_html(), no other transformation. This is the same
    "escape the caption, pass already-built content through verbatim"
    contract stat_tile()'s `content_html` parameter uses; re-encoding
    either of these two here would double-encode already-escaped tags
    and print them as visible text instead of rendering.
```

The illustration parameter carries `draw.py` output and therefore follows the
`*_html` passthrough convention, **including the `_html` suffix in its name** so
the convention is legible at the call site.

---

## 3. `companion/draw.py` — CONSUMED, NOT MODIFIED (26-06)

Created by Phase 24 plan 24-01. Its contract, from that plan:

- stdlib-only; imports no page module and nothing from `server/`
- two differently-named coordinate schemes (percentage for card-filling series,
  user-unit for aspect-locked marks) — **never one helper with a flag**
- one escaping helper; every interpolated string passes through it
- **every shape emitter requires an explicit class name and refuses to emit a
  shape without one** — "a primitive that can emit an unclassed shape is a
  primitive that can emit an invisible one"
- **no colour literal anywhere**: `grep -icE '#[0-9a-f]{3,8}|rgb\(|hsl\(' companion/draw.py` → `0`
- 24-01 Task 3's guard: every class name `draw.py` can emit resolves to at least
  one selector in `style.css`; an unpainted shape fails

**The trap 24-01 records and 26-06 inherits:** `layout.icon_html()`'s docstring
notes that an `<svg>` with neither an attribute nor a CSS size renders at
300×150. An empty-state illustration must carry its own size.

---

## 4. `companion/first_run.py` — NEW (26-05)

### The exact analog: `companion/frame_state.py` — a page-independent, VIEW-FREE module

```python
# Source: companion/frame_state.py:1-30 (abridged)
"""companion/frame_state.py — the one frame-state resolution and the one
delay sentence ...

Sits beside companion/wake.py, companion/i18n.py and companion/screens.py
in this same package — a shared, page-independent, VIEW-FREE module.
"View-free" is load-bearing, not a style preference: this module returns
a state name and a template-key string, never HTML, never a dot-class
string, never formatted clock text. ... This module therefore imports
neither companion.layout nor any companion.pages module, matching
companion/wake.py's and companion/battery.py's own page-independent boundary.
"""
```

`first_run.py` is this module's sibling: it returns **named signal states**, never
HTML, never a CSS class, never a sentence. Home renders the card from those
values.

### The signal that already exists, and names itself

```python
# Source: companion/frame_state.py:156-158 (abridged)
    Degrades to `STATE_UNKNOWN` — never raises — when `next_wake_iso` ...
    fails to parse: exactly the "no check-in recorded yet" [case]
```

"The frame has checked in" is `resolve_state() is not STATE_UNKNOWN`. Do not
invent a second definition of "has the device ever been seen".

### The fail-closed password gate that makes the audit's first checklist item vacuous

```python
# Source: companion/auth.py:153-157 (abridged)
    A missing password must fail closed, never open — companion/app.py
    [depends on this] ... [and the message must never] be re-worded to
    interpolate the configured password.
```

```
# Source: deploy/skypane.env.example:56
SKYPANE_COMPANION_PASSWORD=replace-with-a-long-random-secret
```

The real check is "the configured password is not that literal". Compare in
constant time (`hmac.compare_digest`, as `auth.password_ok()` does at `:186`) and
**never render the configured value or any prefix of it** — `test_companion_app.py`
already pins that `AuthNotConfigured` never leaks it, and this must not become the
first surface that does.

---

## 5. `companion/static/panel-lookup.js` — MODIFIED (26-08, D15)

### The pinned standing constraints that decide the implementation

```js
// Source: companion/static/panel-lookup.js:14-23 (abridged)
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state — it only reads attributes off already-rendered DOM elements and
 * writes them into the dialog's image src/alt, caption textContent, and
 * ... the replace form's action attribute. This file writes to element
 * content only via textContent/src/alt/an attribute value — never via a
 * raw-markup DOM sink of any kind
```

**This is why D15 does not `fetch()` the PNG.** The File is built from the `<img>`
that is already in the DOM via `canvas.drawImage()` + `canvas.toBlob()` — no
network call, no timer, no persistent state, and no raw-markup sink. All three
pins survive, and 26-08 asserts they still hold rather than assuming it.

```js
// Source: companion/static/panel-lookup.js:41-46 (abridged)
 * Standing constraint added by 260902-tli: this script must never
 * decide, from the viewport's dimensions or from the device's reported
 * orientation, whether to open the dialog — that gate belongs entirely
 * in the stylesheet ... The harness pins this by grepping this file's
 * whole source for the two browser APIs such a decision would require.
```

Same shape of pin, same harness technique — 26-08's own "no network call" check
is written as a grep of this file for `fetch(`/`XMLHttpRequest`/`setTimeout`/
`setInterval`, following this precedent exactly.

### The session-gated image route, which does not change

```python
# Source: companion/app.py:2098-2105
    def _serve_gallery_image(self, requested):
        payload = gallery_bytes(self.args.state_dir, requested)
        if payload is None:
            return self.send_html(404, self._not_found_page())
        # This route sits behind do_GET()'s require_session() gate, so it
        # deliberately relies on send_bytes()'s non-shared (private)
        # default rather than opting into shared cacheability.
        return self.send_bytes(200, "image/png", payload, cache_seconds=3600)
```

The download anchor resolves **through this route, through the caller's own
session**. No new route, no gate removed.

---

## 6. `companion/static/style.css` — MODIFIED (26-01, 26-03, 26-05, 26-06, 26-07, 26-08)

Six writers ⇒ six waves for those plans. This is the same serialisation Phase 23
(9 waves / 11 plans), Phase 24 (7/9) and Phase 25 (7/8) each hit, for the same
reason: one writer per file per wave.

### Hard constraints

- `companion/test_status_pages.py` guards **zero stray comment terminators**. Every
  `/*` this phase opens closes exactly once.
- Motion tokens only: `--motion-fast` (180 ms), `--motion-slow` (2 s).
  `interpolate-size` and `calc-size(` are **banned** (Chromium-only).
- **No new `@keyframes`** and **no per-rule `prefers-reduced-motion` block** — the
  global one already covers plain transitions, and a per-rule copy is recorded as
  dead code (Phase 25's own cross-cutting constraint).
- Exactly **one** `@supports selector(:has(*))` block (`test_config_page.py:4002`,
  `:4232`). Nothing in this phase needs `:has()`; if a plan reaches for it, that is
  the signal to re-read the markup instead.

### The paint idiom every drawn surface uses

`currentColor` + a theme token through a CSS class — the `.sparkline*` idiom that
`health_page.battery_sparkline_svg()` established and that 24-01's guard enforces.
A colour literal in an empty-state illustration fails that guard.

---

## 7. The harnesses — MODIFIED (every plan)

### The check idiom

```python
# Source: companion/test_status_pages.py:1093-1102
    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))
```

**The NAME is the identity, never the index.** Every gate in this phase is checked
by name.

### The viewport constants — already named, do not re-introduce literals

```python
# Source: companion/test_browser_ux.py:597-602
VIEWPORT_MIN_SUPPORTED = {"width": 360, "height": 844}
VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_DESKTOP = {"width": 1280, "height": 900}
# Out of contract since 2026-09-13, still measured — see above.
VIEWPORT_WIDTH_NARROW = 320
VIEWPORT_WIDTH_TABLET = 768
```

### The scripts-blocked page — already factored

`context.new_page(java_script_enabled=False)` is used at `test_browser_ux.py:930`,
`:1377` and `:1584`. 26-02 adds no fourth way to make one; it adds the *readers*
this phase needs (focus-restoration, targeted keystroke, announcement text) and
zero net checks — the same zero-net-checks shape 24-02 and 25-02 use.

### `EXPECTED_CHECK_COUNT`

Re-derived by **running**, appended as a NEW last assignment citing the plan and
task — never by arithmetic, never by editing the previous value in place.

### Baseline

Exactly **5** failing checks in this sandbox — 4 × WR-11 (read-only filesystem),
1 × `anomaly_active()` — verified by check **NAME**, never by failing-file count.

---

## 8. `deploy/Caddyfile` — MODIFIED (26-09, D11 gzip)

```
# Source: deploy/Caddyfile — the companion's own site block, in full today
config-203-0-113-10.nip.io {
    reverse_proxy 127.0.0.1:8643

    # Console stream is fine here: the companion interface has no
    # durable-telemetry requirement of its own (unlike the block above) ...
    log {
        output stdout
        format json
    }
}
```

**There is no `encode` directive in either site block.** The directive goes in
**this** block only, scoped to static asset content types, and the device-protocol
block above is left alone — it carries the battery-telemetry access log whose
format `server/history_db.py`'s tailer parses. `deploy/provision.sh` writes this
file with the real IP substituted, so the template and the generator must agree.
