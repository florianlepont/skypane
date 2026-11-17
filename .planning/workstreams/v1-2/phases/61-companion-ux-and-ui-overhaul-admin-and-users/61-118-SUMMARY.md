# Phase 61 Plan 118: Audit 5, lot D (Users table, motion rules, splash, low findings) Summary

**The Users table decision (option A), one motion rule each for A5-04, A5-08, A5-09 and A5-13, a shorter splash, and fourteen low findings fixed (three more in part), in eleven commits. Each change has a behaviour or browser test seen red without it, except X12 (see below). Twenty-one low findings are skipped for a stated reason and fifteen were not attempted.**

Owner decision D56 (treat all audit-5 findings, in lots). This is the fourth and last lot. There was no PLAN.md: the orchestrator's brief was the plan. The branch was not behind `origin/main`, so nothing was merged.

## Step 1: Users table, option A (X03)

Commit `b7c7d3fc`.

- From 600px up an address is one line that ends in an ellipsis. The whole address stays in the element's title and in the row's header cell (its accessible name). There is no person detail view, so nothing was added there. Below 600px the phone card still wraps the address at `@` and `.`.
- "Jamais connecté" / "Never signed in" never wraps, at any width.
- The frame count and the co-manager mark are two whole parts: one under the other in the table, joined by a dot on a card.
- Table columns are as wide as their longest French content; the person takes the rest. The last row keeps the hairline's room, so every row measures 65px at 1280 in EN and FR.
- At 768 the page shows cards, not a table. Cards are equal within each kind: a person who has not signed in carries one more line (the Copy invitation button).

**Two changes beyond the brief:**

- **The table now starts at 1272px, not 1120px.** Beside the sidebar the table is 416px narrower than the window. With every other column on one line, a table narrower than 856px leaves no room for the address and its status pill. Between 1120 and 1271 the page shows the cards.
- **The narrowest phone card (up to 416px) changed its bottom line.** With nowrap, "Jamais connecté" ran into "1 cadre · co-gestionnaire" at 360px in French. The frames and the last sign-in no longer share the role/switch column split.

Tests: `companion/test_browser_users_rows.py` (new, 44 cases at 360, 390, 768, 1120, 1272 and 1280, EN and FR). Updated in place: `test_browser_users_page.py` and `test_browser_users_cards.py`, which pinned the wrapped address in the table.

## Step 2: one motion rule per finding

| Id | Rule | Commit |
|----|------|--------|
| A5-04 | A strip whose segments change page (Style, Fleet, Audit) hands its selection to the page change: the selected segment glides to its new place inside the view transition, like the tab bar's pill, and nothing slides once the page is there. Strips that switch in place (Flights, Airlines) slide as before. | `6ad5ca7a`, `1e07125b` |
| A5-08 | A page change plays one motion, the cross-fade. A page reached through a view transition arrives with an entrance that takes no time. A page opened by its address, a reload or a browser without view transitions plays the entrance. The cross-fade runs on `--motion-view-transition` and `--ease-out`. | `c44407a5` |
| A5-09 | Every page opens in the same order: the header at once, then each block one `--motion-stagger` step after the one before it, in page order, up to five steps. Every block of the first screen takes part. A card, strip or control row rises and fades; a list, grid or table as tall as its data fades as a whole (opacity only); the map stays still. | `87c36c1a` |
| A5-13 | What a control opens (frame menu, More panel, dialog) arrives with a short fade on `--motion-fast` and leaves at once. Only what the person moves away (a dragged sheet, a swiped toast) or what leaves on its own (a toast that times out) has a leaving motion. | `7ee21a90` |

What changed for each:

- **A5-04.** The script's slide from a remembered segment (session storage) is removed, which ends the two pills, the late slide and the slide after arriving by the tab bar. The selected segment carries `view-transition-name: skypane-strip`. The shell holds the first frame until the strip is parsed (`<link rel="expect">`); without it the glide was missed under load.
- **A5-08.** `splash-boot.js` marks `<html>` on a `pagereveal` that carries a view transition; the stylesheet zeroes the entrance's duration and stagger under that mark.
- **A5-09.** Home drops its own order (it now runs 60 to 300ms instead of 0 to 180ms). The Style layout card and strip and the Fleet header row and tabs take the entrance. The Audit list and count, the Airlines grid and the editor table fade as a whole. A section inside a group no longer plays a second entrance, which also closes A5-17. Account's row dialogs moved after its groups so the groups are siblings.
- **A5-13.** The More panel had no motion. It takes a plain fade, not the frame menu's scale: a scale shrank its 44px rows while it arrived and failed twenty existing target-size tests. Dialogs already fade in and leave at once; that is now written in the stylesheet.

