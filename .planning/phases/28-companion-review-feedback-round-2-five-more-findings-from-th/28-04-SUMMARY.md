---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 04
subsystem: ui
tags: [config-page, i18n, settings, typography, playwright, css-nested-supersections]

# Dependency graph
requires:
  - phase: 27
    provides: "_nested_wrapper_html()/_display_groups_html(), layout.section_intro_html(), the shared .theme-status--nested/.page-section--nested > h2 CSS rule, and 27-06's (mistaken) title-form inventory that first investigated this defect"
  - phase: 28 (28-03)
    provides: "ownership of companion/pages/config_page.py, companion/test_config_page.py and companion/test_browser_ux.py for Wave 3"
provides:
  - "Device's four settings cards (Diagnostic LED, Wake interval, Notifications, Manual refresh) render at the same 16px/600/sans nested-card-title tier Display's cards use, instead of the un-nested 22px/400/serif default"
  - "_device_groups_html(), mirroring _display_groups_html(), grouping Device's cards into two supersections (\"When it wakes\", \"How it tells you\") plus a third one-card supersection (\"When you can't wait\") for the Poll card"
  - "a rendered, cross-page getComputedStyle comparator (test_browser_ux.py) proving the claim instead of a markup-level inventory — the exact proof shape 27-06 lacked"
  - "27-06's title-form inventory reconciled in writing with counts re-derived by running"
  - "a hand-off to 28-06 Task 1: style.css:~5691-5702's claim that Device's cards keep their un-nested treatment is now false and must be superseded there"
affects: [28-06, 28-07, companion-config-page, sketch-findings-skypane]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A supersection helper (_device_groups_html) that omits its own heading when every card it would introduce is absent from `builders`, unlike its sibling _display_groups_html which always emits its heading — a deliberate strengthening, not a copy-paste"
    - "A Device-scope-only nested wrap of a card built OUTSIDE the generic `builders` dict (poll_section_html), computed as a second variable so the frozen SCOPE_ALL branch's own copy stays byte-identical"
    - "Browser check clause design that tolerates a genuinely SMALLER rendered set (fewer cards) while still catching an OVER-inclusive selector (class-name addressing picking up unrelated headings) and an UNDER-inclusive one (missing the one differently-wrapped card) — three independent properties, not one exact-count assertion"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/screens.py
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_browser_ux.py

key-decisions:
  - "Device's three builders-tuple cards regroup into 'When it wakes' (Wake interval alone) then 'How it tells you' (LED + Notifications) — reordering the RENDERED sequence relative to advanced_groups' own LED-first tuple; screens.py's own render-order comment superseded in place, comment-only, tuple contents unchanged"
  - "The Poll card gets its own one-card supersection, 'When you can't wait', rather than joining 'When it wakes' — two real DOM siblings (Send-a-test, quick-led forms) sit between them in document order, so a heading that introduced a card four blocks below it would introduce nothing"
  - "The browser check's clause (a) asserts two independent properties instead of an exact-4 count: every Device title is one of the four canonical names (catches over-inclusive class-name addressing), and the Poll card's own title specifically is present (catches under-inclusive selector reach) — this was a mid-task redesign after M-C's own mutation-test requirement proved the original exact-count assertion wrong"

requirements-completed: [CFG-72]

# Metrics
duration: ~65min
completed: 2026-09-15
---

# Phase 28 Plan 04: Device's settings cards get Display's nested-card typography Summary

**Device's four settings cards (Diagnostic LED, Wake interval, Notifications, Manual refresh) now render at the same 16px/600/sans nested-card-title tier Display's cards use, grouped under two new supersections plus a third one-card supersection for the Poll card, proven by a rendered cross-page getComputedStyle comparator rather than 27-06's markup-level inventory.**

## Performance

- **Duration:** ~65 min
- **Completed:** 2026-09-15
- **Tasks:** 2/2 completed
- **Files modified:** 5

## Accomplishments

