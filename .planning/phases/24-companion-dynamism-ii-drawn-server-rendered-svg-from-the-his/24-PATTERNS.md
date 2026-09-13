# Phase 24 — Pattern Map

**Purpose:** for every file this phase creates or modifies, the closest existing
analog in this codebase, with the concrete excerpt an executor should copy rather
than re-derive. Nothing in this phase needs a new idiom; four of the five drawings
are variations on an emitter this app already ships.

**Read this before writing any SVG.** Every rule below was paid for once already.

---

## 1. `companion/draw.py` — NEW

**Role:** shared, stdlib-only geometry + emission primitives for every drawing.
**Data flow:** page module → `draw.<emitter>(series, …)` → HTML string → page shell.

### Closest analog: `companion/battery.py` (the whole file, 38 lines)

Copy its *shape*, not its content — a tiny shared module beside `layout.py`, with a
docstring that states its import rules in the file itself:

```python
# Source: companion/battery.py:1-18 (abridged)
"""companion/battery.py — the shared battery-percentage estimate …

This module is stdlib-only. It must never import from the pages package
and nothing from the server package — its whole purpose is to let
home_page.py and health_page.py share one estimate without either
importing the other, and pulling in a page module or a server module
here would defeat that.
"""
```

`draw.py` inherits exactly this rule and must say so in its own docstring. The
reason is enforced structurally by `companion/pages/__init__.py`: **a page module
may never import another page module.**

### Closest analog for the emitters: `health_page.battery_sparkline_svg()`

The two scale functions to lift into `draw.py`, verbatim in behaviour:

```python
# Source: companion/pages/health_page.py (inside battery_sparkline_svg)
def _point_x(index):
    # Spans the full 0-100% width, edge to edge — "the chart fills
    # its card" is a property of this formula, not a tuned margin.
    return index / (point_count - 1) * 100

def _point_y(value):
    clamped = max(SPARKLINE_Y_MIN_MV, min(SPARKLINE_Y_MAX_MV, value))
    return inset + (
        1 - (clamped - SPARKLINE_Y_MIN_MV) / _SPARKLINE_Y_SPAN_MV
    ) * (100 - 2 * inset)
```

Two properties to preserve when generalising:

1. **The range is a constant, never derived from the data.** An out-of-range value
   pins at the edge instead of silently rescaling the axis (D-04/A-22). A scale
   helper that computes its own min/max from the series reintroduces exactly the
   defect this code was rewritten to remove.
2. **`inset` keeps a marker's radius inside the canvas** and its value is derived
   from `line-height: 1.2` on `.sparkline-axis-label` — a CSS number the Python
   arithmetic depends on. Any new label class must declare its line-height for the
   same reason.

---

## 2. `companion/pages/health_page.py` — MODIFIED (plans 24-04, 24-05, 24-07)

**Role:** page module; owns Health's server-rendered markup.

### Analog for axis chrome: filled `<rect>`, never stroked `<line>`

```python
# Source: companion/pages/health_page.py:1300-1320 (abridged)
axis_chrome = (
    '<rect class="%s" x="0" y="0" width="1" height="100%%" aria-hidden="true"/>'
    '<rect class="%s" x="0" y="100%%" width="100%%" height="1" aria-hidden="true"/>'
    '<rect class="%s" x="-4" y="%.2f%%" width="4" height="1" aria-hidden="true"/>'
    …
)
```

The recorded reason (keep it, restate it if you copy it): an axis-aligned
integer-width **filled rect** has no stroke-centring or half-pixel rounding to
reason about, and a rect can pair a **percentage position with an absolute size** —
which no stroked line can, and which this whole coordinate scheme needs.

### Analog for the point loop and paint order

```python
# Source: companion/pages/health_page.py:1332-1345 (abridged)
for index, (value, ts, reading_count) in enumerate(pairs):
    x = _point_x(index)
    y = _point_y(value)
    if prev_x is not None:
        line_segments.append(
            '<line class="%s" x1="%.2f%%" y1="%.2f%%" x2="%.2f%%" y2="%.2f%%"/>' % …)
    prev_x, prev_y = x, y
```

Three things to carry forward:

- **`n-1` `<line>` segments, not a `<polyline>`** — percentages are not permitted
  inside a `points` list. The same constraint binds `<polygon>`, which is why
  D8's area is an open design question in 24-05 rather than an obvious `<polygon>`.
- **Document order is paint order**, and pointer events go to the topmost element;
  the cosmetic marker is emitted immediately before its own hit target.
- **The `(value, ts, …)` pairs are built before filtering**, so a dropped row drops
  its own timestamp and the labels can never describe a point that is not drawn.
  **This is the mechanism CFG-39's contract rule 2 names. Reuse it; do not
  re-derive it.**

---

## 3. `companion/static/style.css` — MODIFIED (every drawing plan)

**Role:** the single stylesheet; the only place a drawing's colour is decided.

### Analog: the `.sparkline*` block (`style.css:5418-5535`)

