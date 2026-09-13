---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 14
subsystem: ui
tags: [navigation, tab-bar, bottom-nav, details-summary, mobile-nav, nav-status, aria-current, safe-area-inset, z-index, dirty-bar, i18n-fr, playwright]

requires:
  - phase: 22-04
    provides: "the Frame strip's own sub-960px layout and the `.quick-action` rewrite this plan's save-bar offsets sit beside without touching"
  - phase: 22-08
    provides: "the widened test_i18n.py scanner (app.py + HTML attribute literals + JS fallback literals) that every new string here had to satisfy, and the already-translated `aria-label=\"Primary navigation\"` the tab bar inherits"
  - phase: 22-13
    provides: "companion/static/style.css handed over clean, and the `[hidden]`-versus-author-`display` collision class this plan had to check the tab bar against"
provides:
  - "X9/D-10: a bottom tab bar as the third nav rendering, fed by the ONE shared `_nav_links()`/`_nav_groups()` iteration — never a hand-listed route set"
  - "X9: zero page shift to any everyday destination, and the hamburger's remaining push cut from ~420px to a MEASURED 189px"
  - "X9: a native `<details>` More cell holding the Advanced group — keyboard-operable, announced, and fully functional with scripts blocked"
  - "B10: two `white-space: nowrap` state segments in a wrapping flex row, each one client rect in French at both the 240px sidebar and 390px"
  - "B10/D-04: a Home reminder that is a `<span>` with no href, announcing only the state — it can no longer claim a destination the user already occupies"
  - "T5: a deterministic dropdown close — the transitionend listener filters on its own target and property, and the no-transition path applies `hidden` synchronously with no timer"
  - "T11: exactly one open-state `max-height` for the dropdown, 320px, pinned against a measured 165px of reduced French content"
  - "T7/D-10: geometric separation of the save bar from the tab bar, then one `z-index: 30` across both breakpoints, plus a `.dirty-ready`-scoped content clearance at measured values"
  - "companion/test_status_pages.py's structural guard pinning style.css at zero stray comment terminators — a parse-error class no string-comparison harness can see"
  - "companion/layout.TAB_BAR_BODY_CLASS: a server-rendered `<body>` marker so page-foot clearance is reserved only where a bar exists (a `:has()` selector would have broken the pinned one-block count)"
affects: [22-15, 22-16]

tech-stack:
  added: []
  patterns:
    - "A third rendering of a shared iteration proves it is shared by comparing its RENDERED destinations element-for-element against another rendering's, not by asserting both are non-empty"
    - "A native `<details>`/`<summary>` meets the no-JS floor by construction rather than by a fallback path that can rot — the component emits no script hook at all"
    - "A notification dot inside a collapsed disclosure is invisible exactly when it matters: it belongs on the summary, which is the visible surface that leads there"
    - "`getClientRects().length === 1` per segment is the executable form of \"never breaks mid-phrase\" — a count only a real layout engine can produce"
    - "A flex row that is allowed to wrap uses a COLUMN-only gap when a height ceiling is in play: a symmetric gap is paid again on every wrapped line"
    - "An inline-flex segment stops a `vertical-align: middle` dot from growing the line box past the text's own leading"
    - "Geometric separation first, stacking order second: two fixed elements are made not to overlap before they are told who wins if they do"
    - "Two rules targeting the same element at the same specificity are declared NEXT TO EACH OTHER, because source order is the only thing deciding between them"
    - "A stray comment terminator in CSS silently drops the rule that follows it while leaving the source text a string-comparison harness reads as correct — pin the file structurally"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/static/style.css
    - companion/static/nav-dropdown.js
    - companion/i18n_fr/nav.py
    - companion/test_companion_app.py
    - companion/test_status_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "D-10 held in full: a bottom tab bar, never an overlay drawer. The rejected absolute-overlay verdict on the primary nav is untouched, and `.mobile-nav`'s in-flow `flex-basis: 100%` mechanism is unchanged — only the panel's CONTENTS shrank"
  - "The More sheet's upward `position: absolute` is recorded, in both the stylesheet and `_tab_bar_html()`'s docstring, as NOT a reversal of that verdict: the verdict is about a component that must be able to push content, this is a two-item sheet anchored to an already-fixed bar"
  - "The health-alert dot moves onto the More SUMMARY rather than onto the Health link inside the sheet — one per nav renderer, unchanged, but visible when the sheet is closed"
  - "`aria-current=\"page\"` stays on the one real link and never on the `<summary>`; the summary wears the active pill only"
  - "The page-foot clearance is scoped to a server-rendered `<body class=\"has-tab-bar\">` rather than to a `:has()` selector, because `test_config_page.py` pins the file at exactly one `@supports selector(:has(*))` block"
  - "The phone save-bar clearance was measured in BOTH languages and the usual assumption failed: ENGLISH wraps taller at 390px (122px against French's 110px)"
  - "`.nav-status`'s gap is column-only and each segment is inline-flex — both changes were forced by measurement against B10's own 48px ceiling, not chosen for taste"
  - "Rule 1 auto-fix: 22-10's appended comment note left a stray terminator that silently dropped T10's saved-chip badge rule outright. Fixed, and the whole stylesheet is now pinned structurally"

