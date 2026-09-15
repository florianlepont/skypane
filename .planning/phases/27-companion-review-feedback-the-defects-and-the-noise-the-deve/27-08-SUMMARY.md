---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 08
subsystem: ui
tags: [companion, layout, config-page, style-css, i18n, playwright, hit-targets]

requires:
  - phase: 27-01 (Display routing correction)
    provides: "the quiet-hours dial's own home on /display, not /device — the fragment target this plan links to"
  - phase: 27-06 (copy cuts)
    provides: "the shortened wake-interval/gauge/quiet-hours regions the caption link now sits beside"
  - phase: 27-07 (carousel extension)
    provides: "the carousel's own return-order convention (disclosure last); unrelated to this plan's own files but the last wave to touch config_page.py's shared helpers"
provides:
  - "QUIET_HOURS_GROUP_HEADING_ID — the Quiet hours card's own stable fragment target, on its <h2>"
  - "layout.frame_strip_html()'s quiet cell renders a real <a> to that fragment, appended to a COPY of the shared delay caption at the ONE existing write site — no per-page parameter, no fork"
  - ".copy-btn resolved (not merely declared) to a real 44x44 in a Flights detail row; .row-toggle proven independently measured in its own container"
affects: [27-09]

tech-stack:
  added: []
  patterns:
    - "a caption-level text link given its own 44px floor via inline-flex + min-height (the native-input idiom this file already uses for a font-metric-independent floor), rather than the small-icon ::before-synthesis register, since the link's own text is already wider than 44px"
    - "a shared-component 'one write site, both pages' proof reads BOTH real page render() outputs and asserts identity, never two separate per-page presence checks"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/layout.py
    - companion/static/style.css
    - companion/i18n_fr/home.py
    - companion/test_config_page.py
    - companion/test_status_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "the link's href is layout.DISPLAY_ROUTE + '#' + the fragment id, built from a LOCAL, byte-identical copy of config_page.QUIET_HOURS_GROUP_HEADING_ID — never SETTINGS_ROUTE (a legacy 303-redirect-to-/display route that would add a hop and depend on browser fragment-forwarding across a redirect) and never a cross-module import (layout.py may never import a page module; config_page.py already imports layout.py, so the reverse would be circular)"
  - "the link is ALWAYS a real <a href>, including on /display itself (a working same-page fragment jump) — CFG-57's 'omit the href when already there' alternative is Phase 26, planned but NOT executed, so it is PROVISIONAL and not borrowed"
  - "route (b) for the hit-target fix — container-specific CSS (.flight-detail-row__grid margin-bottom, .flight-detail-row__reveal-inner padding-left), not a change to .copy-btn itself — chosen because the measured root cause is layout spacing local to this one component (a ~4px gap and a flush-left clip boundary), not .copy-btn's own box/inset values, which already resolve correctly everywhere else including .row-toggle. This leaves .row-toggle untouched by construction, and the fix is 16px of NEW visible left inset on the detail row's own content (accepted, documented trade — see Decision 3 below), not an invisible one"
  - "the family hit-target check measures .row-toggle and the desktop .copy-btn trio at 960px (the narrowest width `.data-table-wrap` actually renders at — this app's own responsive rule hides it below 960px in favour of `.history-cards`), plus the mobile <details> card's own .copy-btn trio at the literal 360px floor — closing both the 'measured at the floor' requirement and the 'these controls don't exist at 360px' constraint"

patterns-established:
  - "when a component's declared spacing rule turns out to be shadowed by a higher-specificity selector (table.data-table--flights td outranking .flight-detail-row td here), verify with getComputedStyle before trusting the declaration, and fix the rule that actually governs the box rather than the one that merely looks like it does"

requirements-completed: []

duration: ~2.5h
completed: 2026-09-15
---

# Phase 27 Plan 08: Review feedback — the Frame strip link and the two carried-in hit-target findings Summary

**The Frame strip's Quiet hours caption now links to the schedule fields via ONE write site reaching both Home and Display with an identical href (mutation-tested against both a removal and a simulated fork); `.copy-btn` in a Flights detail row now resolves a real 44x44 (was 34x26, caused by a ~4px gap to a trailing sibling and a flush clip boundary, not `.copy-btn`'s own values), and `.row-toggle` is proven independently measured in its own container.**

