# Settings Page Patterns

## Design Decisions

### The Theme group is a chip grid, not a fieldset (06.6.4.1.1-05)

Settings renders zero `<fieldset>` and zero `<legend>` elements anywhere on the page — all four groups (Theme, Runway, Diagnostic LED, Poll) are named by an `<h2 class="text-heading">` at one consistent heading level, D-04/D-05 (06.6.3) having already dropped `<fieldset>` from Theme and Runway before this phase.

`theme_fieldset()`'s multi-theme branch (`len(device_config.THEME_IDS) > 1`, the normal case) emits a `.theme-status` card — the same wrapper Runway and Diagnostic LED use — holding a `.theme-chip-grid` of one `.theme-chip` per registry entry: a real rendered `/theme-preview/{id}.png` preview, two real-palette swatch dots, and the theme name, replacing what used to be 16 stacked 44px native radios. See `SKILL.md`'s `<design_direction>` Cards paragraph and `references/control-density.md` for the chip's own selectable-card mechanism (reused verbatim from `.runway-card`) and its selected-state treatment (border, check glyph, and — since 06.6.4.1.1-06 — a background wash). The single-theme fallback branch (`len() == 1`) is unaffected: it still renders the plain read-only `.theme-status__row` swatch-plus-label line, no chip grid needed for a one-option "choice."

### The flash-banner slot (06.6.4.1.1-04, D-17)

The flash banner (the "Saved — ..." confirmation) renders directly below `page_header()`'s own markup, not above the page title — so saving no longer shifts the title down the page. `body` is one opaque pre-built string by the time `layout.page_shell()` receives it, so there is no structural handle on "just after the header"; `page_header()` instead leaves `layout.FLASH_SLOT_MARKER` (`"<!--flash-slot-->"`) as a literal handle at exactly that point, appended after its own closing `</div>`.

`page_shell()` resolves the marker in two branches:
- **A page built on `page_header()`** (every authenticated page, including Settings) carries the marker in `body`; the flash banner is spliced in at that exact point and the banner's old pre-body slot is cleared so it is not emitted twice.
- **A page that does NOT use `page_header()`** (login, 404, and any future bare page) has no marker in `body` at all; the flash banner keeps rendering in its original before-body slot, so no such caller needs to change and none silently loses its banner. This is the documented fallback the marker's own contract explicitly names.

An unconditional second `replace()` on the marker string guarantees it never reaches the browser on any path — flash or no-flash, marker-carrying or not.

### The one-caption-per-section rule

Every section on the Settings page (`/settings`, `companion/pages/config_page.py`) renders exactly one muted caption sentence directly under its heading, before its control — Theme, Runway, Diagnostic LED, Poll, Quiet hours, and Wake interval: six sections, six captions, zero heading-without-caption sections. (Phase 10 added Quiet hours and left this enumeration behind at four; 11-03-PLAN.md brings it current to six along with Wake interval — the invariant itself is unchanged, only the enumeration was stale.) That invariant is what a future edit would most easily break silently, since nothing stops a section rendering with no caption at all.