patterns-established:
  - "Bottom tab bar: `display: none` declared OUTSIDE the media query and only lifted below the fractional 959.98px boundary, so a desktop that never matches can never show it"
  - "Edge-anchored floating chrome takes NO border radius; `--radius-card` is for floating elements that do not touch a viewport edge"
  - "The one active-signal idiom (12% accent wash + accent text + semibold) gains a third consumer verbatim, with the inactive hover `:not(--active)`-scoped and placed after it"

requirements-completed: [CFG-30]

duration: 26min
completed: 2026-09-13
---

# Phase 22 Plan 14: Navigation — the bottom tab bar Summary

**Every everyday destination is one tap away at zero page shift: a bottom tab bar fed by the one shared nav iteration, a hamburger reduced to preferences whose remaining push measures 189px against ~420px before, a state reminder that reads on one line in French and stops claiming to be a link to the page you are already on, and two fixed bars that provably never overlap on a 390×844 phone.**

## Performance

- **Duration:** 26 min
- **Started:** 2026-09-13T05:07Z
- **Completed:** 2026-09-13T05:34Z
- **Tasks:** 3 of 3
- **Files modified:** 7

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | `b50c9f2` | `feat(22-14): a bottom tab bar, fed by the one nav iteration` |
| 2 | `3723b7d` | `feat(22-14): the dropdown holds preferences, the reminder stops lying` |
| 3 | `893aa8f` | `feat(22-14): the save bar and the tab bar, apart and ordered` |
| — | *(this commit)* | `docs(22-14): complete the navigation / bottom tab bar plan` — hash omitted deliberately: a commit cannot carry its own hash in its own content |

## Accomplishments

### Task 1 — the bottom tab bar (X9, locked by D-10)

`layout._tab_bar_html()` is the **third** consumer of `_nav_groups()`/`_nav_links()`. The everyday/Advanced split is read from the group LABEL the shared iteration already yields, not from a second list, so adding a route to `NAV_GROUPS` changes the sidebar, the tab bar and any future rendering together or none of them. The check that defends this compares the tab bar's rendered destinations **element-for-element against the sidebar's**, in NAV_TABS order — a hand-listed copy of the routes fails it.

Five cells: Home, Display, Flights, Airlines, then More as a native `<details>` whose sheet opens upward and holds Health and Device at `.mobile-nav__link`'s own 44px/16px geometry (the class is **reused**, not restated). The bar renders from `page_shell()` only and only when `device_config` is present — the same gate that already keeps the state reminder off the login shell and the 404.

Geometry per 22-UI-SPEC §3.1: `display: none` outside the media query and lifted only below the fractional 959.98px boundary; fixed to the viewport bottom; 56px of row plus `env(safe-area-inset-bottom, 0px)`; `--color-secondary` with a top hairline and `--shadow-card-hover` at rest; **no border radius**, because the bar is edge-anchored. Five `flex: 1 1 0` cells = 78×56px at 390px. An 11px `--font-ui` regular sentence-case label, explicitly not the label voice (no `text-transform`, no `letter-spacing` — both pinned as absences).

