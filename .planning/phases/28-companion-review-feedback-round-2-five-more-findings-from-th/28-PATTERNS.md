# Phase 28: Companion review feedback round 2 - Pattern Map

**Mapped:** 2026-09-15
**Files analyzed:** 5 (companion/pages/config_page.py, companion/static/style.css,
companion/static/value-controls.js, companion/static/theme-preview.js,
companion/layout.py) + 2 test harnesses (companion/test_browser_ux.py,
companion/test_config_page.py). No `companion/test_layout.py` exists —
layout.py's own structural checks (icon sprite integrity, nav toggle) live in
`companion/test_companion_app.py`.
**Analogs found:** 5 / 5 (every file being modified already contains the exact
mechanism this phase must extend — this is an extension/bug-fix phase, not new
architecture)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog (same file, different function) | Match Quality |
|---|---|---|---|---|
| `companion/pages/config_page.py` — Device-page grouping (CFG-72) | server-rendered HTML builder | request-response | `_display_groups_html()` + `_nested_wrapper_html()` (same file, lines 4736-4850) | exact |
| `companion/static/style.css` — no new rule expected for CFG-72 (reuse `.page-section--nested > h2`, line 5703) | CSS | n/a | `.page-section--nested > h2` rule itself | exact (reuse, not new) |
| `companion/pages/config_page.py` — `quiet_dial_readout_html()` (CFG-73) | server-rendered HTML builder | request-response | same function, already exists (lines 3010-3099); needs no structural change, only its docstring's "known limitation" is what JS must stop reproducing | exact |
| `companion/static/value-controls.js` — `paintReadouts()` (CFG-73) | client-side interaction script | event-driven (DOM `input`/`change`/drag) | `numberToField()` (same file, lines 388-399) — the existing minute<->HH:MM codec, currently only applied to the native `<input type="time">` field, never to readouts | role-match (function to extend, not create) |
| `companion/pages/config_page.py` — `_theme_carousel_html()` (CFG-75) | server-rendered HTML builder | request-response | same function (lines 1555-1741); also `_frame_colours_card_html()`'s three call sites (lines 1936-2032) for the `strip_id` per-instance discipline | exact |
| `companion/static/theme-preview.js` — new preview-follows-scroll logic (CFG-75) | client-side interaction script | event-driven (scroll / IntersectionObserver) | `onPagerClick()` / `applyPreviewSrc()` / `showUsage()` (same file, lines 142-341, 395-406) | role-match (new event source, same preview-swap sink) |
| `companion/layout.py` — gear icon + toggle glyph swap (CFG-76) | provider/config (icon sprite registry) | n/a (static markup) | any existing `ICON_DEFS_HTML` `<symbol>` entry, e.g. `icon-power`/`icon-moon` (lines 807-814) | exact |
| `companion/test_browser_ux.py` — new/extended checks for all 4 items | browser-driven test harness | request-response (Playwright-driven) | `_assert_surfaces_agree`, `_quiet_arc_minutes`, `_quiet_caption_minutes`, `_commit_field`, `_wait_for_save_status`, `_login`, `_keying_the_strip_selects_scrolls_into_view_and_moves_the_preview` (same file) | exact |
| `companion/test_config_page.py` — no direct analog found for CFG-72/73/75 server-render assertions (grep for `_nested_wrapper_html`/`quiet_dial_readout_html` in this file returned nothing) | server-render unit test | request-response | n/a — these are currently proven only at the browser-harness level, not the page-module unit-test level | no analog (see "No Analog Found" below) |

## Pattern Assignments

### CFG-72 — Title unification (Device cards must match Display's nested-supersection title style)

**Analog:** `_nested_wrapper_html()` + `_display_groups_html()`, `companion/pages/config_page.py` lines 4736-4850, and the Device-scope render branch, lines 5218-5258.

**The wrapper helper itself (lines 4736-4759), copy verbatim, do not reinvent:**
```python
def _nested_wrapper_html(html_fragment, base_class, nested_class):
    """... `nested_class` is passed as a literal string by every call
    site (never derived from `base_class` at runtime) ...
    """
    needle = 'class="%s"' % base_class
    replacement = 'class="%s %s"' % (base_class, nested_class)
    return html_fragment.replace(needle, replacement, 1)
```