Markup shape: `<p class="text-label section-caption">{escaped caption text}</p>`. The two classes deliberately **compose** rather than either restating the other — `.text-label` already supplies `var(--font-label-size)` (14px), so `.section-caption` declares only colour (`color-mix(in srgb, var(--color-text) 70%, transparent)` — this file's one existing muted-secondary strength, not a new value). The markup always carries both classes together; a caption with only `.section-caption` and no `.text-label` would render at the browser's default paragraph size.

What the rule deliberately does *not* declare, and why the absence is a decision rather than an omission: `.section-caption` carries no `margin` of its own. Unlike the heading-rhythm rule (`h1, h2, h3, .text-heading { margin: 0 0 var(--space-sm); }`), this role keeps the user-agent default paragraph margin — the description/helper paragraphs it replaced already relied on that default, and the validated typography sketch was measured against it. Do not "complete" this rule by adding a margin.

This shape replaced an earlier description-above / helper-below paragraph pair: each group used to render a description sentence above its control (`THEME_SECTION_DESCRIPTION`/`RUNWAY_SECTION_DESCRIPTION`) *and* a helper sentence below it (`THEME_HELPER_TEXT`/`RUNWAY_HELPER_TEXT`/`LED_HELPER_TEXT`) — Theme and Runway rendered both, LED escaped the doubling but kept its lone paragraph un-muted and positioned after its control instead of before. All five of those constants are retired outright; each group now carries exactly one caption.

The six constants (`THEME_SECTION_CAPTION`, `RUNWAY_SECTION_CAPTION`, `LED_SECTION_CAPTION`, `POLL_SECTION_CAPTION`, `QUIET_HOURS_SECTION_CAPTION`, `WAKE_INTERVAL_SECTION_CAPTION`) live in one named family, contiguous in `companion/pages/config_page.py`, each with the developer-validated copy verbatim.

One section's caption is consumed by a two-branch renderer: `poll_trigger_section(cooldown_remaining)` has an enabled (zero-cooldown) branch and a disabled (cooldown-active) branch, and `caption_html` is computed once above the `if cooldown_remaining > 0:` split so it is interpolated as the first element of *both* return expressions — the same computed-once-reused-by-both-branches idiom `theme_fieldset()` already established for its own read-only/editable branch split. A caption emitted on only one branch would silently disappear for the whole cooldown window; this is why the constant is computed once outside the branch rather than inlined into each return.

### Display's three supersections (Phase 20, D-12)

Display renders three headed supersections in a locked order — "Look" (Theme, Flight colours, Calendar), "What it watches" (Runway), "When it is on" (Screen on/off, Quiet hours) — each built by `layout.section_intro_html(section_id, heading, description)`, the exact same helper Health's own nested-card sections (`_source_fault_block()`'s siblings, "Battery trend"/"Unresolved prefixes"/"Resolution statistics") already used before this phase, promoted out of `health_page.py` into `layout.py` specifically so `config_page.py` could call it without one page module importing another (`companion/pages/__init__.py`'s own boundary). Display's three supersections deliberately reuse this existing "id-anchored `<h2>` plus a muted one-sentence description on the same baseline" component rather than inventing a fourth heading tier: the visual grammar a household member already learned from Health's own nested groups (a header, one plain sentence, then the cards) is the identical grammar Display now uses to group six settings cards into three named ones. Each grouped card inside a supersection additionally gains the `--nested` modifier (`.theme-status--nested`/`.page-section--nested`) so its own `<h2>` renders at the bottom rung of the page-title/section-heading/nested-card-title ladder (`SKILL.md`'s Typography paragraph) — the same visual demotion Health's own nested cards get, for the same reason: a card's heading inside a named supersection should never compete with the supersection's own heading above it.

The three supersections do not all sit in one DOM position relative to `<form id="settings-form">`: "Look" (Theme, Calendar) stays a literal descendant of the form; "What it watches" (Runway) and "When it is on" (Screen on/off, Quiet hours) render as siblings AFTER the form closes, because Runway's move (Polish fix 4, D-14c) and Screen on/off's and Quiet hours' own instant-switch forms (D-19, below) each need a `<form>` of their own, which HTML forbids nesting inside another `<form>`. `_display_groups_html()` returns a 3-tuple (`in_form_html`, `watches_supersection_html`, `on_supersection_html`) so `render()` can emit the first inside the form and the other two after it, while the locked Look/What it watches/When it is on reading order survives the form boundary unbroken in document order.

### The instant-switch slot (D-19)

`display_group()`/`quiet_hours_group()` each render as a sibling of `<form id="settings-form">`, never a descendant — the exact structural fix D-12 above depends on. Each card's own `.quick-action`/`.quick-action-slot` instant switch posts immediately to its own dedicated route (`/quick/display`, `/quick/quiet-hours`) via its own small `<form>`, above a hairline divider (`.quick-action-slot`'s `border-bottom`) from the card's scheduled settings below it. Those scheduled inputs (the `display_enabled` checkbox, the Quiet hours enable checkbox and both `<input type="time">` fields) still submit with the page-wide Save: each carries an explicit `form="settings-form"` attribute — the cross-DOM form-association idiom this file already used for the dirty-bar's own Save button and the screen-type `<select>`, now a third and fourth consumer of the identical mechanism, not a new one. This is what makes the whole arrangement valid HTML: a browser reads `form="settings-form"` as "this control belongs to that form, wherever it lives in the DOM," so the input's own sibling position relative to the form it submits with is irrelevant to the browser, even though it would be invalid to nest one `<form>` inside another to achieve the same submission.