The active tab reuses the app's one active-pill idiom byte-for-byte, with the inactive hover `:not(.tab-bar__link--active)`-scoped and placed after it. `aria-current="page"` sits on the one real link; on an Advanced page the More **summary** wears the pill so a collapsed bar never lies about where you are, while `aria-current` stays off the disclosure control.

`icon-more` joins the sprite whitelist (21 → 22, both counts edited in place, no check added). "More" gains its French entry, "Plus".

### Task 2 — the dropdown shrinks, the reminder stops lying, the close becomes deterministic

The hamburger panel loses its six destination links **and its navigation landmark with them** — removed, not emptied, because an empty landmark is still announced. The document still carries exactly two `Primary navigation` landmarks (sidebar + tab bar) and still exposes exactly one at any viewport width; a page with no device config now carries exactly one, which the retargeted check also pins.

The toggle is renamed `Account and preferences` / `Compte et préférences`; the retired `Open menu` translation is **deleted**, not superseded in place, so it cannot orphan.

**T11** — one open-state `max-height`, 320px. Both contradicting declarations (420px and 640px) are gone, not re-tuned; the `.mobile-nav__nav` rule and its `.nav-group` override go with them, while `.mobile-nav__link` survives for the tab bar's sheet.

**B10** — two `.nav-status__segment` spans, each `white-space: nowrap`, in a wrapping flex row. On Home the reminder renders as a `<span>` with no `href` whose `aria-label` is composed from the same two translated state strings the visible segments interpolate, so the announced name and the rendered text cannot drift and no new catalogue entry is introduced. The hover underline is scoped to `a.nav-status`.

**T5** — the `transitionend` listener filters on `evt.target === panel` *and* `evt.propertyName === "max-height"`, is registered as a named function (so `addEventListener`'s own duplicate rule makes it idempotent, where `{ once: true }` would be spent by the first rejected event), and re-reads `isOpen()` before hiding. The no-transition path applies `hidden` synchronously, decided by **reading the computed transition style** rather than by a fallback timer — `nav-dropdown.js`'s header forbids timers as a standing constraint.

### Task 3 — the two bars, apart and ordered

Geometric separation first: below 960px the save bar's `bottom` gains the tab bar's 56px. Measured at 390×844 with a real unsaved edit, the save bar ends **15px above** the tab bar's top edge. Then stacking order as belt-and-braces: `z-index: 30` at **both** breakpoints (the desktop rule carried none — T7's desktop half) above the tab bar's 20, with the reason stated where it is declared. The original "No z-index, and why" paragraph is **amended in place**, exactly as its own escape clause asks; the check asserts both the surviving clause and the new stated reason.

`.dirty-ready`-scoped content clearance at both breakpoints, at measured values (below). The phone rule is declared immediately **after** `.has-tab-bar .page-content`, because the two target the same element at the same (0,2,0) specificity and source order is the only thing deciding between them.

## Measurements plan 22-16 needs

| Figure | Measured | Where |
|---|---|---|
| Dropdown content height, FR at 390px | **165px** | drove T11's single 320px cap (headroom for a longer future footer string) |
| Remaining hamburger push, FR at 390px | **189px** (313 − 124) | against X9's ≤220px target, from ~420px |
| `.nav-status`, FR at the 240px sidebar | **207 × 47px**, one client rect per segment (98px / 165px wide) | was 207 × 48 breaking mid-phrase |
| `.nav-status`, FR at 390px | **28px**, one client rect per segment | |
| Save bar height at 1280px | **64px**, identical EN and FR (`width: fit-content`, no wrap) | → `.dirty-ready .dashboard-main` clearance 88px |
| Save bar height at 390px | **122px EN / 110px FR** — English is the taller copy here | → `.dirty-ready .page-content` clearance 144px |
| Save bar bottom → tab bar top, 390×844 | **15px**, boxes non-intersecting, both hit-testable at their centres | |

**Touch-target register entry for `references/control-density.md` (§4):** the tab bar's cells are **78 × 56px at 390px** and clear the WCAG 2.5.5 (AAA) 44px floor **directly in both axes**. This joins the **met-directly** category alongside `.frame-colours__row`. It is explicitly **not** a fifth entry in the traded-away list, because nothing was traded for it.

