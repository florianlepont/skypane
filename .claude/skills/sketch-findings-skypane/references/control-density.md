# Control Density

## Design Decisions

**Button geometry.** Base `button` shrinks from `min-height: 44px` SUPERSEDED to `height: 30px` (06.6.4 D-01), `padding: 0 12px` (was `0 var(--space-md)`/16px SUPERSEDED), `font-size: 13px` (was `--font-body-size`/16px SUPERSEDED), `border-radius: 6px` (was `--radius-control`/8px SUPERSEDED), plus new `font-weight: var(--weight-semibold)` and `letter-spacing: -0.01em`. This is a deliberate WCAG 2.5.5 (Level AAA, 44px) trade the developer accepted after being shown it three times against a live reference artifact; WCAG 2.5.8 (Level AA, 24px) is still met.

**Sub-960px button growth (06.6.4.1.1 D-18/UIR-26) — an extension of D-01, not a reopening of it.** Below `960px` (a `max-width: 959.98px` media query, the fractional-pixel boundary avoiding a one-device-pixel gap against the `>=960px` breakpoint used everywhere else in this file), the base `button` rule grows to `height: 36px; font-size: 14px;`. The override rule is deliberately a bare `button` selector at the same `(0,0,1)` specificity as the base rule — adding a `:not()` qualifier to try to scope it more tightly would RAISE specificity and start winning against every class-scoped control that declares its own geometry (`.theme-form .theme-option`, `.copy-btn`, the nav-footer theme segments), which must all keep their own sizes untouched. Because neither rule exceeds `(0,0,1)` specificity, **source position decides the cascade**: this override is placed last in the file, after every other `button` rule including the `>=960px` block, so it wins on position, not specificity — a harness check in `test_status_pages.py` pins this source-order relationship explicitly, not just the declared values. At `>=960px` buttons stay exactly as D-01 left them (30px/13px); nothing above 960px changed.

**Quiet-at-rest / reveal-on-hover, the wash-strength register.** Every distinct hover/active wash percentage in the file, presented as one register rather than isolated numbers: base quiet buttons are `color-mix(in srgb, var(--color-text) 4.5%, transparent)` at rest with a `9%`-mix border, revealing `7.5%` background / `14%` border on hover; `.copy-btn` (icon-only) uses `7%` on hover with no resting wash at all; nav links (`.sidebar-link`, `.mobile-nav__link`) and the theme-picker segments use `4.5%` on hover for inactive items; active-state pills (nav links, theme segments) use `12%` accent-tinted background. The base `button` rule's background/border declarations are each written twice — a `rgba()` literal fallback immediately before the `color-mix()` form — for browsers without `color-mix()` support (WR-02); this is not two competing values, the second declaration wins in every supporting browser.

**Primary-action treatment and cascade mechanics.** `button[type="submit"]` gets an accent fill with `box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 1px 2px rgba(18,21,27,.14)` (hover deepens to `inset ... .16, 0 2px 5px ... .18`), theme-neutral black/white alphas by design — no dark-mode variant needed. The part most likely to be got wrong: theme-picker buttons are also `<button type="submit">`, but never receive this fill. What actually excludes them is `.theme-form .theme-option`'s **doubled specificity** (`0,2,0`, two classes) outranking `button[type="submit"]`'s `0,1,1` — not their absence from any accent-reservation list. Two other quiet submit buttons (`.logout-form button`, `.dirty-bar__cancel`) are excluded a different way: equal `0,1,1` specificity to `button[type="submit"]`, so **source order** (placed after it) decides the winner instead — the same reasoning documented at each of those rules. This is the case where source order, not specificity, decides the cascade, and both rules must stay after `button[type="submit"]` in the file for the override to hold.

**Press affordance.** `button:active { transform: translateY(1px); }` applies to every button, primary and quiet alike. It is placed *before* `button:disabled` in source order specifically so a disabled button's own (later, winning) treatment is never overridden by an active-press effect a disabled control cannot actually receive.

**Icon-only button pattern.** `.copy-btn` (and any future icon-only action button) is a 22×22px visual box with `border: none`, `background: transparent`, `border-radius: 6px`, `display: inline-flex` centring — no accessibility trade-off, unlike the base button's 30px reduction. A `::before` pseudo-element (`content: ""; position: absolute; inset: -11px;`) synthesizes a real 44×44 hit area centred on the glyph (22 + 11×2 = 44). This is the pattern to reuse for any future icon-only button rather than reintroducing a minimum-size floor on the visual box itself. `.copy-btn .icon` is scoped down to 14px (the global `.icon` default is 20px) — at the original 28px box this nearly filled the button and read as oversized; the 22px box plus 14px glyph reads as a quiet inline affordance instead.

