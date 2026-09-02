---
phase: quick-260831-njw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/plane/render.py
  - server/test_render.py
autonomous: true
requirements: [SPIKE-002a]
must_haves:
  truths:
    - "The state label (DEPARTING/ARRIVING) renders with 6px of extra advance between every pair of adjacent glyphs, at its unchanged 20px size."
    - "The runway tag (ORY · RWY 3) renders with the same 6px extra advance, at its unchanged 18px size, still right-aligned so its last glyph's advance ends at WIDTH - MARGIN."
    - "No top-row label falls outside the 1200x1600 canvas for any registered runway id, in either active state, at either theme weight."
    - "Every other text role on the panel (main flight lines, previous card lines, empty-state heading/body, source-fault caption) is still drawn as one whole-string call - tracking did not leak into any other role."
    - "server/test_render.py passes at its bumped EXPECTED_CHECK_COUNT; scripts/run-all-tests.sh's only failure is the known, pre-existing, cross-platform server/test_poll_loop.py panel.bin digest mismatch."
  artifacts:
    - "server/plane/render.py: LABEL_TRACKING_PX constant, draw_tracked_text(), _tracked_text_width(), _tracked_text_bbox()"
    - "server/plane/render.py: draw_top_labels() rewritten to draw both labels tracked"
    - "server/test_render.py: three rewritten top-label checks + new tracked-geometry checks"
  key_links:
    - "draw_top_labels() -> draw_tracked_text() with tracking=LABEL_TRACKING_PX (both labels)"
    - "draw_top_labels() -> _tracked_text_width() to derive the right-anchored tag's start x"
    - "draw_top_labels() -> _tracked_text_bbox() -> _assert_within_canvas() (guard rebuilt on tracked geometry, replacing the untracked draw.textbbox() measurement)"
---

<objective>
Implement spike 002a's validated finding: add 6px letter-spacing (tracking) to the
panel's two smallest top-row text roles - the state label (`STATE_LABEL_FONT`,
20px, "DEPARTING"/"ARRIVING") and the runway tag (`TOP_TAG_FONT`, 18px,
"ORY · RWY 3") - both drawn inside `server/plane/render.py`'s `draw_top_labels()`.