**Harness pins, old → new:**

| Harness | Before | After | Delta |
|---|---|---|---|
| `companion/test_companion_app.py` | 269 | **271** | +2 (Task 1) |
| `companion/test_status_pages.py` | 258 | **266** | +3 Task 1, +4 Task 2, +1 Task 3 |
| `companion/test_browser_ux.py` | 17 | **20** | +2 Task 2, +1 Task 3 |
| `companion/test_config_page.py` | 232 | 232 | unchanged |
| `companion/test_i18n.py` | 24 | 24 | unchanged |

Every count was re-derived by **running** the harness and reading its printed total, never by arithmetic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] A stray CSS comment terminator was silently dropping a whole rule**

- **Found during:** Task 2, while measuring B10 in a real browser.
- **Issue:** `companion/static/style.css:2281` carried a comment **terminator with no opener** — 22-10-PLAN.md Task 1 appended its note *after* the existing block comment's own closing marker. Everything from that marker to the next brace parses as part of the following selector, so the entire `.theme-chip--selected:not(:has(input:checked))::after` rule — **T10's saved-chip "Current" badge** — was dropped by every browser. The badge had not been rendering since 22-10 landed.
- **Also mine:** this plan's own first draft of the B10 comment made the *identical* mistake and took `.nav-status` down with it, which is how it was found at all. That break was visible as `getComputedStyle('.dashboard-sidebar').display === 'none'` at a 1280px viewport.
- **Fix:** both terminators corrected; a new structural check pins `companion/static/style.css` at **zero** stray terminators and asserts the file does not end inside a comment. No string-comparison harness could ever see this defect class — the file still *contains* every declaration such a harness asks about.
- **Files modified:** `companion/static/style.css`, `companion/test_status_pages.py`
- **Commit:** `3723b7d`

**2. [Rule 2 — Missing critical functionality] The health-alert dot would have vanished from phones**

- **Found during:** Task 1.
- **Issue:** removing the dropdown's Health link removes the only sub-960px surface the notification dot attached to. Nothing in the plan or the UI-SPEC covers it, and the existing "exactly one dot per nav renderer" contract would have silently become "one, sidebar only".
- **Fix:** `_tab_bar_html()` takes `health_alert` and draws `_health_alert_markup()` on the More **summary** — deliberately not on the Health link inside the sheet, because a dot inside a collapsed `<details>` is invisible exactly when it has something to say. The count stays exactly one per nav renderer; the visually-hidden "— attention needed" suffix rides along with it.
- **Files modified:** `companion/layout.py`, `companion/test_companion_app.py`
- **Commit:** `b50c9f2`

**3. [Rule 1 — Bug] `.nav-status` broke its own 48px ceiling, twice**

- **Found during:** Task 2, by measurement.
- **Issue:** the spec's contract (`display: flex; flex-wrap: wrap; gap: var(--space-xs)`) produced **52px** in the 240px sidebar, because a symmetric `gap` is paid again on the second wrapped line; then **48.19px**, because the 12px `.dot`'s `vertical-align: middle` grows every line box past the 14px text's own leading.
- **Fix:** a **column-only** gap (`gap: 0 var(--space-xs)`) and `display: inline-flex; align-items: center` on each segment. Final measurement 47px. The B10 target was met by changing the CSS, never by adjusting the criterion.
- **Files modified:** `companion/static/style.css`
- **Commit:** `3723b7d`

### Deliberate departures from the plan's own wording

**a. Task file lists vs. the frontmatter's `files_modified`.** Tasks 2 and 3 list a narrower `<files>` set than the work requires: removing the dropdown's links invalidates the premise of seven checks in `companion/test_companion_app.py` (Task 2) and the tab bar's clearance interacts with `companion/test_browser_ux.py` (Task 2). Both files are in the plan's own `files_modified` frontmatter, so nothing outside the plan's declared surface was touched; the per-task lists were simply narrower than the per-task work.