Tests, all in `companion/test_browser_page_opening.py`: the selection glides on Audit, Fleet and Style and no thumb slides afterwards; a strip reached by the tab bar moves nothing; no entrance under a page change; the order of the opening on fifteen pages at 360 and 1280 and on each Fleet tab; the newly animated blocks; the More panel with and without reduced motion. Updated in place: three slide tests there, `test_browser_personalisation.py`, `test_browser_home_title.py`, `test_browser_sky_motion.py`, `test_companion_app_04.py` (pinned entrance selectors), `test_shell_meta.py`, `test_browser_ux_helpers.py`.

## Step 3: splash and warm-up

- **A5-10 (duration), commit `66dc57c2`.** The opening from the frame takes 400ms instead of 520ms and starts after a 60ms hold instead of 100ms. Six runs here on a phone viewport: 1.94-1.96s before, 1.79-1.80s after. Test: the planned sequence ends by 1.75s (`test_browser_splash.py`).
- **A5-10 (main-thread outline and per-node clip), not done.** Opening the page with one clip on a single wrapper means restructuring the splash.
- **P5-05, left as is.** The warmed copy still lives 10 seconds. The two options are a longer lifetime or dropping the idle warm-up; neither is clearly better without the owner's choice.

## Step 4: low findings

Fixed:

| Id | Fix | Commit |
|----|-----|--------|
| X05 | The French Flights search hint is "Rechercher…" and fits its field at 1280. | `68097119` |
| X06 | Suggestion chips of a special look are 44px tall. | `68097119` |
| X08 | The Fleet cell's warning dot sits at the icon's corner; every icon of the bar is at one height. | `68097119` |
| X09 | A focused control is scrolled clear of the floating tab bar (`scroll-padding-bottom`). | `68097119` |
| X11 | Quiet hours presets keep 12px of padding at 360px. | `68097119` |
| X12 | Users phone cards: the last sign-in is one line. Fixed by step 1; the phone test was added afterwards and was not seen red. | `b7c7d3fc`, `68097119` |
| X14 | Fleet > System cards fill the page column. | `68097119` |
| X15 | On a frame's not-found page the More cell is at most 96px wide, at the far end of the bar. | `68097119` |
| X16 | Audit chips keep their own width when they wrap on a phone. | `68097119` |
| X18 | Credits' way back and the System view's "Airlines we could not name" link are 44px targets. | `68097119` |
| X19 | An airline without a picture shows a plane in the placeholder. | `68097119` |
| W5-08 | The request language is set before any handler runs, so a refused invite and the role toast are in the language of the page. | `eff57bd4` |
| W5-25 | `/fleet?frame=<unknown>` shows a docked notice naming the frame shown instead (EN/FR). | `eff57bd4` |
| W5-26 | The Flights lists are `aria-busy` while a filter request is out. No "Searching…" wording was added. | `804792ac` |
| A5-14 (part) | The root cross-fade uses the tokens (with A5-08). | `c44407a5` |
| A5-17 | No nested entrance (with A5-09). | `87c36c1a` |
| A5-18 (part) | The new tests cover the opening order, the page change and the strips. | several |

Tests: `companion/test_browser_small_fit_fixes.py` (new), `test_console_users.py`, `test_console_fleet_view.py`, `test_browser_flights_search_more.py`.

Skipped, with the reason:

| Id | Reason |
|----|--------|
| X13 | The one-line detail with an ellipsis is pinned by `test_view_pages_03.py` as an earlier decision; letting it wrap reverses it. Tried and reverted. |
| W5-13 | Not reproducible: the radius field already carries `min=2 max=28 step=1`. |
| W5-12 | A history entry per sheet changes how every dialog answers Back; needs a design choice. |
| W5-15 | Carrying a refused pairing code through the redirect puts it in a cookie or the address; needs the owner's choice. |
| W5-17 | Redrawing the invite dialog from the address puts the typed e-mail in the address bar and the access log. |
| W5-22 | Needs a paginated no-script airline list. |
| A5-15, A5-16 | How many unlock effects play at once, and how the map moves, are design choices. |
| A5-20 | Removing the Flights fade reverses what lot A kept on purpose. |
| P5-07, P5-10, P5-12 | Refactors of `place-map.js`, the Airlines dialogs and `value-controls.js`: not small, not safe in this lot. |
| P5-08 | The audit asks for a coverage run at 1280px first. |
| P5-09 | An external sprite changes the markup of every page. |
| P5-11, P5-13 | Profiling and real-device checks, not code changes. |
| P5-14, P5-15, P5-17, P5-18 | The audit asks for no change. |
| P5-16 | Owner decision (Brotli), and `deploy/` is out of bounds. |

