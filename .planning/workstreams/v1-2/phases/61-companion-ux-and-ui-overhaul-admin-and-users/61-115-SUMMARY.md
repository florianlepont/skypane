# Phase 61 Plan 115: Audit 5, lot A (quick, safe fixes) Summary

**Fifteen audit-5 findings closed in seven commits: lighter Flights thumbnails, a page opening that plays once and starts readable, a finite waiting pulse, a reduced-motion rule that no longer shifts layout, three French truncations, and four small motion and wording fixes. Each has a behaviour test that was seen red without the fix.**

Owner decision D56 (treat all audit-5 findings, in lots). This is the first lot. There was no PLAN.md for this plan: the orchestrator's brief was the plan.

## What is fixed, per finding

| Id | Fix | Commit |
|----|-----|--------|
| P5-01 | The 44px stand-in on a Flights row asks for the `?w=264` WebP variant (with the override's cache buster) instead of the 450x132 PNG. The cache buster moved to `illustration_normalize.cache_buster()` so Flights shares it with the airline pages. | `8bcd3de9` |
| A5-01 | The entrance rules are scoped to `main[data-page-open]` and `motion.js` drops the mark when the opening's last animation ends. A filter change on the Flights desktop table now only fades: first-row top stays at one value (it went 215 -> 227 -> 215 before). | `109123f2` |
| A5-05 | Same mechanism: a refresh that swaps Home's regions, or a switch flipped in place, no longer fades the hero and the groups in again. The hero's `.reveal` class is scoped to the opening too. | `109123f2` |
| A5-02 | `.is-breathing` runs fifteen beats (30 s) then rests, stops at ambient rest, and is `animation: none` under reduced motion (it was an endless 0.01 ms loop). | `142c7c1c` |
| A5-18 (partly) | The endless-animation guard allows a loop only by name, element and pseudo-element, with a reason per entry. `skypane-pulse` is off the list. An overdue Home is seeded with and without reduced motion. | `142c7c1c` |
| A5-03, A5-11 | The global reduced-motion rule limits transitions to paint-only properties and zeroes their delay, so no style change lays the page out through an intermediate frame. `transitionend` still fires (Leaflet and the scripts that listen for it are untouched). Location under reduced motion: CLS 0.35 -> within 0.03 at 1280, 0.18 -> within 0.03 at 768. | `ac7811ac` |
| P5-02 | The opening fade starts at `--opening-opacity` (0.6) instead of 0. Replayed and appended blocks still fade in from nothing. | `b1b76921` |
| X02 | Fleet > Access: the pill moves under the address instead of squeezing it and is never clipped. The action stays on the row's line. | `0bd9887f` |
| X03 | Users table: the role select keeps the same small padding on both sides, so "Administrateur" shows whole beside the native arrow (it needed 169px in 158px; it now needs 149px). | `0bd9887f` |
| X04 | Special look form: the "Applies to" segments start from their own word, so "Compagnie" is one line at 360 and 390. | `0bd9887f` |
| X10 | The first frame's default name reads in the viewer's language on Account and in the Rename field, through the same helper as Home and the frame menu. A name someone typed is never translated. | `0bd9887f` |
| A5-14 | The 35 transition durations that hardcoded 150ms (14 rules) spend `--motion-fast`. | `dbbc1681` |
| A5-06 | A Save bar that only shows on a change is kept out of the first paint: the server marks it (`data-dirty-wait`), the stylesheet hides a marked bar while `html.js-early` is set, and `dirty-state.js` removes the mark when it takes the bar over. Without scripts the bar shows as before. | `dbbc1681` |
| A5-07 | The Home countdown no longer rolls every second of its last minute. One roll per minute change; none on a rewrite of the same text, the count-up or a refresh. The watcher follows the hero across refreshes. Its figures are tabular. | `dbbc1681` |

## LCP before and after (P5-02)

Measured with the audit's probe (`audit5/perf` `common.py` and `boot.py`, phone profile, Fast 4G, CPU x4, median of 5 loads), before and after the opening change only:

| Page | FCP / LCP before (ms) | FCP / LCP after (ms) |
|------|-----------------------|----------------------|
| Home | 372 / 920 | 428 / 428 |
| Airlines | 440 / 504 | 464 / 488 |
| Account | 416 / 832 | 408 / 408 |
| Users | 424 / 900 | 440 / 456 |
| Audit | 408 / 816 | 424 / 424 |
| Editor | 456 / 924 | 456 / 456 |

P5-01 bytes: not re-measured with the audit's script. The tests assert every stand-in is `image/webp`, under 16 KB, and that the first screen's pictures together weigh less than a third of the same pictures at full size. The audit's own figure for the nine first-screen pictures was 413,608 B -> 60,466 B.

## Tests added or changed

New:

- `companion/test_browser_french_fit.py` (X02 at 360 and 390 FR, a long address, X03 at 1280 FR, X04 at 360 and 390 FR).
- `companion/test_flights_cards.py` and `companion/test_browser_flights_stand_in.py`: the reduced variant in the markup and its weight on the wire.
- `companion/test_browser_page_opening.py`: first-row top stable across a filter change; largest paint within 150 ms of the first paint on Home, Account, Users and Audit; Location under reduced motion at 768 and 1280 (CLS <= 0.03, no layout transition).
- `companion/test_browser_motion_live.py`: no entrance on a live update of Home; the overdue pulse is finite; no pulse under reduced motion; one roll per minute change.
- `companion/test_browser_save_bar.py`: the bar has no box from the moment it is parsed until a field changes; it shows without scripts.
- `companion/test_companion_app_04.py`: every transition duration comes from a motion token.
- `companion/test_frame_rename_and_users_switch.py`: the default name reads one way on Home, Account and Rename in EN and FR.

Updated in place because their subject changed:

- `test_browser_page_opening.py`: the opening tests read the mark when `<main>` is parsed and expect it gone afterwards.
- `test_companion_app_04.py`: the pinned entrance selectors carry `[data-page-open]`.
- `test_browser_round8_fixes.py`: the look-view entrance is read from the animations that started, not from a computed style after load.
- `test_browser_overhaul_sweep.py`: the endless-animation allow-list.
- `test_browser_motion_live.py`: the "rolls on each tick" test became "ticks down without any roll".
- `test_view_pages_02.py`: the stand-in URL carries `?w=264`.

## Tests run

- Before each commit: ruff, mypy, `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`, `stub-server/test_phase47_freeze.py`, the render snapshot (`--write`), `test_render_baseline.py`, `test_sign_in_surfaces.py`, `test_suite_guards.py`, and the browser files of the touched pages.
- After the last code commit (`dbbc1681`): every `companion/test_browser_*.py` file plus `stub-server`, `-n 6`: 3329 passed, 1 skipped (`stub-server/test_byos_hardening.py:528`, root ignores permission bits). The non-browser `companion` and `test-support` suite on the same tree: 7117 passed, 3 skipped (the three `requires_non_root` tests).
- `./scripts/run-all-tests.sh` (coverage gate) was not run, per the test cadence.
- The three `requires_non_root` tests (`test_companion_app_01.py:664` and `:704`, `test_freshness_token.py:348`) were read: they cover the airline-resolution POST routes and the calendar secret's freshness token, none of which this plan touches.

## Deviations

- **Access row (X02).** A first version put the action under the address on phones. An existing test (`test_browser_remaining_audit_fixes.py`) pins the action on the row's first line and a row under 80px, so that version was dropped. In the shipped layout the address at 360px in French still ends in an ellipsis for `admin@example.test` (155px available, 158px needed); its title holds the full value. At 390px it is whole.
- **Users table (X03).** Only the select's padding changed. Widening the role column took width from the frames column and made "co-gestionnaire" run closer to the next column, so the column widths are as before. E-mails and "Jamais connecté" still wrap at word boundaries; the audit's row-height remark is not addressed.
- **Save bar (A5-06).** A first version had the script write a `data-dirty-ready` marker. `test_config_page_03.py` forbids that name in `dirty-state.js`, and the `:not(a, b)` selector tripped the one-rule-per-selector guard. The shipped version uses a server-rendered mark the script removes.
- **Reduced motion (A5-03).** `transition: none` was not used: Leaflet's pan animation waits for `transitionend`. Transitions are limited to paint-only properties instead.
- **Commit trailer.** The executor rules ask for a `Claude Sonnet 5.5` co-author line; the session's own attribution instruction names the model that did the work, so the commits carry `Claude Fable 5.2`.
- X10 was committed with X02-X04 (one French-text commit) because the render baseline is shared.

## For the orchestrator

- **LCP test margin.** `test_the_largest_text_is_painted_with_the_first_paint` allows 150 ms between first and largest paint. It passed 24 runs under 18 parallel browsers here; on Home the largest element in the test seed is the preview image, so a very slow CI image decode could exceed it.
- **One flake seen once.** `test_browser_motion_sheets.py::test_a_short_toast_swipe_springs_back_and_the_toast_stays` failed once in a 2070-test run under load, then passed in 5 further runs (one alone, four in parallel) and in the final full run.
- **Design-system skill.** `sketch-findings-skypane` (line 81) still describes `skypane-pulse` as an endless loop; it is now fifteen beats. The skill file was not edited.
- **Not covered by a test:** that the minute roll still plays after a refresh replaced the hero (the watcher re-attaches on `skypane-regions-swapped`; a refresh with unchanged content swaps nothing, so there was no cheap way to force it).
- A5-18 is only partly done, as scoped: no test samples the 45 s auto-refresh itself (the refresh is requested through `skypane-refresh-request`).

## Self-Check: PASSED

All seven commits exist on `milestone/v1.2-phase-61-companion-ux`; every file named above exists; nothing was pushed; the two untracked `.whl` files in the repo root were not touched.