Both strings are already fully uppercase, so this is **tracked all-caps text, not
a small-caps simulation**. The developer chose the `tracked-6px` variant ("j'aime
bien la 4") from a 5-way visual comparison: full size unchanged (20px/18px), 6px
tracking, **no size reduction**.

Purpose: the museum-placard treatment the developer asked for, at the exact value
the spike validated and Phase 3's own removed `LABEL_TRACKING_PX` had already
converged on (D-15).

Output: a tracked top row on every registered theme, runway and state, with the
suite reconciled - and an explicit, prominent record that **this has never been
seen on real Spectra 6 glass**.

## NOT VERIFIED ON REAL GLASS

This change is **screen-preview-validated only**. Per
`.planning/spikes/MANIFEST.md`'s Round 3 record: tracking has never been checked
against real Spectra 6 ink at any point in this project's history -
`hardware/BRINGUP-LOG.md` has no mention of it, even though the technique shipped
once before in Phase 2/3.

An on-glass check is the natural, expected follow-up (this project's own D-13
precedent: every visual/typography change needs a real on-glass check before being
considered final). **This plan does not attempt it and must not claim it.** The
SUMMARY must state the on-glass status as OPEN.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/spikes/002-small-labels-and-white-rhythm/README.md
@.planning/spikes/002-small-labels-and-white-rhythm/explore_labels.py
@server/plane/render.py
@server/test_render.py

**Project skills:** `.claude/skills/sketch-findings-skypane/SKILL.md` was read
during planning and is **not applicable** - it covers the companion web app's CSS
design system (`companion/static/style.css`), not the e-ink panel renderer. No
rule from it constrains this plan.

## Prior art - resurrect, do not reinvent

`draw_tracked_text()`, `_tracked_text_width()` and `_tracked_text_bbox()` all
existed verbatim in this exact file before commit `73a6eb2` ("two-flight poster
layout on real glass pipeline, D-21/D-24/D-25/D-26") removed them - removed
because that redesign changed the zone, **not** because they failed. Read the
originals first:

    git show 73a6eb2^:server/plane/render.py | sed -n '305,335p'

That range holds all three functions (`_tracked_text_width` at 309,
`draw_tracked_text` at 315, `_tracked_text_bbox` at 330) and `LABEL_TRACKING_PX = 6`
lived at line 112 of that same revision.

`.planning/spikes/002-small-labels-and-white-rhythm/explore_labels.py` is a
working, visually-validated adaptation of the same technique driven through the
real `build_canvas()` pipeline via a `draw_top_labels()` monkeypatch. It is
throwaway exploration code, **not** production code - use it as the reference for
*positioning* behaviour (left-anchored label at `MARGIN`; right-anchored tag
offset by its pre-computed tracked width), not as a file to copy wholesale.

## Geometry, measured during planning (use these as expectations, not guesses)

`MARGIN = 64`, `WIDTH = 1200`, `HEIGHT = 1600`. `draw_top_labels()` has exactly
one call site: `_build_active_canvas()` at `server/plane/render.py:1418`. It is
never called in the empty state.

Tracked widths at 6px, and the resulting right-aligned tag start x
(`WIDTH - MARGIN - tracked_width`), measured against the real fonts:

| weight | run | chars | plain width | tracked width | tag start x |
|--------|-----|-------|-------------|---------------|-------------|
| regular | "DEPARTING" (20px) | 9 | 113.0 | 161.0 | n/a (left-anchored) |
| regular | "ARRIVING" (20px) | 8 | 97.0 | 139.0 | n/a |
| regular | "ORY · RWY 3" (18px) | 11 | 102.0 | 162.0 | 974.0 |
| regular | "ORY · RWY 06/24" (18px) | 15 | - | 222.0 | 914.0 |
| bold | "DEPARTING" (20px) | 9 | 118.0 | 166.0 | n/a |
| bold | "ARRIVING" (20px) | 8 | 101.0 | 143.0 | n/a |
| bold | "ORY · RWY 3" (18px) | 11 | 115.0 | 175.0 | 961.0 |
| bold | "ORY · RWY 06/24" (18px) | 15 | - | 235.0 | 901.0 |

Worst case across all three registered runways and both theme weights is
`tag_x = 901` - comfortably inside the canvas and in fact still inside the 64px
`SAFE_BOX`. **Zero overflow risk at 6px**, matching the spike's own finding.

Font metrics for `_tracked_text_bbox()`'s height term: label font
`getmetrics() == (21, 6)`, tag font `(19, 6)`.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Resurrect the tracked-text helpers and LABEL_TRACKING_PX (not yet wired in)</name>
  <files>server/plane/render.py, server/test_render.py</files>

  <behavior>
    - `render.LABEL_TRACKING_PX` is the integer 6.
    - `_tracked_text_width(font, "", 6)` returns 0.0.
    - `_tracked_text_width(font, "A", 6)` equals `font.getlength("A")` - a
      single glyph carries no trailing tracking.
    - `_tracked_text_width(font, text, 6)` equals
      `sum(font.getlength(c) for c in text) + 6 * (len(text) - 1)` for a
      multi-character string.
    - `_tracked_text_width(font, text, 0)` equals the plain summed advance.
    - `draw_tracked_text()` issues exactly `len(text)` separate text draws (one
      per character, including spaces), each a single-character string, each at
      `anchor="la"`.
    - Consecutive glyph origins differ by exactly `font.getlength(previous_char)
      + tracking`.
    - `draw_tracked_text()` returns the x immediately after the last glyph's
      advance, i.e. `start_x + _tracked_text_width(...) + tracking`.
    - `_tracked_text_bbox(font, (x, y), text, tracking)` returns
      `(x, y, x + _tracked_text_width(font, text, tracking), y + ascent + descent)`.
  </behavior>

  <action>
    Read the three original function bodies out of git first
    (`git show 73a6eb2^:server/plane/render.py | sed -n '305,335p'`) and port them
    back verbatim rather than re-deriving them.

    Add `LABEL_TRACKING_PX = 6` to the Typography section of
    `server/plane/render.py`, immediately after `EMPTY_BODY_FONT` and before the
    "Overflow floors" comment block. Give it a short provenance comment naming
    spike 002a as the source of the value, noting it re-confirms Phase 3's own
    removed `LABEL_TRACKING_PX` (D-15) independently, and stating plainly that the
    value is screen-validated only and has never been checked on real Spectra 6
    ink.

    Add the three helpers immediately after `fit_text_size()` and before
    `_role_weight_path()` - the text-metrics neighbourhood of the module.

    Naming split, preserved exactly from the original commit: `draw_tracked_text`
    is public (no leading underscore); `_tracked_text_width` and
    `_tracked_text_bbox` are private. Do not rename any of the three.

    `_tracked_text_width(font, text, tracking)`: return 0.0 for an empty string;
    otherwise the sum of `font.getlength(ch)` over every character plus
    `tracking * (len(text) - 1)`.

    `draw_tracked_text(draw, xy, text, font, fill, tracking=0)`: unpack `xy` into
    x and y, then for each character issue one `draw.text((x, y), ch, font=font,
    fill=fill, anchor="la")` and advance x by `font.getlength(ch) + tracking`;
    return the final x. Keep the original's docstring intent - Pillow has no
    native letter-spacing API, which is why this draws glyph-by-glyph, and callers
    wanting right- or centre-aligned tracked text pre-compute the block width with
    `_tracked_text_width()` and offset `xy` themselves.

    One deliberate difference from the 73a6eb2^ original: pass `anchor="la"`
    explicitly on each glyph draw. The original relied on Pillow's implicit
    default (which is `la` for horizontal text, so this is behaviourally
    identical), but the spike's visually-validated adaptation passes it
    explicitly, and the existing harness asserts on the anchor kwarg - leaving it
    implicit would make that assertion read `None`. Note this in the docstring.

    `_tracked_text_bbox(font, xy, text, tracking)`: unpack `xy`, take
    `ascent, descent = font.getmetrics()`, and return
    `(x, y, x + _tracked_text_width(font, text, tracking), y + ascent + descent)`.
    Note in its docstring that it exists so `_assert_within_canvas()` can be fed
    real tracked geometry - `ImageDraw.textbbox()` measures an untracked run and
    would under-report the width of a tracked one.

    Do NOT touch `draw_top_labels()` in this task, and do not add a `tracking=`
    parameter to `fit_text_size()` (the old revision had one; no role that shrinks
    is tracked here, so it would be dead surface). After this task the helpers are
    present and self-tested but nothing calls them from a draw path - the suite
    must stay fully green.

    In `server/test_render.py`, re-read the current on-disk `EXPECTED_CHECK_COUNT`
    before editing (it was 101 at planning time - trust the file, not this number)
    and add three checks matching the `<behavior>` block: (1) the constant's value
    plus the presence and public/private naming split of all three helpers; (2)
    `_tracked_text_width()`'s arithmetic across the empty / single-char /
    multi-char / zero-tracking cases, derived from `font.getlength()` rather than
    hardcoded pixel numbers; (3) `draw_tracked_text()`'s per-glyph draw count,
    per-glyph anchor, inter-glyph advance and return value, using the existing
    `_TextSpy` idiom against a scratch `panel_format.new_canvas()` +
    `ImageDraw.Draw()`. Bump `EXPECTED_CHECK_COUNT` by exactly the number of
    checks you actually added.

    Demonstrate check (3) is real before committing: temporarily set the advance
    to omit `tracking`, confirm that check fails, then restore.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 server/test_render.py</automated>
    <automated>server/.venv/bin/python3 -c "import sys; sys.path.insert(0,'.'); from server.plane import render; f=render._role_font(render.TOP_TAG_FONT,'bold'); t=render.runway_tag_text(); assert render.LABEL_TRACKING_PX==6; assert round(render._tracked_text_width(f,t,6))==175, render._tracked_text_width(f,t,6); assert render._tracked_text_width(f,'',6)==0.0; assert render._tracked_text_width(f,'A',6)==f.getlength('A'); print('helpers OK')"</automated>
    <automated>server/.venv/bin/python3 -c "import sys; sys.path.insert(0,'.'); from server.plane import render; src=open('server/plane/render.py').read(); assert 'def draw_tracked_text(' in src and 'def _tracked_text_width(' in src and 'def _tracked_text_bbox(' in src; print('naming split OK')"</automated>
  </verify>

  <done>
    `LABEL_TRACKING_PX = 6`, `draw_tracked_text()`, `_tracked_text_width()` and
    `_tracked_text_bbox()` all exist in `server/plane/render.py` with the
    original commit's naming split. `server/test_render.py` passes at its bumped
    count with three new helper checks, one of which was demonstrated failing
    under a deliberate regression and then restored. `draw_top_labels()` is
    byte-unchanged - confirm with `git diff`. Every panel render is still
    byte-identical to before this task.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Draw both top labels tracked, and reconcile the harness</name>
  <files>server/plane/render.py, server/test_render.py</files>

  <behavior>
    - A departing render draws "DEPARTING" as 9 consecutive single-character
      text calls at `y == MARGIN`, starting at `x == MARGIN`, whose joined text
      reconstructs the label exactly.
    - The runway tag is drawn as `len(tag_text)` consecutive single-character
      calls at `y == MARGIN`, the first at
      `x == WIDTH - MARGIN - _tracked_text_width(tag_font, tag_text, 6)`.
    - The tag's run ends flush right: first glyph x plus its tracked width equals
      `WIDTH - MARGIN` (within float tolerance).
    - Every consecutive pair of glyph origins within each run differs by exactly
      `font.getlength(previous_char) + 6`.
    - For every registered runway id, in both active states, on both a flat
      (`white`) and a dithered (`sky`) theme, both runs stay inside the canvas -
      no `AssertionError` from `_assert_within_canvas()` and the computed tag
      start x is >= 0.
    - The main flight lines, the previous card's lines, the empty-state heading
      and body, and the source-fault caption are each still drawn as one
      whole-string call - tracking has not leaked into any other role.
  </behavior>

  <action>
    Rewrite the drawing half of `draw_top_labels()` in `server/plane/render.py`.
    Keep the signature, the `weight`/`bg_idx` parameters and the `_role_font()`
    resolution exactly as they are - the theme-conditional weight behaviour
    (08-06) must survive untouched.

    State label: it stays left-anchored at `(MARGIN, MARGIN)`. Build its guard
    bbox with `_tracked_text_bbox(label_font, (MARGIN, MARGIN), label_text,
    LABEL_TRACKING_PX)`, pass that to the existing `_assert_within_canvas(...,
    "state label")` call, then draw with `draw_tracked_text(draw, (MARGIN,
    MARGIN), label_text, label_font, ink_idx, tracking=LABEL_TRACKING_PX)`.

    Runway tag: it is right-anchored, so it can no longer use Pillow's
    `anchor="ra"` - tracked text is positioned by hand. Pre-compute
    `tag_width = _tracked_text_width(tag_font, tag_text, LABEL_TRACKING_PX)`, set
    `tag_x = WIDTH - MARGIN - tag_width`, build its guard bbox with
    `_tracked_text_bbox(tag_font, (tag_x, MARGIN), tag_text, LABEL_TRACKING_PX)`,
    pass that to `_assert_within_canvas(..., "top-right tag")`, then draw with
    `draw_tracked_text(draw, (tag_x, MARGIN), tag_text, tag_font, ink_idx,
    tracking=LABEL_TRACKING_PX)`.

    Both `draw.textbbox()` measurements in this function are replaced by
    `_tracked_text_bbox()`; the untracked measurement would under-report a tracked
    run's width and silently stop guarding. Keep both `_assert_within_canvas()`
    call sites and their existing label strings ("state label", "top-right tag")
    so the existing failure messages stay meaningful - and keep the existing
    comment explaining why this function uses the looser within-canvas guard
    rather than the strict safe-box one.

    Update `draw_top_labels()`'s own docstring: its current text asserts that this
    row has no letter-spacing and that tracking was a superseded, larger zone-1
    treatment. That statement is now false. Replace it with the current truth -
    both roles are tracked by `LABEL_TRACKING_PX`, sizes unchanged at 20px/18px,
    per spike 002a - and record that the value is screen-validated only, never
    seen on real Spectra 6 ink, with the on-glass check still open under D-13.
    Also record why the tag no longer uses Pillow's right anchor.

    Do not touch any other draw function, any other font role, `_role_font()`,
    `_role_weight_path()`, the theme registry, or `dither.py`.
    `server/plane/render.py` and `server/test_render.py` are the only two files
    this whole plan may modify.

    Now reconcile `server/test_render.py`. Three existing checks break because
    they assert on whole-string draws that no longer occur:

    1. `_departing_top_row_labels_present` (numbered 14, near line 595) - looks
       for `"DEPARTING"` and `render.TOP_RIGHT_TAG_TEXT` among the captured
       texts. Rewrite it to reconstruct each run: collect the spy's
       single-character calls at `y == MARGIN` in call order and join them; the
       first `len(label_text)` of them must reconstruct the state label and the
       remainder must reconstruct the tag. This ordering is guaranteed by
       `draw_top_labels()`'s own draw order (label first, then tag) - assert on
       that order rather than on x-sorting.
    2. `_top_labels_sit_at_the_margin_inset` (numbered 15, near line 606) -
       asserts the label at `(MARGIN, MARGIN)` anchor `la` and the tag at
       `(WIDTH - MARGIN, MARGIN)` anchor `ra`. Rewrite: the label's FIRST glyph
       must sit at `(MARGIN, MARGIN)` with anchor `la`, and the tag's FIRST glyph
       must sit at `(WIDTH - MARGIN - tracked_width, MARGIN)` with anchor `la`,
       where `tracked_width` is recomputed in the test from `render._role_font()`
       + `render._tracked_text_width()` rather than hardcoded - so the check
       tracks the real fonts and cannot go stale if a weight or size moves. Add
       the flush-right assertion (first glyph x + tracked width equals
       `WIDTH - MARGIN`) here.
    3. `_active_canvas_draws_selected_runways_tag` (numbered 65, near line 2266) -
       looks for `render.runway_tag_text("06-24")` among the captured texts.
       Rewrite it to reconstruct the tag from its glyph run the same way.

    Leave `_runway_tag_text_default_matches_top_right_tag` (numbered 61) alone -
    it exercises the pure function, not a draw, and is unaffected.

    Correct two stale docstrings in the harness while you are in the file: the
    module docstring and `_TextSpy`'s class docstring both claim the text-draw
    seam is the module's sole such call site because a tracked-text compositing
    path was dropped. Both statements are now false. Rewrite them to describe the
    current reality - the top row composites glyph-by-glyph, every other role
    draws whole strings.

    Add three new checks:

    - Inter-glyph advance: for a real departing render, every consecutive pair of
      origins within each of the two runs differs by exactly
      `font.getlength(previous_char) + render.LABEL_TRACKING_PX` (float tolerance
      ~0.01). Derive the expectation from the font, never from a pixel literal.
    - Overflow sweep: loop every `render.device_config.RUNWAY_IDS` entry, both
      active states, and both a flat theme (`white`) and a dithered theme (`sky`),
      calling `render.build_canvas(...)` and letting `_assert_within_canvas()` run
      for real; additionally assert the computed tag start x is >= 0 for each
      combination. Planning measured the worst case at 901 across every
      combination, so this must pass with wide margin - it exists as a guard for
      any future longer tag or larger size.
    - Tracking containment: for a full two-flight active render, assert that the
      main card's line 1, the previous card's lines and the source-fault caption
      are each still captured as a single whole-string draw, and that the total
      count of single-character draws equals exactly
      `len(label_text) + len(tag_text)` - proving tracking is confined to the two
      top-row roles.

    Re-read the on-disk `EXPECTED_CHECK_COUNT` after Task 1's bump and add exactly
    the number of new checks you added. Demonstrate the overflow sweep is real
    before committing: temporarily raise `LABEL_TRACKING_PX` high enough to push
    the longest tag off the left edge, confirm the sweep fails, then restore 6.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 server/test_render.py</automated>
    <automated>server/.venv/bin/python3 -c "
import sys; sys.path.insert(0,'.')
from server.plane import render
from PIL import ImageDraw
calls=[]
orig=ImageDraw.ImageDraw.text
def spy(s,xy,text,*a,**k):
    calls.append((text,xy,k.get('anchor')))
    return orig(s,xy,text,*a,**k)
ImageDraw.ImageDraw.text=spy
try:
    render.build_canvas({'hex':'3985a7','callsign':'AF1380','aircraft_type':'B738'},'departing',route={'airline_name':'Air France','callsign_iata':'AF1380','origin_iata':'ORY','origin_city':'Paris','destination_iata':'JFK','destination_city':'New York'})
finally:
    ImageDraw.ImageDraw.text=orig
top=[c for c in calls if len(c[0])==1 and c[1][1]==render.MARGIN]
joined=''.join(c[0] for c in top)
tag=render.runway_tag_text()
assert joined=='DEPARTING'+tag, repr(joined)
assert all(a=='la' for _,_,a in top)
assert top[0][1]==(render.MARGIN,render.MARGIN), top[0]
tf=render._role_font(render.TOP_TAG_FONT,render.device_config.theme_weight(render.device_config.DEFAULT_THEME_ID))
w=render._tracked_text_width(tf,tag,render.LABEL_TRACKING_PX)
tx=top[len('DEPARTING')][1][0]
assert round(abs(tx-(render.WIDTH-render.MARGIN-w)),2)==0.0, (tx,w)
assert round(abs(tx+w-(render.WIDTH-render.MARGIN)),2)==0.0
print('tracked top row OK: %d glyphs, tag_x=%.1f, flush right at %d'%(len(top),tx,render.WIDTH-render.MARGIN))
"</automated>
    <automated>server/.venv/bin/python3 -c "
import sys; sys.path.insert(0,'.')
from server.plane import render
F={'hex':'3985a7','callsign':'AF1380','aircraft_type':'B738'}
R={'airline_name':'Air France','callsign_iata':'AF1380','origin_iata':'ORY','origin_city':'Paris','destination_iata':'JFK','destination_city':'New York'}
for rid in render.device_config.RUNWAY_IDS:
    for theme in ('white','sky'):
        for st in ('departing','arriving'):
            render.build_canvas(F,st,route=R,runway_id=rid,theme_id=theme)
            w=render.device_config.theme_weight(theme)
            tf=render._role_font(render.TOP_TAG_FONT,w)
            t=render.runway_tag_text(rid)
            x=render.WIDTH-render.MARGIN-render._tracked_text_width(tf,t,render.LABEL_TRACKING_PX)
            assert max(x, 0.0)==x, (rid,theme,st,x)
print('overflow sweep OK across %d runways x 2 themes x 2 states'%len(render.device_config.RUNWAY_IDS))
"</automated>
  </verify>

  <done>
    `draw_top_labels()` draws both labels glyph-by-glyph at 6px tracking, the tag
    positioned by pre-computed tracked width rather than Pillow's right anchor,
    with both `_assert_within_canvas()` guards fed `_tracked_text_bbox()`
    geometry. All three broken checks are rewritten (not deleted, not weakened),
    both stale harness docstrings are corrected, three new checks are added, and
    `server/test_render.py` passes at its bumped count. The overflow sweep was
    demonstrated failing under a deliberately inflated tracking value and then
    restored to 6. `git diff --stat` across both tasks touches exactly
    `server/plane/render.py` and `server/test_render.py` and nothing else.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | This change is confined to local, server-side image composition. It introduces no new input parsing, no network call, no filesystem write, no dependency, and no new external data path. The only strings drawn are two already-validated, registry-sourced constants (`STATE_LABEL_TEXT`, `device_config.RUNWAYS[...]["tag_text"]`) that already reached this same function before the change. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-njw-01 | Denial of Service | `draw_tracked_text()` glyph loop in `server/plane/render.py` | low | accept | The loop is bounded by `len(text)` of a fixed registry constant (max 15 chars across all three registered runways, measured during planning). It is not reachable with attacker-controlled text: `draw_top_labels()` draws only `STATE_LABEL_TEXT[state]` and `runway_tag_text(runway_id)`, and `runway_tag_text()` already normalises an unrecognised/hostile runway id back to the default (T-06-06-01). Per-render cost is ~20 extra `draw.text()` calls on a poll cycle that already runs once per several minutes. |
| T-njw-02 | Tampering | top-row layout guard (`_assert_within_canvas()`) | low | mitigate | Replacing the untracked `draw.textbbox()` measurement with `_tracked_text_bbox()` is required so the guard measures what is actually drawn; leaving the old measurement would silently under-report a tracked run's width and stop guarding. Task 2 makes this substitution at both call sites, and the Task 2 overflow sweep exercises every registered runway x theme x state combination for real. |
| T-njw-SC | Tampering | package installs | n/a | accept | No package install of any kind. No `npm`/`pip`/`cargo` command is run by this plan; `requirements.txt`, `pyproject.toml` and `server/.venv` are untouched, so the Package Legitimacy Gate does not apply. |
</threat_model>

<verification>
Run in order after Task 2's commit.

1. Targeted harness:
   `server/.venv/bin/python3 server/test_render.py` - must print
   `render: N/N checks pass` and exit 0.

2. Full local suite:
   `scripts/run-all-tests.sh`

   **Expected outcome:** every harness green EXCEPT
   `server/test_poll_loop.py`'s pinned `panel.bin` `_DEFAULT_CONFIG_DIGEST`,
   which will mismatch because this change moves real render pixels.

   **This is expected and acceptable. Do NOT attempt to fix it.**
   - Do not recompute the digest locally. That file carries a standing rule
     (five re-pins in its history) that the digest must be read verbatim from a
     real CI FAIL output, because this Mac and the CI container render fonts
     differently - a locally-computed value would be wrong for CI.
   - Do not push, do not open a PR, do not read CI. A CI-based re-pin is a
     separate, heavier workflow this project runs only before merging a batch of
     changes, and it is explicitly **out of scope** for this quick task.
   - If the digest mismatch is the *only* failure, the plan has passed. Record it
     in the SUMMARY as a known, already-documented, pre-existing exception.
   - If ANY other harness fails, that is a real regression - fix it before
     finishing.

3. Scope check:
   `git diff --stat <base>..HEAD` must list exactly two files -
   `server/plane/render.py` and `server/test_render.py`.

4. Visual handoff artifacts for the pending on-glass check. Generate previews of
   both states on a flat and a dithered theme so the developer has something
   concrete to put on real glass later:

   ```
   server/.venv/bin/python3 server/plane/render.py --state departing --theme white --preview /tmp/njw-tracked-white-departing.png
   server/.venv/bin/python3 server/plane/render.py --state arriving  --theme white --preview /tmp/njw-tracked-white-arriving.png
   server/.venv/bin/python3 server/plane/render.py --state departing --theme sky   --preview /tmp/njw-tracked-sky-departing.png
   ```

   Open each and confirm by eye that the top row reads as tracked all-caps
   matching the spike's `tracked-6px` contact-sheet row, and that neither label
   clips or collides. These files are scratch artifacts - do not commit them.
</verification>

<success_criteria>
- [ ] `LABEL_TRACKING_PX = 6` exists in `server/plane/render.py` with a provenance
      comment naming spike 002a.
- [ ] `draw_tracked_text()` (public), `_tracked_text_width()` (private) and
      `_tracked_text_bbox()` (private) are resurrected with the original commit's
      exact naming split.
- [ ] The state label draws tracked at 6px, left-anchored at `(MARGIN, MARGIN)`,
      still 20px.
- [ ] The runway tag draws tracked at 6px, right-aligned by pre-computed tracked
      width so its run ends flush at `WIDTH - MARGIN`, still 18px.
- [ ] Both `_assert_within_canvas()` guards are fed `_tracked_text_bbox()`
      geometry, not the untracked `draw.textbbox()` measurement.
- [ ] Every registered runway id x both active states x flat and dithered themes
      renders with no assertion and a non-negative tag start x.
- [ ] No other font role, draw function, theme, or file is touched. Exactly two
      files in the diff.
- [ ] `server/test_render.py` passes at its bumped `EXPECTED_CHECK_COUNT`; the
      three broken checks were rewritten rather than deleted or weakened; two
      stale harness docstrings corrected.
- [ ] Both deliberate-regression demonstrations were performed and reverted
      (Task 1's tracking-advance check, Task 2's overflow sweep).
- [ ] `scripts/run-all-tests.sh`'s only failure is the known cross-platform
      `server/test_poll_loop.py` digest mismatch, left unfixed on purpose.
- [ ] **NOT VERIFIED ON REAL SPECTRA 6 GLASS.** The SUMMARY states this
      explicitly and prominently, records that tracking has never been checked on
      real ink at any point in this project's history, and lists the on-glass
      check as an OPEN follow-up under the D-13 precedent - it must not be
      claimed as done.
</success_criteria>

<output>
Create `.planning/quick/260831-njw-add-6px-letter-spacing-tracking-to-the-t/260831-njw-SUMMARY.md` when done.

The SUMMARY must record, at minimum:
1. What shipped (helpers resurrected, constant, `draw_top_labels()` rewrite,
   harness reconciliation with real before/after check counts).
2. The `server/test_poll_loop.py` `panel.bin` digest mismatch as a known,
   expected, pre-existing cross-platform exception that was deliberately NOT
   re-pinned - with the reason (CI-based re-pin is a separate workflow, out of
   scope for this quick task).
3. **A prominent "NOT VERIFIED ON REAL GLASS" section** stating that 6px tracking
   is screen-preview-validated only, has never been seen on real Spectra 6 ink at
   any point in this project's history (`hardware/BRINGUP-LOG.md` has no mention
   of tracking even though the technique shipped once in Phase 2/3), and that an
   on-glass check remains OPEN per D-13.
4. Paths to the scratch preview PNGs generated for that future on-glass session.
5. Any deviation from this plan, with the reason.
</output>