**A real Display-page call site (lines 4819-4821) — the exact idiom to replicate for each Device card:**
```python
runway_html = (
    _nested_wrapper_html(builders[screens.GROUP_RUNWAY](), "theme-status", "theme-status--nested")
    if screens.GROUP_RUNWAY in groups else "")
```

**The supersection heading helper this pairs with (`companion/layout.py` lines 3783-3817), and Display's own heading/intro constants to model new Device groupings' tone after (`companion/pages/config_page.py` lines 158-168):**
```python
def section_intro_html(section_id, heading, description):
    return (
        '<div class="section-intro">'
        '<h2 id="%s" class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "</div>"
    ) % (escape_html(section_id), escape_html(heading), escape_html(description))
```
```python
DISPLAY_LOOK_HEADING = "Look"
DISPLAY_LOOK_INTRO = ("— the theme, flight colours and calendar that decide how the picture looks.")
DISPLAY_WATCHES_HEADING = "What it watches"
DISPLAY_WATCHES_INTRO = "— which Orly runway the frame is watching."
DISPLAY_ON_HEADING = "When it is on"
DISPLAY_ON_INTRO = "— when the screen is lit and when it stays quiet."
```

**What Device currently does — CONFIRMED there is NO grouping/supersection concept on Device at all (lines 5244-5254):**
```python
# 20-07-PLAN.md Task 1 (D-10): Device's own advanced_groups no
# longer includes GROUP_DISPLAY/GROUP_QUIET_HOURS at all ...
groups_html = "".join(builders[g]() for g in groups if g in builders)
```
Device's three cards (LED — `screens.GROUP_LED`, Wake interval —
`screens.GROUP_WAKE_INTERVAL`, Notifications — `screens.GROUP_NOTIFICATIONS`,
all built via the same `builders` dict at lines 5099-5125 that Display also
reads from) are flat-joined with no `_nested_wrapper_html()` call and no
`section_intro_html()` heading at all — this is the exact gap CFG-72 names.
The three builder functions themselves (`led_group()`, `wake_interval_group()`,
`notifications_group()`) are untouched by this phase; only the wrapping at the
Device `render()` branch changes, mirroring `_display_groups_html()`'s shape
(a small helper function, e.g. `_device_groups_html(builders, groups)`,
returning a joined string of `section_intro_html(...) + _nested_wrapper_html(builder(), "theme-status", "theme-status--nested")` per new grouping) rather than
inventing a second wrapper mechanism.

**CSS rule to leave untouched — it already produces the target 16px/600/sans
render, it is the render-time verification target, not something to edit
(`companion/static/style.css` lines 5690-5711):**
```css
.page-section--nested > h2,
.battery-trend-section > h2,
.theme-status--nested > h2 {
  font-family: var(--font-ui);
  font-size: var(--font-body-size);
  font-weight: var(--weight-semibold);
  letter-spacing: normal;
  margin-bottom: var(--space-md);
}
```
Note the selector list: Device's three cards render via the `.theme-status`
wrapper class (same as Runway/Quiet hours), so the modifier to add is
`theme-status--nested`, matching `--nested_wrapper_html(..., "theme-status", "theme-status--nested")` verbatim — NOT `page-section--nested` (that modifier
is for `.page-section`-wrapped cards like Frame colours/Calendar, a different
base class).

**Verification pattern (getComputedStyle-based, cross-page comparator) — no
existing helper compares two pages' computed styles side by side; the closest
structural analog is the theme-probe helper `companion/test_browser_ux.py`
lines 1250-1265** (build a small JS probe returning `{fontSize, fontWeight,
fontFamily}` per heading selector, call it once per page, assert equality —
follow this shape rather than reusing it directly, since its subject
(`data-ui-theme` on `<body>`) is unrelated):
```python
_THEME_PROBE = (
    "args => {"
    "  const html = document.documentElement;"
    "  const sampled = {};"
    "  const read = () => {"
    "    const s = getComputedStyle(document.body);"
    "    return {canvas: s.backgroundColor, text: s.color,"
    "            attr: html.getAttribute('data-ui-theme')};"
    "  };"
    "  args.themes.forEach(t => {"
    "    html.setAttribute('data-ui-theme', t);"
    "    sampled[t] = read();"
    "  });"
```