### The fused Calendar card (D-14c)

The Calendar card's own read-only status/chip-grid portion (`calendar_group()`) stays a literal descendant of `#settings-form`, unchanged in position. The write-only feed-URL field and its "Connect calendar" button are a genuinely separate small `<form>` (`calendar_connect_section()`), posting immediately to its own dedicated `POST /settings/calendar/connect` route rather than the page-wide Save — the same reasoning D-19's instant switches above follow: an immediate-action form can never be a literal descendant of the settings form. `calendar_connect_section()`'s own `.page-section` wrapper is the element the `:has(+ .calendar-disconnect-form)` CSS rule actually targets, visually fusing Connect and Disconnect into one small two-part unit by removing the shared border/radius between them — never the whole Calendar card, since Runway's own supersection and (once Runway moved after the form, Polish fix 4) potentially other content can render between Calendar's card and the connect/disconnect pair. **Documented degradation:** the `:has()` rule lived inside this file's existing `@supports selector(:has(*))` progressive-enhancement convention. **Both this rule and this paragraph's block count are SUPERSEDED — read the correction below before quoting either.**

> **Correction of a stale, load-bearing number (Phase 22, Gate row).** This paragraph used to end "`test_config_page.py` pins the file to exactly **two** such blocks." **It is ONE, and has been since Phase 21.** 21-07-PLAN.md Task 3 retired both Calendar-card fusion rules and deleted the now-empty feature-query block that had held one of them, taking the whole-file count from 2 to 1; the single surviving block is the **live-selection-state** one (`style.css:2341` as of this phase's close — the line number drifts, the identity does not), which Phase 22 **extended** with T6's inset-ring rules and T15's selected-card focus ring rather than opening a second. Two independent checks in `companion/test_config_page.py` assert `count(...) != 1` and fail on a second block, and each additionally asserts its own rules live *inside* that one block. **Verified against the live stylesheet at the time of writing, not copied from a document.**
>
> This correction is recorded whether or not any plan adds a `:has()` rule, because **this exact stale line is what an earlier draft of Phase 22's own UI spec copied instead of checking the code** — it took the "exactly two" from here, and the phase's UI-spec checker raised a BLOCK on the resulting mismatch. A wrong number in a reference file does not stay a documentation defect; it becomes a shipped one a phase later. If you need this count, re-grep `@supports selector(:has(*)) {` before you write it down. A browser without `:has()` support simply keeps all four of the Connect card's corners rounded and lets Disconnect render as its own separate small card at the normal `--space-lg` gap below it — an accepted, fully-styled degradation, never an unstyled one.

### The `.rule-row` list, replacing the rules table (D-15c)

Flight colours' per-rule editor is a `<ul class="rule-list">` of `<li class="rule-row">` items — a theme swatch, the key in `.mono`, a kind badge (reusing `.banner__pill` verbatim, deliberately never colour-coded per 20-UI-SPEC.md §F), the theme name, and a "Remove" button whose own form carries `data-confirm` — replacing the retired table/card split outright, not restyling it. The add form above the list is a single line: a native-radio segmented "Match by" control (`references/control-density.md`), a value input, a compact theme-chip grid (`references/control-density.md`'s own compact-chip entry) and an "Add" button. Up to five suggestion chips drawn from recent runway events sit below the add form as a progressive enhancement — plain, inert underlined text with no JS at all, never a control that does nothing silently.

### The floating save bar — a worked example

This component iterated four times in a single session, which makes it the best available case study for how a pattern in this app actually gets settled. The mechanics below are stated as the CURRENT contract first and completely; the four-iteration history follows as a separate, clearly-marked-historical list.

**Current mechanics.** `.dirty-bar` is a `<div data-dirty-bar hidden role="status">` emitted by `config_page.render()` as the **last** element on the page — a sibling of `<form id="settings-form">`, not a descendant of it, submitting its Save button via `<button type="submit" form="settings-form">` (a cross-DOM form association) rather than native nesting.

