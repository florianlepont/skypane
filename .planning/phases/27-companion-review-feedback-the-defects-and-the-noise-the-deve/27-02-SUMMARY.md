---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 02
subsystem: companion-value-controls
tags: [css-custom-properties, svg-geometry, dial, value-controls-js, i18n-scanner, agreement]
requires:
  - "27-01::_assert_surfaces_agree, _quiet_arc_minutes, _fraction_pair_minutes (the decoders this plan drives)"
  - "companion/static/value-controls.js::paint, ancestorWith, paintReadouts (25-04/25-05)"
  - "companion/pages/config_page.py::quiet_window_span, quiet_dial_svg, quiet_dial_handles_html (25-04)"
  - "companion/layout.py::VALUE_CONTROL_READOUT_* seam (25-05)"
provides:
  - "companion/static/value-controls.js::the pair seam (data-value-pair / data-value-pair-property, paintSweep())"
  - "companion/pages/config_page.py::QUIET_DIAL_PAIR_ATTR, QUIET_DIAL_PAIR_PROPERTY_ATTR, QUIET_DIAL_PAIR_PROPERTIES"
  - "companion/static/style.css::.js .quiet-dial .quiet-dial__arc (the CSS-driven arc override)"
  - "companion/pages/config_page.py::quiet_dial_readout_html() three-child caption"
  - "companion/test_browser_ux.py::_quiet_caption_minutes, _the_arc_the_handles_and_the_caption_agree_after_an_interaction"
affects:
  - "27-09 (the phase gate; this plan ticks no requirement itself — CFG-62/CFG-71 are 27-09's to tick)"
tech-stack:
  added: []
  patterns:
    - "a wrapper may publish its fraction a SECOND time, on a shared ancestor, under a server-named property — additive over the existing per-wrapper fraction, no parallel state"
    - "a wrapping/angular pair's fraction divides by (max - min) + 1, never (max - min) — the handle's own cosmetic-position fraction and a fraction that must decode to an exact integer are NOT the same fraction"
    - "a CSS custom-property-valued module constant that begins with \"--\" must be a DICT VALUE, never a top-level scalar — company/test_i18n.py's D-05 scan only excludes a leading \"--\" under the narrower dict-value rule"
    - "the server-rendered presentation attributes stay authoritative; a .js-scoped CSS rule only ever overrides what is already correct, computed from the SAME custom properties the server also renders inline at rest"
    - "a readout that must blank rather than lie, and can never itself compute the thing it would otherwise show, carries an EMPTY data-value-readout-text template — both of paintReadouts()'s branches then resolve to \"\", regardless of the base comparison's polarity"
key-files:
  created: []
  modified:
    - companion/static/value-controls.js
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/test_browser_ux.py
    - companion/test_config_page.py
decisions:
  - "no pathLength=\"1\" on the arc circle, contradicting the plan's own action text — measured directly (a headless-browser render of the shipped r=78 ring with the 23:00-07:00 dasharray) that pathLength=\"1\" combined with the REQUIRED-unchanged real-unit stroke-dasharray paints a second, spurious dash on the far side of the ring. The CSS override instead reads the pre-existing --quiet-dial-radius custom property (already on .quiet-dial, already read by the handle's own transform) via calc(fraction * radius * 2*pi)"
  - "the three CSS custom-property names live in a DICT (QUIET_DIAL_PAIR_PROPERTIES), not three separate ALL-CAPS constants as first written and as the plan's acceptance bar literally reads — the first shape tripped test_i18n.py's D-05 scan (a leading \"--\" is not a valid identifier start, so only the dict-value exclusion reaches it, the same path layout.py's {\"ok\": \"--ok\", ...} dict already relies on)"
  - "the pair fraction published to the shared ancestor divides by (max - min) + 1, not (max - min) as the handle's own --value-fraction does — found by the agreement check itself: reusing the handle's fraction decoded 23:00 as minute 1381, not 1380, because 1380/1439 of a turn and 1380/1440 of a turn are NOT the same number once rounded back to an integer minute"
  - "the caption's duration segment carries an EMPTY data-value-readout-text rather than a template — the shipped paintReadouts() base-equality rule blanks when the value EQUALS its base (built for a comparison sentence that is noise when unchanged), which is the OPPOSITE polarity a duration that must blank the moment something CHANGES needs; an empty template makes both of that rule's branches resolve to the same safe \"\", sidestepping the mismatch entirely rather than requesting a new script capability"