---

### CFG-73 — Quiet-hours dial readout format (HH:MM + live duration on every interaction)

**Analog:** `quiet_dial_readout_html()`, `companion/pages/config_page.py` lines
3010-3099 (server side, correct and untouched), and `paintReadouts()` /
`numberToField()`, `companion/static/value-controls.js` (client side, the bug).

**The server's existing HH:MM formatting is NOT a separate helper function —
`start_hm`/`end_hm` arrive already as `"HH:MM"` strings** (they are the raw
`device_cfg.get("quiet_hours_start"/"quiet_hours_end")` values, validated
elsewhere), and are substituted directly, escaped, into the readout template
(lines 3082-3099):
```python
return (
    '<p class="time-value %s" aria-hidden="true">'
    '<span %s="quiet_hours_start" %s="%s">%s</span>'
    ' → '
    '<span %s="quiet_hours_end" %s="%s">%s</span>'
    ' · '
    '<span %s="quiet_hours_start" %s="" %s="%d">%s</span>'
    "</p>"
) % (
    escape_html(QUIET_DIAL_READOUT_CLASS),
    layout.VALUE_CONTROL_READOUT_ATTR, layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
    escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(start_hm),
    layout.VALUE_CONTROL_READOUT_ATTR, layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
    escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(end_hm),
    layout.VALUE_CONTROL_READOUT_ATTR, layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
    layout.VALUE_CONTROL_READOUT_BASE_ATTR, quiet_window_minute_of_day(start_hm),
    escape_html(layout.duration_text(span.minutes * 60)),
)
```
The duration itself comes from `layout.duration_text(seconds, lang=None)`
(`companion/layout.py` line 1156) — this app's ONE length-of-time ladder,
already reused correctly; do not invent a second one in JS.

**THE ACTUAL BUG, confirmed by direct code read: `value-controls.js` has NO
minute-to-HH:MM converter for readouts at all.** `paintReadouts()` (lines
489-510) calls `readoutQuantity()` (lines 473-483), which does only a
scale-divide and writes the raw number as text:
```javascript
function readoutQuantity(readout, value) {
  var scale = numberOrNull(readout.getAttribute(READOUT_SCALE_ATTR));
  if (scale === null || scale <= 0) {
    return value;
  }
  return Math.ceil(value / scale);
}

function paintReadouts(wrapper, value) {
  var name = wrapper.getAttribute(FIELD_ATTR);
  ...
  for (var i = 0; i < readouts.length; i++) {
    var readout = readouts[i];
    var template = readout.getAttribute(READOUT_TEXT_ATTR);
    ...
    readout.textContent = template.split(TEXT_TOKEN).join(
      String(readoutQuantity(readout, value)));
  }
}
```

**The converter that DOES already exist — `numberToField()` (lines 388-399) —
is the one to reuse/port, currently applied only to the native `<input
type="time">` field, never to a readout:**
```javascript
function isClockFormat(wrapper) {
  return wrapper.getAttribute(FORMAT_ATTR) === "clock";
}

function numberToField(wrapper, value) {
  if (!isClockFormat(wrapper)) {
    return String(value);
  }
  var whole = Math.max(0, Math.round(value));
  var hours = Math.floor(whole / MINUTES_PER_HOUR) % HOURS_PER_DAY;
  var minutes = whole % MINUTES_PER_HOUR;
  return (hours < 10 ? "0" : "") + hours + ":" + (minutes < 10 ? "0" : "") + minutes;
}
```
`VALUE_CONTROL_FORMAT_ATTR`/`VALUE_CONTROL_FORMAT_CLOCK` (`companion/layout.py`
lines 304-305, `data-value-format="clock"`) is the existing server-rendered
attribute that already marks the quiet-hours wrapper as clock-formatted
(emitted at `quiet_dial_handles_html()`'s handle-wrapper markup,
`companion/pages/config_page.py` line 2992-2993). The planner's fix is almost
certainly: give `paintReadouts()` (or a new sibling function) access to
`isClockFormat`-equivalent logic scoped to the READOUT (readouts are found by
field name via `document.querySelectorAll`, not by wrapper containment — see
`READOUT_ATTR`'s own comment, lines 213-217 — so the clock-format signal has
to reach the readout element itself, e.g. a new `data-value-readout-format`
attribute mirroring `FORMAT_ATTR`'s existing idiom, or a lookup back to the
wrapper via `fieldFor`-style resolution) and call `numberToField`-equivalent
zero-padding logic instead of `String(readoutQuantity(...))` for clock-format
readouts.

