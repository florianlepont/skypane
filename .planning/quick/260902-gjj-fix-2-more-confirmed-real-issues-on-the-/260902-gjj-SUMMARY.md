---
phase: quick-260902-gjj
plan: 260902-gjj
subsystem: companion-ui

tags: [companion, health-page, css, design-system, accessibility, harness, status]

requires:
  - phase: 260901-tsa
    provides: "the text-label section-caption pairing (finding B's _section_intro_html()) this task's Task 1 reuses verbatim for two more fragments"
  - phase: 260901-re6
    provides: "the Settings-page section-caption precedent that established the composed-not-restated muted-colour pattern this task follows"
  - phase: 06.6.4.1-04
    provides: "the migrated Unresolved-prefixes/Resolution-statistics .page-section--nested cards this task adds a status modifier to (one of them)"
provides:
  - "layout.card_status_class(base_class, status) — the one status->card-modifier mapping, whitelisted like status_dot()/stat_tile(), empty-string fallback (not accent) so a verdict-free card keeps its plain hairline"
  - "the battery-trend section and the Unresolved-prefixes card each carry a 3px status top border driven by the unchanged battery_status()/coverage_status() values, in the existing --color-status-* tokens; the Resolution-statistics card is confirmed verdict-free from source and gets none"
  - "both status_dot() badges (BATTERY_STATUS_LABEL/_battery_badge_block, and the registry card's own Coverage dot) retired outright, licensed by a source-level accessibility finding — status_dot()'s first span is empty, its label names only the subject, never the state"
  - "the latent .stat-tile hover/focus-within specificity defect (status border silently losing to border-color: transparent on hover) found and fixed, matching the doubled-selector-form fix this task's own Task 2 introduced for the two page-level cards"
  - "two subtitle-role fragments (the battery heading's trailing span, the Unresolved-prefixes read-only note) now compose .section-caption onto their existing sizing class, fixing the full-strength-ink defect"
affects: [companion-ui-implementation, health-page-visual-defects, stat-tile-status-border-mechanism]

tech-stack:
  added: []
  patterns:
    - "Card-level status accent via a doubled-specificity modifier selector (.COMPONENT.COMPONENT--status), placed in source order AFTER the component's own :hover/:focus-within rule — the general pattern this task establishes for .battery-trend-section/.page-section and retrofits onto the pre-existing .stat-tile mechanism it was modelled on"
    - "A whitelisted status->class-suffix builder (layout.card_status_class()) with an EMPTY-STRING fallback, deliberately differing from stat_tile()'s accent-class fallback — because a page-level card's base rule has no 'always some colour' border to fall back onto, so 'no status' correctly means 'no modifier at all'"
    - "Removing a status_dot() badge is licensed only after reading its own accessibility contract from source (empty first span, subject-naming label) — not assumed from its visual presence"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/layout.py
    - companion/static/style.css
    - companion/test_status_pages.py
    - companion/test_companion_app.py
    - .planning/phases/06.6.1-companion-visual-polish-pass-logo-branding-mobile-hamburger-/06.6.1-UI-SPEC.md
    - .planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md