- `_device_groups_html(builders, groups)` replaces the Device branch's flat join, wrapping all three builders-tuple cards with `theme-status--nested` under two new supersections, "When it wakes" (Wake interval) and "How it tells you" (LED + Notifications) — mirroring `_display_groups_html()`'s shape, with one strengthening: a supersection whose only card is absent from `builders` emits no orphaned heading.
- The fourth Device card — Manual refresh / Poll, built outside `builders` entirely — is wrapped with `page-section--nested` under its own one-card supersection, "When you can't wait", computed Device-scope-only so the legacy SCOPE_ALL branch's own bare `poll_section_html` stays byte-identical (re-verified by rendering before/after and diffing: identical, 9355 bytes both times).
- Zero CSS edited. The shared `.page-section--nested > h2, .battery-trend-section > h2, .theme-status--nested > h2` rule already existed and already named both selector forms the new wraps use.
- `companion/test_browser_ux.py` gained the real proof: `_a_settings_card_title_renders_identically_on_both_settings_pages()`, one `getComputedStyle` probe that loads both Display and Device in one session, addresses every settings-card title by structural position (never by class name — the exact move that let 27-06 miss this), and asserts the combined `(font-size, font-weight, font-family)` set across both pages has cardinality 1.
- `companion/test_config_page.py` gained the cheap structural guard (`_device_scope_wraps_all_four_settings_cards_with_the_nested_modifier`), explicitly documented as *not* the real proof.
- 27-06's title-form inventory reconciled: Device's counts move from `(4, 3, 0, 1)` to `(7, 3, 3, 1)`, re-derived by running; its written classification of the Poll heading ("neither a settings card nor a supersection") superseded in place with the original sentence kept legible, and the correction recorded ("it remains unclassified by this check's own arithmetic ONLY because it holds no persisted field — which is what the banner already said, and is why wrapping it was correct").

## Task Commits

Each task was committed atomically:

1. **Task 1: Device's cards get the same wrapper and the same kind of heading Display's have** - `87351d7` (feat)
2. **Task 2: THE check — both pages rendered, every card title's computed style asserted equal** - `ae379e1` (test), `8f84a71` (fix — mid-task redesign of clause (a) after M-C's mutation-test requirement proved the original exact-count assertion incompatible with a genuinely smaller Device card set)

_Note: Task 2 needed a second commit because mutation-testing M-C (remove one Device card from `builders`, check must still pass) revealed the initial "exactly four named titles" assertion was too strict — it was redesigned into two weaker, still load-bearing properties before the mutation pass could be completed cleanly._

## Files Created/Modified

- `companion/pages/config_page.py` - `_device_groups_html()`, the Device-scope-only Poll supersection wrap, and the new heading/intro module constants
- `companion/screens.py` - `advanced_groups`' render-order comment superseded in place (comment-only; tuple contents unchanged)
- `companion/i18n_fr/display.py` - French entries for the three new headings/intros
- `companion/test_config_page.py` - the D-12 section-intro count check retargeted (Device now renders three, not zero), the title-form inventory reconciled, and the new cheap structural guard added
- `companion/test_browser_ux.py` - `_a_settings_card_title_renders_identically_on_both_settings_pages()`, the real cross-page proof

## Decisions Made