```css
/* Source: companion/static/style.css:5463-5490 (abridged) */
.sparkline-line { stroke: currentColor; stroke-width: 2; stroke-linecap: round; fill: none; }
.sparkline-axis { fill: var(--color-border); }
.sparkline-dot  { fill: currentColor; pointer-events: none; }
.sparkline-hit  { fill: transparent; cursor: pointer; }
```

**The idiom to copy exactly: `currentColor` + a token.** The SVG inherits `color`
from its container, the container's colour is a theme token, and the drawing is
therefore correct in both themes with no second rule and no media query. A literal
hex in either the CSS or the markup breaks this; so does a shape with no rule at
all, which paints SVG-default black.

Note `fill: none` on `.sparkline-line` — that is the **explicit "deliberately
unfilled"** declaration CFG-39's contract rule 4 requires for stroked shapes. D21's
ring arcs need the same.

### Analog for the label grid (`.sparkline` / `__y` / `__x`)

```css
/* Source: companion/static/style.css:5418-5456 (abridged) */
.sparkline      { display: grid; grid-template-columns: auto minmax(0, 1fr);
                  column-gap: var(--space-sm); row-gap: var(--space-xs); }
.sparkline__y   { grid-column: 1; grid-row: 1; display: flex; flex-direction: column;
                  justify-content: space-between; align-items: flex-end; }
.sparkline__x   { grid-column: 2; display: flex; justify-content: space-between; }
```

This is **the mechanism that makes viewBox-overflow unreachable** for the
time-series drawings: the labels are HTML, outside the SVG, laid out by grid.
`minmax(0, 1fr)` on the canvas column is what lets it shrink to 360 px instead of
forcing an overflow — omitting the `minmax(0, …)` is the classic grid blowout and
would produce exactly the horizontal scrollbar CFG-45 forbids.

### The accent reservation, in the file's own words

```css
/* Source: companion/static/style.css:5505-5516 (abridged) */
/* Deliberately var(--color-text), not var(--color-accent): this file's
 * header comment reserves accent to exactly five uses, and a chart-point
 * highlight is not one of them. */
```

A status-coloured grid cell (24-07) uses the **status** tokens, never accent.

### Hard constraint

`style.css` is pinned at **zero stray comment terminators** by
`companion/test_status_pages.py`. Every new comment goes *inside* a block comment.
A stray `*/` silently dropped a whole rule for four plans once; that check exists
because of it.

---

## 4. `companion/pages/home_page.py` — MODIFIED (plans 24-04, 24-06, 24-08)

**Role:** page module; Home's assembly.

### Analog: `_status_tiles_html()` — how a tile gets its content

```python
# Source: companion/pages/home_page.py (abridged)
reading = _safe_query(ctx.get("state_dir"), _latest_battery)
if reading and reading.get("battery_mv"):
    pct = battery.battery_percent(reading["battery_mv"])
    pct_text = ("≈ %d%%" % pct) if pct is not None else ""
    …
tiles = (
    layout.stat_tile(i18n.t(FRAME_ROW_LABEL), frame_html, device_state, icon="icon-device")
    + layout.stat_tile(i18n.t(BATTERY_ROW_LABEL), battery_html, battery_state, icon="icon-battery")
    + …
)
```

Three constraints this excerpt encodes:

- **Every DB read goes through `_safe_query()`** — a page must render when
  `history.db` is missing or unreadable. A drawing that raises on an absent
  database has broken Home, not just itself.
- **`battery.battery_percent()` is already the shared estimator call.** The ring
  gauge in this tile must take the same value from the same call — never a second
  computation from `battery_mv`.
- **`≈` is already the honesty marker** on this estimate. The gauge must not
  out-claim it.

### `render()`'s assembly order, and what must not come back

```python
# Source: companion/pages/home_page.py:611-617
return (
    header
    + layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE, next_wake_iso=next_wake_iso)
    + _status_tiles_html(ctx)
    + '<div class="home-columns home-picture-row">'
    + _hero_figure_html(ctx, current_flight_row)
    + _recent_flights_html(rows, now, ctx.get("state_dir"))
    + "</div>"
)
```

`_status_tiles_html()`'s docstring records a **fixed bug** that D4 must not
resurrect: the frame verdict appears **exactly once** on this page, and the
phase-20 status-card builder that duplicated it was deleted by 21-04. A hero that
re-renders the verdict reopens it.