metrics:
  duration: ~2h30m
  completed: 2026-09-15
  checks_added: "browser-ux 81 -> 82; config-page 259 -> 260"
  browser_harness: "82/82, 0 SKIP, ~340s standalone"
  config_harness: "260/260"
requirements-completed: []
---

# Phase 27 Plan 02: the pair seam — an arc and a caption become functions of two values, not one — Summary

**value-controls.js now models a PAIR (a shared ancestor two handles publish their fraction onto, deriving a wrap-correct sweep), the arc is redrawn from it under `.js` while its presentation attributes stay byte-identical, and the caption's two endpoints follow the pair live while its duration blanks rather than lies — closing the exact gap 27-01 measured live on the tree with no mutation needed.**

## Performance

- **Duration:** ~2h30m
- **Tasks:** 4 of 4, plus two bugs the check itself found and fixed
- **Files modified:** 5 (`value-controls.js`, `config_page.py`, `style.css`, `test_browser_ux.py`, `test_config_page.py`)
- **Commits:** 6

## Commits

| # | Commit | Subject |
|---|---|---|
| 1 | `31aade5` | feat: the pair seam — value-controls.js models a wrapper PAIR |
| 2 | `2336074` | feat: the server publishes the pair; the arc reads it under .js |
| 3 | `4e719a9` | feat: the caption follows the pair, or says nothing |
| 4 | `2d0b3ba` | fix: the pair fraction wraps at max+1, not the handle's own max |
| 5 | `23bd305` | test: THE check — arc, handles and caption agree after an interaction |
| 6 | `a73013e` | fix: fold the pair-property names into a dict — the i18n scanner |

Commits 4 and 6 are bugs `_the_arc_the_handles_and_the_caption_agree_after_an_interaction()` and the full
`scripts/run-all-tests.sh` run respectively found on this plan's OWN code, fixed inline (Rule 1), and are
listed here rather than folded into an amended earlier commit, per the "never amend, always a new commit"
git-workflow rule.

## The decision that mattered most

**No `pathLength="1"` on the arc, contradicting the plan's own action text — because it corrupts the exact
thing the no-JS floor exists to protect.**

The plan's Task 2 action said: *"Add `pathLength=\"1\"` to the arc `<circle>`... Leave `stroke-dasharray` and
`transform` on the element exactly as they are."* Both halves cannot be true at once. `pathLength` recalibrates
what "one unit" of `stroke-dasharray` means for THAT element to the author-declared value — every dasharray
number on it, from ANY source (a presentation attribute or a CSS override), gets reinterpreted through it. The
presentation attribute this task must leave unchanged is expressed in REAL SVG USER UNITS
(`draw.unit_circle_dash_array()`'s own output, e.g. `"163.3628 326.7256"` for the seeded 23:00→07:00 window) —
not `pathLength`-relative fractions. Measured directly, before writing a line of CSS:

```python
# r=78 (QUIET_DIAL_RADIUS), the shipped 23:00-07:00 dasharray, pathLength="1" added
# sampled which shape paints at 14 angles around the ring
{"30": ["withPL", "noPL"], "60": ["withPL", "noPL"],   # both correct, drawn arc
 "210": ["withPL", None], "240": ["withPL", None]}     # withPL paints a SECOND arc here — noPL does not
```

`pathLength="1"` with the real-unit dasharray unchanged paints a second, spurious dash roughly opposite the
real one. That is not a subtle rendering nuance — it is a visibly wrong ring for every scripts-blocked visitor,
which is exactly the population the no-JS floor exists to protect. The fix used the constant that was already
sitting one line away and already load-bearing: `--quiet-dial-radius`, declared on `.quiet-dial` and already
read by the handle's own transform (`.quiet-dial__handle`'s `translateY(calc(-1 * var(--quiet-dial-radius)))`).
The `.js`-scoped override rule computes the same real-unit dasharray the server does,
`calc(fraction * var(--quiet-dial-radius) * 6.283185307)`, using the SAME already-pinned relationship a harness
already asserts (`_the_handle_rides_the_ring_the_emitter_drew`), so nothing new needed pinning. Verified against
the presentation attribute across every sampled angle and against `getComputedStyle` numerically — matches to
six decimal places once resolved.

