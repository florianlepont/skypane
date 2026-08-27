# Pattern Map: Phase 03 Gap Closure — Corrupt/Oversized Illustration Guard

**Gap being closed:** `_resize_illustration()` (`server/plane/render.py`) calls
`Image.open(path).convert("RGBA")` with no exception handling anywhere in its
call chain (`_build_active_canvas()` → `_resize_illustration()` →
`draw_illustration()`). A corrupt/decompression-bomb `.png` that passes
`os.path.isfile()` raises `PIL.UnidentifiedImageError` (or similar) straight
out of `render_panel()`, freezing all future panel updates via
`poll_loop.py`'s outer `except Exception` (which only stops crash-looping —
it does not restore graceful per-flight degradation).

**Fix shape:** restore a try/except safety net around the illustration
load-and-composite step, degrading tier-by-tier to
`illustrations.generic_fallback_path()` and finally to "skip drawing the
illustration at all" — mirroring the already-correct "missing file" tier
skipping in `select_illustration()`. Optionally pre-check with
`illustrations.validate_illustration_file()`'s pixel-count guard before
decode, closing the oversized-file gap in the same stroke.

---

## Files Likely Touched

| File | Role | Change type |
|------|------|-------------|
| `server/plane/render.py` | Render pipeline (data flow: `route`/`aircraft_type` → `illustrations.select_illustration()` → path → `_resize_illustration()` → `draw_illustration()` → composited canvas) | Modify: wrap illustration load in defensive fallback logic |
| `server/test_render.py` | Regression harness for `render.py` (asserts on canvas/packed bytes only, never screenshots) | Modify: add corrupt-file and (optionally) oversized-file regression checks, bump `EXPECTED_CHECK_COUNT` |
| `server/fixtures/` (new, maybe) or an in-test tempfile | Corrupt-PNG test fixture | Create (or synthesize inline in the test, no new committed binary needed) |

No changes anticipated in `server/plane/illustrations.py` — its
`validate_illustration_file()` already contains the exact guard logic needed;
it just needs to be *called* from the render path, or its pattern
(header-only pixel check, `try/except Exception` around `Image.open`) needs
to be replicated at the render call site.

---

## Closest Existing Analog #1 (still live): `validate_illustration_file()`

`server/plane/illustrations.py:380-428` — this is the canonical "never let a
Pillow decode error propagate" pattern already proven in this codebase, plus
the header-only decompression-bomb guard (`ILLUSTRATION_MAX_PIXELS =
40_000_000`, checked from `img.size` *before* any `.convert()`/`.load()`
call):

```python
def validate_illustration_file(path):
    """... Never raises - any Pillow exception is
    turned into a problem string.
    """
    problems = []
    if not os.path.isfile(path):
        return ["file does not exist: %s" % path]

    try:
        with Image.open(path) as img:
            fmt = img.format
            width, height = img.size
            ...
            pixel_count = width * height
            if pixel_count > ILLUSTRATION_MAX_PIXELS:
                problems.append(...)
                # Do not decode any further - the whole point of checking
                # the header first is to never call load()/convert() on a
                # file this large.
                return problems
            ...
    except Exception as exc:  # never propagate a Pillow decode error
        problems.append("failed to open/parse image: %r" % (exc,))

    return problems
```

**What to reuse:** the `try/except Exception as exc` wrapping every
`Image.open(path)` / `.convert()` call, and the "check `img.size` before
decoding pixel data" discipline for the oversized case. This function is
only invoked from `illustrations.py`'s own `main()` (`--validate` CLI) today
— it is never imported/called by `render.py` or `poll_loop.py`. The gap
closure should either (a) call this function (or a lightweight render-path
variant of it) before `_resize_illustration()` decodes the file, or (b) wrap
`_resize_illustration()`/`draw_illustration()`'s own `Image.open()` call in
an equivalent try/except, falling back tier-by-tier.