**Server-side duration on interaction is the harder half — there is currently
NO client-side duration computation at all, by design** (lines 3058-3078,
`quiet_dial_readout_html()`'s own docstring): the duration span's readout
carries `layout.VALUE_CONTROL_READOUT_TEXT_ATTR=""` (an EMPTY template, on
purpose, so `paintReadouts()` always blanks it). CFG-73 requires this to
change to a LIVE, correct duration on every interaction — this is new
client-side arithmetic (duration = wrapped difference between the two paired
minute-of-day values already available via the CFG-62 pair seam,
`PAIR_ATTR`/`PAIR_PROPERTY_ATTR`, lines 263-264 and `paintSweep()` lines
536+), not a port of an existing function. `layout.duration_text()`'s own
COARSE-ladder wording ("names the largest unit that fits") is the one
duration vocabulary this app has; if it needs to be spoken from JS, port its
exact ladder rather than inventing a second one — read `companion/layout.py`
lines 1156+ before writing this.

**Test harness — the CURRENT decoder actively encodes the bug as expected
behavior and MUST be rewritten, not merely extended** (`companion/test_browser_ux.py` lines 3215-3268):
```python
# Any run of digits, for the caption's own text — 27-02-PLAN.md Task 3's
# own design (see quiet_dial_readout_html()'s docstring): the two
# endpoint spans substitute value-controls.js's paintReadouts() raw,
# UNCONVERTED value — the same minute-of-day number the handles publish
# ... So the LIVE caption (after any interaction) reads
# like "480 → 1080 · ", and this decoder reads it exactly that way ...
def _quiet_caption_minutes(page, where, selector=None):
    ...
    numbers = _CAPTION_NUMBER_RE.findall(text)
    ...
    return (int(numbers[0]) % MINUTES_PER_DAY, int(numbers[1]) % MINUTES_PER_DAY)
```
Once CFG-73 ships, the live caption will read `"08:00 → 18:00 · 10h"`
(HH:MM, not raw minutes), so `_CAPTION_NUMBER_RE = re.compile(r"\d+")`
naively re-applied would misparse `"08:00"` into digit runs `0`, `8`, `0`,
`0` instead of one HH:MM token — this decoder's regex and unpacking logic
need to change to parse `HH:MM` pairs, and this is exactly the kind of
"relationship, not endpoint" rewrite `_assert_surfaces_agree()` (lines
2872-2957) already composes with — reuse `_assert_surfaces_agree` unchanged
once `_quiet_caption_minutes` speaks the new format; do not touch
`_assert_surfaces_agree`, `_quiet_arc_minutes`, or `_fraction_pair_minutes`
themselves (unrelated surfaces, still correct).

---

### CFG-75 — Theme carousel preview-follows-scroll

**Analog:** `_theme_carousel_html()`, `companion/pages/config_page.py` lines
1555-1741 (server markup), and `theme-preview.js`'s pager/selection handlers,
lines 142-341 and 395-406 (client script).

**`strip_id`-per-instance discipline (27-07, MUST be preserved for any new
preview-tracking attribute) — three real call sites, each with its own id
(lines 1936-1937, 1991-1992, 2024-2025, and the carousel calls at 1969, 1999, 2032):**
```python
departures_grid_attr = 'role="radiogroup" aria-labelledby="%s" id="%s"' % (
    escape_html(FRAME_COLOURS_HEADING_ID), escape_html(THEME_CAROUSEL_STRIP_ID))
...
departures_carousel = _theme_carousel_html(departures_grid, THEME_CAROUSEL_STRIP_ID)
...
arrivals_carousel = _theme_carousel_html(arrivals_grid, THEME_CAROUSEL_STRIP_ID_ARRIVALS)
...
calendar_carousel = _theme_carousel_html(calendar_grid, THEME_CAROUSEL_STRIP_ID_CALENDAR)
```
```python
THEME_CAROUSEL_STRIP_ID = "theme-carousel-strip"
THEME_CAROUSEL_STRIP_ID_ARRIVALS = THEME_CAROUSEL_STRIP_ID + "-" + COLOUR_USAGE_ARRIVALS
THEME_CAROUSEL_STRIP_ID_CALENDAR = THEME_CAROUSEL_STRIP_ID + "-" + COLOUR_USAGE_CALENDAR
```
Any new preview-tracking DOM state (e.g. an IntersectionObserver instance per
strip) must be keyed the same way — built once per `strip_id`, in a loop over
`card.querySelectorAll("[role=radiogroup]")`-equivalent, exactly as the
existing pager wiring at line 408 already loops
`card.querySelectorAll("[" + PAGER_ATTR + "]")` rather than hardcoding three
call sites in the script.

**Current pager-click scroll mechanism (`companion/static/theme-preview.js`
lines 377-406) — what to model the NEW scroll-listener setup on for finding
"which strip", but note it does NOT currently touch the preview at all:**
```javascript
function pagerStep(strip) {
  var chip = strip.querySelector(".theme-chip");
  var gap;
  if (!chip) {
    return strip.clientWidth;
  }
  gap = parseFloat(getComputedStyle(strip).columnGap);
  if (isNaN(gap)) {
    gap = 0;
  }
  return chip.getBoundingClientRect().width + gap;
}

function onPagerClick(evt) {
  var button = evt.currentTarget;
  var strip = document.getElementById(button.getAttribute("aria-controls"));
  if (!strip) {
    return;
  }
  if (button.getAttribute(PAGER_ATTR) === "prev") {
    strip.scrollLeft -= pagerStep(strip);
  } else {
    strip.scrollLeft += pagerStep(strip);
  }
}

var pagers = card.querySelectorAll("[" + PAGER_ATTR + "]");
var pagerIndex;
for (pagerIndex = 0; pagerIndex < pagers.length; pagerIndex++) {
  pagers[pagerIndex].addEventListener("click", onPagerClick);
}
```

**How "selection" is currently represented, and exactly what a new "preview"
state must and must not touch:**
- The theme radio: `<input type="radio" name="theme">` (or `colour_usage`-
  scoped equivalents), each wrapped in a `<label class="theme-chip" data-preview-src="...">` (`companion/pages/config_page.py` line ~1499).
- The live preview `<img class="theme-live-preview__image">` — its `src` is
  driven EXCLUSIVELY by `applyPreviewSrc(src)` (lines 142-180), itself called
  only from `showUsage()` (on usage-panel switch, line 272) and the delegated
  `card.addEventListener("change", ...)` listener (lines 314-341) that reads
  `chip.getAttribute("data-preview-src")` off the CHECKED radio's own parent
  label:
```javascript
card.addEventListener("change", function (evt) {
  var input = evt.target;
  if (!input || input.type !== "radio") {
    return;
  }
  if (input.name === "colour_usage") {
    showUsage(input.value);
    return;
  }
  var chip = input.parentNode;
  if (!chip || !chip.getAttribute) {
    return;
  }
  var isThemeChip = chip.className && chip.className.indexOf("theme-chip") !== -1;
  var src = chip.getAttribute("data-preview-src");
  if (!src && isThemeChip) {
    src = checkedChipSrc(departuresPanel());
  }
  applyPreviewSrc(src);
});
```
- CFG-75's new "preview-follows-scroll" state must call the SAME
  `applyPreviewSrc(src)` sink (never write `.src`/`setAttribute("src", ...)`
  directly a second way — that would create two preview-swap code paths) with
  the `data-preview-src` of whichever chip an IntersectionObserver/scroll
  handler determines is centered — but must NEVER call `input.checked = true`
  or dispatch a `change` event on the radio, since that would (wrongly) also
  fire `showUsage`/persist selection. This is the one clean separation point:
  reuse `applyPreviewSrc`, do not reuse or extend the `change` listener itself
  for scroll-driven preview.
- CSP note already on record and load-bearing here: `applyPreviewSrc` only
  ever calls `preview.setAttribute("src", ...)` with a server-rendered
  `data-preview-src` value already present in the DOM — never
  `URL.createObjectURL()` — so the new scroll-preview code has a ready-made,
  CSP-compliant sink; it needs no new mechanism for the swap itself, only a
  new trigger (scroll/IntersectionObserver) and a new "find the centered
  chip's `data-preview-src`" read.

**Existing browser-harness precedent for driving/asserting carousel scroll
state (`companion/test_browser_ux.py` lines 13382-13530,
`_keying_the_strip_selects_scrolls_into_view_and_moves_the_preview`)** — the
closest existing check to model CFG-75's new scroll-driven-preview check on,
though it currently drives selection via keyboard/native radiogroup, not raw
scroll:
```python
box = page.evaluate(
    "sel => {"
    "  const s = document.querySelector(sel);"
    "  const a = document.activeElement;"
    "  const chip = a.closest ? a.closest('.theme-chip') : null;"
    "  if (!chip) return {error: 'no-chip'};"
    "  const c = chip.getBoundingClientRect();"
    "  const r = s.getBoundingClientRect();"
    "  return {left: c.left - r.left, right: r.right - c.right,"
    "          value: a.value, scrollLeft: s.scrollLeft};"
    "}", THEME_STRIP_SEL)
...
preview = page.eval_on_selector(
    THEME_PREVIEW_SEL,
    "el => [el.getAttribute('src'),"
    "       parseFloat(getComputedStyle(el).opacity)]")
```
and the pager check's direct `scrollLeft` manipulation pattern (lines
13494-13516) is the pattern to extend for "dispatch real scroll events across
several intermediate positions" (CFG-75's own verification requirement):
```python
paged = page.evaluate(
    "sels => {"
    "  const s = document.querySelector(sels.strip);"
    "  ..."
    "  s.scrollLeft = 0;"
    "  ..."
    "  document.querySelector(sels.next).click();"
    "  const forward = s.scrollLeft;"
    "  ..."
    "}", {...})
```
A new check should set `s.scrollLeft` to several intermediate values (not a
jump straight to the end), dispatch a real `scroll` event after each
(`s.dispatchEvent(new Event('scroll'))`, or better, drive it via
`s.scrollTo({left: x, behavior: 'instant'})` if the IntersectionObserver
implementation is threshold-based and needs a real layout settle), and after
each assert the preview `<img src>` matches whichever chip's bounding box is
now geometrically centered in the strip — following `_assert_surfaces_agree`'s
own "assert relationships, not endpoints" discipline (do not merely assert a
scroll listener is attached).

