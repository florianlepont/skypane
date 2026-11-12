# Phase 61 Plan 117: Audit 5, lot C (workflow, motion residue and performance) Summary

**Three workflow findings, the reduced-motion residue on Location, four performance findings and one splash defect, in ten commits. Each has a behaviour or browser test that was seen red without the fix. P5-05 is only partly done (the warmed copy still lives ten seconds) and three medium motion findings are left for lot D.**

Owner decision D56 (treat all audit-5 findings, in lots). This is the third lot. There was no PLAN.md: the orchestrator's brief was the plan. The branch was two commits behind `origin/main`; it was merged first (clean, no conflict, `render_baseline.json` untouched by the merge).

## What is fixed, per finding

| Id | Fix | Commit |
|----|-----|--------|
| W5-03 | Cancel after an airport picked in place on a page that opened without a pin: the pin and its readout go, the "tap the map" hint is back, the nearest-airport offer is hidden and the map returns to the view it opened with. The address was already restored. | `e12fcc1d` |
| A5-03 residue, A5-11 residue, A5-19 | On a wide screen the loading state takes the map layout's page box and app bar margin from the first paint, so nothing moves when the map takes over. With reduced motion the map library's tile fade is off and a tile's class change starts no transition. | `6a33dbb3` |
| W5-07 | A list request that gets no answer (offline) no longer falls back to a navigation. The page stays, an error toast in the page's alert region says the list could not be updated (EN/FR), the chips and the sort go back to what the list shows, Load more is ready for another try, and the toast goes with the next answer. An HTTP refusal still falls back to the plain navigation. Flights and Airlines. | `4e03518b` |
| W5-05 | A refused POST goes to `/login?next=<the form's page>&expired=1`, with a stale session cookie or none. The page is the request's same-host Referer, checked like any `next`. `POST /logout` without a session stays a plain `/login`. | `66cdadf4` |
| P5-04 | Flights and the Airlines collection read one cached fold of the history (`history_query.folded_history`). Flights applies the owner's airline names and its scan bound on top; the collection reads it as is. | `14a98d2e` |
| P5-03, P5-06 (Flights) | `GET /flights?part=new&more=N` answers the flights of the last Load more step only; `?part=list` answers the list without the page around it. `list-filter.js` asks for those; the address bar, the no-script links and a reload use the plain addresses. | `156c5d50` |
| P5-06 (Airlines) | Each card carries its place in the four orders (`data-sort-rank`, computed by the server over the whole collection). The sort moves the cards on the page: no request. The order equals the server's for the same address; without scripts the form is submitted as before. | `36d53128` |
| P5-05 (part) | The idle warm-up runs on a new page view only: not after Back, Forward, a reload or a back/forward-cache restore. A link is still warmed on touch, hover and focus. | `a1052503` |
| A5-10 (part) | The splash percentage never goes below zero or backwards: a first frame stamped before the script's clock counts as no time and the shown share is kept within 0 and 1. | `33864e5a` |
| W5-07 (catalogue) | The Components page shows the no-connection notice in its Messages family (EN/FR); the helper that renders the hidden template is catalogued. | `4b57593e` |

## Numbers before and after

Measured here with copies of the audit's scripts against a server booted on the tree before and after each change (18,000 stored events; phone profile = 390x844, CPU x4, Fast 4G).

| Finding | Metric | Before | After |
|---------|--------|--------|-------|
| A5-03 / A5-19 | Location at 1280, cumulative layout shift (both motion settings) | 0.02 | 0 |
| A5-11 | Transitions started by a Location load at 1280 under reduced motion | 464 (420 tile opacity, 34 visibility) | 14 |
| P5-04 | Server CPU, four different history pages at once after a new flight (median of 8) | 890 ms (850-1090) | 260 ms (250-330) |
| P5-04 | Same four pages one after another (median of 4) | 310 ms | 240 ms |
| P5-04 | Four identical Flights requests at once | 240 ms | 230 ms |
| P5-03 | HTML for ten Load more steps | 6.28 MB (215 KB to 1.04 MB per step) | 0.95 MB (95 KB per step) |
| P5-03 | Tap to cards, steps 1 to 10 | 510 to 1337 ms | 287 to 390 ms |
| P5-03 | Longest task per step | up to 196 ms | up to 82 ms |
| P5-06 | Flights chip: bytes, tap to list | 123 KB, 271-375 ms | 96 KB, 253-338 ms |
| P5-06 | Airlines sort: requests | 35 requests, 547 KB (audit figure) | 0 (asserted by the browser test) |
| P5-05 | Warm-up traffic over one session (Home, Flights, Back, Forward, Home, Airlines, Back) | 14 requests, 1.32 MB raw | 8 requests, 0.74 MB raw |