**Segmented theme control.** `.theme-form` is a bordered container (`border: 1px solid var(--color-border); border-radius: var(--radius-control); padding: 2px; gap: 2px;`) wrapping three borderless `.theme-option` buttons (`height: 28px; padding: 0 12px; font-size: 13px; border-radius: 6px;`). The doubled-specificity selector (`.theme-form .theme-option`, not the bare class) is load-bearing, not stylistic — see Primary-action treatment above. `.theme-option--active` reuses the exact same tinted-pill idiom `.sidebar-link--active` uses (12% accent background, accent text, semibold) — the same visual language, not a reinvention.

**Shared active-pill idiom and `:not()`-scoping.** Both nav renderings (`.sidebar-link--active`, `.mobile-nav__link--active`) and the theme segments use one signal: a `color-mix(in srgb, var(--color-accent) 12%, transparent)` background plus accent text and semibold weight — a single cue, not the two-cue (left-border plus tint) model an earlier revision used SUPERSEDED (06.6.4 D-05 dropped the redundant left-border on nav links). The corresponding hover rules are `:not()`-scoped (`.sidebar-link:not(.sidebar-link--active):hover`, etc.) — an unscoped hover selector at equal specificity, later in source, would outrank the active modifier and erase the active tint the instant the pointer crossed it. This scoping pattern is the correct way to add a hover state next to an existing active-pill rule; do not add an unscoped hover instead.

**Filter bar field.** `.filter-bar__field input` is scoped to 32px (`height: 32px; min-height: 0;` — the `min-height: 0` is load-bearing, since the global `input`/`select` rule's 44px minimum otherwise outranks any plain `height` declaration regardless of specificity), with a transparent background instead of the global filled-secondary style. This scoping is intentional and narrow: the global native `input`/`select` rule keeps its 44px floor for every other field in the app — only this one wrapper's descendant input is exempted.

**Hidden form controls, the fourth floor-register category (quick task 260902-l9w, joined by 06.6.4.1.1-05).** `input.visually-hidden, select.visually-hidden` clears both 44px minimums (plus native control theming) off any form control that also carries the `.visually-hidden` utility class — originally the three Runway-picker radios (`config_page.py`'s `runway_fieldset()`), now joined by the 16 theme-picker chip radios (`config_page.py`'s `theme_fieldset()`, 06.6.4.1.1-05, sketch 004 variant B). This is a distinct category from kept / traded / relocated, added alongside them below: **exempt-by-delegation** — an off-screen control with no hit area of its own, whose wrapping label (`.runway-card` or `.theme-chip`, both of which exceed 44px in both axes on every viewport) is the real activation target. It is explicitly NOT a fifth entry in the traded-away list: no accessibility floor was given up, because the control was never the hit target to begin with. See `references/accessibility-contrast.md`'s `.visually-hidden` entry for the mechanism (why the utility's own 1px sizing is otherwise inert on an `<input>`/`<select>`).

**Card hairline-at-rest contract.** 06.6.4 (D-03) reverses 06.6.1's shadow-at-rest treatment: every card in the set (`.stat-tile`, `.page-section`, `.battery-trend-section`, `.runway-card`, `.history-card`, `.login-card`, `.airline-card`, `.theme-status`, and — 06.6.4.1.1-05 — `.theme-chip`) now declares `border: 1px solid var(--color-border); box-shadow: none;` at rest, with `border-color: transparent; box-shadow: var(--shadow-card-hover);` on `:hover`/`:focus-within`. The two states are mutually exclusive, not additive — never restore both a resting shadow and the hairline at once.