The `.quiet-dial__radius` fallback costs exactly nothing `pathLength` would have saved: `QUIET_DIAL_RADIUS`
already lived in CSS before this plan (for the handle), so "the geometry constants never leave Python" is no
less true than it was — the ONE new number this plan adds to CSS is `6.283185307` (2π, a universal constant,
not a policy decision that could drift).

## The mutation that reproduces the shipped defect on this plan's own fix — quoted

Per the plan's own instruction, the three pair-publication lines from Task 1 were reverted and the live check
re-run against the real tree:

```
_assert_surfaces_agree: drag path — the 4 surfaces describing this value DISAGREE on
http://127.0.0.1:.../display. They read: the two native <input type="time"> fields -> (480, 1080);
the two handles' aria-valuenow -> (480, 1080); the arc's resolved geometry -> (480, 1380);
the caption's text -> (480, 1080). The interaction asked for (480, 1080). A surface that did not
follow is a surface that is now lying to the visitor about a value the page beside it shows correctly
```

**This is the D17 defect, reproduced on demand, on this plan's own code with the three lines removed:** the
arc is frozen at the pre-interaction value while every other surface follows. The lines were restored
immediately after and the check re-verified green.

**A criterion that did not evaluate as predicted, recorded rather than adjusted quietly:** the plan's Task 4
text says this mutation "must FAIL, naming the arc **and the caption** as the surfaces that disagreed." On
this tree, only the arc disagrees — the caption's own text still reads `(480, 1080)`, correctly. The reason is
structural, not a weaker mutation: the caption's two endpoints (Task 3) are wired through the PRE-EXISTING,
independent `paintReadouts()` seam, which reads each field's own value directly and has no dependency on the
pair-seam custom properties Task 1 adds at all — reverting Task 1's three lines cannot touch it. The mutation
still does exactly what it exists to do (reproduce the shipped defect and name the surface that is now lying),
just through a narrower, more cleanly separated failure than the plan predicted. This is a property of the
design (Task 3 does not couple the caption to Task 1's pair seam, because nothing about a single-field
endpoint NEEDS the pair) rather than a shortfall in the check.

A second mutation — a no-op drag (the end handle picked up and put back at its own current position) —
correctly fails the check's "differs from before" clause rather than passing vacuously:

```
_assert_surfaces_agree: no-op drag — all 4 surfaces on http://127.0.0.1:.../display agree on
(480, 1380), which is exactly what was there BEFORE the interaction. They read: the two native
<input type="time"> fields -> (480, 1380); the two handles' aria-valuenow -> (480, 1380);
the arc's resolved geometry -> (480, 1380); the caption's text -> (480, 1380). The interaction
changed nothing, so this reading proves nothing: a no-op is the cheapest way to make every
surface on a page agree
```

## Checks that failed the vacuity question, and what was done

- **The pair-seam markup check** (`_the_pair_seam_publishes_both_handles_onto_the_shared_ancestor`) would have
  been vacuous if it only asserted the two `data-value-pair-property` attributes were PRESENT. It additionally
  asserts they are **different** from each other and are exactly `{start, end}` — a check that passed a page
  where both handles named the same property would have let the sweep derivation compute `(x - x + 1) % 1 = 0`
  for every window, silently.