The DOM after ten Load more steps is unchanged (18,031 nodes for 550 cards): both representations are still in the page.

## Tests added or changed

New:

- `companion/test_browser_place_boot.py`: Cancel after a pick on a page opened without a pin, at 390 and 1280 (pin, readout, hint, address, map back on the frame's airport, My position offers nothing about the discarded airport).
- `companion/test_browser_page_opening.py`: Location at 1280 reports no layout shift with and without reduced motion; no transition runs on a map tile under reduced motion.
- `companion/test_browser_flights_search_more.py`: offline search (EN/FR), offline Load more, offline sort; Load more downloads only the next flights (390 and 1280, no repeated id, one day group); a filter change downloads the list alone and the address never carries `part=`.
- `companion/test_browser_airline_collection.py`: an offline show chip; the sort without any request, in EN and FR, with the four orders compared to the server's.
- `companion/test_refused_post_sign_in.py`: the refused POST over HTTP (settings, quick switches, invite; no cookie and stale cookie), a query kept, nine addresses that are never carried, another host with the same path, an escaped line break, the unchanged GET.
- `companion/test_browser_save_bar.py`: Save on Style after the session cookie is gone lands on sign-in with Style as the way back.
- `companion/test_history_shared_fold.py`: one fold for Flights and the collection, one fold for four concurrent readers after a new flight, each page still reads what it read, the scan bound applies to Flights alone.
- `companion/test_flights_fragment.py`: the two fragments over HTTP (same flights as the page, no shell, the Load more block, unique group ids, constant weight per step, refused without a session or for a stranger).
- `companion/test_browser_navigation_assist.py`: no idle warm-up after Back, Forward or a reload; intent still warms.
- `companion/test_browser_splash.py`: the percentage with an early first frame, with and without reduced motion.

Updated in place because their subject changed:

- `test_companion_app_04.py`: three reduced-motion blocks in the stylesheet (was two); an unauthenticated quick-switch POST answers `/login?expired=1`.
- `test_companion_app_02.py`, `test_companion_app_04b.py`, `test_companion_app_05.py`: an unauthenticated POST answers `/login?expired=1` (`POST /logout` still `/login`).
- `test_access_matrix.py`, `test_route_table.py`: the same answer in the policy matrix and the route table.

## Tests run

- Before each commit: ruff, mypy, `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`, `stub-server/test_phase47_freeze.py`, the render snapshot (`--write`), `test_render_baseline.py`, `test_sign_in_surfaces.py`, `test_suite_guards.py`, `test_i18n.py`, and the test files of the touched areas (the Location browser files, every test file that mentions the login route, the Flights and list-filter files, the history and collection files, the prefetch and splash files). Each new browser test was run in four parallel processes without a failure.
- After the last code commit (`4b57593e`): every non-browser test of `companion`, plus `test-support` and `stub-server`, `-n 8`: 7550 passed, 4 skipped. The same run one commit earlier had one failure (the Components catalogue test, see Deviations). The browser files of the touched areas (Location, page opening, Flights, Airlines collection, Save bar, navigation assist, splash, page restore, live motion, the overhaul sweep, Users, the quick-win checks), `-n 6`: 1280 passed.
- The four skips need a non-root user (`test_companion_app_01.py:664` and `:704`, `test_freshness_token.py:348`, `stub-server/test_byos_hardening.py:528`); they cover file permission bits, which this plan does not touch.
- Not run: the browser files of untouched areas and `./scripts/run-all-tests.sh` (coverage gate), per the test cadence.

## What falls short

- **P5-05: the warmed copy still lives ten seconds, and a new page view still downloads its two likeliest destinations** (138 to 220 KB raw each time). The audit's main point (a tap 14 s after load fetches the page again) is not addressed. Its two options are a lifetime of 45 s, which shows pages up to 45 s old before the refresh loop's next tick, or dropping the idle warm-up, which reverses the earlier decision to warm when idle. That is a choice between freshness and speed, not a small fix.
- **P5-03: the DOM still grows** (18,031 nodes at 550 cards) because cards and table rows are both in the page. Scroll cost at 550 cards was not re-measured and is presumably unchanged. Sending only the representation the viewport shows would halve it but leaves the other one stale after a resize across 960px.
- **P5-06 (Flights): a chip or sort still downloads 96 KB** (both representations of 50 flights). The tap-to-list time barely moved (about 20 ms).
- **P5-04: a boundary case differs.** With more stored events than the scan bound (20,000), a kept flight at the bound may now take its picture name from a duplicate just past it. Below the bound nothing changes. `server/history_db.py` gained one public helper (`override_airline_name`), extracted from `recent_runway_events` without changing what it returns.
- **W5-05 relies on the Referer.** A browser or proxy that strips it gets `/login?expired=1` (the notice, no way back). The script-driven quick switches were already handled by the session guard. The notice also shows for someone who posts a form after signing out in another tab on purpose.
- **W5-07: the typed search text is kept, but the list is not filtered offline.** The audit's other option (filter the rows already loaded) was not taken. The toast can cover the Load more link on a phone until it is dismissed.
- **W5-03: only the in-place pick path is covered.** A page opened on carried values (`?airport=...`) still uses the Save bar's own Cancel link, as before.
- **A5-10: only the negative percentage is fixed.** The duration (1.96 to 2.39 s visible) and the main-thread outline and opening animations are untouched.
- **A5-04, A5-08, A5-09 (medium) are not addressed.** Each needs one rule decided first: how a strip's thumb crosses a page change, whether a page reached through a view transition also plays its entrance, and which blocks take the entrance on every page.
- **X01 (high, invisible "Add your frame" text) was already fixed on the branch** before this lot (the primary rule sits after the base rule in `style-admin.css`); nothing was changed here and no contrast test was added.
- Low findings of the four files are untouched.

## Deviations

- **Commit trailer.** The executor rules ask for a `Claude Sonnet 5.5` co-author line; the brief asks for the model doing the work, so the commits carry `Claude Fable 5.2`.
- **Step 5 is four commits, not one**, one per finding or pair of findings, so each could be measured alone.
- **Sign-out is exempt from W5-05.** The audit asked for every refused POST; `POST /logout` without a session keeps the plain `/login`, since nothing was lost.
- **The Components page was updated one commit late.** The offline notice is the catalogue's error toast in the existing alert region, so no new component was introduced, but its helper (`ui_filter.list_offline_template_html`) had to be catalogued. `test_components_page.py::test_every_public_component_helper_is_catalogued_or_exempt_with_a_reason` fails on the six commits from `4e03518b` to `33864e5a` and passes from `4b57593e` on: that file was not among the ones run before the W5-07 commit, and the final non-browser run caught it.
- **A third reduced-motion block** was added to the stylesheet (`style-place.css`, map tiles) and the pinned count updated.
- **A bulk clean-up of leftover test servers was refused by the permission system** after an interrupted run; the processes were left alone. A few idle `companion/app.py` processes and four measurement servers under the scratchpad may still be running.
- `companion/app.py` is at 1491 lines (ceiling 1500); `list-filter.js` 944, `place-map.js` 1222 (ceiling 1500).

## For the orchestrator

- **`b75c1817` ("record the Users table decision") landed on the branch during this lot** and is not part of it.
- **Design-system skill.** `sketch-findings-skypane` does not mention the offline toast for lists or the `data-sort-rank` contract; the skill file was not edited.
- **`part=` is a new query parameter on the Flights route** (`list`, `new`); any other value is the plain page. It is session-gated like the page and answered `no-store`.

## Self-Check: PASSED

All ten commits exist on `milestone/v1.2-phase-61-companion-ux`; `companion/pages/history_fragment.py`, `companion/test_flights_fragment.py`, `companion/test_history_shared_fold.py` and `companion/test_refused_post_sign_in.py` exist; nothing was pushed; the two untracked `.whl` files in the repo root were not touched; ROADMAP, STATE and REQUIREMENTS were not edited; no file under `hardware/` or `deploy/` was changed by these commits.