**Never-raises API convention already established in this codebase**
(`normalise_airline_key()`, `classify_aircraft_type()`,
`illustration_path_for_key()`, `display_airline_name()`,
`_flight_line2_text()` in `render.py`): return a safe/degraded value for any
falsy, non-string, or hostile input rather than raising — the fix should
follow this same idiom for the illustration *loading* step, not just the
*selection* step.

---

## Closest Existing Analog #2 (retired, historical precedent): `draw_silhouette()`

Found via `git log --all -p -- server/plane/render.py | grep "def draw_silhouette" -A40`
(commit `cdcc6bf`, "feat(02-03): composite the silhouette centrepiece with
hard edges and state mirroring"; retired later during the D-25/D-26
two-flight redesign — `draw_silhouette()` no longer exists anywhere in
`server/plane/render.py`, confirmed by the verifier).

The retired function's docstring (captured in the diff) documents its intent
— a flat, mirrored fallback centerpiece drawn from a single vendored CC0
silhouette (`SILHOUETTE_PATH`), with sizing derived from an `Image.open()`
probe:

```python
def draw_silhouette(canvas, state, ink_idx):
    """Draw UI-SPEC zone 3 - the aircraft silhouette centrepiece: a flat
    `ink_idx`-coloured fill of the vendored CC0 aircraft silhouette,
    ...
    """
    with Image.open(SILHOUETTE_PATH) as probe:
        src_w, src_h = probe.size
    aspect = src_w / src_h
    ...
```