Not attempted in this lot (no reason beyond time): **X07** (resolve buttons), **X17** (Components specimens), **W5-09** (toast after the Active switch), **W5-10** (way back on the CSRF page), **W5-11** (Back after a first search), **W5-14** (quiet hours with equal times), **W5-16** (sign-in cancelled then reload), **W5-18** (unsaved layout across Style tabs), **W5-19** (HEAD and other methods), **W5-20** (headings and titles), **W5-21** (focus after Cancel, sort by keyboard), **W5-23** (anti-forgery token in the upload address), **W5-24** (upload refusal reasons), **A5-12** (pull to refresh), **A5-21** (Load more shift), and the rest of **A5-14** (picture, unlock and splash timings).

## Tests run

- Before each commit: ruff, mypy, `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`, `stub-server/test_phase47_freeze.py`, the render snapshot (`--write`), `test_render_baseline.py`, `test_sign_in_surfaces.py`, `test_suite_guards.py`, `test_i18n.py`, `test_components_page.py`, `test_companion_app_04.py`, and the test files of the touched areas. From the A5-08 commit on, `test_browser_ux_02.py` and `test_browser_overhaul_sweep.py` as well. New browser tests were run in four parallel processes.
- Largest runs: 79 files around the opening (5762 tests) and 70 files around the visual batch (5634 tests).
- After `804792ac`: every non-browser test of `companion`, plus `test-support` and `stub-server`, `-n 8`: 7556 passed, 4 skipped, **1 failed** (`test_stylesheet_structure.py`, see Deviations). After the fix `1e4249b3`, the last code commit, the same run: 7557 passed, 4 skipped. The browser files of the opening, the Users pages, French fit, `test_browser_ux_02.py` and the overhaul sweep were run on the fixed tree before that commit: 1490 passed.
- The four skips need a non-root user (`test_companion_app_01.py:664` and `:704`, `test_freshness_token.py:348`, `stub-server/test_byos_hardening.py:528`); they cover file permission bits, which this plan does not touch.
- Not run: `./scripts/run-all-tests.sh` (coverage gate) and the browser files of untouched areas, per the test cadence.

## Deviations

- **Nine commits fail the stylesheet structure guard.** `test_stylesheet_structure.py::test_no_selector_is_declared_in_two_rules_of_one_context` fails from `b7c7d3fc` (the Users table declared the menu cell twice in one media block) to `804792ac`; `87c36c1a` added four more duplicates. That file was not among those run before each commit; the final non-browser run caught it and `1e4249b3` fixes it. The orchestrator should not push a state between those two.
- **A second red commit.** `6ad5ca7a` (A5-04) added a view-transition name without listing it in `test_browser_ux_helpers.py`; `test_browser_ux_02.py::test_view_transition_names_are_unique_on_every_route` fails on that one commit. `1e07125b` fixes it. That test file was not among those run before the commit.
- **A5-13 uses a fade, not the frame menu's entrance** the finding suggested (see above).
- **Home's opening is 120ms longer** (last block at 300ms instead of 180ms), a consequence of the one order.
- **`:nth-child(n of S)`** is used for the Fleet tabs' order on a phone. A browser without it shows that tab's blocks together, one step after the tabs.
- **Commit trailer.** The executor rules ask for `Claude Sonnet 5.5`; the brief asks for the model doing the work, so the commits carry `Claude Fable 5.2`.
- `companion/app.py` is at 1493 lines (ceiling 1500); `list-filter.js` 959, `motion.js` 1078.

## For the orchestrator

- **Two flaky tests seen once each under load, green alone:** `test_browser_motion_sheets.py::test_a_short_toast_swipe_springs_back_and_the_toast_stays` (already reported by lot A) and `test_browser_ux_03.py::test_a_refresh_keeps_every_picture_action_working` (three runs alone, all green).
- **The request language is now set for every request before its handler** (`app.py`, one line). Every flash a POST builds is translated at POST time in the reader's language.
- **Design-system skill.** `sketch-findings-skypane` does not describe the 1272px Users table, the opening order, the single page-change motion or the carried strip selection; the skill file was not edited.
- **`61-UI-SPEC.md` was not edited** for the Users breakpoint or the motion rules.

## Self-Check: PASSED

All eleven commits exist on `milestone/v1.2-phase-61-companion-ux`; `companion/test_browser_users_rows.py` and `companion/test_browser_small_fit_fixes.py` exist; nothing was pushed; the two untracked `.whl` files were not touched; ROADMAP, STATE and REQUIREMENTS were not edited; no file under `hardware/` or `deploy/` was changed.