**b. Task ordering inside `layout.py`.** Task 1 was landed as a purely *additive* commit (the tab bar renders **alongside** the still-intact dropdown menu), and Task 2's commit then removes the dropdown's links. This keeps each commit's own verification meaningful — the alternative would have left Task 1's harness run red through no fault of its own.

**c. The phone `.dirty-ready` clearance is declared in the tab bar's block, not beside the sub-960px `.dirty-bar` rule.** `.dirty-ready .page-content` and `.has-tab-bar .page-content` target the same element at the same specificity, so writing them ~900 lines apart would have let the shorter value silently win by source order. A comment at the `.dirty-bar` site points at where it really lives, and a check pins the ordering.

## Checks retargeted (never weakened, never excepted)

Nine existing checks had their premise changed by this plan. Every one was **retargeted in place and strictly narrower**; none was deleted, skipped or excepted, and none contributed to an `EXPECTED_CHECK_COUNT` delta.

| Check | Retarget |
|---|---|
| `_page_shell_marks_only_the_active_dropdown_link` | → the tab bar, **and** gains an `aria-current` assertion the dropdown never carried |
| `_sidebar_and_dropdown_render_exactly_four_links_one_active_each` | → sidebar + tab bar, **and** gains "the dropdown holds zero destination links" |
| `_page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme` | → two landmarks on a render that has a tab bar, **and** gains "exactly one when there is none" |
| `_health_nav_notification_dot` (×2, error and warn) | → sidebar + More summary, **and** gains "no second dot inside the sheet / none on the four everyday tabs" |
| `_dropdown_contents_and_order` | → the panel's whole real contract (reminder, language, theme, Sign out, in order, and nothing else) rather than a prefix of a menu |
| `_dropdown_survives_with_javascript_disabled` | → the tab bar, **and** gains "the Advanced group opens natively via `<details>`, with no script hook at all" |
| `_three_file_nav_dom_contract_guard` | `mobile-nav__nav` → `tab-bar`/`tab-bar__link`; `mobile-nav__link` stays, since the sheet reuses it |
| `_advanced_group_always_renders_in_both_nav_copies` | → sidebar + tab bar slices, **and** tightened from "twice anywhere in the document" to "in each rendering's own slice" |
| `_nav_status_appears_once_in_each_nav_copy_after_the_brand` | "before its own nav list" → "before its footer", **and** gains "no third copy inside the tab bar" |
| `_icon_sprite_integrity` / `_page_shell_emits_sprite_once` | 21 → 22 members, edited in place |

## Self-inflicted criterion trips (caught, reworded — never the criterion)

The standing warning held true three more times. In each case the *prose* was changed, never the check:

1. A backtick in a new `nav-dropdown.js` comment tripped the file's ES5/template-literal guard (three occurrences). Reworded.
2. `parseFloat(durations[i] || "0s")` tripped `test_i18n.py`'s JS fallback-literal scanner, which reads `|| "..."` as an untranslated user-facing string. The default was removed outright — a missing entry parses to `NaN`, which is not `> 0`.
3. A new CSS comment containing the literal `.js .mobile-nav--open { max-height: 640px }` would have made `grep -c "mobile-nav--open"` return 2 against the criterion's "exactly one". Reworded to describe the deleted rule without naming it. The criterion now returns `1`.
4. In a new check, `".nav-status:hover {"` is a substring of `"a.nav-status:hover {"`, so the "is the unscoped rule gone?" test reported the scoped replacement as the thing it replaced. Replaced with a boundary-anchored regex.

## Acceptance criteria — every one run literally

**Task 1**

| Criterion | Result |
|---|---|
| rendered tab destinations equal the sidebar's, derived from the one iteration | PASS (pinned, element-for-element) |
| `grep -c "radius-card" companion/static/style.css` shows no radius on the tab bar's own rule | PASS — 13 hits, none inside `.tab-bar`'s rules; the two new ones are `.tab-bar__more-panel`'s top corners (a sheet that does not touch the bottom or left edge) |
| the login shell and the 404 render no tab bar | PASS |
| active tab carries `aria-current="page"`; on an Advanced page the More summary carries the pill | PASS |
| `test_companion_app.py` reports only its two documented FAILs; `test_i18n.py` exits 0 | PASS — 269/271 and 24/24 |
| `ruff check .` clean | PASS |

