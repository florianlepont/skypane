# Accessibility & Contrast

## Design Decisions

**06.6.2's accent darkening.** Light-mode `--color-accent` moved from `#E8622C` SUPERSEDED to `#B13F16` (D-14, UXA-04) to meet WCAG AA text contrast — the accent is used as text (links) and as a fill with white/`--color-on-accent` text (primary buttons), so both directions needed checking. The accent-hover token moved with it, from `#D2521F` SUPERSEDED to `#963610`. Dark-mode accent (`#FF8A5C`) was already compliant and is unchanged. `WCAG_AA_NORMAL_TEXT` (4.5), `WCAG_AA_LARGE_TEXT` (3.0) and `WCAG_AA_UI_COMPONENT` (3.0) in `companion/contrast_check.py` are the named threshold constants this change was checked against, reproduced from the published WCAG 2.1 SC 1.4.3 spec text and verified in `06.6.2-RESEARCH.md` to reproduce `06.6.1-UX-AUDIT.md`'s own published contrast numbers exactly.

**The three-level surface model.** A two-level model (`--color-dominant` doing double duty as both page background and card surface) could not survive the accent/contrast work: once cards needed to visually separate from the page again, one token could no longer serve both roles without either flattening the page (no card definition) or losing the warm-canvas direction. 06.6.2 (D-14) split this into `--color-canvas` (page background), `--color-dominant` (primary card/control surface) and `--color-secondary` (secondary/elevated/nav surface), in both themes. `.page-section` was the one component this split initially missed — it kept a pre-split "no background at all" rule that was correct under the two-level model but rendered Config's Poll/LED sections and both of Preview's sections as shadowed canvas-coloured blocks once every other card had moved to the dominant surface; that gap is closed in the current stylesheet.

**The executable colour-separation contract.** For three phases, "the accent must stay distinguishable from every status colour" was prose only in `style.css`'s header comment, and it named only the accent-vs-warn pair — the one pair 06.6.1's D-04 actually examined and accepted (dE76 28.6 in light mode). That gap is exactly how 06.6.2's WCAG-AA accent darkening was able to move the accent to within dE76 22.9 of the then-current `--color-status-error` (`#DC2626`) unnoticed: contrast checks (foreground-vs-background) stayed green throughout, because contrast and signal-separation are different questions — contrast asks "can this be read against that background," separation asks "can these two colours be told apart as different signals at a glance." The heading-color-consistency debug session closed the gap by adding three functions to `companion/contrast_check.py` — `hue_degrees()`, `hue_separation()` (0-180°, shortest angular distance) and `perceptual_distance()` (CIE76 delta-E in CIE L*a*b*, D65) — plus two named thresholds: `MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0` (the primary gate, applied to every accent-vs-status pair in both themes, calibrated to the one pair 06.6.1's D-04 already validated) and `MIN_SIGNAL_HUE_SEPARATION = 24.0` (the secondary gate, applied to the accent-vs-ERROR pair only, since both are saturated red-oranges and hue angle is the only channel left to separate them with once lightness is controlled for). `companion/test_contrast_check.py`'s separation section enforces both on every accent/status pair — a token change that violates either now fails a test, not a reading of a comment.

**The status-error recolour.** `--color-status-error` moved from `#DC2626`/`#F87171` (light/dark) SUPERSEDED to `#BE123C`/`#FB7185` in the heading-color-consistency debug session, once the new separation contract measured the old error red at only dE76 22.9 / 15.9° from the darkened accent — closer than the accent-vs-warn pair 06.6.1 had already accepted, which is why a primary-action button and an error edge were reading as the same brick red on screen. Moving to crimson (hue ≈345°) restores separation (dE76 29.3, 30.5° hue) without touching the accent, so UXA-04's WCAG-AA fix stays intact; it also raised the token's own worst-case contrast on the three light surfaces from 3.96 to 5.16, making it safe as text and not only as a fill.

**Focus-visible floor.** Every focusable element (`a`, `button`, `input`, `select`) gets a 2px solid `--color-accent` outline with a 2px offset on `:focus-visible` — an accessibility floor (D-22) never removed without a replacement.

**Skip link.** `.skip-link` is the first focusable element in `<body>` (06.6.2-05, UXA-10) — visually hidden 40px above the viewport until it receives keyboard focus, at which point it becomes the first visible, high-contrast element on the page (accent fill, `--color-on-accent` text), letting a keyboard user bypass the nav entirely.

**`.visually-hidden` utility.** Off-screen-but-present text (the Health nav-tab's "— attention needed" suffix, the runway check glyph's "Selected" label). Must never be given `display: none` or `visibility: hidden` — either removes the text from the accessibility tree and defeats its only purpose. The correct implementation is the file's own: `position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0;`.

