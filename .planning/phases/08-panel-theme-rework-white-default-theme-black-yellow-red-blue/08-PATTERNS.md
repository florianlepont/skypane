# Phase 8: Panel theme rework - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** 4 (all modified, none new)
**Analogs found:** 4 / 4 (self-referential — every change is a small, targeted
edit to an existing, well-established registry/module; the "analog" for each
edit is the existing sibling entry/call-site in the same file, not a
different file)

There is no RESEARCH.md for this phase (research skipped — spike
`.planning/spikes/001-panel-theme-colours/` already validated every decision
against real renders). This PATTERNS.md is sourced entirely from the current
state of the four target files plus the spike/manifest.

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `server/device_config.py` | config (registry dict) | CRUD (dict entries) | Existing `THEMES["sky"]` entry / `RUNWAYS` dict (same file) | exact — literally the same dict shape, add sibling entries |
| `server/plane/render.py` (font constants + `_paint_text_backing`) | component/renderer (drawing pipeline) | transform (canvas paint) | Existing font-role constant block + existing `_paint_text_backing()` call sites | exact — same file, same established pattern, mechanical substitution/removal |
| `server/plane/render.py` (`_flight_line1_text`, `draw_main_text_block`, `draw_previous_text_block`) | component/renderer (text-layout logic) | transform (text content → positioned glyphs) | Existing `_flight_line2_text()`'s fallback-ladder style (already handles a multi-tier "what do we know" decision) | role-match — `_flight_line2_text()` is the best in-file precedent for a tiered content fallback with a single `ROUTE_FALLBACK_TEXT` floor |
| `server/plane/enrich.py` (`_parse_route`, `lookup_route`, `_route_from_entry`) | service (external-data normalisation) | CRUD (parse → cache-write → cache-read, both symmetric) | Existing `origin_iata`/`destination_iata` field threading through the same three functions | exact — `callsign_iata` is a new field of the identical shape already threaded for `origin_iata`/`destination_iata` |
| `server/assets/fonts/VENDOR.md` | doc/config (provenance record) | N/A (static doc) | Existing "Supersession (Phase 3...)" note under the Zilla Slab / Inter entries in the same file | exact — same file, same section pattern, just a new instance for PT Serif Regular |

## Pattern Assignments

### `server/device_config.py` — `THEMES` registry (D-01/D-02/D-03/D-04)

**Analog:** the existing `"sky"` entry (same file, lines 71-78) plus the
module's own stated rule at lines 20-24 ("Adding a theme... append one entry
to `THEMES` keyed by [id]... no structural change to this module and no
call-site change anywhere else is required").

**Current state** (lines 48-78):
```python
from server.panel_format import IDX_BLUE, IDX_GREEN, IDX_WHITE

DEFAULT_THEME_ID = "sky"
DEFAULT_RUNWAY_ID = "3"
DEFAULT_LED_ENABLED = True

# --- Theme registry ----------------------------------------------------
THEMES = {
    "sky": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_GREEN,
        "ink_index": IDX_WHITE,
        "label": "Sky (default)",
    },
}
```

**Pattern to copy:** each new entry is a flat dict with the same four keys
(`departing_index`, `arriving_index`, `ink_index`, `label`); `departing_index
== arriving_index` for every new single-colour theme (unlike `"sky"`, which
intentionally differs). `THEME_IDS = tuple(THEMES)` (line 107) and
`normalise_theme_id()` (lines 117-126) already derive from the dict — no
call-site changes needed anywhere else, confirmed by the module's own D-09
comment (lines 20-24) and by CONTEXT.md's `code_context` section.

**Required import change:** add `IDX_BLACK, IDX_YELLOW, IDX_RED` to the
existing `from server.panel_format import IDX_BLUE, IDX_GREEN, IDX_WHITE`
line (line 48) — `panel_format.py` (lines 74-79) already defines all six as
`IDX_BLACK = 0`, `IDX_WHITE = 1`, `IDX_YELLOW = 2`, `IDX_RED = 3`,
`IDX_BLUE = 4`, `IDX_GREEN = 5`; no new constants to define.