- **Surface, border, radius.** `background: var(--color-dominant)` (the same card surface every other card on the page uses, not the receding `--color-secondary` an earlier iteration used), a full `1px solid var(--color-border)` border on all four sides, `border-radius: var(--radius-card)` (10px — the floating-overlay radius, not the 8px card-set radius; see `references/control-density.md`'s radius pairing note).
- **The two-layer shadow.** `box-shadow: var(--shadow-card-hover), 0 12px 32px rgba(18, 21, 27, 0.16);` — two layers, not one. The first layer is the real `--shadow-card-hover` token, which carries its own dark-mode and `[data-ui-theme]` variants automatically; the second, larger layer is a raw `rgba()` literal, consistent with this file's existing raw-rgba shadow precedent (`button[type="submit"]`'s own inset-highlight declarations), and exists to push the card visibly further off the page than a card-hover shadow alone achieves. `.lightbox` is this file's other precedent for a floating element carrying a resting (not hover-revealed) shadow, for the same reason: both are floating overlays, not page-flow cards.
- **Positioning, per breakpoint.** The base rule is full-width and in normal document flow (`margin-top: var(--space-md)`), immediately after the form's own always-rendered bottom Save Settings button. At `>=960px` it becomes `position: fixed` — not `sticky` (see history below) — with `bottom: var(--space-lg)`. **Below 960px it is `position: fixed` too** (pinned on phones since Phase 18; the "full-width, in normal document flow below 960px" this bullet used to state is SUPERSEDED), with `left`/`right` at `var(--space-md)`, `flex-wrap: wrap`, and — Phase 22, T7/D-10 — a bottom offset of `calc(var(--space-md) + 56px + env(safe-area-inset-bottom, 0px))`: **the bar's own gap plus the bottom tab bar's whole height**, so the two never overlap at all in the normal case. Measured at 390×844 with a real unsaved edit, the save bar ends **15px above** the tab bar's top edge, the boxes do not intersect, and both are hit-testable at their centres. Geometric separation first; the stacking order below is only the belt-and-braces half.
- **Reproducing the content column's geometry.** `left: calc(240px + var(--space-xl) + var(--space-md))`, `right: var(--space-md)`. The `240px` and `var(--space-xl)` pair is a **duplicated-not-imported must-equal value** — it has to stay equal to `.dashboard-shell`'s `grid-template-columns` first track (`240px`) and `column-gap` (`var(--space-xl)`); there is no shared token for either, so the pair is guarded by a harness check instead of a shared variable. The trailing `var(--space-md)` is the inset from the content column's own edge.
- **Sizing.** `width: fit-content; max-width: calc(min(1440px, 100%) - var(--space-md) * 2); margin: 0 auto;` — the bar sizes to its own content (the changed-sections label plus the two buttons), not the full column width. `margin: 0 auto` is the classic auto-margin-centring trick for a positioned box, which requires a definite `width` to engage — this is why `width: fit-content` is set explicitly rather than left unset.
- **Why the max-width is reduced, not just copied.** For a `position: fixed` box, `100%` resolves against the *viewport*, not the content column. Left as the bare `min(1440px, 100%)` `.dashboard-main` itself uses, once the viewport passes roughly 1712px (240px sidebar + 32px gap + 1440px cap) the `1440px` half of the `min()` alone would size the box — flush with the content column on both sides, silently cancelling the visible inset at exactly the widths (e.g. a 16-inch MacBook Pro's 1728px default logical width) where it matters most. Reducing the cap by twice the inset (`- var(--space-md) * 2`) keeps the inset visible past that width too.
- **Centring mechanism dependency.** `margin: 0 auto`'s centring only works because `width: fit-content` gives the box a definite width to centre within its `left`/`right` positioning region — removing the `width` declaration silently disables the centring.
- **Bottom inset.** `var(--space-lg)` (24px), not `var(--space-md)` (16px) — a deliberately larger gap from the viewport edge, which reads as more clearly "floating" rather than merely "shorter."
- **No `z-index`, and why. SUPERSEDED (Phase 22, T7/D-10) — by the paragraph's own escape clause, used exactly as it was written.** The original read: *"This is the last positioned element in document order and nothing it overlaps creates a competing stacking context, so a `z-index` here would be an unearned magic number. If a future overlap appears, add one then, with a stated reason — do not add one preemptively."* That future overlap has appeared. The bottom tab bar is a new `position: fixed` element competing for the same corner of a phone viewport, so "nothing it overlaps creates a competing stacking context" simply stopped being true. **`.dirty-bar` now takes `z-index: 30` at BOTH breakpoints** — one value for the component, not one per width; the desktop rule had carried none at all, which was T7's desktop half. **The stated reason, which is what the escape clause actually demanded:** the save bar is the user's **active task** and the tab bar is **ambient chrome**, and a blocked save is the P0 (B1/CFG-25) this whole phase exists to fix. A wrapped, taller save bar covering a tab is acceptable; a tab bar covering the Save button is not. The tab bar sits at 20, deliberately below. Note what is *not* superseded: the discipline. The number was not added preemptively, it was added when a real overlap arrived, and it arrived with its reason written beside it — which is the paragraph working as designed, not failing.
- **Hidden-state specificity collision.** `.dirty-bar[hidden] { display: none; }` exists because the base rule's `display: flex` (author stylesheet) always beats the user-agent stylesheet's `[hidden] { display: none }` regardless of source order — without this override, `dirty-state.js`'s native `hidden` property toggle would have no visible effect and the bar would render even when the form isn't dirty. **This is a whole collision CLASS, not one component's quirk, and it now has four consumers (Phase 22).** The rule: *a component whose own base rule declares `display` always needs its own higher-specificity `[hidden]` selector.* The four are `.dirty-bar[hidden]`, `.refresh-pill[hidden]`, `.login-reveal[hidden]` (X3 — `.copy-btn`'s `display: inline-flex` had defeated the server-rendered `hidden` on the show-password toggle, rendering a **visible control that did nothing** with scripts blocked, which is precisely what the no-JS floor forbids) and `.banner__pill[hidden]` (T13). One **deliberate divergence** inside the class, worth stating so it is not "harmonised" away: `.refresh-pill[hidden]` hides by `visibility`, because it is absolutely positioned and must reserve nothing; the other three hide by `display`. Note also the class of defect: no string-comparison harness can see it — the declaration is present and correct in the file — which is the clearest argument this phase produced for its browser harness.

