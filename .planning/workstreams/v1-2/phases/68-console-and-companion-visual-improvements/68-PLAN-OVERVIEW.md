# Phase 68: plan overview, waves and coverage

Requirement for every plan: CON-01. Source of truth for scope: `68-CONTEXT.md` (D-01 to D-32), `68-WALKTHROUGH.md` (R01 to R36), `68-CANDIDATE-ITEMS.md` (D-15, D-26, D-27). The list is closed; no plan adds anything to it. R12 = D-06 and R15 = D-04.

## Process rules that apply to every plan

- **Mockup first (D-17).** Every visual change has an HTML mockup in this directory (`68-MOCKUP-<name>.html`) approved by the owner at a `checkpoint:human-verify` task (mockup plans are `autonomous: false`). The owner's decisions are recorded in an `OWNER-APPROVED` comment block at the top of that mockup file; build plans read it. This is an explicit owner rule and overrides the config default `workflow.human_verify_mode=end-of-phase` for mockup approval only; every other check in the phase is automated, and the end-of-phase owner validation is plan 32.
- **No code is written by a build plan before its mockup plan is approved** (`depends_on` carries the mockup plan).
- **Wave rule (shared files).** `style.css`, `ui_shell.py`, `ui_nav.py`, `ui_modal.py`, `i18n_fr/nav.py`, `style-admin.css`, `style-airlines.css`, `history_db.py`, `health_page.py`, `fleet_page.py` and `companion/testdata/render_baseline.json` each have one owner per wave. Plans in the same wave have disjoint `files_modified`; shared files run sequentially in later waves.
- **Baseline.** Only one plan regenerates `companion/testdata/render_baseline.json` per wave end with `python test-support/companion_render_snapshot.py --write`. Wave 2 (parallel build) plans do NOT write it; they run `pytest companion/test_render_baseline.py` and expect a diff only on their own pages. Plan 22 (wave 4) regenerates it once for waves 2 and 3 (plan 13 is in wave 3 because it builds on plan 33) and derives the allowed list of changed captures from the summaries of plans 13 to 21, 33 and 36. Every later build plan is alone in its wave and regenerates it as its last task, with two exceptions: plan 26 does not write it and plan 35 regenerates it once for both (the `/fleet` captures differ between the two plans on purpose), and plans 24 and 34 each regenerate it. Review the diff: only the expected pages change.
- **Golden files.** `companion/testdata/update_page_one_type_golden.json` is regenerated only by plan 16. `RETIRED_GOLDEN_SHA256` in `server/test_pairing_image.py` is changed only by plan 18, on purpose. The legacy render golden hashes (`server/test_golden_render.py`, `server/test_golden_giant_render.py` with `server/fixtures/golden/giant_render_baseline.json`, including `status_retired_portrait` and `status_retired_landscape`) and `stub-server/test_phase47_freeze.py` are never edited and must stay green. Consequently `status.build_status("retired")` in `server/plane/render/giant/status.py` stays byte-identical (its tables `RETIRED_BODY_LINES`, `_LINES`, `_BODIES` are not changed): plan 18 adds a separate builder (`build_retired(size, reset_hint)`) used only by `pairing_image.render_retired_image`.
- **Human gates (intentional Nyquist exception).** The `checkpoint:decision` and `checkpoint:human-verify` tasks of plans 02 to 12 and 32 carry `<automated>MISSING — human decision: ...</automated>` verify lines on purpose: the owner's answer is the evidence and there is nothing to run. Their automated checks sit in the neighbouring `auto` tasks.
- **Plan size.** Plans 13, 24, 26 and 30 were split (into 33 + 13, 24 + 34, 26 + 35 and 36 + 30) to stay within the context budget. Plans 14, 17, 28 and 29 stay whole, each with a sizing note in its objective.
- **Gates (run by every build plan before it finishes).** `SKYPANE_REQUIRE_BROWSER=1 pytest <touched test files> companion/test_i18n.py companion/test_structure_guards.py companion/test_suite_guards.py -q`; `python scripts/check_function_size.py`; `python scripts/check_comment_history.py check`; `ruff check .`; mypy on the module list in `pyproject.toml`. Size limits: `companion/app.py` 1500 lines (it is at 1493: do not edit it), JS files 1500 lines, functions 80 lines.
- **i18n.** Every string has English next to the code and French in the matching `companion/i18n_fr/` module (sentence case, U+2019, U+00A0 before `:;?!`); removed strings leave no orphan French id; keep ids stable when only the text changes.
- **Tests.** Behaviour over source: assert served HTML (`parse_html`), computed style or geometry in a browser; never read source files or `.planning/` (`companion/test_suite_guards.py`). Browser checks at 360 px and 1280 px, English and French, light and dark where the change is visual; no horizontal overflow; 44 px hit areas; accessible names.
- **Code comments** carry no plan, phase, decision or requirement IDs (`scripts/check_comment_history.py`).
- **Phase 64 ownership.** Several files below were last changed by Phase 64 work, all merged on main. Each build plan states this in its first task and re-checks `gh api repos/{owner}/{repo}/pulls?state=open` for open PRs on those files before editing.
- **Production deploys are approved by the owner only; executors never approve or trigger one.**