key-decisions:
  - "ISSUE 1's fix composes .section-caption onto each fragment's existing sizing class (text-label for the battery heading span, text-body — deliberately NOT downgraded to text-label — for the registry note), following _section_intro_html()'s own in-file precedent rather than inventing a second muted value or class."
  - "ISSUE 2's dot removal decision: remove both status_dot() badges outright, not just their text. Read status_dot()'s own output character by character first — the dot span is empty (no text/role/aria-label/title, state lives only in a background-colour-mapped CSS class) and the label names only the SUBJECT ('Battery readings'/'Coverage'), never the state. A screen-reader user got the word 'Coverage' and nothing else; the border-top replacement loses no accessible information. Per-card safety independently confirmed from source: the registry card's own visible content already states its state in both branches (empty_state or the filter bar's 'N of N shown'); the battery card's state was and remains colour-only before and after (a like-for-like swap, not a regression)."
  - "Considered and rejected in writing: a visually-hidden state sentence on the battery card. Four reasons — it closes only the screen-reader half of the colour-only gap while implying the whole gap is handled; it would be new copy with no Copywriting-Contract home; the one candidate string ('A battery reading shows an abnormal drop.') is asserted ABSENT from the page by an existing harness check backed by 06.6.1-UI-SPEC's own 'Anomaly detail list (removed)' row; and it would land on two of six colour-only status sites, a half-measure. The pre-existing six-site WCAG 1.4.1 (Use of Color) gap — four stat tiles, and now these two cards, all colour-only, while the anomaly banner deliberately says only 'check the tiles below' — is escalated by name as a scoped follow-up, neither introduced nor closed by this task."
  - "card_status_class()'s fallback deliberately differs from stat_tile()'s: stat_tile() falls back to stat-tile--accent because .stat-tile's base rule already declares SOME border-top colour; a page-level card's base rule declares a plain 1px hairline, so 'no status' correctly means 'no modifier at all' — an accent fallback would put an invented 3px border on the Resolution-statistics card, which carries no status field of any kind (confirmed from _stats_table_html()/resolution_stats() source, not assumed)."
  - "Task 3's hover-specificity fix (.stat-tile.stat-tile--{status}, doubled form) is scoped to rewriting the four modifier selectors only — narrowing .stat-tile:hover's border-color shorthand into per-side longhands was considered and rejected because it would touch six OTHER card components' hover treatment (.page-section, .battery-trend-section, .runway-card, .history-card, .login-card, plus .airline-card/.theme-status) for a fix only two of them needed."
  - "Two prior decisions reversed and recorded at the removal site, matching 260902-chc's own D-12 reversal shape: 06.5-CONTEXT D-01's status_dot() badge request (superseded by the card-level border D-01's own reference note already expected), and style.css's false '.battery-trend-section carries no verdict' comment (corrected — _battery_section() has always computed a real battery_status() verdict)."

requirements-completed: [QUICK-260902-gjj]

coverage:
  - id: muted-captions
    description: "The battery heading's trailing span and the Unresolved-prefixes read-only note both render at the file's single 70%-muted strength, composing section-caption onto their existing sizing class"
    requirement: QUICK-260902-gjj
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_gjj_muted_captions_compose_section_caption — pins the markup pair AND .section-caption staying a single-declaration rule, mutation-tested both halves"
        status: pass
      - kind: manual
        ref: "server/.venv/bin/python3 -c '...' inline verification script from PLAN.md's Task 1 <verify> block"
        status: pass
    human_judgment: true
    rationale: "The harness proves the class composition and the single muted-colour declaration; only a real browser (both themes) confirms both fragments visually read at the same muted strength as the file's other section-intro descriptions."
  - id: card-status-borders
    description: "The battery-trend card and the Unresolved-prefixes card each carry a 3px status-coloured top border driven by battery_status()/coverage_status()'s own real value, in the existing --color-status-* tokens; the Resolution-statistics card carries none"
    requirement: QUICK-260902-gjj
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_gjj_card_status_borders_render_correct_modifiers — seeded battery drop (error) + non-empty registry (warn), asserts each card's own tag carries the matching card_status_class() modifier and the stats card carries none; also pins all three doubled-form CSS rules to a 3px border in their own token"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py::_card_status_class_whitelist_and_empty_fallback"
        status: pass
      - kind: manual
        ref: "standalone live-HTTP smoke script: real companion/app.py subprocess, real login, seeded battery drop + registry, fetched /health and /static/style.css — confirmed the served response bodies (not just the on-disk source) carry both section-caption classes, both card-status modifiers, no dot-label inside either card, the stats card's unmodified class, and all three doubled-form CSS rules"
        status: pass
    human_judgment: true
    rationale: "The harness and the live-HTTP smoke test prove the class attributes and CSS rules exist and are served; only a real browser proves the 3px edge visually reads as status colour at both card widths, and reads right rather than heavy at the ~846px card width vs. a stat-tile's ~240px."
  - id: hover-focus-survival
    description: "The status border on both new cards, and on all four .stat-tile modifiers, survives :hover and :focus-within rather than losing to the hover rule's border-color: transparent shorthand"
    requirement: QUICK-260902-gjj
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_card_status_modifiers_survive_hover_source_order — pins every doubled-form status selector (battery-trend-section, page-section, and — Task 3 — stat-tile) after its own :hover/:focus-within rule in style.css's source order; mutation-tested (duplicated a rule before the hover rule, confirmed exactly this check failed; reverted one .stat-tile modifier to single-class form, confirmed exactly this check failed)"
        status: pass
      - kind: manual
        ref: "server/.venv/bin/python3 -c '...' inline verification scripts from PLAN.md's Task 2/Task 3 <verify> blocks"
        status: pass
    human_judgment: true
    rationale: "This is THE highest-risk item on this plan's own verification split, flagged explicitly in the plan and in this SUMMARY's own Pixel-Level Items Outstanding — the harness proves the selector shape and source order; only a real browser, with a computed-style diff before/during hover and keyboard focus, proves the rendered colour actually survives the pointer and Tab/arrow-key traversal of the battery chart's hit targets."
  - id: dot-removal-scoped
    description: "Both status_dot() badges are removed with no screen-reader-accessible information lost, the removal is SCOPED to the two cards (Corroboration's three dots survive untouched), and the retired symbols are gone via hasattr"
    requirement: QUICK-260902-gjj
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_quick_260902_gjj_dot_removal_scoped_not_global — no dot-label inside either card's own boundaries, dot-label present inside the Corroboration tile on a fixture seeding corroboration rows, hasattr(health_page, 'BATTERY_STATUS_LABEL')/hasattr(health_page, '_battery_badge_block') both False; mutation-tested (reintroduced each dot individually, reintroduced the retired constant, broke the Corroboration dots — each caught)"
        status: pass
      - kind: manual
        ref: "standalone live-HTTP smoke script (same run as card-status-borders above) — confirmed no dot-label in either card's served markup"
        status: pass
    human_judgment: true
    rationale: "The harness and live-HTTP smoke test prove the markup-level removal and its scope; only a VoiceOver pass (named explicitly in Pixel-Level Items Outstanding below) proves the accessibility-tree prediction this task's source-level finding makes actually holds for a real screen reader."