**Task 2**

| Criterion | Result |
|---|---|
| the rendered dropdown contains zero destination links | PASS |
| `grep -c "mobile-nav--open" companion/static/style.css` shows exactly one max-height declaration for that state | PASS — outputs `1` (after rewording my own comment, see above) |
| on Home the reminder renders as a span with no href; elsewhere as a link | PASS (source-level and in a real browser) |
| `grep -c "transitionend" companion/static/nav-dropdown.js` shows the listener filtering on target and property | PASS — 6 occurrences; the listener at `onCollapsed()` filters on `evt.target !== panel \|\| evt.propertyName !== COLLAPSE_PROPERTY` |
| `test_status_pages.py` reports M/M at its new pin apart from the documented `anomaly_active()` FAIL | PASS — 264/265 at that point |
| `ruff check .` clean | PASS |

**Task 3**

| Criterion | Result |
|---|---|
| the browser check reports both bars visible, non-intersecting and hit-testable at 390×844 | PASS |
| the save bar declares one stacking value, present at both breakpoints, higher than the tab bar's | PASS — 30 vs 20 |
| the `.dirty-ready`-scoped content padding exists at both breakpoints and its measured value is recorded | PASS — 88px / 144px, recorded above |
| `grep -c '@supports selector(:has(\*)) {' companion/static/style.css` outputs `1` | PASS — outputs `1` |
| `scripts/run-all-tests.sh` shows no new failure and coverage stays at or above 83 | PASS — the same three harnesses fail as at baseline, with the same five check names; coverage **93%** |
| `ruff check .` clean | PASS |

**No criterion evaluated other than predicted**, once the four self-inflicted trips above were reworded.

## Regression floor

The sandbox baseline is unchanged: **exactly 5 failing checks**, by name, across three harnesses, all of which pass in CI (this container runs as root).

| Harness | Baseline | After |
|---|---|---|
| `server/test_manual_resolutions.py` | 21/23 (2 × WR-11) | **21/23**, same two names |
| `companion/test_companion_app.py` | 267/269 (2 × WR-11) | **269/271**, same two names |
| `companion/test_status_pages.py` | 257/258 (`anomaly_active()`) | **265/266**, same name |
| `companion/test_browser_ux.py` | 17/17 | **20/20** |
| `companion/test_config_page.py` | 232/232 | **232/232** |
| `companion/test_i18n.py` | 24/24 | **24/24** |

**No test exception was added anywhere.** One check was added that did not exist before and could have been omitted: the stray-comment-terminator guard.

## Requirements

- **CFG-30 — ticked.** `grep -l "CFG-30" *-PLAN.md` returns nine plans and nothing beyond 22-14; 22-15 and 22-16 carry `CFG-31` only, so this plan is the last one serving it. X9 and B10 landed here. 22-13's handover note listed "B3, B10 and B13" as remaining — re-checked against the code, **only B10 was**: B3 landed in 22-03 (`resolution_stats()` counting every row with unknown sources bucketed as "Other", the empty section omitted outright, the 30-day window named) and B13 in 22-04 (one `.frame-strip__cell`, `align-items: stretch`, one three-row internal grid, the update line demoted). Every clause the requirement text enumerates is now landed. One caveat carried forward rather than hidden: 22-10 reported that X6's page-height pixel target is not met and cannot be by chip density alone — that is an audit measurement, not one of this requirement's own clauses, and the remaining half is D5/Phase 23.
- **CFG-31 — NOT ticked.** T5, T7 and T11 landed here; T1–T4, T6, T8, T9, T13–T16 and the whole `sketch-findings-skypane` update are 22-15's and 22-16's. Its traceability row records this plan's contribution.
- **CFG-28 — left un-ticked and untouched**, as instructed. 22-16's closing sweep owns Health's page-header clock.

## Notes for 22-15