---

### CFG-76 — Mobile hamburger to gear icon

**Analog:** `ICON_IDS` + `ICON_DEFS_HTML`, `companion/layout.py` lines
632-822ish, and the toggle button render site, lines 2415-2420.

**Icon registry pattern — every icon is an inline `<symbol>` in one shared
sprite, referenced by a whitelist tuple (`ICON_IDS`) that a test asserts is in
1:1 correspondence with the sprite's own symbol ids. Two example existing
entries, chosen for simplicity of stroke count (closest visual weight to a
new gear glyph), lines 807-814:**
```python
'<symbol id="icon-power" viewBox="0 0 20 20" fill="none" '
'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
'<path d="M10 3v7"/><path d="M6 6a6 6 0 1 0 8 0"/>'
"</symbol>"
'<symbol id="icon-moon" viewBox="0 0 20 20" fill="none" '
'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
'<path d="M16 12.5A7 7 0 0 1 7.5 4a7 7 0 1 0 8.5 8.5z"/>'
"</symbol>"
```
The whitelist entry itself, appended (never reordered — every prior append in
this file follows the same "appended, not reordered" comment convention,
lines 678-704):
```python
ICON_IDS = ICON_IDS + (
    "icon-more",
)
```
A new `"icon-gear"` (or similar) entry should be appended the same way, as its
own trailing tuple-concat, with a one-line comment stating the old/new
`ICON_IDS` member count (currently 22 — see below) exactly like every prior
append's comment does.