**Concrete new entries to add** (per D-01/D-02/D-04, values not text —
exact ids/labels are locked by CONTEXT.md):
```python
THEMES = {
    "white": {
        "departing_index": IDX_WHITE,
        "arriving_index": IDX_WHITE,
        "ink_index": IDX_BLACK,
        "label": "White",
    },
    "black": {
        "departing_index": IDX_BLACK,
        "arriving_index": IDX_BLACK,
        "ink_index": IDX_WHITE,
        "label": "Black",
    },
    "yellow": {
        "departing_index": IDX_YELLOW,
        "arriving_index": IDX_YELLOW,
        "ink_index": IDX_BLACK,
        "label": "Yellow",
    },
    "red": {
        "departing_index": IDX_RED,
        "arriving_index": IDX_RED,
        "ink_index": IDX_WHITE,
        "label": "Red",
    },
    "sky": {
        "departing_index": IDX_BLUE,
        "arriving_index": IDX_GREEN,
        "ink_index": IDX_WHITE,
        "label": "Sky",   # D-04: label changes from "Sky (default)" -> "Sky"
    },
}
DEFAULT_THEME_ID = "white"  # D-01: moves the DEFAULT_THEME_ID assignment target
```
Insertion order among the new entries is Claude's Discretion per CONTEXT.md
(no functional effect — `THEME_IDS = tuple(THEMES)` derives automatically).
`DEFAULT_THEME_ID = "sky"` (line 50) must change to `"white"`.

**Comment maintenance:** the block comment above `THEMES` (lines 56-70)
narrates the historical real-glass tuning of Blue/Green specifically — it
should gain a short note (not a rewrite) that White/Black/Yellow/Red are new
per-phase-8 additions still awaiting their own on-glass pass (D-13), to keep
the comment's provenance claims accurate rather than stale.

---

### `server/plane/render.py` — font-role constants (D-06/D-07/D-11)

**Analog:** the existing font-role constant block itself (self-referential —
these are the six call sites CONTEXT.md names by exact identifier).

**Current state** (lines 118-134):
```python
PT_SERIF_REGULAR = os.path.join(FONT_DIR, "PTSerif-Regular.ttf")
PT_SERIF_BOLD = os.path.join(FONT_DIR, "PTSerif-Bold.ttf")
...
STATE_LABEL_FONT = (PT_SERIF_REGULAR, 20, 400)
TOP_TAG_FONT = (PT_SERIF_REGULAR, 18, 400)
MAIN_LINE1_FONT = (PT_SERIF_REGULAR, 44, 400)
MAIN_LINE2_FONT = (PT_SERIF_REGULAR, 22, 400)
PREVIOUS_LINE1_FONT = (PT_SERIF_REGULAR, 28, 400)
PREVIOUS_LINE2_FONT = (PT_SERIF_REGULAR, 16, 400)
EMPTY_HEADING_FONT = (PT_SERIF_BOLD, 72, 700)
EMPTY_BODY_FONT = (PT_SERIF_REGULAR, 40, 400)
```

**Pattern to copy:** `EMPTY_HEADING_FONT` (already `PT_SERIF_BOLD, ..., 700`)
is the exact target shape every other role-tuple constant should match —
swap `PT_SERIF_REGULAR` for `PT_SERIF_BOLD` and the weight number `400` for
`700` in `STATE_LABEL_FONT`, `TOP_TAG_FONT`, `MAIN_LINE1_FONT`,
`MAIN_LINE2_FONT`, `PREVIOUS_LINE1_FONT`, `PREVIOUS_LINE2_FONT` (D-06 is
explicit: universal, not just coloured themes — `EMPTY_BODY_FONT` is
untouched, since D-06 scopes only to text roles inside the active-state
render path, and the empty state was already explicitly out of scope per
CONTEXT.md's Claude's Discretion note).

