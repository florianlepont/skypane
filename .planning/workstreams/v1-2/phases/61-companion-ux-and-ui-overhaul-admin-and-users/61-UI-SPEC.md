---
phase: 61
slug: companion-ux-and-ui-overhaul-admin-and-users
status: as-built
reference_commit: c9ce584
reference_date: 2026-11-13
created: 2026-11-02
consolidated: 2026-11-13
supersedes: "revisions 1 to 6 and the plan 61-42..61-63 notes of this file (layered, never signed off; history is in git)"
checker_sign_off: none (the six-dimension check was never run on any revision; see the last section)
owner_approval: "none recorded for this document; owner decisions are recorded one by one in 61-OWNER-VALIDATION.md and 61-OWNER-DECISIONS.md"
shadcn_initialized: false
preset: none
---

# Phase 61: companion UI design contract (as built at c9ce584)

## 0. How to read this document

This is the consolidated, as-built description of the SkyPane companion web app at commit `c9ce584`
(origin/main, 2026-11-13, PR #377, "round 39"). It replaces a spec that grew by revision layers
(revision 1 approved 2026-11-02, revisions 2 to 6 never checked) and that, by round 39, contradicted
the code in many places. Where this document and the code disagree, the code is right and this document has a bug.

**Markers.** Every item in the tables of sections 1 to 7 and 9.3 carries exactly one:

- **DECISION**: an owner or design decision with its rationale (ID such as D39, W5-18; the ledger is
  `61-OWNER-VALIDATION.md`). A decision may also be shipped; when it is, the item says where.
- **SHIPPED**: a fact verified in the code at `c9ce584`, with the file or test that carries it.
- **OPEN**: not delivered, undecided, contradicted by the code, or not verified. The reason is stated.

**Evidence.** Values were read from `companion/static/style*.css`, `companion/ui_*.py`, `companion/pages/*.py` and
`companion/i18n_fr/`. Test files named here exist at `c9ce584`; they were **not re-run** for this consolidation.
Strings: the English `Message` constants in code and the French catalogue in `companion/i18n_fr/` are the single
source of truth, so the per-string copy tables of earlier revisions are dropped; only labels that identify a
page or an action are listed here.

**Depth of verification.** Tokens, geometry, navigation, routes, labels, dialogs and the Home, Users, Fleet and Location structure were read in
the code. Finer behaviour (the exact Location search flow, the look-picker controls, the quiet-hours preset values, the toast and
swipe details, the sign-in refusal wording) was taken from module docstrings, plan summaries and the names of the tests that pin it,
with about twenty message strings spot-checked in `companion/`; those items are marked SHIPPED because a named test or module
carries them, not because every line was re-read.

**Numbering.** "Round N" is the title of a PR ("Phase 61 round N": round 17 = #330 ... round 39 = #377). The
rounds of `61-OWNER-VALIDATION.md` are numbered differently (its Round 23 to 29 cover PR rounds 25 to 39).
"Plan 61-NNN" names a SUMMARY in this directory. Planning documents may cite plan, round and PR numbers; code comments may not.

**Not covered.** Firmware, the e-ink render images, the device protocol (Phase 47, frozen), the server poll loop.

## 1. Scope and standing constraints

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| C1 | DECISION | D10: navigation, structure, modals, lists, messages. Stdlib Python server, hand-written CSS, no runtime dependency, first-party scripts only; Phase 47 files and `hardware/` untouched; every route change expand-only (old paths answer a 303 or a 404, never vanish silently). | `stub-server/test_phase47_freeze.py`; `legacy_pages.py` |
| C2 | DECISION | D18/D19: the one external-content exception is the Location page (OpenStreetMap tiles, Nominatim, vendored Leaflet 1.9.4). No other page loads or contacts anything off-site. | section 5.6 |
| C3 | SHIPPED | One shared stylesheet `static/style.css` (8,185 lines) plus eight area sheets (`style-admin`, `-airlines`, `-c-console`, `-c-lists`, `-display`, `-flights`, `-home`, `-place`) linked per route by `page_styles.py`; served CSS and JS are comment-stripped (`js_minify.py`). No library, no preset (shadcn not applicable). | `test_page_styles.py`, `test_stylesheet_structure.py`, `test_stylesheet_load_order.py` |
| C4 | SHIPPED | Token discipline: no colour value appears in a rule outside a custom-property declaration in `style.css` (after the token blocks) or in any area sheet. Only `style-place.css` (about lines 885 to 895) re-declares the light palette as custom properties on purpose (ink over light map tiles). | grep at `c9ce584`; `test_stylesheet_structure.py` |
| C5 | SHIPPED | Icons are the inline SVG sprite (`ui_base.ICON_IDS`, `icon_html()`), no external icon set. | `ui_base.py` |
| C6 | SHIPPED | Component rule: new UI uses a catalogue component (`ui_components.py`, `ui_groups.py`, `ui_segmented.py`, `ui_modal.py`, `ui_save_bar.py`, `ui_entity_list.py`); the catalogue page is the admin-only `/components` (`pages/components_page.py`). | `test_components_page.py`, `test_browser_components_page.py` |

## 2. Foundations (tokens)

### 2.1 Spacing, safe areas, geometry

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| F1 | SHIPPED | Spacing scale (px): xs 4, sm 8, md 16, lg 24, xl 32, 2xl 48, 3xl 64 (`--space-*`). | `style.css` `:root` |
| F2 | SHIPPED | Safe areas are tokens (`--safe-top/right/bottom/left` = `env(safe-area-inset-*)`); full-height boxes use `svh/dvh/lvh`, not `vh` (except legacy `88vh` on one sheet rule, see D-14). Every page shell carries `viewport-fit=cover` and two `theme-color` metas (`#E7EEF7` light, `#12151D` dark), rendered from the theme cookie so an explicit Light/Dark writes that colour into both tags. | `ui_base.theme_color_meta`; `test_shell_meta.py` |
| F3 | SHIPPED | Touch targets are at least 44px; the `.btn` family is `min-height: 44px`, sidebar links 44px, the copy button is 22px with a 44px hit pseudo-element. Grouped rows are at least 54px. | `style.css` `.btn`, `.row`; `test_browser_overhaul_sweep.py`, `test_browser_hit_area_settle.py` |
| F4 | SHIPPED | 360px is the minimum supported width (320 is out of contract, though the tab bar was measured there); no horizontal page scroll. | `VIEWPORT_MIN_SUPPORTED` in `test_browser_ux_helpers.py`; `test_browser_french_fit.py` |

### 2.2 Typography

System fonts only, nothing downloaded, no serif anywhere (D39).

| Role | Size and weight | Token | Notes |
|------|-----------------|-------|-------|
| Page title (`.page-title`, the one `h1`) | 30 to 34px phone (`clamp(1.875rem, 1.55rem + 1.4vw, 2.125rem)`); 40 to 44px from 960px (`clamp(2.5rem, 2.2rem + 0.9vw, 2.75rem)`); 700, letter-spacing -0.03em, line-height 1.08 | `--font-page-title-size`, `--weight-title` | display face |
| Sub-page / dialog title | 22px, 600 | `--font-heading-size` | e.g. a frame name on Fleet, sheet titles use the card title size |
| Card title in a free-content card | 17px, 600 | `--font-card-title-size` | |
| Body | 16px, 400 | `--font-body-size` | |
| Secondary / label | 15px | `--font-label-size` | not 14px |
| Caption, section label above a group | 13px, 600 for section labels, sentence case, no tracking | `--font-caption-size` | `.section-label` |
| Tab-bar labels / chart axis labels | 11px / 10px | none | the only sub-scale sizes |

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| Y1 | SHIPPED | `--font-ui` is `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Helvetica, Arial, system-ui, sans-serif`; `--font-display` swaps in "SF Pro Display"; `--font-mono` is `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`. No `--font-serif` exists. | `style.css` `:root` |
| Y2 | SHIPPED | Monospace is for identifiers (callsigns, pairing code, MAC, device id, hashes, firmware version, URLs). Times and counts use the UI face with tabular numerals (`.tnum`). | `update_page`, `home_page` |
| Y3 | DECISION | Labels are sentence case; the label voice (tracked uppercase 12px) of the old system was retired in the sky-and-glass restyle (plans 61-52 to 61-60, D39). Table headers are 12px, 600, not uppercase. | `61-VISUAL-AUDIT-NOTES.md` |
| Y4 | OPEN | Three rules still set `text-transform: uppercase` with 0.05 to 0.06em tracking, against Y3: `.update-sum__label` and `.update-hist__title` (round 39 Device and version panel, `style-admin.css`) and the More panel's Settings label (`.tab-bar__prefs .section-label`, `style.css`). Not an owner decision; undecided whether to keep or normalise. | CSS grep |

### 2.3 Colour

Both themes are shipped; a theme is chosen by `html[data-ui-theme=light|dark]` (cookie, rendered server side) or, for Auto, by `prefers-color-scheme`. The token blocks are repeated three times in `style.css` (`:root`, the dark `@media`, the two explicit-theme blocks), so a token change needs several edits (debt D-3).

| Token | Light | Dark |
|-------|-------|------|
| `--sky-top / --sky-mid / --sky-bottom` | `#E7EEF7 / #F1F3F6 / #EDF1F6` | `#12151D / #161A24 / #1A1F2B` |
| `--color-canvas` | `#F1F3F6` | `#161A24` |
| `--color-dominant` (solid card) | `#FFFFFF` | `#151922` |
| `--color-secondary` (cool tint) | `#E9EEF5` | `#1C222D` |
| `--color-border` | `#DAE1EB` | `#2A3040` |
| `--color-accent` (graphite / ivory) | `#1F2430`, hover `#343B4D`, on-accent `#FFFFFF` | `#F2EFE9`, hover `#E2DED5`, on-accent `#14171F` |
| status ok / warn / error | `#16A34A / #D97706 / #BE123C` | `#4ADE80 / #FBBF24 / #FB7185` |
| rarity occasional / rare | `#0F766E / #6D28D9` | `#5EEAD4 / #C4B5FD` |
| `--color-switch-off` | `#7C8799` | `#6B7589` |
| `--color-map-ground` (both themes) | `#F2EFE9` | same |

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| K1 | DECISION | D37/D39: one background per theme, a pale-sky gradient (light) or ink gradient (dark), painted on `<html>` itself with `--color-canvas` as the floor and `--sky-top` as the flat colour, no time-of-day skies, no fixed layer. Direction A of the mockups was chosen for the whole app. | `61-OWNER-VALIDATION.md` Round 5 to 6 |
| K2 | DECISION | D39: the accent is neutral (graphite in light, ivory in dark) so it can never be mistaken for a status colour. It colours links, the active tab, primary buttons, toggles, icon chips and the focus ring; status colours and the two rarity colours are separate. The legacy terracotta is gone (logo included, W179, plan 61-113). | `test_brand_logo.py`, `test_browser_brand_logo.py` |
| K3 | SHIPPED | Contrast is gated: every sky stop and the glass composited over each, both themes; accent, rarity and status pairs; edges. | `test_sky_contrast.py`, `test_contrast_check.py`, `test_browser_contrast_edges.py`, `test_browser_overhaul_sweep.py`; module `test-support/skypane_contrast_check.py` (thresholds 28.0 perceptual distance, 24.0 hue separation) |
| K4 | OPEN | The accent-versus-status separation thresholds were designed for a terracotta accent. With graphite/ivory they are met trivially; nobody re-examined whether the contract is still meaningful. | `skypane_contrast_check.py` |
| K5 | SHIPPED | Dots: `.dot--ok/--warn/--error/--off` and `.dot--hollow` (retired, waiting for pairing). A status is never colour alone: the word is in `title`, `aria-label` and screen-reader text. | `frame_status.py`, `test_frame_status.py` |

### 2.4 Radii, surfaces, glass

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| S1 | SHIPPED | Radius scale: control 14px, card/group/dialog 22px, sheet (top corners of phone sheets and dialogs) 28px, pill (pills, switches, floating bars, tab bar) 32px, chip 9px, drawn frame picture 5px (`--radius-frame-pic`; it had used 14px and looked like a capsule, W63). Circles use 50%. | `style.css` `:root` |
| S2 | SHIPPED | One glass tier: `--glass-bg` (white 0.72 light, 0.09 dark), `--glass-border`, `--glass-highlight`, `--shadow-glass`, `--glass-solid` (opaque fallback), `--glass-hairline` (row separators), `--glass-blur` 22px with `--glass-saturate` 165%. Groups, free-content cards (`.page-section`), tables, dialogs, sheets, popovers and the desktop sidebar use it; a glass surface never sits inside another. | `style.css`; `test_browser_surfaces.py` |
| S3 | SHIPPED | All `backdrop-filter` for the tier sits inside one `@supports ((-webkit-backdrop-filter...) or (backdrop-filter...))` block near the end of `style.css`; outside it every surface keeps its solid fill. The More-panel scrim and the Location sidebar add their own blur outside that block's list (see N5, P-L). | `style.css` |
| S4 | SHIPPED | The gate "at most six blurred elements per page" lives in the overhaul sweep. | `test_browser_overhaul_sweep.py` (`_BLURRED`, `len(blurred) <= 6`) |
| S5 | DECISION | A card does not lift on hover; only an action reacts (hover shadow token is used for floating panels such as the frame-menu panel, not for cards). Primary buttons lift 1px on hover and every button sinks 1px on press. | plan 61-60 |
| S6 | SHIPPED | Segmented control contract (`--seg-*`): a track with a visible edge, a solid accent pill for the selected segment, muted others; one geometry for every chip track (44px track, label 44px, pill inset 3px, label then count on one line at 13px). Used by theme and language, look views, Flights and Airlines filters, Fleet tabs, Location modes. | `ui_segmented.py`; `test_browser_segment_centring.py` |

### 2.5 Motion

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| M1 | SHIPPED | Motion tokens: `--motion-fast` 180ms, `--motion-enter` 400ms, `--motion-stagger` 60ms, `--ease-out`, `--motion-spring` (+`-spring-duration` 420ms), `--motion-press` 90ms, `--motion-view-transition` 260ms, `--motion-shimmer` 1.3s, `--motion-reveal` 900ms, `--motion-picture` 480ms, `--motion-unlock` 560ms, `--motion-count` 600ms, `--motion-slow` 2s, `--motion-dot-pulse` 3.2s, `--motion-breathe` 6s, `--motion-glint` 12s, `--motion-toast-dwell` 6s, `--motion-toast-dwell-long` 12s, `--opening-opacity` 0.6. 23 `@keyframes`, all in `style.css`. A change to this list updates the token-list pin. | `style.css` `:root`; `test_companion_app_04.py` |
| M2 | SHIPPED | Reduced motion: a global rule limits transitions to paint-only properties and zeroes durations and delays (so no style change lays the page out through an intermediate frame, `transitionend` still fires); three `reduce` blocks (two in `style.css`, one in `style-place.css`) and one `no-preference` block are pinned. | `style.css`, `style-place.css`; `test_companion_app_04.py` (`_EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS = 3`) |
| M3 | DECISION | D43/A5-08/A5-09: a page change plays one motion. A page reached by a cross-document view transition (260ms cross-fade) takes `html.page-crossfade` (set in `splash-boot.js`) and its block entrance takes no time; a page opened by address, reload or a browser without view transitions plays the entrance: header at once, then each block one `--motion-stagger` step later, up to five steps (three Flights days); a card, strip or control row rises 12px in whole pixels (`steps(12)`, a fractional rise made 44px controls hit-test one pixel short) and fades from `--opening-opacity`; a list, grid or table fades as a whole; the map stays still. Entrance rules are scoped to `main[data-page-open]`, which `motion.js` drops when the opening ends, so a filter change or a refresh never replays it. | `ui_shell.py`, `motion.js`; `test_browser_page_opening.py`, `test_browser_motion.py`, `test_browser_motion_sheets.py` |
| M4 | DECISION | A5-13: what a control opens (frame menu, More panel, dialog) arrives with a short fade on `--motion-fast` and leaves at once; only what the person moves away (dragged sheet, swiped toast) or what leaves by itself (a timed-out toast) has a leaving motion. | plan 61-118 |
| M5 | SHIPPED | One tab-strip behaviour: a strip whose segments change page (Style, Fleet, Audit) hands its selection to the page change so the thumb glides inside the view transition; strips that switch in place (Flights, Airlines) slide as before. Replay helpers `data-tabs-replay`, `.reveal-replay`, `.reveal-appended`. | `ui_segmented.py`, `motion.js`; `test_browser_tab_pill_transition.py`, `test_browser_motion_live.py` |
| M6 | SHIPPED | Infinite animations are allowed only by name, element and pseudo-element, each with a reason: Home's status dot halo and breath, the picture glow and the glint (`skypane-dot-halo`, `skypane-dot-breathe`, `skypane-picture-breathe`, `skypane-glint`). `.is-breathing` runs fifteen beats (30s) then rests and is `animation: none` under reduced motion; ambient loops stop after about a minute idle. This replaces the earlier rule "the status dot pulse is the only infinite animation". | `test_browser_overhaul_sweep.py` (`AMBIENT_LOOPS`), `test_browser_motion_live.py` |
| M7 | SHIPPED | Pull-to-refresh with a spinner capped at nine turns (6.3s, matching the 6s give-up); airline unlock flip (`--motion-unlock`); Home's countdown rolls once per minute change. | `motion.js`; `test_browser_motion_unlock.py` |
| M8 | SHIPPED | Opening splash ("Cadre"): `splash-boot.js` and `splash.js`, once per session, hard cap 3s, preload of `splash.js`, frame at about 62% of its first size (`--splash-frame-height: min(29svh, 188px)`), percentage never negative or backwards. Duration unchanged by owner decision (W178/D54). | `ui_splash.py`; `test_browser_splash.py` |

## 3. Components

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| B1 | SHIPPED | Buttons: the `.btn` family is the contract (`btn--primary` graphite/ivory, `--secondary` glass, `--ghost`, `--danger`, icon), 44px minimum. | `ui_components.button_html`; `style.css` `.btn` |
| B2 | OPEN | A legacy base remains: bare `button {height: 30px}` and `button[type=submit]` with an accent fill (about `style.css:2333` to `2370`), overridden by `.btn`. Raw `<button>` without `.btn` is still emitted in `pages/airlines_page.py`, `co_managers_card.py`, `locations_page.py`, `pair_frame_page.py`, `update_page.py` and page-specific classes (`collection-controls__apply`, `history-controls__apply`, `row-menu__item`, `airlines-*__save` in `<noscript>`). Any un-classed submit is a 30px target (WCAG 2.5.8 AA met, AAA not). | grep at `c9ce584` |
| B3 | SHIPPED | Grouped lists (`ui_groups`): `section_label`, `group` (one glass `ul.group`), `group_panel` (free content), `row` (>= 54px; main area is an `<a>`, a `<button>` or a `<div>`; optional 32px icon chip, label, detail, value, trailing control placed after the main area so a control is never inside a link), `hero`. A group never contains another group. | `ui_groups.py`; `test_ui_groups.py` |
| B4 | SHIPPED | Pills: `ui_components.pill_html(text, tone)`, neutral plus tones `ok`, `info`, `warn` (added in round 39). | `components_page.py`; `test_components_page.py` |
| B5 | SHIPPED | Switches: `role=switch` button, 52x32 track, 24px thumb, accessible name is the setting; the switch's `::after` makes the whole row its target. | `ui_components.py`; `style.css` `button.switch` |
| B6 | SHIPPED | Entity lists / tables: `ui_entity_list.py` (`ul.entity-list`, count line). Table headers 12px 600 not uppercase, rows >= 56px, hairlines from `--glass-hairline`, the table wrapper is the one glass surface. | `test_ui_entity_list.py` |
| B7 | SHIPPED | Modal component: native `<dialog class="modal">` driven by `modal.js` (`showModal()`, page inert, focus trap by the browser, Esc, 44px close control, focus returns to the opener). A refused re-render comes back with the dialog open, `aria-invalid` and a `.field-error`. | `ui_modal.py`, `modal.js`; `test_ui_modal.py`, `test_browser_ux_01.py` to `test_browser_ux_04.py` |
| B7a | SHIPPED | Initial focus is the first field, or the dismiss control for confirm-only dialogs so Enter never confirms a destructive action; the Quiet hours dialog opens on its title so no time field raises the keyboard. A backdrop click closes only dialogs without inputs. | `modal.js`; `test_browser_quiet_hours_modal.py` |
| B7b | SHIPPED | No-script floor: dialogs open from hash links (`.modal:target`) and submit as plain forms. | `test_browser_quiet_hours_modal.py` (scripts-blocked case), `test_browser_fleet_dialogs.py` |
| B7c | SHIPPED | Geometry: from 700px centred, `width: min(480px, 100% - 48px)`; below 700px a bottom sheet with 28px top radius, grabber, drag to close, `max-height` 85dvh (one legacy rule still says `88vh`, D-14) and safe-area bottom padding. | `style.css` `dialog.modal` |
| B8 | SHIPPED | Dialog helpers beyond the single-form dialog: `ui_modal.sections_dialog_html` (several forms: Manage access, airline sheet) and `ui_modal.choice_dialog_html` (three-way question: the unsaved-changes dialog). Destructive confirmations name their dismiss control ("Keep frame", "Keep retired", "Stay on this frame", "Keep current owner", "Keep special look"); there is no generic "Cancel". | `ui_modal.py` |
| B9 | SHIPPED | Floating flash toast keeps an inverse surface with five tones (`--color-toast-*`), dwell 6s (12s for pending, `--motion-toast-dwell(-long)`), placed above the tab bar and the save bar on a phone, in regions `.toast-region--flash` and `--live`. There is no `.quick-toast` class any more. | `toast.js`, `style.css`; `test_browser_toasts.py`, `test_toasts.py` |
| B9a | SHIPPED | Docked banners (notification, attention) are glass banners with a 32px icon chip; toasts swipe to dismiss (`is-swiping`, `is-returning`, `is-leaving`); a session-expired template and an offline-notice template exist in the shell. One toast and one sheet at a time. | `ui_shell.py`, `toast.js`; `test_browser_one_toast_one_sheet.py` |
| B10 | OPEN | The toast `pending` tone is orange (`#FF9A70` on the dark slab, `#B13F16` on the dark-page variant): the only non-graphite hue left in the accent role. Undecided. | `style.css` `--color-toast-pending` |
| B11 | SHIPPED | One Save bar, one producer: `ui_save_bar.save_bar_html(form_id, ...)` renders the floating "message, Cancel, Save" bar (`.dirty-bar`) for Style, Location, Fleet settings, the frame rename page and the Style form pages. | `ui_save_bar.py`; `test_browser_save_bar.py` |
| B11a | SHIPPED | Tracked mode: a `data-dirty-form` form. The bar is in the page without script with a plain Save marked `data-static-save-fallback`; `dirty-state.js` hides it until a field differs and writes "Unsaved changes" (or "Unsaved changes: Look, Layout" when several areas changed); Cancel is a native `type=reset`. A bar that only shows on change is kept out of the first paint by `data-dirty-wait` while `html.js-early` is set. | `dirty-state.js`; `test_browser_fleet_dirty_bar.py` |
| B11b | SHIPPED | Page mode (`cancel_href` plus title): Cancel is a link back, optional `reveal_on_change`, `shown` for a page redrawn with a refused value, `inline` turns it into the two buttons of a phone sheet. | `ui_save_bar.py`; `test_browser_save_bar.py` |
| B11c | SHIPPED | After Cancel, focus returns to the last changed control (W5-21); on `pageshow` the bar, the Layout summary and the value controls are brought in line with a browser-restored form (W5-01). | `test_browser_cancel_focus.py`, `test_browser_page_restore.py` |
| B12 | DECISION | W5-18, then plan 61-125 (round 38), owner: leaving any page that has a Save bar through an in-app link, with anything unsaved, asks "Unsaved changes: Save and continue / Discard / Stay here" (FR "Enregistrer et continuer / Abandonner / Rester ici"). Rationale: the owner changed pages with the bottom tab bar and lost a colour change. Browser Back keeps its behaviour (Back leaves the page, no history entry per dialog, W5-12). | `ui_save_bar.py`; `test_browser_leave_dialog_pages.py`, `test_browser_style_leave.py` |
| B12a | SHIPPED | One producer: `page_shell` renders the dialog once on any page whose body contains `dirty-bar` and not already `data-leave-dialog`; the Components page carries its own sample. | `ui_shell.py` |
| B12b | SHIPPED | `dirty-state.js` intercepts link clicks (not links inside dialogs or the bar, `target` or `download` links, modal openers, same-page hash links, other origins) and posts of other forms (the theme switch). "Save and continue" lands on the tapped page only when its path is in the page's `data-leave-returns` list (Style views, Device, the nav tabs), a fixed tuple compared byte for byte; otherwise it saves and stays. | `dirty-state.js`, `personalisation_cards.LEAVE_RETURN_ROUTES` |
| B13 | SHIPPED | Dirty state and the tab-strip change inside Style: changing sub-tab with an unsaved layout opens the same dialog (round 36, plan 61-123). | `test_browser_style_leave.py` |

### 3.1 Dialog inventory (as built)

All are `dialog.modal` (B7); a destructive confirm names its dismiss control and focuses it first. Routes are POSTs with CSRF.

| ID | Marker | Dialog | Opened from | Action | Dismiss label (EN) | Evidence |
|----|--------|--------|-------------|--------|--------------------|----------|
| Dg1 | SHIPPED | Invite a user (e-mail, role; submit "Invite user") | Users header action | `/users/invite` | Back to Users | `users_page.py`; `test_console_users.py` |
| Dg2 | SHIPPED | Add a frame (pairing code, owner) | frame menu "Add a frame" on Fleet only | `/fleet/pair` | Back to Fleet | `fleet_page.py`; `test_browser_fleet_dialogs.py` |
| Dg3 | SHIPPED | Retire, Reassign, Re-activate a frame (destructive; Reassign is primary for the served frame) | Fleet Access block and Other frames rows | `/fleet/frames/<id>/{retire,reassign,reactivate}` | Keep frame, Keep current owner, Keep retired | `fleet_page.py`; `test_console_lifecycle.py` |
| Dg4 | SHIPPED | Manage access (sections dialog, `access-sheet`: owner, co-managers, add, Remove per row) and Add co-manager (Fleet add row) | Account (owned frames) and Fleet | `/co-managers/add`, `/co-managers/remove` | Done | `co_managers_card.py`; `test_browser_access_sheet.py` |
| Dg5 | SHIPPED | Leave this frame; owner removes their frame (destructive confirms) | Account | `/co-managers/leave`, remove-frame route | Stay on this frame, Keep frame | `co_managers_card.py`; `test_owner_remove_frame.py` |
| Dg6 | SHIPPED | Role change confirmation (promote and demote; rendered open, `return_on_close`) and Delete user confirmation (names the owner rule) | Users role select, "..." menu | `/users/<id>/role` with `confirmed=1`, `/users/<id>/delete` | per dialog (`_PROMOTE_KEEP`, `_DELETE_KEEP`) | `users_page.py`; `test_console_users_delete.py` |
| Dg7 | SHIPPED | Quiet hours (presets, Start/End tiles) | Home Frame group | `/quick/quiet-hours/window` | Close | `home_page.py`; `test_browser_quiet_hours_modal.py` |
| Dg8 | SHIPPED | Remove special look; Disconnect calendar (destructive confirms) | Style special-look rows; calendar connect page | rules remove route; calendar disconnect route | Keep special look; calendar cancel text | `settings/rules.py`, `settings/calendar.py` |
| Dg9 | SHIPPED | Airline detail sheet (read-only, sections dialog, no form) | Airlines grid card | none | Close | `airline_collection_page.py` |
| Dg10 | SHIPPED | Resolve an unidentified airline, two steps (name, then artwork) | Airline editor "Name it"; reused from the Fleet System registry | `/airlines/resolve` | per step | `resolve_dialog.py`; `test_health_resolve_dialog.py` |
| Dg11 | SHIPPED | Unsaved changes (choice dialog, three buttons) | any in-app link on a page with a Save bar (B12) | the page's own save | Stay here | `ui_save_bar.py` |
| Dg12 | OPEN | The earlier spec's dialog 8 (Manage user), dialog 10/11 (frame sheet, Airline details as form) and dialog 13 (Keep resolution) do not exist as specified: Manage user was replaced by the Users table (U1), the frame sheet by the popover (N19), the resolution delete has no confirmation (U5). | | | | |

## 4. Information architecture and navigation

### 4.1 Spaces and who sees what

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| N1 | DECISION | D16 (V0): the personal space is one set of pages for an administrator and a user, with identical navigation and bodies. The only difference in the whole personal space is the administrator's way to the Console. A user never sees the words Admin, Console, Fleet, Releases, Health, Device or Update. | `test_personal_space_parity.py`, `test_admin_personal_scope.py`, `test_nav_personal_console.py` |
| N2 | SHIPPED | Personal pages (OWNER_DEVICE access): Home `/`, Flights `/flights` (title "Flight history"), Location `/detection` (title "Location and detection"), Style `/display` (+ `/display/arrivals`, `/special-looks`, `/calendar` and their form pages), Airlines `/airlines` (read-only collection), Account `/account`, Pair frame `/pair-frame`. Console pages (administrator only): Fleet `/fleet`, Users `/users`, Airline editor `/airlines/manage`, Audit log `/audit`, Components `/components`. | `ui_nav.py`, `console_routes.py`, `routes.py` |
| N3 | SHIPPED | Health, Device and Releases have no navigation entry: their content lives in the Fleet view. `GET /health` and `GET /device` answer a 303 to the frame's Fleet view (Settings tab for Device); `GET /update` redirects too, except for a hardware type with no frame, which is still served. `/locations` GET is a 303 to `/fleet`; its POST routes remain with no UI (expand-only). `/settings`, `/history`, `/preview` are 303s; `/display/screen` and `/display/layout` redirect to `/display`. | `fleet_moves.py`, `legacy_pages.py`; `test_legacy_redirects.py`, `test_legacy_admin_page_redirects.py` |
| N4 | SHIPPED | Admin-only, device-scoped access kind (`ADMIN_DEVICE`) for `/health`, `/airlines/manage` and the airline POSTs (resolve, rename, rename-reset, manual-resolution delete, artwork upload/delete, default type); a user or co-manager gets 404. | `route_types.py`, `routes.py`; `test_access_matrix.py`, `test_airline_manage_routes.py` |
| N5 | SHIPPED | Landing: an administrator lands on `/fleet` (a validated `?next=` wins); a user lands on the Home of the first frame by name (ties by id), else on `/account` with the empty state; a user requesting an un-prefixed frame page gets a 303 to the same page under their default frame; `/login` while signed in redirects to the landing page. | `next_route.py`; `test_landing.py`, `test_user_view_http.py` |
| N6 | OPEN | An administrator who owns or co-manages no frame sees the empty state on personal Home; reaching the served frame is through Fleet ("Open personal view"). Round 2 chose this as a default (R2-9) and the owner never confirmed it. | `61-OWNER-DECISIONS.md` |

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| R1 | SHIPPED | Routes and access as built (selected). Access kinds: SIGNED_IN, OWNER_DEVICE (frame owner, co-manager or administrator on the frame; un-prefixed pages 303 to the default frame), ADMIN_ONLY, ADMIN_DEVICE (administrator, frame-scoped). Every POST carries CSRF; every old route is expand-only. | `routes.py`, `console_routes.py`, `route_types.py`; `test_access_matrix.py`, `test_route_table.py` |


| Route | Method | Access | Note |
|-------|--------|--------|------|
| `/login`, `/login/auth0`, `/callback`, `/logout`, `/credits` | GET/POST | as today | `/login?error=cancelled&next=` is the closed-set cancelled page |
| `/`, `/flights`, `/detection`, `/display` (+ `/arrivals`, `/special-looks`, `/calendar`, form pages), `/airlines` | GET | OWNER_DEVICE | personal space; `/devices/<id>/...` prefix per frame |
| `/detection` | POST | OWNER_DEVICE | `action=save_place`; old `save_detection` and `save_location` stay for scripts |
| `/quick/quiet-hours/window` | POST | OWNER_DEVICE | writes only the three quiet-hours keys |
| `/account`, `/pair-frame` (GET/POST), `/frame/name` (GET/POST), `/ui-theme`, `/ui-lang` | | SIGNED_IN or OWNER_DEVICE as listed in `routes.py` | rename is checked again server side |
| `/fleet`, `/fleet/pair`, `/fleet/frames/<id>/{retire,reassign,reactivate}`, `/users`, `/users/invite`, `/users/<id>/{role,disable,enable,unlink,delete}`, `/audit`, `/components` | GET/POST | ADMIN_ONLY | `/fleet/register` has no UI |
| `/airlines/manage` and its POSTs, `/airlines/resolve`, `/airlines/rename`, `/airlines/rename-reset`, `/airlines/manual-resolutions/<p>/delete`, artwork routes | GET/POST | ADMIN_DEVICE | a user or co-manager gets 404 |
| `/health`, `/device`, `/update` | GET | ADMIN_DEVICE / ADMIN_ONLY | 303 to the frame's Fleet view (N3) |
| `/locations` | GET | ADMIN_ONLY | 303 to `/fleet`; its POST routes remain with no UI |
| `/settings`, `/history`, `/preview`, `/display/screen`, `/display/layout` | GET | | fixed 303s |


### 4.2 Phone: one tab bar for everyone (below 960px)

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| N7 | DECISION | Round 26 and 27 (plan 61-120, owner): the bottom bar is the same for everyone: Home, Flights, Airlines, Style, Place, More (FR Accueil, Vols, Compagnies, Style, Lieu, Plus). The administrator's Console switch moved from a first cell into the More panel. The earlier "space switch as first cell" and "More without Airlines" designs are gone. "Compagnies" fits at 360px in French and at 320px without shortening. | `ui_nav._personal_bar`; `test_browser_tab_bar_roles.py`, `test_browser_nav_spaces.py` |
| N8 | DECISION | Owner, round 27: the Console-space bar keeps five cells: Fleet, Users, Editor, Audit, More (FR Flotte, Équipe, Éditeur, Journal, Plus). Account and the switch back to "My frame" are in More. Fleet carries the severity dot, drawn at the icon's corner. Labels are the short forms `nav.users_short`, `nav.airlines_short`, `nav.audit_short`. | `ui_nav._console_bar` |
| N9 | SHIPPED | Geometry: a floating pill, `left/right: max(8px, safe)`, `bottom: 6px + safe-bottom`, 68px high, 32px radius, 1px `--bar-border`, a shadow, z-index 20. Page content clears bar + gap + safe area; a focused control is scrolled clear of it (`scroll-padding-bottom`). | `style.css` `.tab-bar`; `test_browser_tab_bar_float.py` |
| N9a | SHIPPED | The bar is **opaque** (`--glass-solid`; no blur, no sheen). Cells are `flex: 1 1 auto; min-width: 44px; height: 56px`, so widths are unequal; labels are 11px and never wrap (ellipsis). | `test_browser_tab_bar_float.py` |
| N9b | SHIPPED | The active cell's pill is solid accent with the on-accent label (semibold); a `.tab-bar__slider` positioned by `motion.js` glides between cells, and the active pill carries the view-transition name `skypane-tab-slider` so it moves through a page change. | `motion.js`; `test_browser_tab_pill_transition.py` |
| N10 | DECISION | The bar never hides on scroll (considered in plan 61-57 and rejected: a bar that slides off-screen breaks pointer targets for assistive and automated input). Implemented: it is fixed, always shown. | `style.css` `.tab-bar` |
| N10a | SHIPPED | More is a native `<details>`, so it works without script; the active pill sits on More on pages that belong to no cell (Credits, Components, error pages); a frame's not-found page shows More alone, at most 96px wide. | `ui_nav._tab_bar_html`; `test_browser_tab_bar_float.py` (no-script case) |

### 4.3 The More panel (rounds 34 and 35, plans 61-120 to 61-122)

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| N11 | DECISION | Owner, round 27: the More panel is redesigned (plans 61-121, 61-122; PR rounds 34 and 35). Top to bottom: grab handle; an Account row (circle with the person's initial, "Account" over the e-mail, chevron); for an administrator one tinted link card to the other space (option B); a "Settings" group; Sign out. | `ui_nav._more_panel_html`; `test_browser_more_panel_redesign.py`, `test_browser_more_sheet.py` |
| N11a | SHIPPED | The link card reads "Console" with the subtitle "Fleet, users, audit" and a shield icon in the personal space, and "My frame" with a device icon and no subtitle in the Console. | `ui_nav._switch_row_html` |
| N11b | SHIPPED | The Settings group holds Theme and Language as segmented trailing controls (plain POST forms, one tap each); Sign out is a full-width soft-error button. On the Account page the panel holds the links only (the page carries its own controls, so no second Sign out). | `ui_nav._sheet_preference_row` |
| N12 | SHIPPED | The sheet is opaque and takes the bar's colour. While it is open a fixed scrim covers the whole window on every page: `body:has(.tab-bar__more[open])::after`, z-index 44, 55% ink with `blur(8px)`, the bar raised to 46. | `style.css`; `test_browser_more_scrim_cover.py` |
| N12a | SHIPPED | The root's own paint carries the same dim so the zones iOS draws under the status bar and toolbar match; `modal.js` rewrites the `theme-color` metas while the sheet is open; on Location the map layers above and below the page are dimmed too. | `style.css`, `modal.js`, `style-place.css` |
| N13 | OPEN | The More-panel dim on every tab and on the Style leave dialog still needs the owner's checks on a real iPhone (OWNER-VALIDATION Round 28), widened since by 61-125 to every Save bar. | `61-OWNER-VALIDATION.md` |
| N14 | OPEN | Naming debt: the More Account row reuses the class `.mobile-nav__link` of the removed hamburger panel; `ui_nav.py` header and one inner comment still mention the "hamburger preferences panel" and "mobile-nav". `nav-dropdown.js` is a 15-line file that only adds the `js` class. | `ui_nav.py`, `style.css` |

### 4.4 Desktop sidebar (960px and up) and the space switch

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| N15 | SHIPPED | A floating glass panel with the brand. Personal sidebar (administrator and user alike): Home, Flight history, Location and detection, Style, Airlines (FR Accueil, Historique des vols, Lieu et détection, Style, Compagnies), then a group with Account; footer: Sign out only. Language and theme are on the Account page and in the phone More panel; the sidebar has neither (W14). Console sidebar: eyebrow group "Administration" (Fleet, Users), a group (Editor, Audit log), a group (Account). The sidebar says "Editor" like the bar; the page title stays "Airline editor" (W04, one full name per page). The current item is a solid accent pill; links are 44px with the focus ring hugging the item. | `ui_nav._personal_sidebar_parts`, `_console_sidebar_parts`, `ui_shell.py`; `test_nav_personal_console.py`, `test_browser_nav_alignment.py` |
| N16 | SHIPPED | The administrator's two-segment switch (Console / My frame, each with a glyph, the current one with a check and `aria-current="page"`, wrapper `nav.space-switch`, label "Space" / "Espace") exists on desktop only, at the top of the sidebar; both segments are fixed-destination GET links (`/fleet`, `/`); the Account page marks neither. It is never rendered for a user. | `ui_nav.space_switch_html`; `test_browser_space_switch.py`, `test_space_switch.py` |
| N17 | OPEN | The desktop sidebar has no theme or language control and the phone has them in More: intentional per W14 (account-only preferences) but the asymmetry is not recorded as a decision. The label `nav.frame_tools` (EN "Frame tools", FR "Outils du cadre") is still declared in `ui_base.py` and the French catalogue but no navigation renders it. `console_routes.CONSOLE_NAV_ENTRIES` still lists Health, Device and Releases (filtered at render). | `ui_base.py`, `i18n_fr/nav.py`, `console_routes.py` |

### 4.5 App bar, frame menu, iOS Home Screen mode

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| N18 | SHIPPED | Phone app bar: transparent (no fill, border or blur), padded by the safe-area top, brand left, frame button right; min-height 52px + safe area. On desktop the header collapses to the frame button. | `style.css` near `.site-header`; `test_browser_tab_bar_float.py` (top bar case), `test_browser_page_title_phone.py` |
| N19 | DECISION | D39/D40: the frame picker is a frame button with a popover, not a tile strip or a sheet (it replaced the D30 strip and its phone fold). The button (`details.frame-menu > summary`) is a glass pill >= 44px with the status dot, the frame name (ellipsis) and a chevron, shown when the person has two or more frames or may add one. | `frame_menu.py`; `test_browser_frame_menu.py` |
| N19a | SHIPPED | The popover (`.frame-menu__panel`) is 300px wide (`max-width: calc(100vw - 24px)`), right-aligned under the button on phone and desktop; rows are >= 52px plain links (frame picture, name, last-seen word, the owner for a frame that is shared or not the viewer's, status dot, a check on the current one). Rows go to the same page of the other frame. | `frame_menu.py`, `style.css`; `test_frame_switcher.py`, `test_frame_sheet.py` |
| N19b | SHIPPED | A native `<details>` works without script; `modal.js` adds Escape (focus back to the button), outside tap and `aria-expanded`. | `modal.js` |
| N20 | SHIPPED | Console variant of the popover: every frame (problems first, with the owner), a "System" row, and a last "Add a frame" row that opens the pairing dialog (the only entry to it). On personal pages "Add a frame" leads to `/pair-frame`. An administrator opening someone else's frame sees a `.frame-notice` strip ("Viewing {owner}'s frame", link "Back to Fleet"). | `frame_menu.console_menu_html`, `ui_shell.frame_notice_html` |
| N21 | DECISION | #372 (2026-11-13): in an iPhone Home Screen web app iOS 27 draws a frost over the top of the window below the status bar. `splash-boot.js` adds `html.web-app` when `navigator.standalone === true` (false in a Safari tab, undefined elsewhere; the site has no manifest, and the `apple-mobile-web-app-*` metas tried in earlier rounds did not survive), and below 960px `--app-bar-drop: 24px` moves the app bar and everything placed under it (Location floats) down. Workaround for an open WebKit bug, documented in `.planning/debug/resolved/home-screen-app-wordmark-blur.md`. | `splash-boot.js`, `style.css` (`html.web-app`); `test_browser_web_app_bar.py` |
| N22 | OPEN | No web-app manifest and no `apple-mobile-web-app-*` meta exist (plan 61-93b's SUMMARY says a translucent status-bar meta was added; it was not kept). The 24px drop is the only iOS Home Screen accommodation besides the Location lead/tail (P-L). | grep at `c9ce584` |
| N23 | DECISION | Breadcrumb-free: no page shows two stacked navigation rows; the Style sub-navigation and the Fleet phone tabs are in-page segmented strips, not a second tab bar. | `ui_segmented.py` |
| N24 | DECISION | Mobile navigation without script: More is a `<details>`; the frame menu is a `<details>`; dialogs open from hash links; every nav item is a plain link. | `test_browser_tab_bar_float.py` (no-script case), `test_browser_flights_cards.py`, `test_browser_home_recent_tiles.py` |

### 4.6 Labels (EN / FR)

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| N25 | SHIPPED | The labels in the table below are verified against `ui_base.py`, `ui_nav.py`, `i18n_fr/nav.py` and `i18n_fr/admin_shell.py`; "Personalisation" is no longer a label anywhere, the Style tab is "Style" in both languages. | those files |

| Where | EN | FR |
|-------|----|----|
| Phone bar, personal | Home / Flights / Airlines / Style / Place / More | Accueil / Vols / Compagnies / Style / Lieu / Plus |
| Phone bar, Console | Fleet / Users / Editor / Audit / More | Flotte / Équipe / Éditeur / Journal / Plus |
| Sidebar and page titles, personal | Home / Flight history / Location and detection / Style / Airlines / Account | Accueil / Historique des vols / Lieu et détection / Style / Compagnies / Compte |
| Sidebar and titles, Console | Fleet / Users / Editor (title "Airline editor") / Audit log | Flotte / Utilisateurs / Éditeur (title "Éditeur de compagnies") / Journal d'audit |
| Space switch | Console / My frame; nav label "Space" | Console / Mon cadre; "Espace" |
| More panel | Account, Console ("Fleet, users, audit"), Settings (Theme, Language), Sign out | Compte, Console ("Flotte, utilisateurs, audit"), Réglages (Thème, Langue), Se déconnecter |


## 5. Pages

### 5.1 Sign-in and first arrival

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| L1 | SHIPPED | Sign-in refusals render in the login card as a docked toast with fixed wording (nothing from the identity provider, no e-mail echoed): unverified e-mail (403, own page chosen before any lookup), not invited or disabled (403, same page for unknown, disabled and unmatched identities, with "Use another account" adding `prompt=login`), incomplete (400), expired (400), cancelled at the provider (a 303 to `/login?error=cancelled`, closed set of codes), unavailable (503), throttled (429). | `login_page.py`, `sign_in.py`; `test_sign_in_messages.py`, `test_sign_in_cancelled.py`, `test_refused_post_sign_in.py` |
| L2 | SHIPPED | A refused POST goes to `/login?next=<the form's page>&expired=1` (the next page is the request's same-host Referer, checked like any `next`); the session-expired card is `session-guard.js` / a shell template; the "request refused, page expired" page offers "Open the page again" (the GET of the page the form came from, no query). | `test_csrf_reopen.py`; `test_browser_audit3_fixes.py` |
| L3 | DECISION | First arrival: a 14px hint under the login line, the landing interstitial names its real target, and the first identity link shows one welcome toast (`flash=welcome`). | `flash.py`, `login_page.py` |
| L4 | SHIPPED | An unexpected exception is answered with a translated 500 page in the app's chrome (logged once: method, path without query, traceback); an unknown asset path answers an empty 404; credits offer "Back to Home / Account / sign in". | `server_error.py`, `static_files.py`; `test_server_error_page.py`, `test_static_assets_404.py`, `test_credits_page.py` |

### 5.2 Home

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| H1 | DECISION | W53/W54 introduced a greeting title; rounds 13 and 14 replaced it. The Home `h1` is the **frame's name** with a small round pencil (>= 44px hit area) shown only to those who may rename the frame (owner, administrators). The pencil opens the Rename page (`/frame/name`), which returns to where it came from; the document title and navigation label stay "Home" / "Accueil". The greeting, `data-greeting-*` and the plane on a trail are deleted. | `pages/home_title.py`, `frame_name_page.py`; `test_home_title.py`, `test_browser_home_title.py` |
| H2 | SHIPPED | Order on Home: attention notice (one short sentence ending with "contact an administrator", mailto button) in `.home-facts`; the frame-state card (`hero`: current picture with a cycle ring, the state word equal to the status-dot word, next-update line); a hidden "Frame state" `h2` follows the `h1`. | `pages/home_page.py`; `test_home_state_card.py`, `test_browser_home_state_card.py` |
| H2a | SHIPPED | **Detection** group: one link row naming the active mode ("Position mode", "Airport & runway mode" or "No place set", with its detail) leading to Location (`detection_summary.home_card_html`, round 25, #356). | `test_home_detection_card.py`, `test_browser_home_detection_card.py` |
| H2b | SHIPPED | **Frame** group: Screen switch, Quiet hours switch (its window text is a dialog trigger) and the Battery row (H3); then the **Recent flights** group (up to five informational rows without links, a plane chip turned by direction, then one "See all flights" link row; a compact empty state); the quiet-hours dialog is a sibling of the swapped regions so a refresh never discards it. | `home_page._switches_html`, `_recent_flights_html`; `test_browser_home_recent_tiles.py` |
| H3 | SHIPPED | Battery row (`home_battery_row.py`, every signed-in person): icon tile, percent with a level word ("Low", "Very low"; never colour alone), thin bar, and an autonomy estimate ("battery life ~N days/weeks", "under 2 days") only when `battery.battery_life_estimate()` supports it; "No reading yet" with no bar when there is none; a charging frame shows "Probably charging" instead of a figure. | `test_browser_home_battery_row.py`, `test_battery_charging.py` |
| H4 | SHIPPED | Quiet-hours dialog (`/quick/quiet-hours/window`, OWNER_DEVICE, csrf): title "Quiet hours"; three preset cards Night 23:00 to 07:00, Day 08:00 to 18:00 and "Always on" (FR "Nuit", "Journée", "Toujours actif"); two Start/End time tiles (step 300); the "Use quiet hours" checkbox is the no-script control and is hidden with script; footer links to the time zone in `/detection#details`; it writes only the three quiet-hours keys; equal start and end with the window on is refused with a field error; a refused save re-renders Home with the dialog open (400). | `settings/quiet_hours.py`, `home_page.quiet_hours_dialog_html`; `test_quiet_hours_modal.py`, `test_browser_quiet_hours_modal.py` |
| H5 | SHIPPED | The status vocabulary is one resolver, `frame_status.frame_status`, feeding Fleet, the frame menu, Account and Home: Retired and Waiting for pairing (hollow dot, administrator only), No contact (error), Not seen yet (warn), Overdue or Low battery (warn), Resting (off), Up to date (ok), first match wins. | `frame_status.py`; `test_frame_status.py` |
| H6 | SHIPPED | Home refreshes in place (`freshness.js`, page key `home`): a cheap token (`stat()` calls, one `SELECT`, the health snapshot) answers a matching tick with a bodiless 304; Home carries no visible freshness line. | `freshness.py`; `test_freshness_token.py` |

### 5.3 Flights

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| FL1 | SHIPPED | Phone: one glass group per Paris calendar day (section label "Today", "Yesterday", "3 Sep"), one row per flight (callsign and route codes, "airline - aircraft" detail, live age over the clock). Desktop from 960px: a glass table with day separator rows. The old detail-row table, `flight-rows.js` and the airline artwork plate are gone. | `history_page.py`, `style-flights.css`; `test_browser_flights_cards.py`, `test_flights_cards.py` |
| FL2 | DECISION | W58/W172 and #358/#359: one lead element per row. A flight links its own archived render only: since #359 the poll cycle stores the render's file name with the flight (`runway_events.gallery_name`) and the page links exactly that render; only rows written before the column fall back to the timestamp window (render archived at most 90s before and 10s after the flight). The lead is then a 44px target holding a 40px thumbnail with an 18px direction glyph; otherwise a 44px **non-interactive stand-in** (the airline's illustration, else a plane icon) that asks for the smallest served WebP variant. The filter chips (Departures / All / Arrivals) carry no counts (W172). | `history_page.py` (`matching_gallery_entry`, `_stand_in_thumb_html`); `test_browser_flights_stand_in.py`, `test_flights_cards.py`, `test_browser_audit4_fixes.py` |
| FL3 | SHIPPED | Server-side search, sort and "Load more" (`?q ?kind ?sort`, `?part=list`, `?part=new&more=N`; ten Load-more steps ship about 0.95 MB instead of 6.3 MB); one cached fold of the history (`history_query.folded_history`) is shared with the Airlines collection; the first live search gets its own history entry, so Back returns to the unfiltered list; an unanswered list request (offline) keeps the page and shows an error toast; lists are `aria-busy` while a request is out. | `history_cache.py`, `list-filter.js`; `test_flights_search_sort.py`, `test_browser_flights_search_more.py`, `test_history_cache.py` |

### 5.4 Airlines (read-only collection)

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| A1 | DECISION | V10/D16: `/airlines` is the same read-only collection for every role: counts, rarity, first/last seen, types and recent callsigns derived only from the frame's `runway_events` plus the curated airline list; no new storage, no points, streaks, ranking or sharing. Rarity by sightings: Regular >= 10, Occasional 3 to 9, Rare below 3; badges at 1, 5, 10, 25, 50 airlines; "New" pill within 7 days. | `airline_collection.py` (`REGULAR_MIN`, `OCCASIONAL_MIN`, `BADGE_THRESHOLDS`); `test_airline_collection.py`, `test_airline_collection_page.py` |
| A2 | SHIPPED | Page: one header line (title, thin `<progress>` with a sentence, five 30px badges); one controls bar (filter field, segmented All / Spotted / Not yet seen, a 44px sort icon button opening a radio menu Most seen / Rarest / Latest / A to Z, an "i" legend button); a grid of cards (2 columns, 3 from 700px; the 4 columns planned from 1280px were not built) each opening a read-only detail sheet (`#dlg-airline-<id>`, bottom sheet, at most 85dvh, head and Close foot fixed); not-yet-seen cards are dimmed (picture only). The rarity colours are the two rarity tokens plus a neutral tier; dots and the word always accompany colour. | `pages/airline_collection_page.py`; `test_browser_airline_collection.py` |
| A3 | SHIPPED | Tabs and sort switch the list in place (a fetch-and-swap, `data-collection-form`, no page reload or entrance replay; Back works); the sort moves cards on the page with no request, each card carrying its server-computed rank per order; the card picture uses the card's content width with no nested box (W176/W177). | `list-filter.js`; `test_browser_airline_collection.py` |

### 5.5 Style (look, special looks, calendar)

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| ST1 | SHIPPED | `/display` is the Style page ("Style" in both languages). A Layout card (one setting per frame) sits above one section navigation, `nav` "Style sections", four plain links with a 20px icon: Departures `/display`, Arrivals `/display/arrivals`, Special looks `/display/special-looks`, Calendar `/display/calendar`; 44px, a sliding thumb, scroll-snap on a phone. Forms are their own pages with the page-mode Save bar (new/edit special look, calendar connect, calendar look `/display/calendar-look`). The Screen view was removed (the switch is on Home, D35). The wake interval, diagnostic LED and manual refresh are not on Style (ST4). | `pages/personalisation_cards.py`; `test_personalisation_page.py`, `test_browser_personalisation_layout.py`, `test_browser_personalisation_pairings.py` |
| ST2 | SHIPPED | The look picker (Departures and Arrivals views): frame picture of the chosen kind plus one picker card (colour dots in 44px targets, background and band segments, "Same as departures" on Arrivals, Reset, Save). 31 themes (`device_config.THEMES`, D50/61-91a) in a swatch picker; disabled combinations keep their colours dimmed with an `aria-describedby` reason. It fits one 390x844 or 360x740 screen above the tab bar (W59). From 960px the picture and picker sit in two columns. | `settings/theme.py`; `test_browser_personalisation.py`, `test_browser_display_looks.py`, `test_theme_picker_profile.py` |
| ST3 | SHIPPED | Special looks and Calendar are one glass group of rows plus an add row; rows have a trailing Remove (a rule opens nothing, so no chevron); Remove confirms in a dialog ("Keep special look"). Each Style page has its own document title. | `settings/rules.py`, `settings/calendar.py`; `test_personalisation_special_looks.py` |
| ST4 | DECISION | Wake interval: administrators set it in the Fleet Settings block (device scope: diagnostic LED, wake interval, manual refresh), not on Style. The diagnostic LED switch stays admin-only, off by default, part of the frame protocol (owner, round 29). The earlier "Refresh" card on Personalisation does not exist. | `config_page.py` (`SCOPE_DEVICE`); `test_browser_device_led_switch.py` |

### 5.6 Location and detection (`/detection`)

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| P1 | SHIPPED | The map is the page; the page title is visually hidden. Phone: a stage from the app bar to the tab bar, a floating search field at the top and two mode chips under it. | `pages/place_page.py`, `style-place.css`; `test_browser_place_page.py` |
| P1a | SHIPPED | Phone sheet: compact, at most 28dvh. Airport mode: one line with the airport name and codes and one row of runway chips; My position mode: the hint "Tap the map to place", then "Radius (km)" with number and slider; the Save bar sits inline in the sheet. | `test_browser_place_sheet.py`, `test_browser_place_compact_sheet.py` |
| P1b | SHIPPED | Desktop (960px and up): the map fills the content area with a 360px card at the left, the mode switch at its top. Modes are the radios `place-mode-runway` / `place-mode-area`, labelled "Airport" / "My position"; with no saved detection setting the default is My position. | `place_page._default_mode` |
| P2 | SHIPPED | One search field: an airport ICAO, IATA or name opens that airport (`?airport=`, no request leaves the page); anything else is an address looked up on submit only (Nominatim, `countrycodes=fr`, `limit=5`, one request in flight, 1.5s lock, one answer cache shared by suggestions and submit). | `place-search.js`, `place-map-search.js`; `test_browser_place_search.py` |
| P2a | SHIPPED | Typing two or more characters lists up to six airports from the page's own catalogue (combobox and listbox, arrow keys, Enter, the first Escape closes the list); no request while typing. | `place-card.js`; `test_browser_place_search_gate.py` |
| P2b | SHIPPED | Locate button (48px round, `geolocation=(self)`, 10s timeout), tap-to-place in My position mode, every catalogue airport drawn as a pin at every zoom (the followed one larger, IATA label from zoom 6), credits behind a 44px "i" popover. | `place-map.js`; `test_browser_place_pins.py`, `test_browser_place_map.py` |
| P3 | SHIPPED | No script and no network: the whole page is server-rendered; choosing an airport is a GET (`?airport=`, `?q=`), coordinates, label and time zone are plain fields in the `#details` block (open without the map), one native POST (`action=save_place`) stores them. With the map running, `#details` shows only when targeted (the Quiet hours note) or after a refused save. | `test_place_page.py`, `test_place_save.py`, `test_detection_page.py`, `test_browser_detection.py` |
| P4 | SHIPPED | Storage (D20, no saved-locations UI): a private `locations` row per frame, created on the first map save, updated in place, copy-on-write when an old row is shared by several devices; an unchanged save writes nothing; legacy runway ids are untouched; validators unchanged (airport and runway from `server/data/airports_fr.json`, `radius_km` 2 to 28, coarse France box for a free pin, a catalogue airport accepted anywhere). The saved toast names what was saved (a runway names its airport; My position names "the area within N km of" the place). | `detection_actions.py`; `test_detection_position.py`, `test_location_picker.py` |
| P5 | SHIPPED | CSP and Permissions-Policy: every response sends the default policy (`img-src 'self' data:`, `geolocation=()`); only the Location page (GET and a refused-POST re-render) sends `img-src ... https://tile.openstreetmap.org`, `connect-src 'self' https://nominatim.openstreetmap.org` and `geolocation=(self)`. Tile layer `referrerPolicy: 'origin'`; no prefetch, no tile cache. | `page_policy.py`; `test_page_policy_headers.py` |
| P6 | SHIPPED | Vendored Leaflet 1.9.4 (BSD-2-Clause) under `static/vendor/leaflet/` (`leaflet.js` SHA-256 `db49d009...e5641a`, `leaflet.css` `a7837102...d04c6`, `LICENSE`, `VENDOR.md`; hashes match the values recorded in the original spec); no CDN, no key, no marker PNG request; tests route both OSM hosts through `page.route`. Credits on `/credits`. | `test_vendored_leaflet.py`, `test_place_map_assets.py`, `test_compliance_credits.py` |
| P7 | DECISION | The iPhone status-bar and toolbar zones (rounds 15 to 27; #357, #363, #369; owner decision 2026-11-13). The app bar draws no backdrop of its own on this page; the map shows through. Where `navigator.standalone` exists (a Safari tab or a Home Screen web app, false or true alike) `place-map.js` adds `html.place-lead`: an 80px lead of map above the page (`--place-lead`) and an 80px tail below (`--place-tail`), the page opens scrolled past the lead, `<html>` is `overflow: hidden` (no manual scroll) and settles back after any script, keyboard or rotation scroll; the 4px `.place-edge` strip shows only while the map loads. Every other phone browser (Android Chrome) gets none of it, so its own toolbar-hiding scroll is untouched. The light-palette ink on the brand and the frame button applies on every phone (tiles are light in both themes); `style-place.css` carries a copy of the light palette for it. The owner confirmed the earlier top-edge fix on device (ledger Round 27); the final narrowing to `navigator.standalone` (#369, owner decision 2026-11-13) has no recorded on-device confirmation yet (I2). | `style-place.css`, `place-map.js`; `test_browser_location_full_bleed.py`, `test_browser_status_bar_band.py`, `test_browser_place_document_map.py` |
| P8 | DECISION | Map content is shown as served (no dark filter): the tile licence and legibility win; the frame and controls use tokens. | `style-place.css` |
| P9 | OPEN | `style.css`'s opening comment and the old skill text say the stylesheet has "no external references"; true of the CSS, not of this page. Wording to settle when the skill is rewritten. | `style.css` header |

### 5.7 Account and pairing

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| AC1 | SHIPPED | `/account`: groups My frames (one row per frame: drawn frame picture, name, an Owner or Co-manager pill, hardware or "Shared by" line, status dot and last-seen word; "Manage access" on owned frames, "Leave frame" on shared ones; last row "Add a frame"), Identity (e-mail; Role with "Co-manager of N frames"), Preferences (Language and Theme rows with a content-sized segmented control), Sign out as its own danger row. Empty state "Your frames will appear here" with a primary "Add your frame" button (readable again since #362/plan 61-114). | `pages/account_page.py`; `test_account_page.py`, `test_browser_account_frames.py` |
| AC2 | SHIPPED | `/pair-frame`: a plain form (pairing code `XXXX-XXXX`, validity help, "Add frame", Cancel) for a signed-in person; the owner is always the signer; same code validation and both throttles as `/fleet/pair`; a refused code is kept for one showing in a 2-minute `sp_pair_code` cookie (outside the address) and put back in the field (round 37, plan 61-124, owner option A); success 303 to the frame's Home with a toast. | `pair_code_cookie.py`, `pages/pair_frame_page.py`; `test_user_pairing.py`, `test_browser_user_pairing.py` |
| AC3 | SHIPPED | Manage access (`dialog.modal.access-sheet`, a bottom sheet on a phone with 28px top padding, 85dvh, fixed head and foot, scrolling body of one "Co-managers" group: owner row, co-manager rows with a quiet Remove, the add row; a co-manager sees "Leave frame" instead). Opened by the owner or an administrator. | `co_managers_card.py`; `test_browser_access_sheet.py`, `test_co_manager_access.py` |
| AC4 | SHIPPED | Rename frame page (`/frame/name`, page-mode Save bar, return target scoped so Cancel and Save never land on a 404 or an unreachable page). | `frame_rename.py`, `pages/frame_name_page.py`; `test_frame_rename_and_users_switch.py` |

### 5.8 Console: Fleet

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| FE1 | SHIPPED | `/fleet` shows the frame in view (chosen from the frame-button popover, N19, N20) as glass groups: State (health rows with native `<details>`), Device and version, Settings (the former Device form: LED, wake interval, manual refresh) and Access (owner with Reassign, co-managers, add row, a Retire row). A header holds two link buttons, "Open personal view" and "Rename". | `console_fleet_view.py`, `pages/fleet_page.py`; `test_console_fleet_view.py`, `test_browser_fleet_sections.py` |
| FE1a | SHIPPED | Phone: a segmented control State / Settings / Access (plain links `?frame=<id>&tab=<tab>`, works without script, deep-linkable) shows one block at a time; from 1000px the blocks are two columns on one page. | `test_browser_fleet_tabs.py` |
| FE1b | SHIPPED | "System" is a separate view of platform-wide parts (flight-data source agreement, identification, backups, unresolved-airline registry); pending and retired frames sit in "Other frames (n)". Settings save, update install and co-manager change 303 back to `/fleet?frame=<id>[&flash=...]`; an unknown `?frame=` shows a docked notice naming the frame shown instead; the page refreshes in place (`freshness.js`, key `fleet`). | `test_browser_console_fleet_view.py` |
| FE2 | SHIPPED | Dialogs on Fleet: pairing code and owner (opened only from the frame menu's "Add a frame"), Retire, Reassign (destructive unless the frame is the served frame), Re-activate, Manage access. Retire and Reassign are not offered for the served frame where the rule forbids it. | `pages/fleet_page.py`; `test_browser_fleet_dialogs.py`, `test_console_lifecycle.py`, `test_console_pairing.py` |
| FE3 | DECISION | Round 39, owner decision (ledger Round 29): redesign the "Device and version" block as in the mockup, display only: the install and revert forms, confirmations, CSRF fields, no-script behaviour and admin-only access are unchanged. | `61-126-SUMMARY.md`; `test_browser_firmware_panel.py` |
| FE3a | SHIPPED | State on top: "On the frame" / "Sur le cadre", the installed version large in monospace, "Installed ... ago" and the model on the next line, and one state chip (Update available, Up to date, or the scheduled, installing or failed state). The separate Model row is gone. | `pages/update_page.py`; `test_update_page.py` |
| FE3b | SHIPPED | One update card, present only while an update is offered: version, its age, the title without a trailing "(DRAFT ...)" tag, one full-width primary "Install fw-vX". | `test_browser_update.py` |
| FE3c | SHIPPED | Flat version list (no table, no card inside the card): each row is a native `<details>` (status dot, monospace version, date, age, notes count, an Installed or Newest chip, a chevron) whose body is the release notes, with a ghost "Revenir" (EN "Revert") button outside the summary, 44px target. In-flight states keep their card; a newer release that is not the offered one keeps a quiet text "Install". | `style-admin.css`; `test_browser_fleet_sections.py` |
| FE4 | OPEN | Two firmware surfaces coexist: the Fleet panel (round 39) and the standalone `/update` page, which keeps its older markup and is served only for a hardware type with no frame. Whether to retire or redesign it is undecided. | `61-126-SUMMARY.md` |

### 5.9 Console: Users, Airline editor, Audit

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| U1 | DECISION | X03, owner option A (Round 25), shipped in PR round 32: the Users page is a glass **table from 79.5rem (1272px)** and glass cards below (the narrower "70rem" and the "Manage user" dialog of the earlier design are gone). Rationale: every row of the same parts must be equally tall, so an address is one line with an ellipsis and its full address in the title. | `pages/users_page.py`, `style-admin.css`; `test_browser_users_rows.py`, `test_browser_users_cards.py` |
| U1a | SHIPPED | Columns: User (initial avatar, e-mail, status pill, "You"), Role (select), Frames, Last sign-in (one line), Active (switch), Invitation (copy the invitation message) and a "..." menu. On phone cards the address wraps at `@` and `.` (W02) and at 26rem the Active label is dropped. | `test_browser_users_page.py` |
| U2 | DECISION | The role select saves on change and lands on a confirmation dialog (`/users?role_change=N&role=...`; promotion and demotion both ask; focus on the way out; only the dialog's button writes the role; "Save role" for no-script users). Owner: the role-change confirmation stays and supersedes the old "no confirmation" line (Round 25). | `users_page.py`; `test_audit4_fixes.py`, `test_browser_users_page.py` |
| U3 | SHIPPED | The Active switch posts through `data-quick-switch` and answers a 200 carrying the toast and `X-Quick-Switch-Result: toast` (the same "User disabled/enabled" toast as the no-script path). | `test_browser_users_page.py`, `test_frame_rename_and_users_switch.py` |
| U3a | SHIPPED | The "..." menu holds the identity unlink (shown once the user has signed in) and "Delete user" (its own confirmation; not on the signed-in administrator's own row). Guard sentences ("This is you", "last active administrator") replace the select with a locked switch. "Invited" shows only with no identity link and no recorded sign-in. Invite dialog: e-mail and role (default User), submit "Invite user". | `console_users.py`; `test_console_users.py`, `test_console_users_delete.py` |
| U4 | SHIPPED | Airline editor (`/airlines/manage`) is one **global** list (the frame strip is gone, W36): views, last seen and type counts aggregate every frame in scope, a flight seen by two frames counting once per frame. No explanatory captions on administrator pages (W34). Table from 70rem, cards below. | `pages/airlines_page.py`, `style-airlines.css`; `test_airline_editor.py`, `test_browser_airline_table.py` |
| U4a | SHIPPED | One table with a `<tbody>` per airline: name field saved in place, prefixes, an artwork thumbnail that opens the lightbox, views, last seen and a "..." menu ("Change artwork", "Reset to the original name"). A native `<details>` chevron expands one sub-row per aircraft type, fetched lazily from `/airlines/manage?types=<n>` (administrator only, bare fragment); unidentified prefixes are amber rows at the top with "Name it". | `airline_table.py`, `airline_types_fragment.py`; `test_browser_airline_editor.py` |
| U5 | OPEN | Deleting a manual resolution ("Delete my name") is a danger button with no confirmation dialog; the row leaving the list is the confirmation (comment at `airlines_page.py:226`). Earlier spec text promised a "Keep resolution" dialog. | `pages/airlines_page.py` |
| U6 | SHIPPED | Audit log: one chip row (scroll-snap, one line), a glass group on phone (`ul.audit-cards`), a glass table on desktop. | `pages/audit_page.py`; `test_browser_audit_page.py` |
| U7 | SHIPPED | `/components`: the catalogue page (admin only; each family ends with "Back to the index"); linked from the Fleet System view footer. | `components_page.py` |

## 6. Cross-cutting behaviour and audit results

### 6.1 Audit 4 (D54, owner: "treat 100%"; plans 61-108 to 61-110, rounds 21, 22, 24)

| ID | Marker | Result | Evidence |
|----|--------|--------|----------|
| Q1 | SHIPPED | Visual findings W01 to W23 treated: "Invited" status follows the last sign-in; user cards wrap addresses at `@` and `.`; sidebar names the editor like the bar; System cards start at the page column; form pages use the page-mode Save bar revealed on change; sidebar focus ring hugs the item; `--picture-placeholder` token and a fade-in for small pictures; Credits has a way back; 3px inset at both ends of every tab strip; pending colour dots keep their colours; one 2px focus ring on the Location search; the Components page ends each family with a link to the index; the pending count is the standard pill. | `test_audit4_fixes.py`, `test_browser_audit4_fixes.py` |
| Q2 | SHIPPED | Workflow partials: CSRF on six routes; rename `return_to` scope (`frame_rename._return_to` refuses unreachable frames and `/components` for a non-administrator); Flights search history; no-JS image load; broken-pipe log noise; a refused special-look key redirects (Post/Redirect/Get) instead of resubmitting on reload. | `test_audit4_fixes.py`, `test_csrf.py` |
| Q3 | SHIPPED | Performance findings R01 to R28: one shared place-search limiter; history and collection caches with single-flight; lazy airline-type rows; deferred map start (`place-start.js` loads Leaflet, the gate, `place-map.js`, `place-card.js` in order after two frames and an idle callback); stylesheet split (R14); empty 404 for asset paths (R18); splash preload (R22); bfcache with a `pageshow` session check (R23). Not changed with reasons: `content-visibility` for cards (R10, R15), Brotli (owner deploy decision in the Caddy build). | `61-109-SUMMARY.md`, `61-110-SUMMARY.md`; `test_history_cache.py`, `test_browser_perf_quick_wins.py`, `test_browser_perf_remaining.py` |

### 6.2 Audit 5 (D56, 84 findings, lots A to E, plans 61-115 to 61-119, rounds 29 to 33)

| ID | Marker | Result | Evidence |
|----|--------|--------|----------|
| Q4 | SHIPPED | HTTP methods (W5-19): `HEAD` answers like `GET` (headers, no body; the bearer-token export answers headers only); `PUT`, `DELETE`, `PATCH`, `OPTIONS` answer 405 with an `Allow` header and the app's own page in the request language. | `test_http_methods.py`, `test_export_battery_history.py` |
| Q5 | SHIPPED | Forms and sessions: expired-page "Open the page again" (W5-10); equal start and end quiet hours refused (W5-14); a sign-in cancelled at the provider is a 303 (W5-16); the request language is set before any handler (W5-08); a refused POST goes to `/login?next=...&expired=1` (W5-05); role-change confirmation (W5-04); Save bar follows a choice the browser restored on Back (W5-01); the pairing code is kept for one showing outside the address and the **upload CSRF token moved from the address into the multipart body** (W5-15, W5-23, round 37). | `test_csrf_reopen.py`, `test_sign_in_cancelled.py`, `test_quiet_hours_modal.py`, `test_user_pairing.py`, `test_airline_editor.py` |
| Q6 | SHIPPED | Headings (W5-20): one `h1` per page; Home's hidden "Frame state" `h2` follows the `h1`; the sign-in document has a `<main>`; the repeated "Special looks" `h3` is removed; each Style page and the rename page have their own title. | `test_page_structure.py` |
| Q7 | SHIPPED | Keyboard and focus (W5-21): after Cancel focus returns to the last changed control; in the Flights and Airlines sort menus an arrow key keeps the menu open on the choice while a pointer choice closes it; no-script floor everywhere. A focused control scrolls clear of the tab bar (X09). | `test_browser_cancel_focus.py`, `test_browser_flights_search_more.py` |
| Q8 | SHIPPED | Upload messages (W5-24): a refusal names its rule: not a PNG, too large (size and pixel caps), not transparent, too small or portrait (four new flash keys, EN/FR; the generic key remains for an unreadable body). | `test_airline_editor.py`, `test_companion_app_05.py` |
| Q9 | SHIPPED | Offline and sessions (lot C): a list request with no answer keeps the page and toasts an error; Cancel after an in-place airport pick on a page that opened without a pin restores the map's opening view (W5-03); the idle warm-up runs on a new page view only (P5-05). | `test_browser_remaining_audit_fixes.py`, `test_browser_page_restore.py` |
| Q10 | SHIPPED | Motion findings (lots A, D): the opening fade starts at 0.6; reduced motion no longer shifts layout (Location CLS from 0.35 to within 0.03); 35 hard-coded 150ms durations use `--motion-fast`; the Home countdown rolls once per minute. | `test_browser_motion.py`, `test_browser_page_opening.py` |
| Q11 | OPEN | Lot E skipped with reasons, of which W5-18 and W5-23 were later delivered (rounds 36 and 37). Still skipped: A5-21 (the 0.146 layout shift is the Load more block moving down as rows are inserted above it, the intended result), A5-12 nested entrance (not reproduced), A5-14 for the splash and Leaflet's own 250 ms (single authored sequence; vendored library). | `61-119-SUMMARY.md` |

### 6.3 Accessibility, bilingual, structure

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| X1 | SHIPPED | Focus ring: a global 2px outline with 2px offset in the accent; rows and the sidebar use an inset ring; a visible ring on every control type; `aria-current` on the current navigation entry, `aria-haspopup`/`aria-expanded` on menus; placeholders at 4.5:1; disabled text at 3:1. | `style.css`; `test_browser_overhaul_sweep.py`, `test_browser_navigation_assist.py` |
| X2 | SHIPPED | Every user-facing string is bilingual: `i18n.t()` accepts only `Message` objects (declared where the English lives), the French catalogue is split over 27 modules in `companion/i18n_fr/` (about 1,500 message ids); French fit is tested at 360px. | `i18n.py`; `test_i18n.py`, `test_browser_french_fit.py` |
| X3 | OPEN | The bilingual contract has two stale leftovers: the dead `nav.frame_tools` id (N17) and the English-only comment drift in `ui_nav.py` (N14). | |
| X4 | SHIPPED | Reading order and landmarks: skip link to `#main-content`, one primary navigation landmark visible at a time (the 960px rule hides the other copy), `main` on every document including sign-in. | `ui_shell.py`; `test_page_structure.py` |

## 7. Tests that carry the contract

Behaviour-over-source rule: tests assert served HTML, CSS, JS or a browser, never source text or `.planning/`
(`companion/test_suite_guards.py` enforces it). Names below exist at `c9ce584`; browser files are `pytest.mark.browser`
(pytest-playwright; a missing browser fails CI). Not re-run for this document.

| Area | Files |
|------|-------|
| Nav, spaces, access | `test_nav_personal_console.py`, `test_nav_spaces.py`, `test_user_nav.py`, `test_space_switch.py`, `test_personal_space_parity.py`, `test_access_matrix.py`, `test_browser_nav_spaces.py`, `test_browser_tab_bar_float.py`, `test_browser_tab_bar_roles.py`, `test_browser_more_sheet.py`, `test_browser_more_panel_redesign.py`, `test_browser_more_scrim_cover.py`, `test_browser_web_app_bar.py` |
| Save bar and leave dialog | `test_browser_save_bar.py`, `test_browser_leave_dialog_pages.py`, `test_browser_style_leave.py`, `test_browser_cancel_focus.py`, `test_browser_page_restore.py` |
| Home | `test_home_title.py`, `test_home_state_card.py`, `test_home_detection_card.py`, `test_quiet_hours_modal.py`, `test_browser_home_battery_row.py`, `test_browser_home_notice.py`, `test_browser_home_recent_tiles.py`, `test_browser_home_signature.py` |
| Location | `test_place_page.py`, `test_place_save.py`, `test_vendored_leaflet.py`, `test_browser_place_page.py`, `test_browser_place_search.py`, `test_browser_place_pins.py`, `test_browser_place_compact_sheet.py`, `test_browser_location_full_bleed.py`, `test_browser_status_bar_band.py` |
| Flights, Airlines | `test_flights_cards.py`, `test_flights_search_sort.py`, `test_browser_flights_stand_in.py`, `test_browser_flights_search_more.py`, `test_airline_collection.py`, `test_browser_airline_collection.py` |
| Console | `test_console_fleet_view.py`, `test_browser_fleet_tabs.py`, `test_browser_firmware_panel.py`, `test_browser_users_rows.py`, `test_browser_users_page.py`, `test_browser_airline_table.py`, `test_browser_audit_page.py`, `test_components_page.py` |
| System-wide | `test_stylesheet_structure.py`, `test_stylesheet_load_order.py`, `test_page_styles.py`, `test_sky_contrast.py`, `test_contrast_check.py`, `test_browser_overhaul_sweep.py` (blur count, ambient loops, focus rings, overflow, 44px), `test_browser_page_opening.py`, `test_companion_app_04.py` (motion tokens), `test_http_methods.py`, `test_page_structure.py`, `test_i18n.py`, `test_browser_french_fit.py`, `test_browser_ux_01.py` to `test_browser_ux_04.py` |
| Gates (repo level) | `scripts/check_function_size.py` (80 lines), `scripts/check_comment_history.py`, `stub-server/test_phase47_freeze.py`, `./scripts/run-all-tests.sh` |

Testable invariants kept from the earlier spec and still true (each is asserted by a file above): no horizontal overflow at 360 and
1280px in both languages and themes on the pages and dialogs; every interactive element at least 44x44 by hit-testing (the OSM
attribution link is the one WCAG inline exception); the admin and user personal pages have identical navigation and controls;
no Health, Device, Fleet, Users, Audit, Releases or Editor link in the personal space; the access matrix has a row for every new
route; every new string exists in English and French.

| ID | Marker | Item | Evidence |
|----|--------|------|----------|
| V1 | OPEN | The earlier numbered assertions R1 to R28 and the step-count table (A1 to A8, U1 to U4, L1 to L4, S1, S2, V1) are not re-measured against the round 39 build. `61-STEP-COUNTS.md` holds the last measurements (rounds before the single tab bar); "Airlines now one tap from the bar for everyone" and "Console switch two taps (More, card)" change some counts. | `61-STEP-COUNTS.md` |

## 8. Decision IDs cited in this document

Not counted in the summary: this table only decodes IDs. The ledger of record is `61-OWNER-VALIDATION.md` (owner answers, by round) and `61-CONTEXT.md` (D1 to D15).

| ID | Meaning |
|----|---------|
| D10 | Scope: navigation, structure, modals, lists, messages; no new runtime dependency |
| D16, V0 | One personal space for administrator and user; Health and Device are Console-only |
| D18, D19, D20 | Real OSM map on Location, place choice by pin, list, address and "Use my position"; no saved-locations UI, a private position row per frame |
| D27, D28 | Quiet-hours dialog design (sketch C); Location page as full map (sketch V1) |
| D29, W10 | Style as a segmented section navigation over one view at a time |
| D30, D39, D40 | Frame picker: strip, then frame button with popover; D39 is also the "style A" visual direction for the whole app |
| D32, D33 | Users and Airline editor as tables from a breakpoint, cards below (rev 3 mockups) |
| D34, D35 | A signed-in person pairs their own frame (`/pair-frame`); the Style Screen view removed |
| D36 | Location mockups L1 to L3 (phone airport, phone position, desktop) |
| D37, D38 | Choose visual direction A; apply it through the shared stylesheet only, no content change |
| D42, D43 | Audit 1 decisions; motion decisions answered idea by idea on demos |
| D50 | The 31-theme look catalogue |
| D53 | Compact Location sheet on phones |
| D54, D55 | Audit 4: treat 100% of it; then the five remaining performance points |
| D56 | Audit 5: treat all 84 findings, in lots A to E |
| W5-nn, X0n, A5-nn, P5-nn | Audit 5 finding IDs (workflow, visual, accessibility-motion, performance) |
| W nn | Owner feedback items of the validation rounds (W02 ... W179) |

## 9. Summary

### 9.1 Decisions, shipped, open

Counts are of the markered items in the tables of sections 1 to 6 and 9.3 (one marker per item; sub-items such as `B7a` count on their own; the
Dg rows of 3.1 and the R1 route item are included; the deviation list in 9.2 and the ID table in section 8 are not).

| Marker | Count | Where the weight is |
|--------|-------|---------------------|
| DECISION | 28 | navigation model (N1, N7, N8, N10, N11, N19, N21, N23, N24), motion and colour (M3, M4, K1, K2, S5, Y3), page choices (H1, FL2, A1, ST4, FE3, U1, U2, L3), Location (P7, P8), the leave dialog (B12), scope (C1, C2) |
| SHIPPED | 131 | tokens and components (sections 2 and 3), navigation and routes (4), pages (5), audit results and accessibility (6) |
| OPEN | 19 | contradictions or undecided points: Y4, K4, B2, B10, Dg12, N6, N13, N14, N17, N22, P9, FE4, U5, Q11, X3, V1; in flight: I1, I2, I3 |
| Total | 178 | |

### 9.2 Known deviations and design debt

| ID | Item | Where |
|----|------|-------|
| D-1 | Legacy bare `button` rules (30px, accent-filled submit) survive under `.btn`; raw `<button>` without `.btn` and page-specific button classes in six page modules (B2). | `style.css`, `pages/*.py` |
| D-2 | Legacy class names reused: `.runway-card` for the Style look picker (`settings/theme.py`, `layout_picker.py`), `.mobile-nav__link` for the More Account row (N14). | `style.css` |
| D-3 | Theme tokens are repeated three to four times in `style.css` (`:root`, dark `@media`, `html[data-ui-theme=light]`, `...=dark`, about 160 lines each) and the light palette is copied again in `style-place.css`; a token change needs several edits. | `style.css`, `style-place.css` |
| D-4 | Inconsistent breakpoints: `959.98px` and `959px`, `699.98px` and `699px`, `70rem`, `79.5rem`, `1280px` are all in use. | `style*.css` |
| D-5 | A duplicate rule `.history-cards ~ .data-table-wrap` exists in `style.css` and `style-c-lists.css`. | `style.css`, `style-c-lists.css` |
| D-6 | The toast `pending` tone is orange, the only non-graphite hue in the accent role (B10). | `style.css` |
| D-7 | Dead strings and constants: `nav.frame_tools` (declared, not rendered), `CONSOLE_NAV_ENTRIES` entries for Health, Device and Releases that have no navigation entry (N17). | `ui_base.py`, `console_routes.py` |
| D-8 | Two firmware surfaces: the Fleet panel (round 39) and the older `/update` page (FE4). | `pages/update_page.py` |
| D-9 | Three uppercase, tracked labels against the "no label voice" rule (Y4). | `style-admin.css`, `style.css` |
| D-10 | No web-app manifest; the iOS Home Screen accommodation is a 24px app-bar drop for an open WebKit bug, recorded only in a debug note and a CSS comment (N21, N22). | `style.css`, `.planning/debug/resolved/` |
| D-11 | The deletion of a manual airline resolution has no confirmation dialog (U5). | `pages/airlines_page.py` |
| D-12 | The WCAG 2.5.8 AAA target size is not met where an un-classed submit button survives (B2). | |
| D-13 | A failing test reported by plan 61-126 and not re-run here: `companion/test_device_routes.py::TestPrefixCrawl::test_global_targets_are_never_prefixed` (three `/display` variants) failed on the branch tip before round 39. | `61-126-SUMMARY.md` |
| D-14 | One sheet rule still uses `max-height: 88vh` where the rest use `dvh`. | `style.css` |
| D-15 | The Airlines collection grid stops at three columns; the four columns of the earlier design (from 1280px) were never built (A2). | `style-airlines.css` |

### 9.3 In flight (after `c9ce584`)

`git fetch origin main` on 2026-11-13: `origin/main` is still `c9ce584`; `git log c9ce584..origin/main` is empty. New commits may land after that;
this document describes `c9ce584` only.

| ID | Marker | Item |
|----|--------|------|
| I1 | OPEN | Draft PR #378 ("docs: frame types and companion mockups for the v1.3 photo milestone", base `explore/photo-mode-v1-3`, planning and design only, no `companion/` code). A frame gets a type (planes or photos) set by an administrator; a photo frame's menu is Home, Photos, Style, Account; a plane frame is unchanged. It will **rewrite navigation** (per-type tab bar and sidebar, a Photos page) and so sections 4.1 to 4.6 of this document. v1.3 phases 66 to 68 (frame type, companion photo frames, wake interval) are not implemented in the companion. Also open: #349, a dependency bump unrelated to the UI. |
| I2 | OPEN | Owner iPhone checks outstanding: the More-panel dim on every tab and the leave dialog on every Save bar (N13). Final owner validation, plan 61-13, is not done (it has a PLAN and no SUMMARY); the phase is therefore not closed. |
| I3 | OPEN | The project skill `sketch-findings-skypane` and the component catalogue describe the earlier warm/serif/hamburger design and are being rewritten by another agent; until that lands the skill is not a source for this contract. |

## Checker Sign-Off

Not performed. The six-dimension check (copywriting, visuals, colour, typography, spacing, registry safety) was run on no
revision of this spec, and this as-built document has not been through it.

- [ ] Dimension 1 Copywriting: not run
- [ ] Dimension 2 Visuals: not run
- [ ] Dimension 3 Color: not run
- [ ] Dimension 4 Typography: not run
- [ ] Dimension 5 Spacing: not run
- [ ] Dimension 6 Registry Safety: not run

**Approval:** none. This document was consolidated on 2026-11-13 by reading the code at `c9ce584` and the phase records;
it is not signed by a checker or by the owner.