**Form-control caveat (quick task 260902-l9w).** On a `<span>` this utility's own 1px sizing is the whole story. On an `<input>` or `<select>` it is not: the global native `input, select` rule's 44px touch-target minimums (`min-height`/`min-width`) are a layout-time floor, not a cascade competitor, so they clamp the utility's 1px box back up to a real 44x44 box regardless of which rule wins on specificity. This is exactly the bug that let the three Runway-picker radios (`config_page.py`'s `runway_fieldset()`) paint a visible 44x44px native radio dot on real mobile browsers despite carrying `class="visually-hidden"`. The fix is a second, narrowly scoped rule — `input.visually-hidden, select.visually-hidden` — that clears both minimums (and native control theming) for elements carrying this class; it does not touch the `.visually-hidden` block itself or the global floor. See `references/control-density.md`'s touch-target floor register for the exempt-by-delegation category this creates.

**Global reduced-motion override.** A single `@media (prefers-reduced-motion: reduce)` block (D-19), placed after the token blocks and before the universal box-sizing reset, sets `transition-duration`/`animation-duration` to `0.01ms` and `scroll-behavior` to `auto` on every element — every later rule's colour/border/shadow transition inherits this for free. `.js .mobile-nav`'s own `max-height` transition carries one narrow additional override (`transition: none`) inside the same media query, since its transition duration is otherwise set inline on the base rule rather than only via the global shorthand properties.

**Floors that survived 06.6.4's density pass.** 06.6.4 traded the 44px AAA touch-target floor away on four named selectors (buttons, nav links, theme segments, filter input — see `references/control-density.md`), but every accessibility floor in this section was left untouched by that pass: focus-visible outlines, the skip link, `.visually-hidden`'s implementation, and the reduced-motion override all still apply exactly as described above regardless of any component's visual density.

**No-JS degradation floors.** `.js`-gated rules only ever govern the *visual/animated* state; the underlying accessibility state is set independently by JS and degrades safely when JS never runs. `.js .mobile-nav`'s `max-height: 0; overflow: hidden` clipping rule is scoped under `.js` (added unconditionally by `nav-dropdown.js`'s first statement) — without that class ever appearing, the base `.mobile-nav` rule alone renders the panel in its natural, unclipped, fully visible document flow (UXA-12's floor). Separately, `nav-dropdown.js`'s own `panel.hidden` toggling (UXA-02's floor) is what removes the closed panel from the accessibility tree and tab order once JS confirms it is closed — the two rules must never be edited independently of each other. `.js [data-static-save-fallback] { display: none; }` similarly only hides Settings' always-server-rendered bottom Save button once `.js` proves script ran; without JS, that button remains the only way to save (D-06 graceful degradation).

## CSS Patterns

```css
/* Focus-visible floor */
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Skip link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--color-accent);
  color: var(--color-on-accent);
  padding: var(--space-sm) var(--space-md);
  z-index: 10;
  border-radius: 0 0 var(--radius-control) 0;
}
.skip-link:focus { top: 0; }

/* Screen-reader-only utility — never display:none / visibility:hidden */
.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

/* Global reduced-motion override */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

```python
# companion/contrast_check.py — named thresholds callers must reference by name
WCAG_AA_NORMAL_TEXT = 4.5
WCAG_AA_LARGE_TEXT = 3.0
WCAG_AA_UI_COMPONENT = 3.0
MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0   # every accent-vs-status pair, both themes
MIN_SIGNAL_HUE_SEPARATION = 24.0        # accent-vs-error only
```

## What to Avoid

- Reverting the accent toward the SUPERSEDED `#E8622C` value without re-checking WCAG AA text contrast — that is the regression 06.6.2 (D-14, UXA-04) fixed.
- Shifting either the accent or a status colour without re-running `companion/test_contrast_check.py`'s separation section — a contrast-clean change can still collide as a signal, which is exactly how the accent/error collision happened the first time.
- Giving `.visually-hidden` a `display` or `visibility` value that removes it from the accessibility tree — its entire purpose is to stay in the tree while invisible on screen.
- Adding a per-rule reduced-motion block for a simple colour/border/shadow transition — the global override (D-19) already covers it; a redundant per-rule block is dead code, not a safety net.
- Narrowing any of the three-file DOM contract's pieces (`.js .mobile-nav`'s clipping rule, `nav-dropdown.js`'s `panel.hidden` toggle, and the underlying `NAV_TOGGLE_ID`/`MOBILE_NAV_ID`/`MOBILE_NAV_OPEN_CLASS` literals) independently of the other two — they must be edited together or the no-JS floor silently breaks.

## Origin
Synthesized from: 06.6.2-companion-ux-accessibility-and-responsive-hardening (D-14 through D-17, D-19, D-21, UXA-04, UXA-10, UXA-12), the heading-color-consistency debug session (status-error recolour, executable colour-separation contract), and `companion/static/style.css` / `companion/contrast_check.py` read live at execution time (quick task 260901-t00).
