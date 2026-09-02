# Visual Direction & Typography

## Design Decisions

**Winning variant, origin: Sketch 001, Variant B ("Full editorial").** The direction this sketch established still governs today: a warm serif on headings, cards with visible relief instead of flat bordered boxes, and a generally airier layout — but nearly every *specific value* below has since moved, in some cases more than once. Read the current value first on each line; the sketch's own draft value follows, marked SUPERSEDED.

- **Background:** the current three-level surface model uses `--color-canvas: #F7F4EF` for the page and `--color-secondary: #EEE8DE` for nav/sidebar surfaces (light mode) — not this sketch's own draft warm-tint pair, `#FBF9F6` for the page body / `#F3EEE7` for sidebar/header surfaces SUPERSEDED. Those draft values were themselves already a revision of 06.3's cool off-white (`--color-dominant: #FAFBFD` / `--color-secondary: #EEF1F7`) SUPERSEDED, but 06.6.2 (D-14) replaced the sketch's own two-level draft with the current three-level split (`--color-canvas` / `--color-dominant` / `--color-secondary`) before either of those values shipped as the sketch drafted them.
- **Cards:** the current contract is a hairline `--color-border` edge at rest, `box-shadow: none`, with `--shadow-card-hover` revealed only on `:hover`/`:focus-within` — not this sketch's own visible-shadow-at-rest / lift-on-hover / transparent-border treatment SUPERSEDED. 06.6.4 (D-03) reversed that specific trade across all eight card components (`.stat-tile`, `.page-section`, `.battery-trend-section`, `.runway-card`, `.history-card`, `.login-card`, `.airline-card`, `.theme-status`) — see `references/control-density.md` for the full contract and the two floating-overlay exceptions (`.lightbox`, `.dirty-bar`) that keep a resting shadow.
- **Headings:** still current — warm serif (`Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif`) on `h1, h2, h3, legend, .text-heading, .page-title, .site-title`, plus the one named Label-role exception `.stat-tile__caption`. Body text, tables, and mono/data content stay on `--font-ui` — serif is headings-only, never dense/tabular content. `legend` was added to this selector after this sketch shipped (a bug fix, not a style change — see `SKILL.md`'s `<design_direction>` for why `<fieldset>`'s accessible-name element needed the same treatment as every other heading role).
- **Stat-tile captions:** the sketch's claimed 15px normal-case serif size no longer exists as a declaration SUPERSEDED. The current `.stat-tile__caption` rule declares `font-family: var(--font-serif)` (still the one Label-role serif exception), `text-transform: none` and `letter-spacing: normal` — but no `font-size` and no `font-weight` of its own, so it inherits `.text-label`'s 14px (`--font-label-size`) and regular weight, not the sketch's 15px. Weight round trip, quick task 260902-iag: quick task 260902-dng (Task 3) added `font-weight: var(--weight-semibold)` here SUPERSEDED, to match a nested card title that had just been demoted to 16px semibold (see the next bullet). Once that demotion was itself reverted, the promotion's only stated reason evaporated — a semibold 14px caption beside a regular 20px card title would have recreated the same weight-vs-size inversion in the opposite direction — so quick task 260902-iag (Task 2) reverted the promotion too. The rule declares no weight again today, the same state this line described before 260902-dng, now reached for a re-adjudicated reason rather than by omission.
- **Nested card title tier** (the `Battery trend` / `Unresolved prefixes` / `Resolution statistics` headings inside Health's own nested cards): current — 20px serif regular, the plain `.text-heading` treatment, identical to every other section heading in the app, including Settings' own group headings (`Theme` / `Runway` / `Diagnostic LED` / `Poll`). This sketch never documented a distinct tier for these headings at all — see below. SUPERSEDED round trip: quick task 260901-uzi (finding 4) demoted them to 16px semibold (the Emphasis role, `.stat-tile__value`'s own tier) to fix a real inverted-hierarchy defect — Health renders two structural levels (D-10's section headings and the cards nested inside them) and both were rendering at one identical 20px tier. The developer then compared that demoted heading against Settings' own 20px heading by screenshot, judged the Settings version correct, and quick task 260902-iag reverted the demotion: each nested card's own border/`--color-dominant` surface/padding now carries the "this is one grouped unit" signal font-size briefly carried instead. Not adopted at either point: the sketch's own `.wide-card__caption` card-title role, a 14px muted uppercase eyebrow label — a genuine third answer to this same hierarchy question that this app has never shipped.
- **Accent color:** the current terracotta accent is `#B13F16` (light) / `#FF8A5C` (dark) — not this sketch's own `#E8622C` (light) SUPERSEDED, darkened by 06.6.2 (D-14, UXA-04) to meet WCAG AA text contrast. The hue-separation reasoning this sketch established (keeping the accent distinct from `--color-status-warn`'s golden amber) still holds and is now executable — see `references/accessibility-contrast.md`.
- **Icons on stat tiles:** still current — accent-tinted (`color: var(--color-accent)`) via `.stat-tile__icon`, small inline SVG (20×20 by default), outline style, `stroke="currentColor"`.
- **Spacing:** the "generous throughout" direction landed, but not exactly where this sketch's own draft numbers placed it — see the token block below. `.page-content`'s base padding is `var(--space-xl) var(--space-lg) var(--space-2xl)`, with sides deliberately held at `lg` (24px) rather than promoted further, because a wider side gutter on a 375px phone viewport would leave too narrow a content column; the fuller `2xl`/`3xl` promotion this sketch anticipated instead lands on `.dashboard-main` at the `>=960px` breakpoint. This is a deliberate mobile-width floor the sketch's own draft numbers did not account for, not an inconsistency between the two rules.
- **Anomaly banner:** the redundant detail-text list this sketch proposed dropping was in fact re-added by 06.6.3 (UXA-06) as prose naming real failing categories — a genuine, still-open conflict between two validated decisions (06.6.1's sketch said drop it; 06.6.3 re-added it), not resolved by this file. Do not treat either direction as settled; it needs a developer decision, not a documentation correction. Separately, the banner's *container* treatment (background wash vs. hairline-plus-edge) did change — see `references/control-density.md`'s Banners section.
- **Battery trend section:** still current — moved out of the stat-tile dashboard grid into its own full-width section, with the same card contract (now hairline-at-rest, not shadow-at-rest — see above) and a serif `<h2>` heading.

### Additions this file predates

These postdate this sketch entirely and are documented in full elsewhere — noted here only so this file's own reader knows they exist:

- The page-title role (`.page-title`, ~30px serif, distinct from the 20px `.text-heading` section-heading role) — 06.6.2 (D-15). See `SKILL.md`'s `<design_direction>` Typography block.
- The retired SUPERSEDED Display type role (`--font-display-size`, 24px) — its two consumers (`.stat-tile__value`, `.runway-card__number`) moved to the Emphasis role (Body size + semibold) in 06.6.4 (D-09). See `references/control-density.md`.
- The heading-rhythm rule (`h1, h2, h3, .text-heading { margin: 0 0 var(--space-sm); }`) — stated in the same selector as the family so a heading role's spacing stays independent of whether it lands on a real `<h2>` or a `<p class="text-heading">`.

## CSS Patterns

The block below is a record of what shipped, not a proposal to add — every value that moved after this sketch is marked; treat this as historical documentation, and read `companion/static/style.css` directly for the live declarations.

```css
/* Serif headings — still current */
h1, h2, h3, legend, .text-heading, .page-title, .site-title {
  font-family: var(--font-serif);
  font-weight: var(--weight-regular);
  letter-spacing: -0.01em;
}

/* Card relief — SUPERSEDED (06.6.4 D-03 reversed this to hairline-at-rest, shadow-on-hover) */
.stat-tile { box-shadow: var(--shadow-card); border-color: transparent; }
.stat-tile:hover { box-shadow: var(--shadow-card-hover); transform: translateY(-1px); }

/* Tokens as they actually shipped, not as this sketch drafted them */
--font-serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;  /* still current */
--color-accent: #B13F16;       /* light theme — was the sketch's own draft #E8622C SUPERSEDED, itself replacing 06.3's #3454D1 */
--color-accent-hover: #963610; /* was the sketch's own draft #D2521F SUPERSEDED */
--shadow-card: 0 1px 3px rgba(18, 21, 27, 0.06), 0 1px 2px rgba(18, 21, 27, 0.04);        /* value unchanged; usage on cards-at-rest is SUPERSEDED, now hover-only */
--shadow-card-hover: 0 4px 12px rgba(18, 21, 27, 0.08), 0 2px 4px rgba(18, 21, 27, 0.05); /* still current */
--radius-card: 10px;  /* still exists, but cards themselves now use --radius-control (8px) — --radius-card is reserved for floating overlays, see references/control-density.md */
```

Dark theme accent: `#FF8A5C` (still current, unchanged since this sketch shipped).

## HTML Structures

No new HTML elements beyond what `companion/layout.py`'s `stat_tile()` and `page_shell()` emit — this was, and remains, a CSS-only visual layer over existing markup, plus the icon `<defs>` sprite block (`ICON_DEFS_HTML`) this sketch introduced, still current and now grown well past its original four icons (see `companion/layout.py`'s `ICON_IDS`).