- **Content clearance for the fixed bar (Phase 22, T7).** A `position: fixed` bar covers whatever sits at the foot of a scrolled page, and nothing was reserving room for it. Both clearances are scoped to `.dirty-ready` — the class `dirty-state.js` adds to `<html>` once it has confirmed its own bar exists — so a page with no save bar reserves nothing. **Both values are measured, not guessed:** `.dirty-ready .dashboard-main` reserves **88px** (the bar renders 64px tall at 1280px, identical in EN and FR since `width: fit-content` means it does not wrap there, plus its 24px gap), and `.dirty-ready .page-content` reserves **144px** (the bar renders **122px EN / 110px FR** at 390px — English is the taller copy here, so the budget follows English). The phone rule is declared **after** `.has-tab-bar .page-content` and physically beside it at the foot of the stylesheet, not 900 lines away: the two target the same element at the same `(0,2,0)` specificity, so source order is the only thing deciding between them.

- **JS-only-affordance rule.** `.js [data-static-save-fallback] { display: none; }` hides the form's own always-rendered bottom Save Settings button once `.js` (added unconditionally by `nav-dropdown.js`'s first statement) proves script is running — so the dirty-state bar is the sole visible save affordance rather than both showing at once. Without JS, the bottom button remains the only way to save; this is the no-JS floor (D-06 graceful degradation), not a decoration.

**How it got here (history, each line SUPERSEDED — none of this describes current behaviour):**