- **The agreement check's own no-op mutation** (above) exists because "the four surfaces agree" alone is
  satisfiable by a page that changed nothing — the plan's own D-32 lesson applied reflexively to this plan's
  own new check, not only to the code it tests.
- **The byte-identical presentation-attribute claim** was not left as an assertion in prose. It is verified
  both in a dedicated `test_config_page.py` check (`arc["stroke-dasharray"] != expected_dash` compares against
  `draw.unit_circle_dash_array()`'s own output) and, separately, literally diffed below.

## The byte-identical-markup proof — run, not asserted

Per the plan's explicit instruction to verify literally rather than assume:

```python
# companion/pages/config_page.py at HEAD~6 (before Task 1) vs. HEAD (after all six commits)
for start, end in [("23:00","07:00"), ("08:00","18:00"), ("00:00","06:00"), ("23:59","00:00")]:
    svg_old = old_mod.quiet_dial_svg(old_mod.quiet_window_span(start, end))
    svg_new = new_mod.quiet_dial_svg(new_mod.quiet_window_span(start, end))
    assert svg_old == svg_new   # True for all four windows, including the wrap and the 1-minute floor
```

`quiet_dial_svg()`'s own output — the `<svg>` carrying both `<circle>` shapes, presentation attributes
included — is **byte-identical** before and after this plan's entire diff, across a wrapping window, a
same-day window, a quarter-day window and the 1-minute floor. The arc's `stroke-dasharray`/`transform` are
provably untouched; everything this plan adds sits in the SURROUNDING markup (`quiet_dial_html()`'s new
attributes on `.quiet-dial`, `quiet_dial_handles_html()`'s new attribute per handle, `quiet_dial_readout_html()`'s
new child spans) which `quiet_dial_svg()` itself never sees.

## What was built

### Task 1 — the pair seam in value-controls.js

Two new attribute constants (`data-value-pair`, `data-value-pair-property`), reusing the existing
`ancestorWith()` walker (`while (node` stays at exactly 2 occurrences — no second walker). `paint()` gains a
conditional block, additive over the existing `--value-fraction` write: if the wrapper declares a pair
property, it finds the nearest ancestor carrying the pair marker and publishes its fraction there too, then
calls `paintSweep()`, which reads BOTH published fractions back off the ancestor's own style (never a cached
number) and derives `(end - start + 1) % 1` — the wrap. A wrapper with no pair declaration is byte-identical
to before this task; the wake-interval slider's own checks pass unchanged.