## What to Avoid

- **Variant A ("Minimal warmth")** — still rejected. Too subtle; serif-only-on-h1 plus shadow-on-hover-only didn't read as a meaningfully different direction from 06.3.
- **Variant C ("Structured warmth")** — still rejected. The colored-left-border-per-status approach competed with the anomaly banner's own left-border for attention and made every card look like a warning/status indicator.
- Do not use serif for body text, table cells, or any monospace/data content — still a hard boundary (06.6.1-CONTEXT.md D-03).
- Do not pick an accent hue close to `--color-status-warn`'s amber — still a named constraint, now enforced mechanically (`references/accessibility-contrast.md`'s `MIN_SIGNAL_HUE_SEPARATION`), not only by eye.
- Do not restore a resting card shadow — 06.6.4 (D-03) is a deliberate reversal of this sketch's own original direction, not an oversight to "fix" back.

## Origin
Synthesized from sketch: 001 (health-page-direction), winner: Variant B. Corrected against the shipped implementation (`companion/static/style.css`) per 06.6.2 (D-14, D-15, UXA-04, three-level surfaces, page-title role) and 06.6.4 (D-03, D-09, card hairline reversal, Display role retirement) — quick task 260901-t00.
Source file available in: `sources/001-health-page-direction.html` (historical artifact, byte-identical, not current-reality documentation).