**Important caveat for the fix:** the historical `draw_silhouette()` itself
had **no try/except** around its own `Image.open()` call — it relied on
`SILHOUETTE_PATH` being a single, permanently-vendored, pre-verified file
that was never expected to be corrupt (there was no "corrupt file" threat
model yet at that point in the project's history; per-airline illustrations
and their attack surface didn't exist). So there is no directly copyable
"old exception handler" to restore verbatim — the historical precedent is
architectural only (a guaranteed-safe last-resort visual with no external
dependency on per-flight data), not a code pattern to lift. The actual
try/except discipline to copy is `validate_illustration_file()`'s (Analog
#1), adapted to the new per-airline tiered-fallback system instead of the
old flat silhouette.

**Adapted approach for the current system:** the "last resort" in the
current architecture is not a redrawn silhouette but
`illustrations.generic_fallback_path()` (already the Tier 4 selection
result) — reused as the *decode*-fallback too. Concretely, in
`_build_active_canvas()`, the illustration loading step should become
something like (illustrative, not prescriptive of exact code):

```python
def _load_illustration_safely(path, target_w):
    """Try `path`; on any decode failure, retry the universal generic
    fallback; on that also failing, return None (caller skips drawing).
    Mirrors the existing 'missing file' degrade-to-None discipline in
    illustrations.select_illustration() and _build_active_canvas().
    """
    for candidate in (path, illustrations.generic_fallback_path()):
        if candidate is None or not os.path.isfile(candidate):
            continue
        try:
            return _resize_illustration(candidate, target_w)
        except Exception:
            continue
    return None
```

Call sites in `_build_active_canvas()` (`render.py:562-584`) currently do:

```python
main_path = illustrations.select_illustration(route, flight.get("aircraft_type"))
main_bbox = None
if main_path is not None:
    main_resized = _resize_illustration(main_path, main_w)   # <-- unguarded
    ...
```

and symmetrically for `prev_path`/`prev_resized`. Both call sites need the
same defensive wrapping.

---

## Data Flow Summary (for the fix's blast radius)

```
route, aircraft_type
   │
   ▼
illustrations.select_illustration()  ── returns a path (str) or None
   │  (already safe: os.path.isfile() at every tier; never raises)
   ▼
_resize_illustration(path, target_w)  ── UNGUARDED Image.open().convert()  <-- GAP
   │
   ▼
draw_illustration(canvas, resized_rgba, left, top)  ── dither + paste (safe, pure-PIL ops on already-decoded data)
   │
   ▼
_build_active_canvas() composites onto canvas
   │
   ▼
render_panel() → pf.pack_panel() → 960,000-byte buffer served by poll_loop.py
```

The only unguarded step is `_resize_illustration()`'s `Image.open(path)`
call (and implicitly `.convert("RGBA")`, which can also raise on certain
malformed files after a successful `open()`). Everything downstream of a
successfully-decoded `RGBA` image is pure Pillow arithmetic and does not
independently need guarding.

---

## Regression Test Pattern (for `server/test_render.py`)

Existing harness conventions to follow (from `server/test_render.py:1-166`):

- `EXPECTED_CHECK_COUNT` constant at top of file — must be incremented for
  each new check added.
- `check(name, fn)` helper: calls `fn()`, expects `(ok, reason)`, converts
  any raised exception into an automatic `FAIL` (never swallows into a
  pass) — this means a naive regression test for this gap does NOT need its
  own try/except; letting `render.render_panel()` raise inside `fn()` will
  already correctly register as `FAIL` today (proving the gap), and after
  the fix, the same call should return `True` because no exception is
  raised.
- `_SelectIllustrationSpy` (`test_render.py:115-141`) is the closest
  existing pattern for injecting a controlled illustration path — it
  monkeypatches `render.illustrations.select_illustration` and records/
  passes through calls. The corrupt-file regression test should follow the
  same monkeypatch-and-restore shape, but instead of recording args, it
  should **override the return value** to point at a byte-garbage file with
  a `.png` extension (this is exactly how the verifier reproduced the crash
  live, per 03-VERIFICATION.md's "Behavioral Spot-Checks" table).

Suggested new check shape (illustrative):

```python
def _corrupt_illustration_degrades_to_fallback():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"not a real png, just garbage bytes")
        corrupt_path = f.name
    try:
        orig = render.illustrations.select_illustration
        render.illustrations.select_illustration = lambda route, aircraft_type=None: corrupt_path
        try:
            buf = render.render_panel(TEST_FLIGHT, "departing", route=TEST_ROUTE)
        finally:
            render.illustrations.select_illustration = orig
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "did not degrade to a valid %d-byte panel" % panel_format.IMAGE_BYTES
        return True, ""
    finally:
        os.unlink(corrupt_path)
check("a corrupt-but-present illustration file degrades to the fallback instead of crashing render_panel()", _corrupt_illustration_degrades_to_fallback)
```

No new binary fixture file needs to be committed — a byte-garbage tempfile
generated inline (as the verifier did) is sufficient and matches the
existing test file's "no new committed test assets" style (it already reuses
real vendored illustrations rather than adding fixtures).

An oversized-file check (Tier 2 of the same gap) can follow the same
monkeypatch shape but write a real-but-huge PNG (e.g. via
`Image.new("RGBA", (10000, 10000))`, whose pixel count exceeds
`illustrations.ILLUSTRATION_MAX_PIXELS`) instead of garbage bytes — this
exercises the decompression-bomb path specifically, if the fix wires in
`validate_illustration_file()`'s header check rather than only a bare
try/except around `Image.open()`.

---

## Constants/Contracts to Preserve

- `illustrations.generic_fallback_path()` — the existing Tier-4 fallback,
  now reused as the fix's "decode fallback" too.
- `illustrations.ILLUSTRATION_MAX_PIXELS` (40,000,000) — the existing
  decompression-bomb cap, already defined; the fix should call
  `validate_illustration_file()` (or replicate its header-check-before-decode
  order) rather than redefining a new threshold.
- `_assert_within_canvas()` / `_assert_legal_palette()` (`render.py:195-206`,
  `510-537`) — existing guard rails that must continue to pass after the fix;
  the fallback-drawn illustration still needs to satisfy these same
  assertions (it will, since it flows through the same
  `draw_illustration()`/`dither.dither_to_full_panel_palette()` path).
- `poll_loop.py`'s outer `except Exception` around `run_once()` — untouched;
  it remains the last-resort safety net for genuinely unanticipated
  failures, not the mechanism this gap-closure fix should rely on for
  per-illustration degradation.