**The toggle's render site — ONLY the icon id argument changes, nothing else
(`companion/layout.py` lines 2415-2420):**
```python
toggle_html = (
    '<button type="button" id="%s" class="site-nav-toggle" '
    'aria-label="%s" aria-expanded="false" aria-controls="%s">%s</button>'
) % (
    NAV_TOGGLE_ID, escape_html(i18n.t(NAV_TOGGLE_LABEL)), MOBILE_NAV_ID,
    icon_html("icon-hamburger", size=24))
```
Change `icon_html("icon-hamburger", size=24)` to
`icon_html("icon-gear", size=24)` (or whatever id is chosen) — this is the
ONLY line in `_mobile_nav_html()` that changes for CFG-76. `NAV_TOGGLE_LABEL`
(line 147, `"Account and preferences"`) and everything else in
`_mobile_nav_html()` (the panel body, lines 2348-2444+) is explicitly
untouched per CONTEXT.md.

**CRITICAL for the planner: `ICON_IDS` currently has exactly 22 members, and
a test hard-codes that count** — adding a member without updating this test
will fail it, not silently pass (`companion/test_companion_app.py` lines
2283-2313):
```python
def _icon_sprite_integrity():
    ...
    if len(layout.ICON_IDS) != 22:
        return False, "expected exactly twenty-two ICON_IDS, got %d" % len(layout.ICON_IDS)
    if len(set(layout.ICON_IDS)) != 22:
        return False, "expected ICON_IDS to have no duplicates"
    ...
    if sorted(symbol_ids) != sorted(layout.ICON_IDS):
        return False, "sprite symbol ids %r do not match ICON_IDS %r" % (
            symbol_ids, layout.ICON_IDS)
```
This count must be bumped to 23 (and the check's own comment/message text
referring to "twenty-two" updated to "twenty-three") as part of this phase's
`companion/test_companion_app.py` edit — note this file is NOT in the
originally-named file list for this phase (config_page.py, style.css,
value-controls.js, theme-preview.js, layout.py, test_browser_ux.py,
test_config_page.py) but IS a required edit; the planner should add it
explicitly.