`CSS.supports('width', 'calc(mod(1,1) * 1px)')` was confirmed `True` in the harness Chromium (re-verified
independently in this plan, matching 27-01's own finding). The sweep is still derived in JS rather than CSS
`mod()`, per 27-RESEARCH.md's recorded trade-off: `mod()` support in the SHIPPED DEVICE'S browser (not the
test harness) is unverified, and an unsupported `mod()` silently drops the whole declaration — reproducing
this exact defect with a different, invisible cause. The trade-off is unchanged by this plan; it is recorded
here again because the plan asked for it to be.

### Task 2 — the server publishes the pair; the arc reads it under `.js`

`quiet_dial_html()` now emits the pair marker and all three fractions as inline style on `.quiet-dial`,
computed from the SAME `span` triple `quiet_dial_svg()` draws from (no second window arithmetic). Each handle
wrapper (`quiet_dial_handles_html()`) declares which property it publishes. `style.css` gains one `.js`-scoped
rule, `.js .quiet-dial .quiet-dial__arc`, that redraws `stroke-dasharray`/`transform` from the three ancestor
properties plus the pre-existing `--quiet-dial-radius`. The arc's own presentation attributes are emitted
completely unchanged (see the byte-identical proof above). `QUIET_DIAL_STROKE`'s stale comment
("64 - 7 - 3 = 54", a figure from before the ring grew to 176px) is corrected to the real, already-shipped
arithmetic (176 - 14 - 3 = 78) in the same commit, since it sits beside code this task already touches.

### Task 3 — the caption follows the pair, or says nothing

`quiet_dial_readout_html()` splits its `<p>` into three `data-value-readout` children: two endpoints (bare
`"#"` token templates, substituting each field's own raw value through the shipped `paintReadouts()` seam —
no clock-formatting logic added anywhere) and a duration span. At rest, the visible text (tags stripped) is
byte-identical to what shipped before this task.

**The duration child's own design departs from the plan's literal instruction in one respect, recorded as
PROVISIONAL per the plan's own request.** The plan says to give it `data-value-readout-base` set to the saved
window's own value "so that `paintReadouts()`'s shipped rule blanks it the instant the pair moves away from
what the server rendered." Read precisely, that shipped rule does the OPPOSITE: it blanks when the CURRENT
value EQUALS its base (correct for 25-05's wake-battery-relative readout, a delta sentence that is noise when
nothing changed) and SUBSTITUTES a raw number otherwise — which for a duration would mean showing a bare,
unrelated minute count (e.g. `"1380"`) the moment the pair moves, not blanking. The fix keeps
`data-value-readout-base` (the plan's acceptance bar asks for it, and it documents intent for a future,
smarter rule) but gives the element an EMPTY `data-value-readout-text`. Both of `paintReadouts()`'s branches
then resolve to `""` once this element is next painted, regardless of the base comparison — the safe side,
which can never show a garbage number, at the cost of also blanking on a genuine no-op touch (an edge case no
check in this plan exercises). **Known limitation, not silently patched over:** the ORIGINAL, broader
provisional trade-off the plan asked for is unchanged — the duration visibly disappears during a drag and is
only re-stated by the server on the next load; the fallback if a reviewer rejects the blanking is C2 from
27-RESEARCH.md (server-emitted per-unit templates plus the ladder's own thresholds).

No duration arithmetic or wording exists in any `.js` file — this task touches only `config_page.py`.

### Task 4 — THE check, plus two bugs it found on this plan's own code

One check (`_the_arc_the_handles_and_the_caption_agree_after_an_interaction`), covering a real pointer drag
(end handle to 18:00, from a fixture already at 08:00 start — the developer's own recorded window) AND, in
the same check, a preset press (Night, 23:00→07:00, the wrap through midnight) from wherever the drag left it.
All four surfaces — native inputs, handles' `aria-valuenow`, the arc's RESOLVED geometry, the caption's text —
decode through 27-01's `_assert_surfaces_agree()` to one canonical `(start_minute, end_minute)` pair, run in
both shipped themes. Separately, a scripts-blocked half confirms the arc's presentation attributes still
decode to whatever window is actually on disk (neither the drag nor the preset above ever clicked Save).

A new decoder, `_quiet_caption_minutes()`, reads the caption's live text as bare minute-of-day integers (not
HH:MM) — the format Task 3's endpoint spans actually produce once touched by script, matching the canonical
unit 27-01 already chose.

Supersedes the "preset moves both handles" and "the wrap reads as eight hours" clauses
`_dragging_and_keying_a_handle_reach_disk()` used to also carry (endpoint-only claims the plan names
explicitly as superseded); that check keeps its still-distinct "a preset is a silent script write" proof.

**Two bugs this check found on this plan's own code, fixed inline (Rule 1):**

1. **The pair fraction reused the handle's own cosmetic `--value-fraction`, which is off by design.**
   `quiet_dial_handle_fraction()`'s own comment already documents that the handle's position deliberately uses
   `(value - min) / (max - min)` rather than `minute / 1440`, "at most 0.25 degrees" different, "worth it" for
   a PAINTED handle. Reusing that same fraction for the pair-seam publication carried the same error into
   something decoded back to an EXACT integer minute: `1380/1439` of a turn resolves to minute **1381**, not
   1380. Fixed by dividing the PAIR fraction by `(max - min) + 1` instead — the wrap point one step past max,
   generically correct for an inclusive-integer-range angular control, reaching exactly
   `QUIET_WINDOW_MINUTES_PER_DAY` (1440) with no knowledge of that constant in the script at all.
2. **Three top-level `"--quiet-*-fraction"` string constants tripped `companion/test_i18n.py`'s D-05 scan.**
   Found by running the FULL suite (`scripts/run-all-tests.sh`), not either harness this plan's own tasks name
   in isolation. A leading `"--"` is not a valid identifier start, so the scanner's lowercase-identifier
   exclusion (every other `*_ATTR` constant in this file relies on it) never reaches it —
   `companion/layout.py`'s own `FRACTION_PROPERTY` comment already recorded this exact trap as the reason no
   Python constant exists there for `"--value-fraction"`. Folded the three names into one dict,
   `QUIET_DIAL_PAIR_PROPERTIES`, scanned under the narrower dict-value exclusion that DOES reach a leading
   `"--"` — the same path `layout.py`'s own `{"ok": "--ok", "warn": "--warn", "error": "--error"}` dict
   already relies on. Still satisfies the plan's own acceptance bar ("the three property names exist as
   module constants, not as literals at the call site").

`companion/test_config_page.py`'s own `EXPECTED_CHECK_COUNT` was also re-derived by running at this point
(259 → 260) — missed in the Task 2/3 commits, found the same way (running the full suite).

## Re-derived counts, obtained by running

- `browser-ux`: **81 → 82** (`EXPECTED_CHECK_COUNT` updated; the new check is the one addition).
- `config-page`: **259 → 260** (`EXPECTED_CHECK_COUNT` updated; the pair-seam markup check is the one
  addition — the two readout-structure fixes inside pre-existing checks add no new check of their own).
- `sandbox baseline, verified BY NAME`: exactly 5 — `POST /airlines/resolve` WR-11, `POST
  /airlines/manual-resolutions/{prefix}/delete` WR-11 (both `test_companion_app.py`), `add_entry()`/
  `delete_entry()` WR-11 (both `server/test_manual_resolutions.py`), and `anomaly_active()`
  (`test_status_pages.py`). **No sixth failure.**

## Files Created/Modified

- `companion/static/value-controls.js` — the pair seam (`paint()`'s additive block, `paintSweep()`) and the
  wrap-correct fraction fix.
- `companion/pages/config_page.py` — `QUIET_DIAL_PAIR_ATTR`/`QUIET_DIAL_PAIR_PROPERTY_ATTR`/
  `QUIET_DIAL_PAIR_PROPERTIES`, `quiet_dial_html()`'s inline pair style, `quiet_dial_handles_html()`'s per-handle
  property, `quiet_dial_readout_html()`'s three-child caption, `QUIET_DIAL_STROKE`'s corrected comment.
- `companion/static/style.css` — the `.js .quiet-dial .quiet-dial__arc` override rule.
- `companion/test_browser_ux.py` — `_quiet_caption_minutes()`,
  `_the_arc_the_handles_and_the_caption_agree_after_an_interaction()`, the superseded-clause note in the
  neighbouring check, `EXPECTED_CHECK_COUNT` 81→82.
- `companion/test_config_page.py` — the pair-seam markup check, the two readout-structure check updates,
  `EXPECTED_CHECK_COUNT` 259→260.

## Decisions Made

See `decisions` frontmatter and "The decision that mattered most" above for the full reasoning on each; in
one line each:

1. No `pathLength="1"` — measured to corrupt the no-JS floor; `--quiet-dial-radius` + `calc()` instead.
2. The three property names live in a dict (`QUIET_DIAL_PAIR_PROPERTIES`), not three top-level constants —
   the literal shape the plan's acceptance bar describes trips the i18n scanner; a dict value does not.
3. The pair fraction divides by `(max - min) + 1`, not `(max - min)` — found by the check itself.
4. The duration readout's template is empty, not the saved-duration template the plan's literal text implies —
   the shipped base-equality rule's polarity does not fit a "blank on change" sentence.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `pathLength="1"` corrupts the no-JS arc with the presentation attribute left unchanged**
- **Found during:** Task 2, before writing the CSS override (measured directly, not assumed)
- **Issue:** the plan's own action text asks for `pathLength="1"` while ALSO requiring `stroke-dasharray`/
  `transform` stay unchanged (real user units); the two are incompatible and the combination paints a second,
  spurious dash
- **Fix:** no `pathLength`; the CSS override computes the same real-unit dasharray via the pre-existing
  `--quiet-dial-radius` custom property and a literal 2π
- **Files modified:** `companion/pages/config_page.py`, `companion/static/style.css`
- **Verification:** headless-browser angle sampling (quoted above); `test_config_page.py`'s new check asserts
  no `pathLength` attribute and the exact dasharray match against `draw.unit_circle_dash_array()`
- **Committed in:** `2336074`

**2. [Rule 1 - Bug] the pair fraction inherited the handle's own ~0.25°-tolerant fraction**
- **Found during:** Task 4, the agreement check's own first real run (arc decoded to (1380, 1381) instead of
  (1380, 420) after the Night preset)
- **Issue:** `paint()`'s existing `FRACTION_PROPERTY` write deliberately uses `(value-min)/(max-min)`, correct
  for a painted handle, wrong once decoded back to an exact integer minute
- **Fix:** the pair-seam publication computes its own fraction, `(value-min)/((max-min)+1)`
- **Files modified:** `companion/static/value-controls.js`
- **Verification:** the manual reproduction script and, subsequently, the full `test_browser_ux.py` suite,
  82/82
- **Committed in:** `2d0b3ba`

**3. [Rule 1 - Bug] three top-level "--quiet-*-fraction" constants failed the D-05 i18n scan**
- **Found during:** running `scripts/run-all-tests.sh` after Task 4 (not either harness named by this plan's
  own verification block in isolation)
- **Issue:** a leading "--" is not a valid identifier start, so the scanner's lowercase-identifier exclusion
  (rule a) never reaches a top-level constant valued that way — matching `companion/layout.py`'s own recorded
  reason for never giving `--value-fraction` a Python constant
- **Fix:** folded the three names into one dict, `QUIET_DIAL_PAIR_PROPERTIES`, scanned under the dict-value
  exclusion that does reach a leading "--"
- **Files modified:** `companion/pages/config_page.py`, `companion/test_config_page.py`
- **Verification:** `companion/test_i18n.py` 24/24; `companion/test_config_page.py`'s
  `EXPECTED_CHECK_COUNT` re-derived (259→260) in the same commit, also found by the full-suite run
- **Committed in:** `a73013e`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs this plan's own code introduced, each found by running
something rather than assumed). **Impact on plan:** all three were necessary for correctness; none changed
this plan's scope, files touched, or the must-haves it satisfies. No scope creep.

## Issues Encountered

None beyond the three auto-fixed bugs above, each already documented with how it was found and resolved.

## Next Phase Readiness

- The pair exists in the script's model for the first time; an arc and a caption sentence have something to
  be a function of.
- The server's presentation attributes are unchanged and provably byte-identical (diffed, not assumed) —
  still correct with scripts blocked.
- ONE check proves all four surfaces agree after both interaction paths, mutation-tested twice, both messages
  quoted above.
- `EXPECTED_CHECK_COUNT` re-derived by running in both harnesses touched.
- No new script, no new route; the deferred-script pin stays at 15.
- CFG-62/CFG-71 are NOT ticked by this plan (27-09's job, per the orchestrator's own instruction) — `STATE.md`,
  `ROADMAP.md` and `REQUIREMENTS.md` are untouched.
- The duration-readout design (empty template, base recorded but functionally inert today) is PROVISIONAL and
  named as such — a human reviewer may prefer C2 (server-emitted per-unit templates) from 27-RESEARCH.md if
  the disappearing duration is rejected; that is a design conversation, not a defect.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*
