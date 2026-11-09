# Phase 62: Plane Screen Redesign (giant-lettering design) - Context

**Gathered:** 2026-11-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the look of the e-ink plane screens with the giant-lettering design validated in the design brief: the destination is set in huge Anton lettering behind the aircraft, a colour pairing carries the mode, and the generic status screens share one calm layout. It covers the flight screens and the status screens, in portrait (1200x1600) and landscape (800x480). The current layout and its golden fixtures stay untouched until the owner chooses to switch; the new layouts are added beside them.

Not part of this phase: the pairing screen (typed from close up), any OTA push to the live frame, anything in Phase 47, 47.1 or `hardware/`.

</domain>

<decisions>
## Implementation Decisions

### Layouts and how a frame picks one
- **D-01:** Four layouts ship: A (large nose entering from the right edge, smaller rear half entering from the left edge below it), B (whole aircraft, centred), C (lettering compressed at the top, whole aircraft below it, at the bottom of the frame; not a coloured band), and A with the diagonal band. All four were mocked and validated by the owner: A, B and C as in the three-layout and landscape sheets of the brief, and A with the diagonal band. C is built as mocked (lettering at the top, aircraft at the bottom; unrelated to the diagonal band), with the same font and pairings as the others.
- **D-02:** The layout is a per-frame setting in the companion's Personalisation tab, next to the theme, as the theme is chosen today (see `companion/pages/personalisation_cards.py` and `config_page.PERSONALISATION_ROUTES`). Default for a frame that chose nothing: B (whole aircraft), applied to every frame at deploy, the live frame included (owner decision, 2026-11-09). Risk to report: this changes the picture shown by the live frame that Phase 47 measures; the deploy is the owner's call and nothing is merged or deployed from this branch.
- **D-03:** The previous-flight card is removed in the new layouts (removed in every mock-up; the old layout keeps it).

### Colours and arrival
- **D-04:** The 18 themes are replaced, for the new layouts, by five field / lettering pairings: grey / black, light blue / blue, light red / red, light yellow / yellow, white / black. Stored old theme ids convert to the closest pairing.
- **D-05:** Yellow needs a lighter field (about 75% white) and, for small text, yellow dithered toward black.
- **D-06:** A landing uses a second colour the owner picks from the pairings (the existing "theme when arriving" setting), not a fixed green. Departure vs arrival is carried by the field colour, since the small direction word is unreadable at 3 m.
- **D-07:** Per-airline colour rules keep working: a rule resolves to a pairing.

### Destination lettering
- **D-08:** Font is Anton (SIL OFL), vendored under `server/assets/fonts/` with its licence text and a `VENDOR.md` entry. On flight screens each line is stretched to the frame width; status screens use natural proportions.
- **D-09:** Names are split into 2-3 lines in portrait, never cutting a word where a space or hyphen exists. Exceptions (owner decision): in landscape the destination is one stretched line, and in portrait a name of 3 letters or fewer (Pau, Aix) stays on one line. Rule: spaces and hyphens first, then syllables. The split is 100% automatic: there is no table of manual corrections and no admin editing of splits, so the rule itself has to produce acceptable results for any name.
- **D-15:** The direction word (DEPARTING / ARRIVING, with the airport or runway tag where the current layout shows one) is always displayed on every flight layout, in portrait and in landscape, including landscape A, B and C which the mock-ups drew without it (owner decision, 2026-11-09). The hyphen of a hyphenated destination is dropped: the owner does not want it kept in the lettering.
- **D-10:** When the destination is unknown and only the airline is known, the airline name is set in the giant lettering instead of the city.

### Status screens
- **D-11:** Seven screens get the new look (watching, quiet hours, display off, battery empty, no connection, updating, retired); pairing does not. Generic: no band, no theme colours. Watching is white with black ink; the others use the dithered dark field with white ink.
- **D-12:** Calm layout: 110 px margins, Anton at natural proportions, flush left, whole words only, each line sized to fit; the production icon (about 120 px) sits top-left above the small label; body text is small, bottom-left. Watching shows "RUNWAY / 3" as the keyword with "WATCHING" as the label; updating reads "FIRMWARE / UPDATE" (label "INSTALLING"); no connection reads "NO / CONNECTION".
- **D-13:** Status screens ship in portrait and landscape; the landscape versions have to be designed in this phase.
- **D-14:** The masks for "no connection" and "updating" are regenerated for the next firmware release (two colours exactly). No OTA is pushed in this phase and nothing touches the live frame.

### Claude's Discretion
- Exact margins, line spacing and font sizes inside the ranges shown in the mock-ups.
- How to redraw the icons at the larger size so their edges are clean.
- Per-aircraft-type crop points for the nose and rear halves of layout A.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design
- `.planning/notes/plane-screen-design-brief.md` - validated direction, retained layouts, colour pairings, status screens, what changes in code, open questions.
- `.planning/notes/plane-screen-design-brief/` - every mock-up image the brief cites.
- `design-exploration/plane-screen/` - standalone mock-up scripts (`mock_*.py`); reference geometry and parameters, not production code.

### Current renderer
- `server/plane/render/layout.py`, `style.py`, `hold_screens.py`, `glyphs.py`, `landscape*.py` - current portrait and landscape families.
- `server/themes.py`, `server/device_config.py` - theme registry and per-device settings.
- `server/plane/colour_rules.py`, `server/plane/illustrations.py` - per-airline colour rules and aircraft illustrations.
- `server/panel_format.py`, `server/plane/dither.py` - palette and dithering.
- `server/hardware.py` - hardware profiles and layout families.
- `server/fixtures/golden` and `server/test_render.py` - golden fixtures that must not change for the current layout.

### Roadmap
- `.planning/workstreams/v1-2/ROADMAP.md` (Phase 56 per-hardware rendering; Phase 62 entry).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `layout.build_canvas()` and the landscape family: the dispatch point for a new layout family.
- `dither.dithered_state_background()`: field generator; its lighten fraction is capped below 0.5 today, yellow needs about 0.75.
- `glyphs.draw_*_icon`: production icons, drawn at 76 px, to be redrawn larger.
- `hold_screens._build_hold_canvas()`: shared composition for the status screens; the firmware masks come from `_build_no_connection_canvas()` and `_build_updating_canvas()`.

### Established Patterns
- Rendering is deterministic and golden-tested; a new layout needs its own fixtures.
- Comments and docs in English, no plan or phase ids in comments (`scripts/check_comment_history.py`), function-size gate of 80 lines.

### Integration Points
- Companion: a layout setting per frame in the Personalisation tab (English and French strings in `companion/i18n_fr/`), following the existing Personalisation cards.
- Device config: the layout and the pairing ids join the per-device configuration, with conversion of stored theme ids.

</code_context>

<specifics>
## Specific Ideas

- The nose and rear halves must keep the impression that the aircraft leaves the frame: cuts stay outside the visible area.
- The flight number sits right-aligned bottom-right with the band, in plain ink on the light field.
- Direction of reading from 2-3 m: letters of about 2 cm cap height need about 120 px at 150 ppi.

</specifics>

<deferred>
## Deferred Ideas

- Real-panel contrast and dither check on glass; the mock-ups are screen renders. Planned as a validation step inside this phase, with the owner.
- Redrawing the aircraft illustrations for the new layouts, if the current ones prove too soft when enlarged.

</deferred>

---

*Phase: 62-Plane Screen Redesign (giant-lettering design)*
*Context gathered: 2026-11-09*