---

### Test harness helper signatures to reuse (all `companion/test_browser_ux.py`)

```python
def _login(page, base_url):
    """Drive the real login form through the UI ..."""

def _wait_for_save_status(page, which, timeout=5000):
    """Waits, via wait_for_function (never a sleep), for the save-status
    region to hold the word its OWN data-save-status-{which} attribute
    names — "saving" or "saved"."""

def _commit_field(page, selector):
    """Fires the real `change` event dirty-state.js's own document-level
    listener is waiting for — for the Playwright `.fill()` shape."""

def _assert_surfaces_agree(page, surfaces, requested, before, where):
    """Decode N rendered surfaces into ONE canonical value and assert
    they agree, that the agreed value is the one the interaction
    REQUESTED, and that it DIFFERS from the pre-interaction value.
    `surfaces` is an ordered {label: zero-arg-callable} mapping.
    Returns {label: decoded} on success; raises AssertionError naming
    which of 3 distinct failure modes occurred."""

def _quiet_arc_minutes(page, where, selector=_QUIET_ARC_SELECTOR, radius=None):
    """The quiet-hours arc, read back off what the browser PAINTED
    (resolved stroke-dasharray + transform matrix), as (start_minute,
    end_minute). UNTOUCHED by this phase — still correct."""

def _quiet_caption_minutes(page, where, selector=None):
    """The quiet-hours caption text, decoded to (start_minute,
    end_minute) ints. MUST BE REWRITTEN for CFG-73 — its docstring
    currently documents parsing RAW MINUTES ("480 -> 1080") as the
    correct/expected live-interaction reading; post-fix the live
    caption reads HH:MM and this decoder's regex/unpacking must change
    to match, while keeping the same (start_minute, end_minute)
    canonical return shape so `_assert_surfaces_agree` composes with it
    unchanged."""
```

No existing IntersectionObserver-adjacent test helper exists in this file —
CFG-75's verification is new. The closest structural precedent is
`_keying_the_strip_selects_scrolls_into_view_and_moves_the_preview`
(lines 13382-13530, full excerpt above) for both "read the currently-centered
chip via getBoundingClientRect" and "read the live preview's resolved `src`
and `opacity`" idioms, and the pager-click scrollLeft-manipulation block
(lines 13494-13516) for "drive the strip's scroll position directly via
`page.evaluate`, across intermediate positions."

## Shared Patterns