1. quick task 260901-re6 — the bar moved from a genuine descendant of `<form>` (sticky positioned, submitting via normal DOM nesting) to a sibling emitted last on the page, `position: fixed` instead of `sticky` SUPERSEDED. `position: sticky`'s containing block is the nearest scrolling ancestor's *box*, which was the short three-section `<form>` — so the bar stopped sticking at the form's own bottom edge instead of the viewport's, visibly detaching above the Poll section on a page much taller than the form. `position: fixed` is immune to that regardless of any ancestor's height.
2. quick task 260901-re6 (same task, styling half) — the bar's surface moved from `--color-secondary` (a receding, secondary-looking strip) to `--color-dominant` SUPERSEDED, with a single top hairline and an upward-only box-shadow (a y-negated `--shadow-card-hover` literal).
3. quick task 260901-s5o — the bar restyled from a flush, square-cornered, top-hairline-only docked toolbar into a floating, inset, rounded pop-up card SUPERSEDED: a full four-side border replaced the top-only hairline, the shadow became a real token (`--shadow-card-hover`) plus one ambient rgba layer instead of the hand-rolled upward-only literal, and the `>=960px` rule gained a symmetric `var(--space-md)` inset on `bottom`/`right`/`left` with a correspondingly reduced `max-width`.
4. Direct follow-up commit `e87d46d` (non-GSD, developer feedback after seeing 260901-s5o live) — `width: fit-content` replaced an implicit full-column stretch SUPERSEDED (the previous rule set `right` with no `width`, which per CSS2.1's abs/fixed sizing rules — `width: auto` plus both `left` and `right` non-`auto` — stretched the box to fill the entire positioning region, exactly as wide as `.dashboard-main`); the ambient shadow layer deepened from `0 8px 24px / .10` SUPERSEDED to `0 12px 32px / .16`; `bottom` grew from `var(--space-md)` to `var(--space-lg)` SUPERSEDED; and the `>=960px` padding override was dropped entirely SUPERSEDED (it only existed to align a full-width bar with the content gutter — once the bar is compact, the base rule's ordinary `padding: var(--space-md)` applies unmodified).

5. **Phase 23 (D3/CFG-32, 23-09) — the fifth iteration, and the first that is NOT a correction.** The four above are a component finding its shape; this one adds motion and a word to a shape that was already settled, and **the settled part was proven untouched rather than declared untouched**: `git diff` on `style.css` across the whole plan is 88 insertions and 0 deletions, so the geometry, stacking, width, clearance and resting shadow of iterations 1–4 are byte-identical. What is new:
   - **An entrance, as an `animation` and not a transition.** `@keyframes skypane-bar-arrive`, `transform` and `opacity` only, `var(--motion-fast)`, travelling `var(--space-md)` **upward into place** — the bar is pinned to the bottom of the viewport at both breakpoints, so it arrives from the direction a physical object would and never crosses the content it is about to sit over. The declaration is on the **base** rule, so the component has one arrival at both widths, the same discipline its own `z-index` paragraph argues for. **Why an animation and not a transition, which is the interesting half:** a transition out of `display: none` has no previous computed value to start from, so it needs an `@starting-style` entry — and `@starting-style` is newer than this component's audience, so a transition would move for some visitors and **silently do nothing for the rest**. That is the same failure shape the motion budget's `interpolate-size` ban exists to stop, and it is not a smaller failure because the property is Baseline-newer rather than Chromium-only. An animation runs everywhere, and an element at `display: none` runs none of it, so the scripts-blocked reader is reached by nothing either way.
   - **No fill mode, and the ban list is asserted on the keyframes body itself.** `height`, `max-height`, `grid-template-rows`, `width`, `display`, `visibility`, `padding` and `margin` are all forbidden inside the block, and the animation holds no final frame. Both rules exist for one reason: **a bar stranded at an intermediate size or held by a `forwards` fill is a blocked save**, and this app has shipped a blocked save once (B1/CFG-25). With no fill, the element is handed straight back to its own computed style the instant the animation ends. `.js .mobile-nav`'s `transition: none` is this file's own precedent for a size-interpolating transition stranding a value at 0.01ms.
   - **The count moves only when the number does — and this turned out to be an announcement fix, not only a motion one.** `setCountText()` is the count's **one** write site, replacing four (one per branch of `updateBar()`), gated on the rendered sentence genuinely differing. The bar is `role="status"` and `updateBar()` runs on every keystroke, so the previous code rewrote identical text into a live region repeatedly. The element is animated (spending the existing `.is-fading-in`, never a fifth keyframes block); **the number is never tweened**, so the accessible value is the real one at every instant. Text first, class second, and the class is removed-reflow-re-added so a second change restarts the animation rather than being coalesced away.
   - **A translated in-flight label on the Save control, made safe by the control's SHAPE rather than by timing.** `submit-guard.js` defers its disable because a submitter's `name`/`value` joins the form data set *after* the listeners return; a relabel needs no such dance here, because both Save controls are `<button type="submit">` with **no `name`**, so they contribute no entry at all and a label cannot displace anything. That property is re-checked on the live control, so **a later plan that gives either Save a `name` makes the relabel stand down automatically rather than silently rewrite a payload** — the safe failure, but a silent one, so say so in the plan that does it. `<input type="submit">` is excluded by the same clause for the sharper reason that its label IS its submitted value. The order against `submit-guard.js` is fixed rather than lucky: this listener is on the **form** and that one is on **document**, so the event reaches this one first and synchronously while the other only queues a zero-delay task. A bfcache restore undoes the relabel, mirroring `submit-guard.js`'s own `pageshow` handler.
   - **There is no "Saved ✓" on the bar, and that absence is a decision.** The save is a full form POST that replaces the document, so the bar showing the in-flight word does not exist when the save completes; carrying a flag across that navigation means browser storage, and this app holds none. The completed state is the existing `FLASH_KEY_SAVED` confirmation on the page the browser lands on, asserted in both languages.
   - **The `[hidden]` override finally has an executable guard**, in two places: a source clause and a real computed-`display` assertion on both a scripted and a scripts-blocked page. It had never had one, which is notable given the collision class it anchors below.