1. **`style.css` is handed over clean**, with this plan's rules in three places: the tab bar as one contiguous block at the **end of the file**, in-place edits to `.nav-status` / `.js .mobile-nav--open` / the two `.dirty-bar` blocks, and two deleted dead selectors (`.mobile-nav__nav`, `.mobile-nav__nav .nav-group`).
2. **T3's chevron will land on the tab bar's More summary.** `.tab-bar__link` is also a `<summary>`, so an explicit `summary::before` chevron will be inserted into a 78px-wide cell above an icon+label stack. Decide deliberately whether to scope it away from `.tab-bar__link` or to accept it — do not discover it by rendering.
3. **T6 ("selection shifts layout by 2px") was left alone**, as instructed. It is yours; nothing in this plan touched `.runway-card`, `.theme-chip` or their `:has(input:checked)` rules.
4. **The `@supports selector(:has(*))` block is still at exactly one**, at the same site, and the criterion still returns `1`. This plan deliberately avoided a `:has()` selector for the page-foot clearance (a server-rendered `<body>` class was used instead) precisely to keep that count where it is.
5. **The stray-comment-terminator guard now runs on every `test_status_pages.py` run.** If a CSS comment edit trips it, the message names the line; append notes *inside* a block comment, never after its closing marker.
6. **`.mobile-nav__link` is now shared** between the (retired) dropdown menu and the tab bar's More sheet. Its 44px/16px floor is load-bearing for the sheet; do not compact it.
7. **Scripts are still eleven.** No twelfth deferred script was added on the authenticated shell — the tab bar needs none, by construction.

## Notes for 22-16 (the design-system sweep)

1. **`references/mobile-navigation.md`** needs: the tab bar as a third rendering; the "What to Avoid" rejected verdicts kept **unchanged and unreversed**; the clarifying note that the More sheet's upward `position: absolute` is not a reversal; the dropdown's reduction to reminder + footer; the renamed toggle label; the single `max-height` (320px, measured 165px).
2. **`references/control-density.md`** needs the tab bar in the **met-directly** touch-target category (78 × 56px at 390px), explicitly not the traded-away list.
3. **`references/settings-page-patterns.md`** needs both superseded entries recorded — the "No `z-index`, and why" paragraph and its matching "What to Avoid" line — with the stated reason (the save bar is the active task, the tab bar is ambient chrome, B1 is the phase's P0), plus the new sub-960px `bottom` offset. The stylesheet paragraph itself was amended in place, not deleted, and a check pins both the surviving escape clause and the new reason.
4. **`SKILL.md`'s Cards paragraph** floating-overlay count: it says "two" (`.lightbox`, `.dirty-bar`), is already stale by one (`.mobile-nav`), and the tab bar makes it **four**. Correct the count and the list in one edit.
5. **`SKILL.md`'s Navigation paragraph** should record that the sub-960px `Primary navigation` landmark moved from the dropdown to the tab bar, and that a page with no device config now exposes exactly one landmark rather than an empty second one.
6. **The accent-reservation list in `style.css`'s header was widened, not extended**: "the active sidebar/dropdown link indicator and its tinted pill" became "sidebar/dropdown/tab-bar", with the widening stated inline. This is one more consumer of an already-listed use — **no new entry, no new accent consumer** — consistent with 22-UI-SPEC §4's "loses two entries and gains none". The C2 arithmetic sentence the harness pins is untouched.
7. **T10's saved-chip badge was never rendering** since 22-10 landed (see Deviation 1). If 22-16 reviews T10 as "done", it is done *now*; it was not before this plan.

## Threat Flags

None. This plan introduced no network endpoint, no auth path, no file access and no schema change. Nav visibility remains presentation-only (T-22-52): `/health` and `/device` stay session-gated on the server regardless of which rendering links to them, and the tab bar's absence from pre-session pages is a rendering gate, never an access-control one.

## Self-Check: PASSED

- `companion/layout.py` — FOUND
- `companion/static/style.css` — FOUND
- `companion/static/nav-dropdown.js` — FOUND
- `companion/i18n_fr/nav.py` — FOUND
- `companion/test_companion_app.py` — FOUND
- `companion/test_status_pages.py` — FOUND
- `companion/test_browser_ux.py` — FOUND
- commit `b50c9f2` — FOUND
- commit `3723b7d` — FOUND
- commit `893aa8f` — FOUND
- the docs commit is this one; its hash is not self-citable