### Escaping
**Source:** every HTML-emitting function in `companion/pages/config_page.py`
uses `escape_html(...)` on every interpolated string, unconditionally — see
`_nested_wrapper_html()`'s docstring note that `nested_class` is a call-site
literal never derived at runtime, and `quiet_dial_readout_html()`'s "escaped
once, after formatting" convention.
**Apply to:** any new heading/label text added for CFG-72's Device
groupings, and any new gear-icon `aria-label` text if one differs from
`NAV_TOGGLE_LABEL` (it should not — CONTEXT.md requires the label stay
unchanged).

### No inline script / CSP
**Source:** `companion/layout.py`'s CSP comment block (referenced throughout
`theme-preview.js`'s own header, lines 21-30) — `script-src 'self'`, no
`on*` attributes, no `URL.createObjectURL()`. `theme-preview.js`'s own rule:
"the only DOM writes this file ever makes are one `<img>`'s `src` (always
from a server-rendered `data-preview-src` attribute) and a class-list toggle."
**Apply to:** CFG-75's new scroll-preview logic (extend `theme-preview.js`,
do not add a new `<script>` file — the deferred-script pin count is tracked,
per CONTEXT.md's own canonical-refs section) and CFG-73's readout fix
(extend `value-controls.js`).

### ES5-safe, no-dependency static JS
**Source:** `theme-preview.js`'s header comment: "var-only declarations, no
arrow functions, no template-literal syntax... no build step, no bundler, no
framework." The same constraint applies to `value-controls.js` (see its own
`writeValue`/`numberToField` style — all `var`, no arrow functions).
**Apply to:** every new function added to `value-controls.js` and
`theme-preview.js` in this phase.

### Mutation-testing / EXPECTED_CHECK_COUNT discipline
**Source:** ROADMAP.md's Phase 28 entry: "every new check must assert
relationships, not just endpoints... Mutation-test every new check, with the
failure message quoted... `EXPECTED_CHECK_COUNT` re-derived by running."
**Apply to:** every new check added to `companion/test_browser_ux.py` and
`companion/test_config_page.py` this phase.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `companion/pages/config_page.py` — new `_device_groups_html()`-equivalent function for CFG-72 | server-rendered HTML builder | request-response | No prior grouping mechanism exists on the Device scope at all (confirmed: `groups_html = "".join(builders[g]() for g in groups if g in builders)`, a flat join with no headings) — this is new code, modeled on `_display_groups_html()`'s shape but not a literal port, since Device's grouping labels are new (Claude's Discretion per CONTEXT.md) |
| `companion/static/value-controls.js` — live client-side duration computation for CFG-73 | client-side interaction script | event-driven | The duration readout's template is currently deliberately EMPTY (`VALUE_CONTROL_READOUT_TEXT_ATTR=""`) specifically so no client-computed duration sentence can ever appear — CFG-73 requires inverting this design decision; there is no existing "compute a coarse duration ladder in JS" code anywhere to copy from (`layout.duration_text()` is server-side Python only) |
| `companion/static/theme-preview.js` — IntersectionObserver-based "centered chip" detection for CFG-75 | client-side interaction script | event-driven (scroll) | No IntersectionObserver usage exists anywhere in the companion static JS tree today (grep confirmed 0 hits) — CFG-75 introduces this mechanism from scratch, though it must reuse the existing `strip_id`-per-instance loop shape and the existing `applyPreviewSrc()` sink |
| `companion/test_companion_app.py` — icon count bump for CFG-76 | test | n/a | Not one of the originally-named phase files but is a required edit (`_icon_sprite_integrity`'s hard-coded `22`) — flagged here since the planner may otherwise miss it |

## Metadata

**Analog search scope:** `companion/pages/config_page.py`,
`companion/layout.py`, `companion/static/style.css`,
`companion/static/value-controls.js`, `companion/static/theme-preview.js`,
`companion/test_browser_ux.py`, `companion/test_config_page.py`,
`companion/test_companion_app.py`
**Files scanned:** 8 (all read via targeted `Read`/`Grep`, no full-file loads
— every file here is well over 2,000 lines; all reads were non-overlapping
targeted ranges located via `Grep` first)
**Pattern extraction date:** 2026-09-15