**Selected-card treatment: border + check glyph + background wash (06.6.4.1.1-06, developer checkpoint follow-up).** `.runway-card--selected` and `.theme-chip--selected` both carry an always-visible 2px accent border, unaffected by the hairline-at-rest contract above — it already overrides the general border with a real signal, and each component's hover rule is `:not(...--selected)`-scoped so hovering a selected card can never clear that border. This USED to be the whole selected-state signal (border plus a small stroke-only check glyph), and the developer's real-device checkpoint review reported it was too subtle to notice at a glance, site-wide, especially against `.theme-chip`'s photo-heavy preview band at 16-chip density. The fix adds a `color-mix(in srgb, var(--color-accent) 12%, transparent)` background wash on both selected states — the SAME idiom `.theme-form .theme-option--active` and the nav-pill active-link rules below already use, so this is the third component to reuse the app's one "current selection" language rather than a fourth invented one. On `.runway-card--selected` the wash covers the whole card (no separate body wrapper exists to scope it more narrowly, and the card's only other content — a number and an optional airport-diagram image — is not obscured by 12% opacity). On `.theme-chip--selected` the wash is scoped to `.theme-chip__body` specifically, NOT the whole chip, because unlike `.runway-card` this component has a real rendered preview band (`.theme-chip__preview`) that must stay visually untinted so the theme's own colours read correctly. Border-only selection SUPERSEDED as this app's general selected-card idiom — do not add a third selectable-card component with a border-only treatment; reuse the wash.

## CSS Patterns

```css
/* Base button: 30px, quiet-at-rest */
button {
  height: 30px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: var(--weight-semibold);
  border-radius: 6px;
  background: color-mix(in srgb, var(--color-text) 4.5%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-text) 9%, transparent);
}
button:hover {
  background: color-mix(in srgb, var(--color-text) 7.5%, transparent);
  border-color: color-mix(in srgb, var(--color-text) 14%, transparent);
}
button:active { transform: translateY(1px); }

/* Sub-960px button growth (06.6.4.1.1 D-18) — extends D-01, does not
 * reopen it. Bare `button` at the same (0,0,1) specificity as the base
 * rule above; placed LAST in source order so it wins on position, not
 * specificity, and class-scoped controls (.theme-form .theme-option,
 * .copy-btn) keep their own geometry untouched. */
@media (max-width: 959.98px) {
  button { height: 36px; font-size: 14px; }
}

/* Icon-only button: visual 22x22, real 44x44 hit area */
.copy-btn {
  width: 22px; height: 22px;
  position: relative;
  border: none; border-radius: 6px; background: transparent;
}
.copy-btn::before { content: ""; position: absolute; inset: -11px; }

/* Segmented theme control */
.theme-form { display: flex; gap: 2px; padding: 2px; border: 1px solid var(--color-border); border-radius: var(--radius-control); }
.theme-form .theme-option { height: 28px; padding: 0 12px; font-size: 13px; background: transparent; border: none; border-radius: 6px; }
.theme-form .theme-option--active { background: color-mix(in srgb, var(--color-accent) 12%, transparent); color: var(--color-accent); font-weight: var(--weight-semibold); }

/* Card hairline-at-rest / shadow-on-hover */
.stat-tile { border: 1px solid var(--color-border); box-shadow: none; }
.stat-tile:hover, .stat-tile:focus-within { border-color: transparent; box-shadow: var(--shadow-card-hover); }

/* Selected-card treatment: border (unchanged) + background wash (06.6.4.1.1-06 addition) */
.runway-card--selected {
  border: 2px solid var(--color-accent);
  background: color-mix(in srgb, var(--color-accent) 12%, transparent);
}
/* .theme-chip--selected itself stays border-only; the wash is scoped to
 * the body so it never sits behind the rendered preview band. */
.theme-chip--selected .theme-chip__body {
  background: color-mix(in srgb, var(--color-accent) 12%, transparent);
}
```

## What to Avoid

- Reintroducing a blanket minimum-size floor on an icon-only button's visual box instead of relocating the hit area into a `::before` pseudo-element — the relocation pattern is what avoids the accessibility trade-off.
- Writing a lower-specificity (or bare-class) hover rule for the theme-picker segments or any `button[type="submit"]`-adjacent quiet button — it cannot reach past `button[type="submit"]`'s or `.theme-form .theme-option`'s specificity and will silently do nothing.
- Restoring a resting card shadow on any of the card set (nine components as of 06.6.4.1.1-05) — 06.6.4 (D-03) is a deliberate reversal of 06.6.1's own direction, not an oversight to "fix."
- Adding a second muted-text strength or a new hover-wash percentage instead of reusing the existing register (4.5% / 7% / 7.5% / 9% / 12% / 14%) — the file already documents having fixed a second-muted-strength defect twice; a new value reopens it. The 12% background wash on `.runway-card--selected`/`.theme-chip--selected` (06.6.4.1.1-06) reuses this exact register value, not a new one.
- Reintroducing a border-only selected-card treatment on any future selectable-card component — 06.6.4.1.1-06 found this too subtle to notice at a glance once a second, denser instance of the pattern shipped; reuse the border-plus-wash-plus-check-glyph combination instead.
- Adding a background wash across a whole `.theme-chip` (rather than scoped to `.theme-chip__body`) — it would sit behind and visibly tint the rendered preview band, which must stay undithered so the theme's real colours are legible.

## Origin
Synthesized from: 06.6.4-companion-sober-visual-refinement-linear-inspired-sobriety-p (D-01 through D-09), and `companion/static/style.css` read live at execution time (quick task 260901-t00). Updated 06.6.4.1.1-06 (D-18 sub-960px button growth as a D-01 extension; the selected-card background-wash addition on `.runway-card--selected`/`.theme-chip--selected`, a developer-checkpoint follow-up fix).