## Waves

| Wave | Plans | Notes |
|------|-------|-------|
| 0 | 01 | Housekeeping: merge main, D-07 harness, baseline rule, skill "as of". |
| 1 | 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12 | Mockups and decisions, parallel, one owner checkpoint each (`autonomous: false`). 12 also holds the D-31 sizing checkpoint. |
| 2 | 14, 15, 16, 17, 18, 19, 20, 21, 33, 36 | Build, parallel, disjoint files. No baseline write. 33 = Home read queries and stats/strip builders; 36 = Style preview reload fix (D-07). |
| 3 | 13 | Home page assembly (uses plan 33). No baseline write. |
| 4 | 22 | Baseline gate for waves 2 and 3 (regenerate once, full suite). |
| 5 | 23 | Airlines page: known-by-name rows and user Airlines (`style-airlines.css`). |
| 6 | 24 | Navigation order, naming, console label (`ui_nav.py`, `i18n_fr/nav.py`). |
| 7 | 34 | More sheet, grab handle, active tab tap, Safari check (`style.css`, `ui_shell.py`). |
| 8 | 25 | Frame notice banner and Back to Fleet target (`ui_shell.py`, `style.css`). |
| 9 | 26 | Frame list and frame switch (`style-admin.css`, `fleet_page.py`). No baseline write. |
| 10 | 35 | Frame page sections and Access text (`style-admin.css`, `fleet_page.py`, `health_page.py`); regenerates the baseline for 26 and 35. |
| 11 | 27 | Pairing wording and re-activation message (`fleet_page.py`, pairing modules). |
| 12 | 28 | Users dialogs and Auth0 invitation wiring (`ui_modal.py`, `users_page.py`). |
| 13 | 29 | Account, sign-in, credits entry, 404 (`style.css`). |
| 14 | 30 | Style page: leave dialog and yellow contrast (`style.css`). |
| 15 | 31 | Route sources (D-26, D-27) per the owner's sizing decision (`history_db.py`, `health_page.py`). |
| 16 | 32 | Final: coverage audit, ROADMAP check, skill update, full suite, draft PR, owner validation in EN and FR. |

Plan list (36 plans, 17 waves 0 to 16): 01 housekeeping; 02 frame list and frame page mockup; 03 frame banner mockup; 04 Update panel mockup; 05 Users dialogs and invitation mockup; 06 Editor mockup; 07 Account, sign-in, 404 mockup; 08 Flights, user Airlines, Home title row mockup; 09 Location and Style mockup; 10 shell, naming, Audit mockup; 11 retired frame screens and pairing messages mockup; 12 route sources sizing and mockup; 13 Home page assembly; 14 Editor; 15 Location; 16 Update; 17 Locations removal; 18 retired screen on the frame; 19 Auth0 Management client; 20 Flights; 21 Audit; 22 baseline gate; 23 Airlines known rows; 24 Navigation order and naming; 25 Frame banner; 26 Frame list and switch; 27 Pairing messages; 28 Users and invitation; 29 Account and 404; 30 Style leave dialog and yellow contrast; 31 Route sources; 32 final; 33 Home queries, statistics and strip builders; 34 More sheet and shell polish; 35 Frame page sections and Access text; 36 Style preview reload fix.

## PLAN-COVERAGE (all 49 items; R12 = D-06, R15 = D-04)

M = mockup/decision plan, B = build plan.

