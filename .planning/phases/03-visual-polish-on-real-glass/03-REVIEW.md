---
phase: 03-visual-polish-on-real-glass
reviewed: 2026-08-27T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - server/assets/fonts/VENDOR.md
  - server/assets/fonts/ZillaSlab-Bold.ttf
  - server/assets/fonts/ZillaSlab-OFL.txt
  - server/assets/fonts/ZillaSlab-SemiBold.ttf
  - server/assets/icons/illustrations/VENDOR.md
  - server/panel_format.py
  - server/plane/dither.py
  - server/plane/render.py
  - server/test_dither.py
  - server/test_illustrations.py
  - server/test_render.py
findings:
  critical: 2
  warning: 2
  info: 1
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-08-27
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the D-21/D-24/D-25/D-26/D-27 two-flight poster renderer (`server/plane/render.py`), the full-6-color dither helper (`server/plane/dither.py`), the shared panel byte-format module (`server/panel_format.py`), the three matching test harnesses, and the two font/illustration vendor-provenance records.

`panel_format.py` and `dither.py` are solid — palette bridging, packing, and the quantization contract all check out, and the sha256 digests in both `VENDOR.md` files were spot-checked (and, for the illustrations VENDOR.md, exhaustively re-hashed against every vendored PNG) with zero mismatches.

`render.py` has two genuine correctness bugs, both empirically reproduced against the actual code (not just read-through speculation):

1. When illustration loading fails all the way down the degradation ladder (primary file *and* `generic-fallback.png` both undecodable), the renderer silently omits **all** flight text — callsign, route, airline, aircraft type — not just the illustration. The panel ships with only the static "DEPARTING"/tag labels and a colored background: the device's entire reason for existing (showing which flight is departing/arriving) disappears with no visible error on the glass.
2. `_flight_line2_text()` treats a non-string `airline_name` (e.g. an int, list, or dict from a malformed/corrupted route payload) as a *hit*, silently `%s`-formatting it into the drawn text (e.g. `"['x', 'y'] · A320"`), instead of falling back to `ROUTE_FALLBACK_TEXT` the way `illustrations.select_illustration()` already does for the exact same malformed input. This is a real, reproduced inconsistency, not a theoretical one.