duration: ~55min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-gjj: Fix 2 More Confirmed Real Issues on the Health Page Summary

**Mutes two subtitle-role fragments by composing the existing section-caption class, replaces two status_dot() badges with a card-level 3px status border (layout.card_status_class(), reusing battery_status()/coverage_status() unchanged), and fixes a latent hover/focus-within specificity defect in the .stat-tile mechanism the new card pattern was modelled on.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3 completed (Task 2 shipped as two atomic commits, per plan)
- **Commits:** 4
- **Files modified:** 7 (`companion/pages/health_page.py`, `companion/layout.py`, `companion/static/style.css`, `companion/test_status_pages.py`, `companion/test_companion_app.py`, `06.6.1-UI-SPEC.md`, `06.6.4.1-UI-SPEC.md`)

## Accomplishments

- **Task 1 (ISSUE 1) — muted captions:** the battery heading's trailing `— Latest 20 readings` span and the Unresolved-prefixes read-only note both now compose `section-caption` onto their existing sizing class (`text-label`, `text-body`), following `_section_intro_html()`'s own in-file precedent. `.section-caption` itself is untouched — still a single 70%-muted `color-mix` declaration, pinned by a new harness check so a future edit can't satisfy the markup half while quietly forking a second muted value.
- **Task 2 Commit A (ISSUE 2, mechanism) — card-level status border:** `layout.card_status_class(base_class, status)` is the one status→card-modifier mapping, whitelisted like `status_dot()`/`stat_tile()`, with an empty-string fallback (not an accent class — see key-decisions). The battery-trend section and the Unresolved-prefixes card now compose this modifier from the unchanged `battery_status()`/`coverage_status()` values. Three shared CSS rules give both components a 3px status top border in the doubled `(0,2,0)` selector form, placed after both components' hover rules — the load-bearing ordering that makes the status colour survive `:hover`/`:focus-within` instead of losing to `border-color: transparent`. The Resolution-statistics card is confirmed verdict-free from source and gets no modifier. Corrects a false `.battery-trend-section` CSS comment that claimed the section "carries no ok/warn/error verdict of its own."
- **Task 2 Commit B (ISSUE 2, removal) — retire both dots:** `BATTERY_STATUS_LABEL`/`_battery_badge_block` and the registry card's own `status_dot()` call are both removed outright, licensed by the source-level accessibility finding above. Both reversed prior decisions (06.5-CONTEXT D-01's badge request; the false CSS comment, corrected in Commit A) are recorded at their removal sites, and both UI-SPECs updated in the same commit.
- **Task 3 — the hover defect the new pattern was modelled on:** found (from source, not assumed) that `.stat-tile`'s own status modifiers were `(0,1,0)` against `.stat-tile:hover`'s `(0,2,0)`, so the status-coloured top border was already silently losing to `border-color: transparent` on hover/focus-within, TODAY, for every existing stat tile — the exact defect Task 2's new card pattern was built to avoid, discovered because Task 2 cited this rule's own (false) "unaffected either way" comment as its precedent. Fixed identically: all four `.stat-tile` modifiers rewritten into the doubled `(0,2,0)` form. Task 2's own source-order harness check extended in place (no count change) to cover `.stat-tile` alongside the two page-level cards.
- **Harness:** `EXPECTED_CHECK_COUNT` 95 → 99 across three genuinely new checks (the muted-caption pair, the card-status-modifier check, the dot-removal-scoped check); the hover-source-order check (also new) was folded into an in-place extension by Task 3 rather than counted twice. Every exact-literal `BATTERY_SECTION_CLASS`/`page-section page-section--nested` open-tag lookup, every `dot--ok`/`dot--error` count and negative assertion, and every `BATTERY_STATUS_LABEL` reference was retargeted in place, re-derived per fixture's own seeded data rather than adjusted by a fixed offset. `companion/test_status_pages.py` 99/99, `companion/test_companion_app.py` 106/106, `companion/test_view_pages.py` 43/43, `companion/test_config_page.py` 61/61, `companion/test_contrast_check.py` 36/36. `scripts/run-all-tests.sh` reports exactly one failing harness — the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch — with no coverage-gate shortfall (92% total).
- **Live-HTTP smoke test:** started a real `companion/app.py` subprocess against a seeded state directory, signed in over HTTP, seeded a battery drop and a non-empty registry, and fetched the real `/health` and `/static/style.css` response bodies. Confirmed the SERVED bodies (not just the on-disk source) carry both `section-caption` classes, both cards' correct status modifiers, no `dot-label` inside either card's own boundaries, the Resolution-statistics card's unmodified class, and all three doubled-form CSS status rules for both components — closing the gap between source-level checks and what the running server actually emits.