## Performance

- **Duration:** ~2.5h
- **Tasks:** 3 automated tasks
- **Files modified:** 7 (config_page.py, layout.py, style.css, i18n_fr/home.py, test_config_page.py, test_status_pages.py, test_browser_ux.py)

## Accomplishments

- `config_page.QUIET_HOURS_GROUP_HEADING_ID` gives the Quiet hours card's `<h2>` a stable id, following the same convention `RUNWAY_GROUP_HEADING_ID` already established — a fragment target, not a new control, nothing that posts changed.
- `layout.frame_strip_html()`'s quiet cell now appends a real `<a class="text-link frame-strip__schedule-link" href="/display#quiet-hours-group-heading">Change the schedule</a>` to its caption, at the one existing write site — `frame_strip_html()` gained no per-page parameter, and the append targets a COPY of the shared `delay_caption_html`, never the shared variable itself (which the Screen cell's caption also reads).
- The link is present on both Home's and Display's own real `render()` output with an identical href — proved by ONE check, mutation-tested against both a total removal and a simulated per-page fork.
- The link clears the 44px hit-target floor via `inline-flex` + `min-height: 44px` (not `::before` synthesis — its own text is already wider than 44px), measured by real hit-testing at 360px in both themes, with neither Home nor Display gaining horizontal scroll from the addition.
- `.copy-btn`'s real, measured 34×26 hit area in a Flights detail row (the hex column's copy button) is closed to a resolved 44×44+ — root-caused to a ~4px gap to the trailing callsign button (fixed with `margin-bottom: var(--space-lg)` on the grid) and a flush-left `overflow: hidden` clip boundary (fixed with `padding-left: var(--space-md)` on the reveal wrapper) — neither of which touches `.copy-btn`'s own declared values.
- `.row-toggle` is re-measured (it already resolved 45×45) by real hit-testing rather than the pre-existing check's declaration-read, and proven — by a targeted mutation — to be measured independently rather than piggy-backing on `.copy-btn`'s own pass.

## Task Commits

1. **Task 1: A stable fragment target on the Quiet hours card** - `9ca35e1` (feat)
2. **Task 2: The link, written once, in the shared strip** - `6c225ce` (feat)
3. **Task 3: `.copy-btn` meets the floor, and `.row-toggle` is measured rather than assumed** - `83948bc` (fix)