Both are provable, not hypothetical: reproductions are included below. Existing tests (`test_render.py` #38, #30) exercise the surrounding scenarios but only assert "does not raise" / "returns a string" — they don't assert on the actual text content, which is exactly why both bugs shipped with all tests green.

## Critical Issues

### CR-01: Illustration-load failure silently blanks all flight text, not just the illustration

**File:** `server/plane/render.py:641-663`
**Issue:** In `_build_active_canvas()`, `draw_main_text_block()` (and, transitively, the entire previous-flight card) is only called when `main_resized is not None`:
```python
main_resized = _load_illustration_safely(main_path, main_w)
if main_resized is not None:
    main_left = (WIDTH - main_resized.size[0]) // 2
    main_bbox = draw_illustration(canvas, main_resized, main_left, main_top)
    _assert_within_canvas(main_bbox, "main aircraft illustration")
    draw_main_text_block(canvas, flight, state, route, main_bbox, fg_idx)
...
if previous_flight is not None and main_bbox is not None:
    ...
```
If `_load_illustration_safely()` exhausts its ladder (both the selected illustration file *and* `illustrations.generic_fallback_path()` fail to decode — e.g. a corrupted/missing `generic-fallback.png`, a bad deploy, or a disk issue on the server), `main_resized` is `None`, `main_bbox` stays `None`, and the text block is never drawn — even though the flight/route data needed to render the text has nothing to do with whether an image decoded. The previous-flight card is dropped too, since it's gated on `main_bbox is not None`. Reproduced directly:
```
$ server/.venv/bin/python3 -c "... force select_illustration/generic_fallback_path to a garbage file, then build_canvas(...) ..."
text calls drawn: ['DEPARTING', 'ORY · RWY 3']
```
Only the static top-row labels are drawn — the callsign, destination city, airline, and aircraft type are completely absent from the panel. For a battery-powered, deep-sleep e-ink departure board whose entire value proposition is "glancing at the frame tells you what's departing," a bad asset on the server silently produces a panel that shows nothing useful, with no diagnostic reaching the device (only a `stderr` print on the server).
**Fix:** Decouple text drawing from illustration success. Compute a text anchor bbox independent of whether an illustration was actually composited (e.g. fall back to `main_top` + a fixed nominal illustration height when `main_resized is None`), and always call `draw_main_text_block()` (and, independently, the previous card's text) regardless of illustration load outcome:
```python
main_resized = _load_illustration_safely(main_path, main_w)
if main_resized is not None:
    main_left = (WIDTH - main_resized.size[0]) // 2
    main_bbox = draw_illustration(canvas, main_resized, main_left, main_top)
    _assert_within_canvas(main_bbox, "main aircraft illustration")
else:
    # No illustration decoded at all (ladder exhausted) - still anchor the
    # text block so flight info is never silently dropped.
    main_bbox = (main_left_fallback, main_top, main_left_fallback + main_w, main_top)
draw_main_text_block(canvas, flight, state, route, main_bbox, fg_idx)
```
(and drop the `previous_flight is not None and main_bbox is not None` compound guard down to just `previous_flight is not None`, computing its own anchor the same way).

### CR-02: `_flight_line2_text()` renders a raw non-string `airline_name` instead of treating it as an enrichment miss

**File:** `server/plane/render.py:477-488`
**Issue:**
```python
try:
    airline_name = route.get("airline_name") if isinstance(route, dict) else None
except Exception:
    airline_name = None
if not airline_name:
    return ROUTE_FALLBACK_TEXT
display_name = display_airline_name(airline_name)
...
return "%s" % (display_name,)
```
`if not airline_name` only filters out falsy values (`None`, `""`, `0`). A truthy non-string value (an `int`, `list`, `dict`, etc. — plausible from a corrupted cache entry or a future upstream API contract change) passes through, `display_airline_name()` returns it unchanged (its own contract: "returns airline_name unchanged for any non-string ... value"), and the final `"%s" % (display_name,)` stringifies it directly onto the panel. Reproduced:
```
>>> render._flight_line2_text({'airline_name': 12345}, 'A320')
'12345 · A320'
>>> render._flight_line2_text({'airline_name': ['x', 'y']}, 'A320')
"['x', 'y'] · A320"
```
This is inconsistent with `illustrations.select_illustration()`, which explicitly treats the identical malformed input (`{"airline_name": 123}`) as a miss and falls back to the generic illustration (`server/test_illustrations.py::_select_route_non_string_airline_name_falls_back`). The result on real hardware: the illustration silently degrades to the generic fallback plane, but the text underneath it shows a raw Python repr fragment (e.g. `['x', 'y'] · A320`) instead of `"Route unavailable"` — visibly broken output on the physical panel for the exact failure mode the module's own docstring says should "still be a miss."
**Fix:** Require `airline_name` to actually be a non-empty string before treating it as a hit:
```python
if not isinstance(airline_name, str) or not airline_name:
    return ROUTE_FALLBACK_TEXT
```

## Warnings

### WR-01: `previous_state=None` silently defaults the previous card's direction text to "from"

**File:** `server/plane/render.py:522-536` (via `_flight_line1_text`, `server/plane/render.py:385-397`)
**Issue:** `draw_previous_text_block()` passes `previous_state` straight into `_flight_line1_text(flight, state, route)`, which computes `direction = "to" if state == runway_config.STATE_DEPARTING else "from"`. If a caller supplies `previous_flight`/`previous_route` but omits `previous_state` (it defaults to `None` in both `build_canvas()` and `render_panel()`), the previous card silently renders "... from {city}" regardless of whether the previous flight was actually departing or arriving, with no warning that the state was unknown/unset.
**Fix:** Validate `previous_state` is one of the two known constants whenever `previous_flight` is provided, and fail loudly (or clearly label direction as unknown) rather than defaulting to "from":
```python
if previous_flight is not None and previous_state not in (runway_config.STATE_DEPARTING, runway_config.STATE_ARRIVING):
    raise ValueError("previous_state %r is required and must be a known state when previous_flight is supplied" % (previous_state,))
```

### WR-02: `_assert_legal_palette()`'s guard rail silently no-ops if `Image.getcolors()` ever returns `None`

**File:** `server/plane/render.py:589-616`
**Issue:**
```python
colors = canvas.getcolors()
idx_set = {value for _count, value in colors} if colors else set()
...
counts = {value: count for count, value in colors} if colors else {}
```
`Image.getcolors()` returns `None` when the image has more distinct colors than its `maxcolors` argument (default 256). The code treats that `None` case as "zero colors" (`idx_set = set()`, `counts = {}`), which makes both assertions in this function vacuously pass (`illegal = set() - {...} = set()`; `bg_count = 0 >= other_max = 0`). In the current codebase this path is unreachable (a "P"-mode canvas has at most 256 possible index values, matching the default `maxcolors`), so this isn't exploitable today — but it means the one guard rail whose entire job is "assert no illegal palette index ever reaches the panel" degrades to a silent no-op instead of failing loudly if that invariant is ever violated (e.g. a future edit widens the effective palette size, or calls `getcolors(maxcolors=...)` with a smaller cap somewhere else).
**Fix:** Treat `colors is None` as a hard assertion failure rather than "zero colors observed":
```python
colors = canvas.getcolors()
assert colors is not None, "canvas has more distinct colors than getcolors()'s default cap - assertion cannot verify palette legality"
```

## Info

### IN-01: Existing tests assert "never raises" but not "renders correct content," which is why CR-01/CR-02 shipped green

**File:** `server/test_render.py:825-851` (check #38), `server/test_render.py:657-674` (check #30)
**Issue:** Check #38 (`_both_illustration_and_fallback_undecodable_still_renders`) only asserts the output byte length and that it differs from a forced-fallback render — it never asserts that flight text is still present (CR-01 above passes this exact test today with zero text drawn). Check #30 (`_flight_line2_text_never_raises_for_hostile_inputs`) only asserts "no exception" and "result is a string" — it never asserts the *content* of the returned string for a non-string `airline_name`, which is why CR-02 passes today while returning `"12345 · A320"`.
**Fix:** Once CR-01/CR-02 are fixed, strengthen these two checks to assert on drawn text presence/content (e.g. capture `_TextSpy` calls in check #38 and assert the callsign/route text is still drawn; assert `_flight_line2_text(...)` returns exactly `ROUTE_FALLBACK_TEXT` for every non-string `airline_name` case in check #30's hostile-input matrix).

---

_Reviewed: 2026-08-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