Two things this history section must get right because they are the parts most likely to be reintroduced wrongly, both already covered above: the duplicated-not-imported `240px`/`column-gap` must-equal geometry (guarded by a harness check, not a shared variable), and the reason the width cap is *reduced* rather than left copied from `.dashboard-main` (a fixed-position box's `100%` resolves against the viewport, not the content column). **A third, as of Phase 23:** the entrance is an `animation` with no fill mode, and both halves of that are load-bearing — "tidying" it into a transition plus an `@starting-style` entry would ship motion that runs for some visitors and not others, and adding `forwards` would reintroduce the stranded-bar class of defect this component has a P0 in its history for.

### `.field-error` is not a settings-only class (Phase 22, X3)

`.field-error` gains a **second consumer**: the login card's password error (`app.py`'s `_login_body()`), alongside its original Settings use. **The placement rule, stated because it is what the class's own `margin-top` exists for: the message goes directly under the offending control** — never above it, never at the top of the form, never beside it. The markup shape is unchanged and composes exactly as Settings' does, `<p class="field-error text-label" role="alert">`, with `.text-label` supplying the size and `.field-error` adding colour only. On the login card it is additionally wired for assistive technology: `aria-invalid="true"` plus `aria-describedby` on the input **only when an error is actually rendered** — never `aria-invalid="false"`, which would announce a state that is not there. Any error-coloured input border is gated through `WCAG_AA_UI_COMPONENT` (3.0) in both themes before shipping, and dropped rather than the threshold weakened if it fails.

## CSS Patterns

```css
/* Section caption — composes with .text-label, adds colour only */
.section-caption {
  color: color-mix(in srgb, var(--color-text) 70%, transparent);
}

/* Save bar, base rule (all widths) */
.dirty-bar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-dominant);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  margin-top: var(--space-md);
  box-shadow: var(--shadow-card-hover), 0 12px 32px rgba(18, 21, 27, 0.16);
}
.dirty-bar[hidden] { display: none; }
.js [data-static-save-fallback] { display: none; }

/* Save bar, >=960px: fixed, inset, content-sized.
 * Phase 22 (T7): z-index added, its absence SUPERSEDED — see the
 * "No z-index, and why" entry above for the stated reason. */
@media (min-width: 960px) {
  .dirty-bar {
    position: fixed;
    bottom: var(--space-lg);
    left: calc(240px + var(--space-xl) + var(--space-md));
    right: var(--space-md);
    width: fit-content;
    max-width: calc(min(1440px, 100%) - var(--space-md) * 2);
    margin: 0 auto;
    z-index: 30;
  }
  .dirty-ready .dashboard-main { padding-bottom: 88px; }   /* measured */
}

/* Save bar, <960px (Phase 22, T7/D-10): also fixed. The bottom offset
 * carries the tab bar's whole 56px row plus the safe-area inset, so the
 * two boxes never overlap — geometric separation first, z-index only as
 * belt-and-braces. */
@media (max-width: 959.98px) {
  .dirty-bar {
    position: fixed;
    left: var(--space-md);
    right: var(--space-md);
    bottom: calc(var(--space-md) + 56px + env(safe-area-inset-bottom, 0px));
    margin: 0;
    z-index: 30;
    flex-wrap: wrap;
  }
  /* Declared AFTER .has-tab-bar .page-content — same element, same
   * (0,2,0) specificity, so source order is the only tiebreak. */
  .dirty-ready .page-content { padding-bottom: 144px; }    /* measured */
}
```