**D-11 change (same block):**
```python
PREVIOUS_LINE2_FONT = (PT_SERIF_BOLD, 20, 700)   # was 16, PT_SERIF_REGULAR, 400
```

**Two additional call sites that read `PT_SERIF_REGULAR` directly** (not
through a role tuple — must also change to `PT_SERIF_BOLD`, per CONTEXT.md's
"Established Patterns" note):
- `render.py:995-996` inside `draw_main_text_block()`:
  ```python
  line1_font = fit_text_size(PT_SERIF_REGULAR, MAIN_LINE1_FONT[1], line1_text, safe_width, MAIN_LINE1_MIN_SIZE)
  line2_font = fit_text_size(PT_SERIF_REGULAR, MAIN_LINE2_FONT[1], line2_text, safe_width, MAIN_LINE2_MIN_SIZE)
  ```
- `render.py:1042-1043` inside `draw_previous_text_block()`:
  ```python
  line1_font = fit_text_size(PT_SERIF_REGULAR, PREVIOUS_LINE1_FONT[1], line1_text, available_width, PREVIOUS_LINE1_MIN_SIZE)
  line2_font = fit_text_size(PT_SERIF_REGULAR, PREVIOUS_LINE2_FONT[1], line2_text, available_width, PREVIOUS_LINE2_MIN_SIZE)
  ```
Both must become `PT_SERIF_BOLD` for the font-weight change to actually take
effect on the main/previous text blocks — the constant tuples above alone
are not read by `fit_text_size()`, only `[1]` (the size) is.

---

### `server/plane/render.py` — `_paint_text_backing()` removal (D-05)

**Analog:** the four call sites of `_paint_text_backing()` itself.

**Current definition** (lines 542-556):
```python
def _paint_text_backing(draw, bbox, bg_idx, pad=4):
    """Paint a small solid `bg_idx` rectangle behind a text bbox..."""
    draw.rectangle(
        (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad),
        fill=bg_idx,
    )
```

**All four call sites to remove** (delete the `_paint_text_backing(...)`
line at each; keep the surrounding `textbbox`/`_assert_within_canvas`/
`draw.text` calls unchanged):
- `draw_top_labels()`: lines 580 and 585
- `draw_main_text_block()`: lines 1001 and 1007
- `draw_previous_text_block()`: lines 1048 and 1054