## What `status_dot()` actually announces

Read from `layout.py` L965-975 (its full source, not its visual behaviour) before relying on it: it returns `'<span class="dot %s"></span><span class="dot-label">%s</span>'`. The **first span is empty** — no text node, no `role`, no `aria-label`, no `title`. Its entire state lives in the CSS class name, which maps to a `background` colour — a purely visual signal, invisible to a screen reader. The **second span** (`dot-label`) holds a noun naming the SUBJECT being measured — `"Battery readings"` or `"Coverage"` — never the state. Both strings are equally true whether the signal is healthy or failing. `BATTERY_STATUS_LABEL`'s own prior comment even concedes its wording was chosen only to disambiguate harness substring assertions from `BATTERY_SECTION_HEADING`, a test-disambiguation reason, not a reader-value one. `status_dot()`'s own docstring names one contract only — the whitelist-with-safe-fallback discipline for injection safety — and states no accessibility contract at all.

**Conclusion:** a screen-reader user encountering either dot today gets the word "Battery readings" or "Coverage" and nothing else — no state. A `border-top` colour replacement therefore loses nothing a screen reader could already report.

**Per-card confirmation, done from source, not assumed:**
- **Unresolved prefixes:** its own visible content already states its state in BOTH branches — `empty_state("No coverage gaps.", "No unresolved callsign prefixes — airline coverage looks complete.")` when `coverage_status()` is `"ok"`, and a filter bar reading `"N of N shown"` over a real table when it is `"warn"`. Nothing is lost, visually or programmatically, by the removal.
- **Battery trend:** its visible content does NOT independently state the verdict — the drop signal is named only in the page-level anomaly banner, which deliberately says "check the tiles below" without naming which tile. This card's state was colour-only before this task and remains colour-only after it. Stated plainly as a like-for-like swap, not an improvement.

## Why no `visually-hidden` state sentence

Considered and rejected in writing, so a later reader doesn't mistake the omission for an oversight:

1. It would close only the screen-reader half of the colour-only gap while creating the impression the whole gap is handled — sighted colour-blind users would still see nothing.
2. Every user-facing string in this codebase has a Copywriting-Contract home or a recorded provenance; a new sentence here would have neither.
3. The one candidate string that fits ("A battery reading shows an abnormal drop.") is asserted ABSENT from the rendered page by a live harness check backed by `06.6.1-UI-SPEC.md`'s "Anomaly detail list (removed)" row — rendering it here would reverse a different phase's decision as a rider on this one.
4. It would land on two of six colour-only status sites on this page, a half-measure that improves the appearance of the problem more than the problem itself.

## The WCAG 1.4.1 gap this task did not close

This page conveys WHICH signal is unhealthy by colour alone at **six** places: the four `stat-tile` modifiers (Device, Pipeline, Corroboration, Resolution-rate) plus — as of this task — the battery-trend and Unresolved-prefixes card borders. The anomaly banner deliberately carries only a count and "check the tiles below," never naming which tile. This is a pre-existing WCAG 1.4.1 (Use of Color, Level A) gap that this task neither introduces (the four tiles already had it) nor closes (extending the mechanism to two more sites without a non-colour cue doesn't fix the tiles, and the rejected visually-hidden approach above would only have half-fixed two of six). **Named as a scoped follow-up:** closing it properly means one coordinated change across the banner and all six card/tile sites — a full audit of how each site's state could be conveyed by shape, text, or icon in addition to colour — and is its own task, not a rider on this one.

## Two reversals, recorded

- **06.5-CONTEXT.md D-01** ("Add a persistent status badge next to the Battery Trend section heading, reusing the exact status_dot() pattern the Device and Pipeline sections already render") — recorded as retired at the removal site: `companion/pages/health_page.py`, the block replacing `BATTERY_STATUS_LABEL`'s old definition (immediately after `PIPELINE_FRESHNESS_LABEL`), and again at `_battery_section()`'s own return-statement comment. D-01's own reference note already expected "06.3's 3px top-border-by-status treatment" to apply to this content — this task restores that original intent rather than inventing something new.
- **`style.css`'s false `.battery-trend-section` "carries no verdict" claim** — corrected in place, in `.battery-trend-section`'s own comment block, in the Task 2 Commit A commit. `_battery_section()` has always computed a real `battery_status()` verdict; the comment was wrong when written.

Both `06.6.1-UI-SPEC.md` (the stale "unchanged in mechanism" bullet) and `06.6.4.1-UI-SPEC.md` (the Color table's three status-token rows) were updated in the same commit as the code change each describes.

## The hover defect found in the pattern being extended

`.stat-tile:hover, .stat-tile:focus-within` is one class plus one pseudo-class = specificity `(0,2,0)`, and declares `border-color: transparent` — a SHORTHAND expanding to all four `border-*-color` longhands, including `border-top-color`. Each `.stat-tile--{status}` modifier was a single class = `(0,1,0)`. At unequal specificity the higher-specificity rule always wins regardless of source order, so on hover or `:focus-within` a stat tile's status-coloured top border was **already** silently resolving to `transparent` — a pre-existing, live defect this task did not introduce. The CSS comment above `.stat-tile` asserted the opposite ("the status-coloured top border is unaffected either way... the two always coexist without fighting each other"), which was factually wrong: `border-top` and `border-color` are not "different properties" in the sense that comment meant — they overlap on `border-top-color`.

Worth fixing in this task specifically because Task 2 cited this exact rule's mechanism (and its now-corrected comment) as the precedent it extends to two page-level cards, and because `:focus-within` is in the same selector — Health's tiles contain focusable chart hit targets, so this was never only a pointer-hover cosmetic issue.

**Fix:** all four `.stat-tile` status modifiers rewritten into the doubled `(0,2,0)` form (`.stat-tile.stat-tile--ok`, etc.) — same property, same tokens, same values, only the selector specificity changes. They already sat after the hover rule in source order, so at equal specificity they now win.

**Rejected alternative, in writing:** narrowing `.stat-tile:hover`'s `border-color: transparent` shorthand into per-side longhands instead. That would touch the hover treatment of six OTHER card components sharing similar hover rules (`.page-section`, `.battery-trend-section`, `.runway-card`, `.history-card`, `.login-card`, plus `.airline-card`/`.theme-status`) for a fix only two of them needed, and would change how the hairline clears rather than how the status border survives.

## Task Commits

1. **Task 1:** `9d76083` — `fix(quick-260902-gjj): mute the battery-heading and read-only-note captions` — `companion/pages/health_page.py`, `companion/test_status_pages.py`
2. **Task 2 Commit A:** `e403bc2` — `feat(quick-260902-gjj): carry Health's card status on the card's own top edge` — `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_companion_app.py`, `companion/test_status_pages.py`
3. **Task 2 Commit B:** `6a0680b` — `refactor(quick-260902-gjj): retire the two redundant Health status dots` — `companion/pages/health_page.py`, `companion/test_status_pages.py`, `06.6.1-UI-SPEC.md`, `06.6.4.1-UI-SPEC.md`
4. **Task 3:** `66a62e4` — `fix(quick-260902-gjj): keep a stat tile's status border through hover and focus` — `companion/static/style.css`, `companion/test_status_pages.py`

## Files Created/Modified

- `companion/pages/health_page.py` — `_battery_trend_section_html()` widened to take `state`, composes its section class from `BATTERY_SECTION_CLASS` + `card_status_class()`; the trailing span composes `text-label section-caption`; `_registry_section()`'s note composes `text-body section-caption` and its status dot is removed; the registry card's class is composed in `render()` from `card_status_class("page-section", coverage_status(...))`; `BATTERY_STATUS_LABEL`/`_battery_badge_block` retired with a reversal comment at the removal site
- `companion/layout.py` — `card_status_class(base_class, status)` added, backed by `_CARD_STATUS_SUFFIXES`, living beside `_STATUS_DOT_CLASSES`/`_STAT_TILE_BORDER_CLASSES`
- `companion/static/style.css` — `.section-caption` unchanged (verified single-declaration); three shared doubled-form status-modifier rules for `.battery-trend-section`/`.page-section`, placed after both hover rules; `.battery-trend-section`'s false "carries no verdict" comment corrected; all four `.stat-tile` modifiers rewritten into doubled form; `.stat-tile`'s own comment corrected
- `companion/test_status_pages.py` — `EXPECTED_CHECK_COUNT` 95 → 99; one new muted-caption check, one new card-status-modifier check, one new hover-source-order check (extended in place by Task 3), one new dot-removal-scoped check; every exact-literal `BATTERY_SECTION_CLASS`/nested-card open-tag lookup, dot-count assertion, negative dot assertion, and `BATTERY_STATUS_LABEL` reference retargeted in place; the nested-card-rhythm allowlist extended for the registry note's new class and the battery readout's own prefix
- `companion/test_companion_app.py` — `EXPECTED_CHECK_COUNT` 105 → 106; one new `card_status_class()` whitelist/fallback check, following `stat_tile()`'s own check in shape
- `.planning/phases/06.6.1-.../06.6.1-UI-SPEC.md` — the stale "unchanged in mechanism" bullet corrected to record the badge's retirement and the card-border replacement
- `.planning/phases/06.6.4.1-.../06.6.4.1-UI-SPEC.md` — the Color table's error/ok/warn rows extended to name the new battery-trend-section/page-section top-border usage

## Decisions Made

See `key-decisions` in the frontmatter above for the full reasoning on the caption composition, the dot-removal licensing, the rejected visually-hidden alternative, `card_status_class()`'s fallback divergence from `stat_tile()`'s, the rejected hover-shorthand-narrowing alternative, and the two recorded reversals.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_nested_card_heading_rhythm_end_to_end()`'s allowlist did not anticipate the registry note's new class attribute or the battery readout's own prefix**
- **Found during:** Task 2 Commit B (dot removal)
- **Issue:** An existing harness check (`_nested_card_heading_rhythm_end_to_end`, pre-existing from quick task 260902-bl2) asserts the element immediately following each nested card's `</h2>` is a member of a fixed allowlist of opening-tag prefixes. Two of this task's own changes broke it silently: the registry note's opening tag is now `<p class="text-body section-caption">` (Task 1), no longer matching the allowlist's bare `<p class="text-body">`; and with the battery badge retired (Task 2 Commit B), the seeded/chart-present battery-trend section's next element is now the readout paragraph (`<p id="battery-readout" ...>`), which never matched any allowlist member. Not named in the plan's own line-number list for known-breaking checks.
- **Fix:** extended the `allowed` tuple in place with `'<p class="text-body section-caption">'` and `'<p id="%s"' % health_page.BATTERY_READOUT_ID`.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** re-ran `companion/test_status_pages.py` (green at both intermediate and final states), confirmed the check now passes for both `seeded=False` and `seeded=True`.
- **Committed in:** `6a0680b` (Task 2 Commit B)

**2. [Rule 1 - Bug] The plan's own inline Task 2 `<verify>` block fixture was accidentally oldest-first, not newest-first**
- **Found during:** Manual verification of Task 2 Commit B's plan-provided inline verify script
- **Issue:** `battery_status(rows)` documents and requires a newest-first `rows` argument (it internally does `list(reversed(rows))` to get chronological order). The plan's own inline verify script built `rows = [{'ts': '2024-01-01T00:0%d:00' % i, 'battery_mv': 4200 - i * 150} for i in range(3)]`, which is oldest-first (ascending timestamp with descending index), the opposite of the convention the function expects — running it as written computed `battery_status(rows) == "ok"`, not the intended `"error"`.
- **Fix:** this is a verification-script-only issue, not a production code defect — every real production call site (`battery_trend_rows()`) already seeds newest-first, confirmed correct by every harness check (which use real seeded fixtures via `_seed_device_health()`, not this hand-built list). Re-ran the verify script with a corrected, explicitly newest-first fixture (`battery_mv` ascending down the list, `ts` descending) and confirmed `"error"` as intended; all other assertions in that script then passed unchanged.
- **Files modified:** none (verification-only; no production or harness code needed a fix)
- **Verification:** corrected inline script run, `OK2` printed
- **Committed in:** N/A (not a code change)

---

**Total deviations:** 2 (1 Rule-1 harness bug auto-fixed and committed; 1 Rule-1 verification-script-only correction, no code change)
**Impact on plan:** Both were necessary for correctness/completeness — the first closes a real regression-guard gap the plan's own retarget list didn't anticipate; the second is a one-off verification-script correction with zero production impact (confirmed by every seeded-fixture harness check passing). No scope creep.

## Issues Encountered

- No package installs, no auth gates. Rule 4 (architectural change) was never triggered — all three fixes are scoped CSS/Python changes within the plan's own stated levers.
- No computer-use/chrome-devtools MCP browser-automation tools were bound to this executor, matching all six preceding Health quick tasks today (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc, 260902-dng, 260902-ep7), each of which handed pixel-level confirmation back to the orchestrating session, which performed it successfully every time.
- `companion/test_companion_app.py`'s own concurrent-poll-trigger check (`_POLL_LOCK` serialization test) showed transient flakiness across repeated local runs (1/106 or 3/106 failing, always the same timing-sensitive check, always passing on immediate re-run) — pre-existing test infrastructure timing sensitivity, unrelated to this task's changes (confirmed: the failing check exercises `/poll-now` concurrency, nothing this task touched). Not investigated further as out of scope; `scripts/run-all-tests.sh`'s final run reported only the one expected `server/test_poll_loop.py` failure.
- `Skill("sketch-findings-skypane")` has now gone **seven** consecutive Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc, 260902-dng, 260902-ep7, and this one, 260902-gjj) without an update. Per the plan's own explicit instruction, this deferral is recorded here rather than silently repeated an eighth time. Folding seven tasks' worth of deltas (card-status-border pattern, hover-specificity fix, caption composition precedent reuse) into that skill file is real outstanding work, not a forgotten item — it is deliberately not a rider on any of these focused quick tasks.

## Pixel-Level Items Outstanding

No browser-automation tools were bound to this executor. **None of the following is claimed as verified here** — only source-level, harness-level, and live-HTTP-served-body verification was performed (see "Live-HTTP smoke test" above).

Provable from source/harness/live-HTTP and already covered, so do NOT re-verify these by eye: the presence of both `section-caption` classes, the modifier class each card carries, the three status rules' selectors/tokens/widths, the source order relative to the hover rules (for all three components), the absence of `dot-label` inside the two cards, the survival of the Corroboration dots, and the retirement of the two symbols.

Needs a real browser:

1. **The two captions.** Confirm the battery heading's trailing span and the Unresolved-prefixes read-only note both compute to the muted colour rather than `rgb(23, 25, 31)`, matching Health's own section-intro descriptions exactly. Check both themes.
2. **Caption legibility at the muted strength.** The read-only note is a full sentence of Body-size prose; confirm 70%-muted Body prose still reads comfortably against `--color-dominant` in dark theme.
3. **Does the card border read.** Seed or find a `coverage_status()` → warn state and confirm the Unresolved-prefixes card shows a visible amber top edge that reads as belonging to that card, not as a divider from the card above.
4. **[MOST LIKELY TO NEED A FOLLOW-UP TUNING PASS] Does a 3px edge read right at ~846px card width vs. a stat-tile's ~240px width.** The brief's explicit question. A colour that reads as punctuation at tile width may read as a heavy rule at card width. Human judgment. If it reads too heavy, the recorded lever is the border WIDTH, not a new colour token.
5. **Both themes, both removals.** Confirm the dot+label really are gone from both cards in light AND dark theme, that neither card opens with an awkward gap where the badge used to sit, and that the Corroboration tile's three dots are visibly untouched.
6. **[HIGHEST-RISK ITEM] Hover and focus survival — Task 3's whole point.** Hover each of the three Health stat tiles and confirm the status-coloured top border STAYS while the hairline clears and the shadow appears. Then hover the battery-trend card and the Unresolved-prefixes card and confirm the same. Then Tab into the battery chart and arrow across its points, watching the battery card's top edge — `:focus-within` fires on every point, and this is the case that would have blinked the status colour out on every keystroke before Task 3. Capture computed `border-top-color` before and during hover/focus and diff it; do not judge this one by eye alone.
7. **The stat-tile blast radius.** Task 3 changes four selectors used by every tile in the app. Spot-check Health's tiles in all three status states plus a neutral (`stat-tile--accent`) tile, and confirm nothing else about the hover treatment moved — the shadow, the 1px lift, and the other three edges clearing are all unchanged.
8. **Screen-reader pass on the removal, the brief's explicit ask.** With VoiceOver, traverse the battery-trend card and the Unresolved-prefixes card and confirm what is announced is exactly what was announced before minus the two subject nouns — i.e. that no state information was lost, which is what the source-level finding predicts. Also confirm the registry card still announces "No coverage gaps." (or the filter count and table) so its state genuinely does survive in text.
9. **Still outstanding from prior rounds, unchanged by this task:** a full dark-theme pass over the whole Health page, a 375px pass, real Safari confirmation of 260902-dng's table-header padding fix, and 260902-ep7's own item 10 (the chart's keyboard interaction path, still INCONCLUSIVE from that round — item 6 above exercises the same keys and is a good opportunity to settle it).

## User Setup Required

None to run the code. **Recommended before signing off:** the nine-item live-browser pass above, on `/health`, with item 6 (hover/focus survival) flagged as highest-risk and item 4 (does the 3px edge read right at full card width) flagged as most likely to need a follow-up tuning pass.

## Next Phase Readiness

All three fixes are implemented and pinned by harness: `companion/test_status_pages.py` 99/99; `companion/test_companion_app.py` 106/106; `companion/test_view_pages.py` 43/43; `companion/test_config_page.py` 61/61; `companion/test_contrast_check.py` 36/36. `scripts/run-all-tests.sh` reports exactly one failing harness — the pre-existing, unrelated `server/test_poll_loop.py` `panel.bin` digest mismatch — with no coverage-gate shortfall (92% total). The nine-item live-browser handoff above is the concrete next action for the orchestrating session before this can be considered visually verified, not just source-verified — items 6 (hover/focus survival) and 4 (does the edge read right at card width) are the priority items.

---
*Phase: quick-260902-gjj*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 7 modified files (`companion/pages/health_page.py`, `companion/layout.py`, `companion/static/style.css`, `companion/test_status_pages.py`, `companion/test_companion_app.py`, `06.6.1-UI-SPEC.md`, `06.6.4.1-UI-SPEC.md`) confirmed present on disk. All 4 task commit hashes (`9d76083`, `e403bc2`, `6a0680b`, `66a62e4`) confirmed present in `git log`.