| Item | Mockup (wave 1) | Build | Notes |
|------|-----------------|-------|-------|
| D-03 Home mockup | approved (`68-HOME-MOCKUP.html`) | 33 (queries, builders), 13 (page) | Online, sleeping, offline; new read queries in `history_db.py` (33). |
| D-04 / R15 retired frame on another frame's page | 02 | 26 | List and switch; baseline in 35. |
| D-05 Flights header search wrap | 08 | 20 | |
| D-06 / R12 Back to Fleet returns to the frame | 03 | 25 | |
| D-07 Style tab reloads previews | harness in 01 | 36 | Investigation first (01), fix in 36 (wave 2). |
| D-08 Flights vs Flight history naming | 10 | 24 | Owner chooses EN and FR words. |
| D-09 More sheet width on tablet | 10 | 34 | |
| D-10 Yellow Full/Soft-stripe contrast | 09 | 30 | Real-device check in 32. |
| D-11 More sheet grab handle | 10 | 34 | |
| D-12 44 px quiet-hours link | 08 (Home pill) | 13 | |
| D-13 Tapping the active tab | 10 | 34 | |
| D-14 hand-built `banner__pill` | none (no visual change) | 13, 15, 16, 23, 26, 28, 29, 31, 34, 35; verified in 32 | Each plan converts the files it owns. |
| D-15 Airlines known by name | 06 | 23 | |
| R01 Home "i" and pencil on phone | 08 | 13 | |
| R02 Recent flights preview | approved Home mockup | 33 (builder), 13 (page) | |
| R03 Flights row content | 08 | 20 | |
| R04 Airlines rarity visibility and nav order | 08 (rarity), 10 (order) | 23 (rarity), 24 (order) | |
| R05 Airlines detail sheet | 08 | 23 | |
| R06 Style leave dialog | 09 | 30 | |
| R07 Location "position found" text | 09 | 15 | |
| R08 Location dark map | 09 | 15 | |
| R09 Location icon buttons | 09 | 15 | |
| R10 More sheet in Safari | 10 (checklist) | 34, 32 | Verification item; code only if a cause is found. |
| R11 Frame page phone and desktop rework | 02 | 35 | |
| R13 Frame selector | 02 | 26 | |
| R14 Access text | 02 | 35 | |
| R16 Device and version panel | 04 | 16 | Golden JSON regenerated in 16. |
| R17 Install/Revert confirm page | 04 | 16 | |
| R18 Pair refusal wording | 11 | 27 | |
| R19 Account manage access | 07 | 29 | |
| R20 Account battery as dot | 07 | 29 | |
| R21 Account hardware hidden for admin | 07 | 29 | |
| R22 Sign-in first-visit block | 07 | 29 | |
| R23 Credits reachable when signed in | 07 | 29 | |
| R24 404 page | 07 | 29 | |
| R25 Users dialogs | 05 | 28 | |
| R26 Invitation and first sign-in (D-22, D-28 option B) | 05 | 19 (client), 28 (wiring) | Threat model in 19 and 28. |
| R27 Editor Complete/Edit/Rename | 06 | 14 | |
| R28 Remove "Ignore" | 06 | 14 | |
| R29 Editor rows, "..." menu, filter, expand speed | 06 | 14 | "Marchand" word asked at 06. |
| R30 Customise / Change illustration / Revert | 06 | 14 | Policy wording asked at 06. |
| R31 Editor desktop unknown rows, overlap | 06 | 14 | |
| R32 / D-29 Locations removal | none (removal) | 17 | Matrix change limited to this; plan 17 also removes the `nav.locations` id (`LOCATIONS_LABEL` and `i18n_fr/nav.py`). |
| R33 Audit phone navigation | 10 | 21 | |
| R34 / D-30 "Mes cadres" / "My frames" | 10 | 24 | Label fixed by D-30. |
| R35 / D-21 Foreign-frame marker | 03 | 25 | |
| R36 / D-24 re-activation message and pairing page | 11 | 27 | 24 h wake kept; no change to `server/pairing_code.py`. |
| R36 / D-25 retired screen on the frame | 11 | 18 | Both hardware types; cache invalidation; new `build_retired` builder, giant render manifest untouched. |
| D-26 Route sources comparison card | 12 | 31 | Sized first (D-31). |
| D-27 Route directories status | 12 | 31 | Sized first (D-31). |

Items D-01, D-02, D-16 to D-23 and D-28 to D-32 are process or decision records, honoured as stated in the plans.