**Pattern:** function definition and all four call sites are removed
together (D-05: "removed entirely, for every theme... no replacement box,
outline, or shadow"). `bg_idx` parameters on `draw_top_labels()`,
`draw_main_text_block()`, `draw_previous_text_block()` stay in each
signature — still needed for other logic in those functions (verify at
execution time whether `bg_idx` becomes an unused parameter anywhere once
this call is gone, and if so leave it in place rather than changing the
function signature, since CONTEXT.md does not ask for a signature change).

---

### `server/plane/render.py` — `_flight_line1_text()` 4-tier ladder (D-08/D-09/D-10)

**Analog for the fallback-ladder shape:** `_flight_line2_text()` (lines
932-969) — already the file's established pattern for "walk several optional
data sources, return the richest available string, floor at
`ROUTE_FALLBACK_TEXT`."

**Current `_flight_line1_text()`** (lines 847-864):
```python
def _flight_line1_text(flight, state, route):
    """`"{callsign} to|from {city}"`, or bare `callsign` when `route` has no
    city for this state...
    """
    callsign = flight.get("callsign") or (flight.get("hex") or "").upper() or "?"
    city = enrich.city_for_state(route, state) if route is not None else None
    if city:
        direction = "to" if state == runway_config.STATE_DEPARTING else "from"
        return "%s %s %s" % (callsign, direction, city)
    return callsign
```

**Required rewrite (D-10), signature unchanged** — 4-tier ladder, must never
emit the raw ICAO `callsign`/`hex` at any tier:
1. `route.get("callsign_iata")` (new field, D-09) present AND
   `enrich.city_for_state(route, state)` truthy →
   `"%s %s %s" % (iata_id, direction, city)`.
2. City truthy, no IATA id → `"%s %s" % (direction_titlecase, city)` (e.g.
   `"To New York"` — capitalised "To"/"From", distinct from the existing
   lowercase "to"/"from" used in tier 1's mid-sentence position).
3. `route.get("airline_name")` truthy, no city, no IATA id → return
   `None`/empty sentinel — **line 1 omitted entirely**, both call sites
   (`draw_main_text_block()`, `draw_previous_text_block()`) must detect this
   and skip line 1's `draw.text()`/`textbbox()` calls, using
   `main_placement.content[3] + MAIN_TEXT_GAP_PX` /
   `prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX` directly as line 2's
   top instead of `line1_bbox[3] + MAIN_LINE_GAP_PX` /
   `line1_bbox[1] + PREVIOUS_LINE_GAP_PX`.
4. Nothing resolves (`route is None` or no airline either) →
   `"Departing"`/`"Arriving"` (title case) based on `state ==
   runway_config.STATE_DEPARTING`.

**Reference for what "state → direction word" already looks like in this
file** (reuse this exact conditional shape, do not invent a new one):
```python
direction = "to" if state == runway_config.STATE_DEPARTING else "from"
```
(line 862, inside the current function — same `state ==
runway_config.STATE_DEPARTING` test is the correct analog for deriving both
the tier-1 lowercase word and the tier-4 title-case
`"Departing"`/`"Arriving"` word.)

---

### `server/plane/render.py` — `draw_main_text_block()` / `draw_previous_text_block()` line-1-omitted handling (D-10)

**Analog:** the functions' own existing line2-positioning math (lines
1004-1005 and 1051-1052), which already derives line 2's top from line 1's
bbox — this is the exact code path that needs a conditional branch.

**Current** (`draw_main_text_block()`, lines 998-1008):
```python
top_y = main_placement.content[3] + MAIN_TEXT_GAP_PX
line1_bbox = draw.textbbox((center_x, top_y), line1_text, font=line1_font, anchor="ma")
_assert_within_canvas(line1_bbox, "main flight text line 1")
_paint_text_backing(draw, line1_bbox, bg_idx)   # <- also removed, see D-05 above
draw.text((center_x, top_y), line1_text, font=line1_font, fill=ink_idx, anchor="ma")

line2_top = line1_bbox[3] + MAIN_LINE_GAP_PX
line2_bbox = draw.textbbox((center_x, line2_top), line2_text, font=line2_font, anchor="ma")
```

**Current** (`draw_previous_text_block()`, lines 1045-1052):
```python
top_y = prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX
line1_bbox = draw.textbbox((right_x, top_y), line1_text, font=line1_font, anchor="ra")
...
line2_top = line1_bbox[1] + PREVIOUS_LINE_GAP_PX
```

**Required change:** wrap the line-1 draw block in `if line1_text:` (or
equivalent truthy check on `_flight_line1_text()`'s return); when falsy,
skip line 1 entirely and set:
- main card: `line2_top = main_placement.content[3] + MAIN_TEXT_GAP_PX`
- previous card: `line2_top = prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX`

i.e. line 2 starts exactly where line 1 would have started — the same
`content[3] + <GAP>_PX` expression already used to seed `top_y` for line 1,
just reused as line 2's top when line 1 is absent. `line1_font` computation
(`fit_text_size(...)`) can be skipped too when `line1_text` is falsy (minor
efficiency, not required for correctness — Claude's Discretion).

---

### `server/plane/render.py` — `PREVIOUS_LINE2_FONT` size (D-11)

Already covered above in the font-constants section
(`PREVIOUS_LINE2_FONT = (PT_SERIF_BOLD, 20, 700)`), folded into the same
D-06 edit since they touch the same line.

---

### `server/plane/render.py` — `draw_previous_text_block()` x-anchor offset (D-12)

**Analog:** the function's own existing `right_x` assignment (line 1036) —
single-line change, same variable, both of the card's text lines already
read `right_x` for their `anchor="ra"` position.

**Current** (line 1036):
```python
right_x = prev_placement.content[2]
```

**Required change (D-12):**
```python
right_x = prev_placement.content[2] - 20
```
This one-line change automatically applies to both line 1 and line 2 of the
previous card, since both already read `right_x` (lines 1046, 1049 for line
1; the line-2 `draw.text`/`textbbox` calls further down reuse the same
`right_x`). No change to `available_width = right_x - SAFE_BOX[0]` (line
1037) beyond it naturally picking up the new `right_x` value — confirm this
doesn't need separate adjustment (CONTEXT.md doesn't call this out as a
problem, since `available_width` shrinking by 20px is a harmless side
effect, not a regression). Main card's `center_x = WIDTH // 2` (line 989,
`draw_main_text_block()`) is explicitly **not** touched (D-12: "Only the
previous card gets this offset").

---

### `server/plane/enrich.py` — thread `callsign_iata` through (D-09)

**Analog:** the existing `origin_iata`/`destination_iata` fields — same
three-function chain, same shape, being extended with a fourth sibling
field.

**`_parse_route()`, current** (lines 160-200): parses `flightroute.get(
"airline")` / `.get("origin")` / `.get("destination")` from the adsbdb
response body, validates every field is a non-empty string (lines 190-192),
and returns a dict with exactly `airline_name`, `origin_iata`, `origin_city`,
`destination_iata`, `destination_city` (lines 194-200). **Note:**
`callsign_iata` lives at the top level of `flightroute` in adsbdb's response
shape (confirmed via `server/fixtures/adsbdb_hit_TVF16VB.json` /
`adsbdb_hit_AIA6412.json`, per CONTEXT.md's canonical_refs) — not nested
under `airline`/`origin`/`destination` like the other five fields, so it
needs its own `flightroute.get("callsign_iata")` read, and per D-09 it
should NOT be required-non-empty the way the other five fields are (line
190-192's `for value in (...)` loop) — a route can still be valid with the
other five fields present and no IATA callsign (this is CONTEXT.md's tier-2
case). Add it as an optional field appended to the return dict, not folded
into the existing all-or-nothing validation loop.

**`_route_from_entry()`, current** (lines 210-217):
```python
def _route_from_entry(entry):
    return {
        "airline_name": entry.get("airline_name"),
        "origin_iata": entry.get("origin_iata"),
        "origin_city": entry.get("origin_city"),
        "destination_iata": entry.get("destination_iata"),
        "destination_city": entry.get("destination_city"),
    }
```
**Pattern to copy:** add `"callsign_iata": entry.get("callsign_iata"),` as a
sixth key, exact same `entry.get(...)` shape as every sibling line.

**`lookup_route()`'s cache-write, current** (lines 360-364):
```python
cache_entry = dict(route)
cache_entry["found"] = True
cache[normalised] = cache_entry
```
No change needed here — `dict(route)` already copies whatever keys
`_parse_route()` put in `route`, so once `_parse_route()` includes
`callsign_iata`, the cache-write path carries it through for free. This is
the third leg of D-09's chain, and CONTEXT.md's warning ("missing any one of
the three means a cache round-trip silently drops the field") means: the
only two functions that actually need an edit are `_parse_route()` (must add
the field to its return dict) and `_route_from_entry()` (must add the field
to its return dict) — `lookup_route()`'s generic `dict(route)` copy already
handles the middle leg correctly as long as both ends are fixed.

**Consumer note:** `render.py`'s new `_flight_line1_text()` (D-10 above)
reads `route.get("callsign_iata")` — confirm the key name matches exactly
what `_parse_route()`/`_route_from_entry()` write (`callsign_iata`, per
CONTEXT.md D-09's own naming).

---

### `server/assets/fonts/VENDOR.md` — PT Serif supersession note (D-07)

**Analog:** the existing "Supersession (Phase 3, later in the same
session — D-20/D-27)" note under the Zilla Slab entry (lines 101-107):
```markdown
### Supersession (Phase 3, later in the same session - D-20/D-27)

Zilla Slab is **no longer referenced** by `server/plane/render.py`'s active
font-role constants. After seeing a real rendered preview, the developer
did not like Zilla Slab's look and chose **PT Serif** instead (see the
entry below) - files stay vendored here for provenance, same
"retained but inactive" treatment this file already gives Inter above.
```

**Pattern to copy:** append an equivalent `### Supersession (Phase 8, D-06/
D-07)` subsection under the existing `## PTSerif-Regular.ttf / PTSerif-
Bold.ttf` heading (starts line 109), same three-sentence shape: (1) which
constants stopped referencing Regular, (2) why (D-06: Bold's heavier stroke
replaces the removed backing-plate's legibility job — this is a functional
substitution, not just a look preference like the Zilla Slab case), (3)
"stays vendored, unreferenced... retained for provenance" — same closing
clause as the Zilla Slab/Inter entries. This note should sit alongside, not
replace, the existing "Known risk — Regular weight is active (D-27...)"
subsection (lines 142-157) — that subsection's claim ("Regular weight IS
the active weight") becomes stale once D-06 lands, so it needs a short
correction/pointer to the new Supersession note (mirroring how the
Inter entry above got a dated "Correction" paragraph at lines 23-30 when a
past claim went stale) rather than silent deletion.

## Shared Patterns

### Registry-driven config: no call-site fanout
**Source:** `server/device_config.py` module docstring, lines 20-24, and
`THEME_IDS = tuple(THEMES)` (line 107) / `normalise_theme_id()` (lines
117-126) / `theme_background_index()` / `theme_ink_index()` (lines 235-252,
not fully re-read here but referenced by line numbers in the grep above).
**Apply to:** the `THEMES` dict edit only — every other module that consumes
theme ids (companion picker, `render.py`'s `--theme` CLI flag) already
iterates the registry generically per CONTEXT.md's `code_context` section;
no changes needed there, but the plan should include a verification step
(run the existing test suite / manually exercise
`companion/pages/config_page.py`'s `theme_fieldset()`) confirming this holds
rather than assuming it blind.

### Defensive parsing / never-raise discipline
**Source:** `server/plane/enrich.py`'s `_parse_route()` (T-02-04-01 comment,
lines 161-162) and `correct_airline_name()` (lines 257-268, "Never raises").
**Apply to:** the `callsign_iata` field addition — read it with `.get(...)`
(never `[...]`), never add it to the required-non-empty validation loop
(lines 190-192), and never let its absence cause `_parse_route()` to return
`None` for an otherwise-valid route (that would be a regression: currently
those 5 fields alone constitute a valid route, and D-09 must not change what
counts as a route miss).

### On-glass verification gate structure
**Source:** `.planning/phases/07-final-on-glass-verification/07-01-PLAN.md`
(task structure: CLI forcing flags, step-by-step verification protocol) and
`hardware/BRINGUP-LOG.md`'s "Final On-Glass Verification" / "Phase 7 On-Glass
Verification" entries (the two prior cases where a monitor-preview judgment
was overturned by real ink).
**Apply to:** whichever plan closes this phase (D-13) — reuse Phase 7's task
shape (force each theme via `render.py`'s existing `--theme`/`--preview`
CLI flags, no new CLI surface needed per CONTEXT.md's `code_context`), not
its content (RGB calibration/bezel clipping are not being re-run).

## No Analog Found

None — every file/function this phase touches already exists with an
established in-file sibling pattern (a dict entry, a font-constant tuple, a
fallback-ladder function, a field-threading chain, or a doc subsection).
There is no new architectural pattern being introduced in this phase.

## Metadata

**Analog search scope:** `server/device_config.py`, `server/plane/render.py`,
`server/plane/enrich.py`, `server/panel_format.py`,
`server/assets/fonts/VENDOR.md` — all read directly (no broader codebase
search needed; CONTEXT.md and the spike already named every touched
function/constant precisely).
**Files scanned:** 5 (the 4 target files + `panel_format.py` for the
`IDX_*` constant definitions)
**Pattern extraction date:** 2026-08-31