- **Grouping argument (recorded in the source, restated here):** "When it wakes" (Wake interval alone) is the frame's own schedule. "How it tells you" (Diagnostic LED + Notifications) is a real shared subject — both cards are the frame's SIGNALLING channels: the LED reports on the device itself, notifications report on the reader's phone — not a bucket invented so a wrapper class would have somewhere to live. The Poll card gets its own supersection, "When you can't wait", because it is the one Device control that acts immediately rather than on a schedule — the manual counterpart to "When it wakes" — and because two real DOM siblings (the Send-a-test and quick-led forms) sit between "How it tells you"'s cards and the Poll card in document order, so joining them would either swallow foreign fragments into the group or reorder the page.
- **Rendered order changed from screens.py's own documented D-10 list** (LED, wake interval, notifications, manual refresh) **to wake interval, LED, notifications, manual refresh** — a real, disclosed consequence of the new grouping. `screens.py`'s own comment is superseded in place, comment-only, with the original sentence kept legible; `advanced_groups`' tuple CONTENTS are unchanged, and its second clause ("manual refresh is rendered directly by render()'s own has_manual_poll branch, never through this tuple") stays true.
- **Browser check clause (a) redesigned mid-task.** The plan's own wording ("Device must contribute exactly four titles and they must be NAMED") was implemented literally first, then found incompatible with M-C's own required behavior (removing one card from `builders` must still PASS). Redesigned into two independent, still load-bearing properties: every title found is one of the four canonical names (catches a class-addressed probe picking up supersection intro headings — M-B's own failure mode), and the Poll card's own title specifically is present (proves the probe's reach extends past the three `.theme-status` cards to the one `.page-section` card — the exact miss 27-06 made). This is documented as a Task 2 mid-task correction, not a plan deviation requiring Rule 4, since it stayed within the plan's own stated intent ("a probe that silently misses the Poll card... would pass this check while leaving CFG-72 unmet") while making the mechanics consistent with the plan's own M-C requirement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Retargeted a pre-existing D-12 check that Task 1's own required behavior directly contradicted**

- **Found during:** Task 1 verification (`companion/test_config_page.py`)
- **Issue:** A pre-existing check from 20-07-PLAN.md, `_display_render_carries_three_section_intros_in_locked_order` (registered description: "...and the Device scope renders none (D-12)"), literally asserted `"section-intro" not in device`. Task 1's own required behavior (Device gains three supersection intros) makes this assertion false by construction — the check would fail forever once Task 1 shipped correctly, blocking the plan's own acceptance criteria (`companion/test_config_page.py` exits 0).
- **Fix:** Retargeted the check in place: Display's own three-intro assertion is untouched; the Device half now asserts Device renders exactly three of its own, in the new locked order ("When it wakes" < "How it tells you" < "When you can't wait"), with the retargeting stated in the check's own registered description.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `companion/test_config_page.py` exits 0, 265/265.
- **Committed in:** `87351d7` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking, Rule 3)
**Impact on plan:** The retarget was a required consequence of the plan's own instructed change, not scope creep — a check asserting the literal opposite of what the plan requires cannot be left unedited and passing was still mandatory per the plan's own acceptance criteria.

## Issues Encountered

- **Browser check design tension (M-C vs. the plan's own literal clause-(a) wording), resolved mid-task 2 — see "Decisions Made" above.** Not a deviation from the plan's INTENT (the redesign implements the same reasoning the plan gives for the "named" requirement — catching a probe with the wrong reach — just via two properties that also tolerate a genuinely smaller card set, which the plan's own M-C mutation requires).
- **One flaky pre-existing check, unrelated to this plan, observed once.** `a Display page with a typed-but-uncommitted edit issues ZERO requests...` (23-06-PLAN.md Task 3) failed once on a clean tree (no mutation applied, `git status` confirmed clean) and passed on an immediate re-run with the identical tree. Not investigated further — out of this plan's scope per the scope-boundary rule (pre-existing, unrelated file/behavior), and the re-run confirms it is not caused by this plan's changes.

## Findings Recorded (per plan instruction)

- **`has_colour_rules` re-verified dead.** `grep -rn 'has_colour_rules' companion/` returns exactly three hits: `companion/screens.py:108` (`"has_colour_rules": True`, the source) and two `False` fixtures in `companion/test_config_page.py` (lines 9206, 9293). No production code reads it — 21-05 retired the flight-colours section and its `show_rules` flag, leaving this key a dead leftover gating nothing. It is not a fifth rendering surface and was correctly left alone.
- **Hand-off to 28-06 Task 1.** `companion/static/style.css:~5691-5702`'s header comment states "Runway/Theme/LED on Device keep their current, un-nested 22px-serif heading treatment." This plan falsifies that sentence (all four Device cards are now nested) but does not own `companion/static/style.css` and cannot edit it. 28-06 Task 1 (Wave 5) owns that file and must supersede the sentence in writing on this plan's behalf, naming 28-04/CFG-72.
- **28-02's and 28-03's dial checks still pass unchanged**, confirmed by name in the final full run: `THE handle-stays-on-its-ring check (CFG-73 Bug B, 28-02-PLAN.md Task 2)` and `the dial caption keeps the SAME FORM the server emits at load after EACH of a drag...` (CFG-73 Bug A, 28-03-PLAN.md Task 3).

## Mutation Testing (Task 2)

All five required mutations were applied to the state after both Task 2 commits, reverted with `git checkout-index -f --`, `git status --porcelain` clean after each:

- **M-A (load-bearing):** Device branch reverted to the flat join with headings kept (drop `_nested_wrapper_html()` calls in `_device_groups_html`). Browser check FAILED on clause (b):
  > `expected exactly one (font-size, font-weight, font-family) triple across every settings-card title on both settings pages, got 2 distinct triples — 'Wake interval' on /device (theme=light) renders ('22px', '400', '"Iowan Old Style", Charter, "Palatino Linotype", Georgia, "Book Antiqua", serif'), while the rest render ('16px', '600', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif')`
- **M-B:** the probe's selector pointed at a class name (`h2.text-heading`) instead of structural position, then M-A re-applied on top. Outcome: **the check does NOT catch M-A's regression specifically under class-name addressing** — it fails with the byte-identical message whether M-A is applied or not:
  > `expected every Device settings-card title to be one of [...], found unexpected title(s) ['How it tells you', "When you can't wait", 'When it wakes']`
  This is the executable demonstration of 27-06's own error: class-name addressing (`.text-heading`) cannot distinguish a card title from a supersection intro (both carry that class), so it fails identically on correct code and on M-A's regressed code — it can prove nothing about the actual typography defect. Structural addressing (`.theme-status > h2.text-heading, .page-section > h2.text-heading`) is what lets the check reach the real comparison at all.
- **M-C:** one Device card (`GROUP_NOTIFICATIONS`) removed from `builders`. The new check PASSED (device_texts = {LED, Wake interval, Manual refresh}, no unexpected titles, Poll's own title present, clause (b) cardinality still 1) — proving the comparator is not secretly counting rather than comparing. One unrelated, pre-existing check (`...the re-homed 'Send a test' button on Device`, 22-10-PLAN.md Task 3) failed as a collateral consequence of mutating shared production code — expected, out of this plan's scope, and reverted with the same `git checkout-index -f --` call.
- **M-D:** `theme-status--nested` dropped from LED only. Both checks failed, quoted:
  - Source check: `expected exactly 3 theme-status--nested settings-card wrappers on Device (LED, wake interval, notifications), got 2`
  - Browser check: `...got 2 distinct triples — 'Diagnostic LED' on /device (theme=light) renders ('22px', '400', '...serif'), while the rest render ('16px', '600', '...sans-serif')`
- **M-E:** `page-section--nested` dropped from the Poll card only, the other three left wrapped. Both checks failed, quoted:
  - Source check: `expected exactly 1 page-section--nested settings-card wrapper on Device (Poll), got 0`
  - Browser check: `...got 2 distinct triples — 'Manual refresh' on /device (theme=light) renders ('22px', '400', '...serif'), while the rest render ('16px', '600', '...sans-serif')` — the mutation that proves the fourth card is genuinely in the probe's reach.

## Verification

- `companion/test_config_page.py` — 265/265 (was 264/264; +1 new check, EXPECTED_CHECK_COUNT re-derived by running)
- `companion/test_i18n.py` — 24/24
- `companion/test_browser_ux.py` — 91/91 (was 90/90; +1 new check, EXPECTED_CHECK_COUNT re-derived by running)
- `ruff check .` — clean
- `git diff --stat` — does not name `companion/static/style.css`
- `PYTHON=.../python bash scripts/run-all-tests.sh` — exactly the documented 5-check root-sandbox baseline, verified BY NAME: 4× WR-11 (`manual_save_failed`/`manual_delete_failed` flash keys, `add_entry()`/`delete_entry()` read-only-dir simulation) + 1× `anomaly_active()` for a non-existent state_dir. Coverage 93%.
- `<human-check>` (from the plan's own `<verification>` block, not yet performed by the developer): open Settings → Display and Settings → Device side by side on a phone at 360px and on desktop, in both themes and both languages — confirm all four Device cards (including Manual refresh) match Display's title typography, and confirm the new supersection headings read as sensible groupings.

## Self-Check: PASSED

- FOUND: `companion/pages/config_page.py` (modified, contains `_device_groups_html`, `DEVICE_WAKES_SECTION_ID`, `DEVICE_TELLS_SECTION_ID`, `DEVICE_POLL_SECTION_ID`)
- FOUND: `companion/screens.py` (modified, comment-only)
- FOUND: `companion/i18n_fr/display.py` (modified, three new entries)
- FOUND: `companion/test_config_page.py` (modified, retargeted + new check)
- FOUND: `companion/test_browser_ux.py` (modified, new check)
- FOUND commit `87351d7` in `git log --oneline`
- FOUND commit `ae379e1` in `git log --oneline`
- FOUND commit `8f84a71` in `git log --oneline`

## Next Phase Readiness

- 28-04's own work is complete and verified; the phase's remaining plans (28-05, 28-06, 28-07) can proceed.
- 28-06 Task 1 has a concrete, named hand-off waiting: supersede `companion/static/style.css:~5691-5702`'s "Runway/Theme/LED on Device keep their current, un-nested 22px-serif heading treatment" sentence.
- The developer's own `<human-check>` (rendered side-by-side comparison across breakpoints/themes/languages) has not yet been performed — CFG-72 is not fully closed until that happens.

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Completed: 2026-09-15*