Also: **one read, reused** — `rows` is fetched once and feeds both the hero's
current flight and the recent-flights list ("never two independent queries for what
is the same data", D-20). A hero that re-queries breaks the same rule.

---

## 5. `server/history_db.py` — MODIFIED (plan 24-03)

**Role:** the only SQLite access layer; shared by the poll oneshot and the companion.

### Analog: `daily_battery_averages()` — a reader whose row shape is a contract

```python
# Source: server/history_db.py:292-300 (docstring, abridged)
"""One row per Europe/Paris calendar day that has at least one numeric
battery reading, newest day first: {"ts": "YYYY-MM-DD", "battery_mv": <int>,
"reading_count": <int>}.

The key is deliberately named `ts`, not `day` — it makes these rows
structurally interchangeable with recent_device_health()'s rows for
battery_sparkline_svg(), which reads exactly `battery_mv` and `ts` off
whatever it is given. One plotting function, one row contract, no …"""
```

**The lesson to copy:** name the new reader's keys so one emitter can consume both
shapes. A second emitter that exists only because a reader named a key differently
is the avoidable duplication this phase is explicitly guarding against.

### Analog: parameterised `since`, never interpolated

```python
# Source: server/history_db.py:227-243 (abridged)
rows = conn.execute(
    "SELECT route_source, COUNT(*) AS n FROM runway_events WHERE ts >= ? GROUP BY route_source",
    (since,),
).fetchall()
```

Every timestamp bound is a `?` placeholder. No exception.

### Analog: Paris-day bucketing in Python, not SQL

```python
# Source: server/history_db.py:276-291 (abridged)
def _paris_day_or_none(ts):
    """… A naive ts (no UTC offset) is taken as UTC before converting — the
    same assumption SQLite's date() made, so a 2026-09-02T01:30:00+02:00
    reading still buckets to 2026-09-02 in Paris, not 2026-09-01 in UTC."""
```

D13's day band and D20's grid rows are **Paris** days. Reuse this function; a
second date path is how two surfaces on the same page come to disagree.

### The migration fact that settles D20

```python
# Source: server/history_db.py:97-101 (docstring)
"""Create all three tables (and their indexes/constraints) with
IF NOT EXISTS, so both the poll oneshot and the companion service can
call this safely on every connection."""
```

There is **no** `PRAGMA user_version` and **no** `ALTER TABLE` anywhere in the
tree. A brand-new table costs nothing (it is created on next connect by both
processes); a new **column on an existing table** would require inventing this
project's first migration mechanism. That asymmetry is the whole basis of
24-RESEARCH.md's Risk 1 verdict.

---

## 6. The harnesses — MODIFIED (every plan)

**Role:** the executable contract. A check's NAME is its identity.

### Analog: the check idiom

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

```python
# Source: companion/test_status_pages.py:1121-1136 (abridged)
def _staleness_status_boundaries():
    if health_page.staleness_status(warn_s, warn_s, error_s) != "warn":
        return False, "expected warn exactly at the warn threshold"
    …
check("staleness_status() returns ok/warn/error at the right boundaries, "
      "warn for a never-seen signal", _staleness_status_boundaries)
```

Two conventions visible here and binding on every new check:

- **The failure message names the offending thing**, not just "assertion failed".
- **Boundaries are asserted AT the boundary**, not near it. A drawing check that
  only exercises a comfortable series is vacuous — see 24-VALIDATION.md's sampling
  list for the six series shapes each emitter must be asserted against.

### `EXPECTED_CHECK_COUNT`

```python
# Source: companion/test_view_pages.py:464-578 (the tail of the assignment chain)
EXPECTED_CHECK_COUNT = 148
EXPECTED_CHECK_COUNT = 152
```

The file carries the **whole history** as successive assignments, each with a
comment naming the plan and task that moved it. Append a new last assignment;
never edit an earlier one; never compute the new value by arithmetic — **run the
harness and read it**.

### The script pin (touched only if a plan adds a script — none should)

`companion/test_companion_app.py:4398-4477`,
`_fourteen_deferred_scripts_before_closing_body` — currently **fourteen**. Re-read
before assuming; Phase 23's outstanding plans may move it.

---

## 7. `companion/i18n_fr/{home,health}.py` — MODIFIED

**Role:** French parity, enforced by `companion/test_i18n.py` across `app.py`, HTML
attribute literals and JS fallbacks.

Every new caption, `<title>`, `aria-label` and axis label needs its French sibling
in the module for **its own page** — `home.py` and `health.py` are separate files,
so two plans in different waves never collide here.

---

## Anti-patterns this phase must not commit

| Anti-pattern | Why it is wrong here | Do instead |
|---|---|---|
| A second battery percentage computation | Five estimators that disagree is the failure the phase goal names | `companion/battery.py`, always |
| A colour literal in emitted SVG | Correct in one theme only — a defect, not polish | `currentColor` + a theme token via a class |
| A shape with no class and no `fill` | Paints SVG-default black; invisible in dark mode | explicit class, or `fill="none"` + stroked class |
| An `<svg>` with no size route | Renders at the SVG default 300×150 and blows the layout apart (`layout.icon_html()`'s own docstring) | a CSS rule on its class, or intrinsic width/height |
| A scale derived from the data's own min/max | Silently rescales when a reading goes out of range; D-04/A-22 removed exactly this | a constant range, clamp and pin at the edge |
| Labels built from the unfiltered series | Names a value the drawing does not reach | one filtered pair list feeding marks *and* labels |
| `<polyline points="…%">` | Percentages are illegal in a points list | `n-1` `<line>` segments |
| A page module importing another page module | Forbidden by `companion/pages/__init__.py` | put it in `draw.py` / `battery.py` / `layout.py` |
| A new static script to make a drawing correct | Breaks the no-JS floor and needs a new `app.py` route + pin move | server-render it |
| Two writers of one file in one wave | This project's wave rule | serialise the wave |