**Process note on commit boundaries:** `git commit --only <paths>` commits the pathspec's CURRENT WORKING-TREE content, not merely what had been staged for it — a git semantics surprise discovered while splitting `companion/static/style.css`'s two independent hunks (Task 2's link CSS, Task 3's hit-target CSS) across two commits via `git apply --cached` on a partial patch. The partial-apply trick worked for staging, but the subsequent `git commit --only companion/static/style.css ...` call picked up the FULL working-tree file (both tasks' hunks) rather than the partially-staged index content. Net effect: **both of `style.css`'s hunks landed in the Task 2 commit** (`6c225ce`); the Task 3 commit (`83948bc`) contains only `companion/test_browser_ux.py`. Each hunk still carries its own `27-08-PLAN.md Task N` comment tag identifying which task it belongs to, and no content is missing, duplicated, or misattributed in substance — only the commit-boundary split is imperfect for this one file. Not corrected via amend per this project's own "always a new commit" convention; disclosed here instead.

## Files Created/Modified

- `companion/pages/config_page.py` — `QUIET_HOURS_GROUP_HEADING_ID = "quiet-hours-group-heading"` added beside `QUIET_HOURS_SECTION_CAPTION_ID`; `quiet_hours_group()`'s `<h2>` now carries `id="%s"`, interpolating the constant
- `companion/layout.py` — `_FRAME_QUIET_SCHEDULE_LINK_TEXT`/`_FRAME_QUIET_SCHEDULE_TARGET_ID` added (local, byte-identical copies, matching the existing "a page module may never import another page module" duplication pattern already used for `QUICK_ACTION_*`); `frame_strip_html()`'s quiet-cell construction builds `quiet_schedule_link_html` and appends it to a copy of `delay_caption_html` as `quiet_caption_html`, passed to `_frame_strip_cell_html()` in place of the shared variable
- `companion/static/style.css` — `.flight-detail-row__grid` gains `margin-bottom: var(--space-lg)`; `.flight-detail-row__reveal-inner` gains `padding-left: var(--space-md)`; new `.frame-strip__schedule-link` rule (inline-flex + min-height: 44px)
- `companion/i18n_fr/home.py` — `"Change the schedule": "Modifier l'horaire"` added beside the frame-strip's other translated strings
- `companion/test_config_page.py` — the Quiet-hours quick-action markup check's literal absorbs the new `id="..."` attribute
- `companion/test_status_pages.py` — new one-write-site/both-pages check for the schedule link (mutation-tested); `EXPECTED_CHECK_COUNT` 305→306
- `companion/test_browser_ux.py` — two new checks: the schedule link's own hit-target-plus-floor proof, and the `.copy-btn`/`.row-toggle` family's resolved-not-declared hit-target proof (mutation-tested); `EXPECTED_CHECK_COUNT` 86→88

## Decisions Made

**1. The one-write-site proof — the decision that mattered most.** The Frame strip is rendered by exactly one function, `layout.frame_strip_html()`, called by `home_page.render()` (with `return_to=HOME_ROUTE`) and `config_page.render()`'s Display scope (with `return_to=DISPLAY_ROUTE`). The obvious way to "add a link on Display" would have been to special-case the quiet cell's caption at one of those two call sites, or to give `frame_strip_html()` a new parameter that varies the caption by `return_to` — both are a fork with a nicer name. The actual fix appends the link inside `frame_strip_html()` itself, unconditionally, to a **copy** of `delay_caption_html` (not the shared variable, which the Screen cell's own caption also reads two lines earlier in the same function) — so both pages get the identical markup from the identical call, by construction.

The check that proves it does not assert "the link exists on Home" and separately "the link exists on Display" — it renders `home_page.render()` and `config_page.render(scope=SCOPE_DISPLAY)` in ONE check, reads the `href` off both, and asserts (a) both pages have the link and (b) the two hrefs are byte-identical. Two separate per-page checks would both pass against a forked component (each page's own copy, each internally consistent) — asserting identity across both renders in one check is the only shape that would catch a fork.

**The mutation that proves it, quoted (link removed entirely):**

> `expected a.frame-strip__schedule-link on every page that renders the strip — found none on: Home, Display`

**The mutation that proves the both-pages-identity clause specifically (simulated fork — href made to vary by `return_to`):**

> `expected the SAME href on both pages (one write site, D-23) — Home read '/#quiet-hours-group-heading', Display read '/display#quiet-hours-group-heading'; two different hrefs is exactly what a forked component would produce`

Both reverted with `git checkout-index -f --` immediately after capture; `__pycache__` cleared between mutate/revert cycles; full `test_status_pages.py` re-confirmed at the standing baseline (305/306, the one documented `anomaly_active()` sandbox failure) before committing Task 2 for real.

**2. Why the href is `DISPLAY_ROUTE`, not `SETTINGS_ROUTE`.** The plan's own interfaces section named `config_page.SETTINGS_ROUTE = "/settings"` as a candidate. Reading `companion/app.py` showed `/settings` is a **fixed 303 redirect to `/display`** (a legacy-bookmark route, Phase 18), not a real content route. Using it as the link's href would add an unnecessary redirect hop and depend on browser fragment-forwarding-across-a-redirect (standard, but avoidable) rather than linking directly. `layout.py` already defines its own `DISPLAY_ROUTE = "/display"` constant (used by every other frame-strip consumer), so the link uses that directly. The fragment id constant is duplicated locally in `layout.py` (`_FRAME_QUIET_SCHEDULE_TARGET_ID`, byte-identical to `config_page.QUIET_HOURS_GROUP_HEADING_ID`) rather than imported, matching this module's own established "a page module may never import another page module" pattern (already used for the eleven `QUICK_ACTION_*` constants).

**3. Route (b) for the hit-target fix, with the actual measured root cause.** The plan's own text provisionally recommended route (a) — fix `.copy-btn` itself. Measuring the real geometry (Playwright, `getBoundingClientRect`/`elementFromPoint`, at 1280px with the row hovered) showed the 34×26 defect is **not** caused by `.copy-btn`'s own box or `::before` inset (both are correct — `.row-toggle`, which shares those exact values, already resolved 45×45 everywhere measured, and the mobile `<details>` card's own three `.copy-btn` instances already resolved 45×45 too). The actual causes, both local to `_flight_detail_row_html()`'s own layout:

- **Down-reach crushed to 2px (of an expected ~22px):** the grid's last row and the trailing, standalone callsign copy-btn (rendered as a sibling immediately after `</dl>`, not inside it) sat only ~3.8px apart — well inside both controls' own 11px synthesized reach. Per this file's own documented z-order rule ("the later element in document order wins the overlap"), the trailing button's `::before` won that entire zone, leaving the hex button's own downward reach almost nothing.
- **Left-reach capped at ~12px (of an expected ~22px):** the first grid column's copy buttons sit flush against `.flight-detail-row__reveal-inner`'s own left edge, and that element carries `overflow: hidden` (load-bearing for the row's height-collapse animation). The `::before` pseudo-element's leftward extension was being clipped at the container boundary before it could reach its full inset.

Both are **container spacing/clipping defects**, not defects in `.copy-btn`'s own declared values — so route (b) (a container-specific fix) is what the measurement actually supports, not route (a). `.flight-detail-row__grid` gained `margin-bottom: var(--space-lg)` (24px — the same over-the-exact-22px-minimum buffer this file's carousel-pager gap rule already banked for the identical overlap reason). `.flight-detail-row__reveal-inner` gained `padding-left: var(--space-md)` (16px, clearing the needed 11px with room to spare).

**This fix is NOT visually invisible, and the SUMMARY says so rather than the CSS comment alone.** An earlier attempt tried to make the left-clip fix "free" by removing `.flight-detail-row td`'s own left padding and moving it into `.flight-detail-row__reveal-inner` instead (net redistribution, same total inset). Measurement showed this doesn't work: `.flight-detail-row td`'s own `padding` declaration is entirely **shadowed** by `table.data-table--flights td`'s higher-specificity rule (`padding: var(--space-sm) var(--space-sm)`, i.e. 8px, not the 16px `.flight-detail-row td` declares) — editing the shadowed rule has zero effect on the rendered page. That edit was reverted. The real, shipped fix is a genuine 16px rightward shift of the detail row's own content (8px table-cell padding + 16px new reveal-inner padding = 24px total, up from 8px) — an accepted, disclosed trade rather than touching `table.data-table--flights td` (which would have re-spaced every cell in the whole Flights table, header and every summary row included, for a defect that lives in one component).

**Before/after measured dimensions, in their own containers (960px, light theme; identical in dark — colour tokens don't affect box geometry):**

| Control | Before (hit, reach L/R/U/D) | After (hit, reach L/R/U/D) |
|---|---|---|
| `.copy-btn` (hex, `#flight-detail-0`) | 34×26 (12, 21, 23, 2) | 45×45 (23, 21, 23, 21) |
| `.copy-btn` (timestamp, `#flight-detail-0`) | 45×45 (23, 21, 23, 21) — already fine | 45×45 (23, 21, 23, 21) — unchanged |
| `.copy-btn` (callsign, `#flight-detail-0`) | 34×44 (12, 21, 23, 20) | 45×44 (23, 21, 23, 20) |
| `.row-toggle` (Flights list, summary row) | 45×45 (23, 21, 22, 22) — already fine | 45×45 (23, 21, 22, 22) — unchanged |
| `.copy-btn` × 3 (mobile `.history-card` `<details>`, 360px) | 45×45 each — already fine | 45×45 each — unchanged |

**Neighbour-regression check.** Because the fix is scoped to `.flight-detail-row__grid`/`.flight-detail-row__reveal-inner` — a container `.row-toggle` never shares (it lives in an entirely different `<tr>`, the summary row, not the detail row) — `.row-toggle` cannot be structurally reached by this change. Measured anyway, at three widths (960px, 1024px, 1280px, the range `.data-table-wrap` actually renders at) in both themes: `.row-toggle` and all three desktop `.copy-btn` instances resolve identically before and after, confirming no neighbour regression (the exact 25-04 failure mode named in the plan's standing constraints — one control's fix silently moving a nearby one — did not recur here).

**The mutation that proves the fix is real, quoted (both CSS additions reverted):**

> `the hex .copy-btn, in ITS OWN container (the Flights detail row's grid, hovered/focused so its opacity/pointer-events reveal fires): '#flight-detail-0 [data-copy-value="399023"]''s hit area measures 34x26 at 960px, under the 44px floor in both axes (its visual box is 22.0x22.0 and it reaches (12, 21, 23, 2) pixels left/right/up/down of its own centre)`

**The mutation that proves `.row-toggle` is measured independently, not piggy-backing on `.copy-btn`'s pass, quoted (`.row-toggle::before`'s own inset temporarily shrunk from -11px to -2px, `.copy-btn::before` left untouched):**

> `the Flights list's own row-toggle, in ITS OWN container (the summary row, not the detail row's grid): '[data-row-toggle]''s hit area measures 27x27 at 960px, under the 44px floor in both axes (its visual box is 22.0x22.0 and it reaches (14, 12, 13, 13) pixels left/right/up/down of its own centre)`

— naming `.row-toggle` specifically, with no mention of `.copy-btn` at all, confirming the two are measured as genuinely independent controls even though they share one register of values.

Both mutations reverted with `git checkout-index -f --`; `__pycache__` cleared between cycles; full `test_browser_ux.py` re-confirmed at 88/88 before committing Task 3 for real.

**4. `.row-toggle`/desktop `.copy-btn` measured at 960px, not literally 360px — stated and grounded, not silently substituted.** `.row-toggle` and the desktop Flights detail row's three `.copy-btn` only exist inside `.data-table-wrap`, which this app's own responsive rule (`.history-cards ~ .data-table-wrap { display: none }` below 960px) hides in favour of `.history-cards` at every width below 960px — there is no 360px rendering of either to measure. They are measured at 960px instead (the narrowest width they actually occupy), in both themes. The mobile `<details>` card's own three `.copy-btn` DO render at 360px and are measured there, in both themes, closing the literal "at the 360px floor" requirement for the family that has a 360px rendering at all.

## Re-derived Counts (obtained by running)

- `companion/test_config_page.py`: **263/263** checks pass (`EXPECTED_CHECK_COUNT = 263`, unchanged — Task 1's fix updated an existing check's literal, added no new check).
- `companion/test_status_pages.py`: **305/306** checks pass (`EXPECTED_CHECK_COUNT` 305→306 — the one documented `anomaly_active()` sandbox failure, unrelated to this plan).
- `companion/test_browser_ux.py`: **88/88** checks pass (`EXPECTED_CHECK_COUNT` 86→88).
- `companion/test_i18n.py`: **24/24** checks pass (unchanged count; the new `"Change the schedule"` string and its French sibling are both present, D-08 completeness and no-dead-translations both hold).
- `ruff check .`: all checks passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_config_page.py`'s existing quick-action markup check broke on the new `id="..."` attribute**
- **Found during:** Task 1
- **Issue:** `_schedule_cards_carry_no_quick_action_markup` located the Quiet hours `<h2>` by the exact literal `'<h2 class="text-heading">%s</h2>' % heading`, which no longer matches once the heading gained `id="quiet-hours-group-heading"`.
- **Fix:** the literal absorbs the new attribute (`'<h2 class="text-heading" id="%s">%s</h2>' % (config_page.QUIET_HOURS_GROUP_HEADING_ID, heading)`). The check's own contract (no quick-action markup inside the card) is unchanged.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** full suite re-run green (263/263)
- **Committed in:** `9ca35e1` (Task 1 commit)

**2. [Rule 1 - Bug] `.flight-detail-row td`'s own padding redistribution attempt was dead code**
- **Found during:** Task 3, while designing the left-clip fix
- **Issue:** An initial attempt tried to make the fix visually invisible by moving 16px of left padding from `.flight-detail-row td` into `.flight-detail-row__reveal-inner`. Measurement (via `getComputedStyle`) showed `.flight-detail-row td`'s own `padding` declaration is entirely shadowed by the higher-specificity `table.data-table--flights td` rule (8px, not 16px) — the edit had zero effect on the rendered page.
- **Fix:** reverted the `.flight-detail-row td` edit; kept only `.flight-detail-row__reveal-inner`'s new `padding-left`, and documented (in both the CSS comment and this SUMMARY, Decision 3 above) that this is a real, disclosed 16px visual shift, not an invisible redistribution.
- **Files modified:** `companion/static/style.css`
- **Verification:** re-measured after the revert — the fix still closes the hit-target defect (45×45); `test_config_page.py` and `test_browser_ux.py` both green
- **Committed in:** `83948bc`-attributed content, landed in `6c225ce` per the commit-boundary note above

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs/dead code found while implementing, neither scope creep beyond the plan's own stated tasks). No architectural changes, no Rule 4 escalation.

## Issues Encountered

- The `git commit --only <paths>` commit-boundary issue for `companion/static/style.css`, documented above under Task Commits — a process note, not a code defect.
- One flaky, pre-existing, unrelated `test_browser_ux.py` check (`a Display page with a typed-but-uncommitted edit issues ZERO requests...`, about `window.SkyPaneDirtyState` timing on the `quiet_hours_start` field, nothing this plan touches) intermittently failed under `scripts/run-all-tests.sh`'s parallel (`JOBS=4`) load and passed consistently in every standalone/serial run (four separate confirmations, both before and after this plan's own code changes existed). Treated as environmental flakiness under contention, not a regression — the final full-suite run (below) confirms the failing set is exactly the 5-name baseline with no sixth.

## Known Stubs

None. The link's href, fragment target and translated text are all real and wired; the hit-target fixes are real CSS geometry changes, not placeholders.

## Threat Flags

None. `T-27-08-A` (a per-page parameter on the shared strip), `T-27-08-B` (`.copy-btn`'s fix silently enlarging `.row-toggle`) and `T-27-08-C` (the fragment id existing on one scope only) are exactly the three surfaces this plan's own tasks mitigate — no new network endpoint, auth path, file access pattern or schema change.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- 27-09 (the closing plan) can now tick CFG-69/CFG-70/CFG-71 in `.planning/REQUIREMENTS.md`/`STATE.md`/`ROADMAP.md` — deliberately left untouched by this plan per its own standing constraint 12.
- `<human-check>` from this plan's own `<verification>` section remains open for 27-09 or the developer: from Home and from Display, at 360px in both themes and both languages, tap the Quiet hours caption link and confirm it lands on the schedule fields; open a Flights detail row on a real phone and confirm the copy control and the row toggle are both comfortably tappable.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*

## Self-Check: PASSED

- Commits `9ca35e1`, `6c225ce`, `83948bc` all found in `git log --oneline --all`.
- `companion/pages/config_page.py`, `companion/layout.py`, `companion/static/style.css`, `companion/i18n_fr/home.py`, `companion/test_config_page.py`, `companion/test_status_pages.py`, `companion/test_browser_ux.py` all found on disk.
- `companion/test_config_page.py`: 263/263 checks pass (`EXPECTED_CHECK_COUNT = 263`).
- `companion/test_status_pages.py`: 305/306 checks pass (`EXPECTED_CHECK_COUNT = 306`, the one documented `anomaly_active()` sandbox failure).
- `companion/test_browser_ux.py`: 88/88 checks pass (`EXPECTED_CHECK_COUNT = 88`).
- `companion/test_i18n.py`: 24/24 checks pass.
- `ruff check .`: all checks passed.
- `PYTHON=server/.venv/bin/python3 bash scripts/run-all-tests.sh`: exactly 5 failing checks, confirmed BY NAME — the sandbox baseline (2× WR-11 in `companion/test_companion_app.py`, 2× WR-11 in `server/test_manual_resolutions.py`, 1× `anomaly_active()` in `companion/test_status_pages.py`). No sixth failure in the confirming run.