## HTML Structures

```html
<!-- One caption per section, directly under the heading -->
<div class="theme-status" data-dirty-section="Theme">
  <h2 class="text-heading">Theme</h2>
  <p class="text-label section-caption">Panel colors for departing/arriving flights...</p>
  <!-- control -->
</div>

<!-- Save bar: sibling of the form, cross-DOM submission via form= -->
<form id="settings-form" data-dirty-form method="post" action="/settings">
  <!-- sections -->
  <button type="submit" data-static-save-fallback>Save Settings</button>
</form>
<div class="dirty-bar" data-dirty-bar hidden role="status">
  <span data-dirty-count>Unsaved changes</span>
  <button type="submit" class="dirty-bar__save" form="settings-form">Save settings</button>
  <button type="button" class="dirty-bar__cancel" data-dirty-cancel>Cancel</button>
</div>
```

## What to Avoid

- Re-docking the bar: any return to a top-only hairline, squared corners, an upward-only shadow, or full-column width — all four are recorded historical states above, not alternatives still on the table.
- Reintroducing `position: sticky` for the `>=960px` rule — its containing-block behaviour is exactly the bug `position: fixed` fixed.
- ~~Adding a `z-index` to `.dirty-bar` without a stated reason — none is needed today, and one added preemptively is an unearned magic number.~~ **SUPERSEDED (Phase 22, T7): one IS needed today.** `.dirty-bar` carries `z-index: 30` at both breakpoints, above the bottom tab bar's 20, and the reason is stated at the rule and in the mechanics above: the save bar is the active task, the tab bar is ambient chrome, and the blocked save was this phase's P0. The entry is kept because its underlying rule still holds in the form that matters — **do not add or change a `z-index` on this component without a stated reason**, and do not read the surviving 30 as licence to sprinkle more.
- Adding a Settings-specific caption CSS rule instead of reusing the existing `.text-label.section-caption` pair.
- Reintroducing the `>=960px` two-column `.config-form` grid — removed outright by 06.6.4.1 (D-01); do not restore it while "fixing" Settings' layout.

## Origin
Synthesized from: 06.6.3-companion-per-page-redesign (D-03, the original dirty-state bar), 06.6.4.1-companion-page-by-page-ia-consolidation (D-01, D-03, D-04, D-26, closed), quick tasks 260901-qif/260901-re6/260901-s5o, direct commit `e87d46d`, and 06.6.4.1.1-04/06.6.4.1.1-05 (D-01 through D-08/D-17: the theme-chip grid, and the flash-slot move below `page_header()`), cross-checked against `companion/pages/config_page.py` / `companion/static/style.css` / `companion/static/dirty-state.js` / `companion/layout.py` read live at execution time (quick task 260901-t00, updated 06.6.4.1.1-06). Updated Phase 20 (20-companion-suggestions-from-the-audit-french-localisation-liv, D-12/D-14/D-15/D-19, closed 2026-09-12): Display's three supersections reusing `layout.section_intro_html()`, the instant-switch slot's `form="settings-form"` cross-DOM submission, the fused two-form Calendar card and its `:has()` degradation, and the `.rule-row` list replacing the retired rules table. Updated Phase 22 (22-companion-audit-round-4, T7/X3/Gate row, CFG-31): the `@supports selector(:has(*))` block count corrected from a stale "exactly two" to **one**, verified against the live stylesheet (that stale line is what an earlier draft of this phase's own UI spec copied instead of checking the code); the save bar's two contradicted entries — the "No `z-index`, and why" paragraph and its matching "What to Avoid" line — superseded **in place** via the paragraph's own escape clause, with the stated reason and the new sub-960px bottom offset and measured content clearances; the `[hidden]`-versus-`display` collision recorded as a four-consumer class with its one deliberate `visibility` divergence; and `.field-error` recorded as no longer settings-only, with its placement rule stated.
