---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 07
subsystem: ui
tags: [python, css, home-page, frame-state, i18n, airline-naming, time-value]

# Dependency graph
requires:
  - phase: 22-02
    provides: "companion/frame_state.py's resolve_state()/headline_template() and server/wake.py's next_wake_status() triple — the one frame-state resolution this plan's Frame tile now calls directly"
  - phase: 22-03
    provides: "health_page.compute_health_state()'s verdict-free pipeline_detail_html key — consumed here instead of re-embedding the whole pipeline_html fragment"
  - phase: 22-04
    provides: "the Frame strip (frame_strip_html()) and its .time-value/.time-value--primary CSS role — the strip this plan's Frame tile must never disagree with, and the role this plan adopts for its own clock text"
provides:
  - "Home's Frame tile resolved from the SAME frame_state.resolve_state()/wake.next_wake_status() call the strip makes, never disagreeing with it"
  - "Home's Flight-data tile rendering exactly one verdict (its own DATA_STATE_TEXT), with Health's verdict-free pipeline_detail_html beneath it"
  - "home_page.py's recent-flight airline names and thumbnail alt text routed through server.plane.render.display_airline_name(), matching Flights"
  - "home_page._recent_flight_time_html(): one line, .time-value clock + .cell-inline-sep + .time-value__age, no monospace"
  - "companion/static/style.css: .home-status-grid's explicit align-items: stretch, .recent-flight__time's white-space: nowrap, the real thumbnail's shared white-backing/hairline/radius treatment (img.recent-flight__thumb)"
affects: [22-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Recompute-not-reuse for the frame-state triple: _status_tiles_html() calls wake.next_wake_status()/frame_state.resolve_state() fresh from the SAME ctx fields render() already used for the strip, rather than reading a stored decision — the two can never disagree because neither computes anything the other does not (the same pattern 22-04's frame_strip_html() established)."
    - "A page-module-local mirror of a sibling page module's state->vocabulary mapping (_FRAME_STATE_TO_TILE_STATE, byte-identical in shape to health_page._FRAME_STATE_TO_DEVICE_STATE) — necessary because companion/pages/__init__.py forbids one page module importing another."
    - "detail_class as an optional third parameter on a shared tile-content builder (_tile_content_html), so a single call site can opt a specific detail into the shared .time-value CSS role without turning the builder's own escaped `detail` parameter into a second raw-markup injection point."
    - "Tag-qualified CSS selector (img.recent-flight__thumb) instead of a bare class selector, specifically to give a shared rule higher specificity than a sibling class also carried by a different-tagged element (the dashed placeholder <span>) that must NOT match it."

key-files:
  created: []
  modified:
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/i18n_fr/home.py
    - companion/test_view_pages.py

key-decisions:
  - "Home's Frame tile detail is a BARE clock (wrapped in a `.time-value`-classed span via _tile_content_html()'s new detail_class parameter), never the full frame_state.HEADLINE_HELD/HEADLINE_DUE/HEADLINE_LATE sentence — this mirrors health_page._device_section()'s own already-shipped shape (22-04-PLAN.md Task 3: verdict paragraph names the state, detail row is a bare clock) rather than the forward-looking assumption recorded in companion/test_i18n.py's _FRAME_STATE_AWAITING_CONSUMERS comment (which expected this plan to become HEADLINE_HELD's real consumer and delete that frozenset entry). Since Home does not render that template string, the frozenset is UNCHANGED by this plan — see Issues Encountered."
  - "The Frame tile's STATE_UNKNOWN fallback (no check-in recorded at all) still reads ctx['health_state']['device_state']/'device_detail_html' — the one case frame_state.py itself cannot resolve, and the one case the strip itself renders no update cell for, so there is nothing for this fallback to disagree with. Every OTHER state (due/held/late) is resolved fresh from wake.next_wake_status()/frame_state.resolve_state(), never from health_state."
  - "display_airline_name() aliases the airline text at every USER-VISIBLE call site (the flight one-liner, the thumbnail alt text) but never the illustration-key resolution (illustrations.normalise_airline_key() still reads the RAW stored airline) — server/plane/render.py's own _flight_line2_text() docstring is explicit that the alias 'never reaches illustration selection'; aliasing the key too would have been a second, silent behavioural change this plan's own scope does not call for."
  - "The Flight-data tile's DATA_STATE_TEXT dict gains a fourth 'off' key ('No detection yet', byte-identical to health_page.PIPELINE_STATE_TEXT['off']) — not explicitly named in the plan's own task text, but a direct consequence of consuming pipeline_state values that can now legitimately be 'off' (22-03-PLAN.md's never-ran state): without this addition, a never-ran pipeline would have rendered Home's own 'A little stale' wording, misreporting a frame that has simply never seen a flight as one that is falling behind — the exact class of cross-page disagreement this phase exists to remove (Rule 1/2)."
  - "The real recent-flight thumbnail joins the shared white-backing/hairline/radius rule via a TAG-QUALIFIED selector (img.recent-flight__thumb), not a bare class — the dashed placeholder <span> also carries the bare .recent-flight__thumb class for its own 40x40 sizing, and a bare-class shared selector would have tied in specificity with the placeholder's own dashed-border rule, letting source order (not intent) decide which border/background the placeholder actually shows."
  - "The placeholder's own dashed-border/canvas-fill values are reused BY VALUE from .airline-card__placeholder (the exact same var() tokens), never by SHARING that selector — companion/test_status_pages.py (owned by plan 22-06 this wave, not editable here) pins the literal standalone text '.airline-card__placeholder {' as a rule whose own body alone must carry all five of its declarations; sharing the selector broke that pinned check during verification and was reverted (see Issues Encountered)."

requirements-completed: [CFG-26]  # CFG-26 is served by exactly three plans per each plan's own frontmatter `requirements:` field (22-02, 22-04, 22-07) — this is the third and last, so it is now complete. CFG-30 is served by nine plans (D-07's B2-B18/X3-X9); NOT complete after this one alone.

# Metrics
duration: ~75min
completed: 2026-09-13
---

# Phase 22 Plan 07: Home reads one frame state, one pipeline detail and one airline name Summary

**Home's Frame tile now resolves from the exact same frame-state call the strip makes (never disagreeing with it, including the X2 nightly held regression), its Flight-data tile renders exactly one verdict with Health's verdict-free detail beneath it (B2), its recent-flight airline names and thumbnail alt text route through `display_airline_name()` to match Flights (X4), its tile caption is renamed away from the strip-heading collision (X4), and its recent-flight time now reads on one line out of the monospace family (B18) with a real thumbnail that matches its own placeholder in visual weight.**

## Performance

- **Duration:** ~75 min
- **Started:** 2026-09-13 (approx.)
- **Completed:** 2026-09-13
- **Tasks:** 2 completed
- **Files modified:** 4 (all pre-existing; no new files)

## Accomplishments

- **Task 1 (X2/B2/X4):** `_status_tiles_html()` calls `wake.next_wake_status()`/`companion.frame_state.resolve_state()` fresh from the SAME `ctx["last_checkin_ts"]`/`ctx["device_config"]`/`ctx["now"]` fields `render()` already used to build the Frame strip above it — the Frame tile can never disagree with the strip because neither computes its own independent decision. A new `_FRAME_STATE_TO_TILE_STATE` mapping (mirroring `health_page._FRAME_STATE_TO_DEVICE_STATE`'s own shape, since a page module may never import another) routes `STATE_DUE`/`STATE_HELD`/`STATE_LATE` to `"ok"`/`"off"`/`"warn"`; `FRAME_STATE_TEXT` gains a fourth `"off"` key reusing health_page's own `"Asleep for quiet hours"` wording verbatim. The tile's detail is now the bare next-wake clock (via `_tile_content_html()`'s new `detail_class="time-value"` parameter), the SAME `layout.local_clock_text()` output the strip renders — confirmed byte-equal by a new nightly-regression test. The one case `frame_state.py` cannot resolve (`STATE_UNKNOWN`, no check-in at all) falls back to the pre-existing `ctx["health_state"]["device_state"]`/`"device_detail_html"` path, the one case the strip itself renders no update cell for either.

  The Flight-data tile's detail now reads `health.get("pipeline_detail_html")` (health_page's verdict-free sibling of `pipeline_html`, 22-03) instead of the whole verdict-carrying fragment, so Home renders exactly one verdict per tile — never Health's own `PIPELINE_STATE_TEXT` sentence stacked underneath Home's own `DATA_STATE_TEXT` sentence. `DATA_STATE_TEXT` gained a matching fourth `"off"` key for the same reason `FRAME_STATE_TEXT` did.

  `_flight_secondary_text()` (feeding both the hero's flight one-liner and the recent-flights list) and `_recent_flight_thumb_html()`'s alt text now resolve the stored airline through `server.plane.render.display_airline_name()` — imported the exact way `history_page.py` already does (`from server.plane import render as panel_render`) — so an aliased carrier ("CCM Airlines") reads as "Air Corsica" on Home exactly as it does on Flights. The thumbnail's illustration-KEY resolution (`illustrations.normalise_airline_key()`) deliberately stays on the raw stored name, matching `render.py`'s own documented boundary that the alias "never reaches illustration selection".

  `home_page.FRAME_ROW_LABEL` is renamed `"Frame"` -> `"Check-ins"` (French: "Connexions") to resolve the X4 collision with the shared Frame strip's own `<h2>` heading (`companion/layout.py`'s `FRAME_STRIP_HEADING`, untouched — that file belongs to a sibling plan this wave) — exactly one element on a rendered Home page is now named "Frame".

- **Task 2 (B18/B2):** A new `home_page._recent_flight_time_html()` builds the recent-flight time as two sibling spans — the clock in `.time-value` (sans, tabular numerals — the C5 role 22-04 defined, never `--font-mono`) and the relative age in `.time-value__age` (the muted label voice C5 also defined), joined by the existing `.cell-inline-sep` middle dot (`history_page.py`'s own "Inline compact" convention, reused as a local literal since a page module may never import another) — replacing `layout.concise_timestamp_html()`'s single monospace span at this call site. `.recent-flight__time` gained `white-space: nowrap` in `companion/static/style.css` (its own `overflow-wrap: anywhere`, previously shared with `.recent-flight__detail` and capable of forcing a mid-word break even under `nowrap`, moved to `.recent-flight__detail` alone).

  `.home-status-grid` gained an explicit `align-items: stretch` declaration — already inherited from `.dashboard-grid` (a class this element also carries), restated here for the same "kept explicit, greppable" reason that rule's own comment gives. The real height-equalization on a phone (measured 112/112/131px by the audit) comes from Task 1's own B2 fix, which removed the Flight-data tile's extra re-embedded-verdict line — this declaration is the belt to that fix's own suspenders.

  The real recent-flight thumbnail (`img.recent-flight__thumb`) joins `.now-showing__image`/`.preview-frame__image`'s shared white-backing/hairline/radius rule — tag-qualified specifically so the dashed placeholder `<span>` (which also carries the bare `.recent-flight__thumb` class for its own 40x40 sizing) can never match it. The placeholder's own dashed-border/canvas-fill values are reused BY VALUE from `.airline-card__placeholder` (the exact same `var()` tokens, no new literal) rather than by sharing that selector — see Issues Encountered for why the selector-sharing approach was tried first and reverted.

## Task Commits

1. **Task 1: Home reads one frame state, one pipeline detail and one airline name** - `3f6bdde` (fix)
2. **Task 2: One line for the time, one height for the tiles, one weight for the thumbnails** - `75f2b36` (fix)

_Note: no TDD-mode gate applies to this plan (`tdd_mode: false`) — each task's own new checks were written and run before its own commit, not as a separate RED/GREEN pair._

## Files Created/Modified

- `companion/pages/home_page.py` — new imports (`companion.frame_state`, `server.plane.render as panel_render`); `FRAME_ROW_LABEL` renamed; `FRAME_STATE_TEXT`/`DATA_STATE_TEXT` widened with a fourth `"off"` key each; new `_FRAME_STATE_TO_TILE_STATE`; `_tile_content_html()`'s new `detail_class` parameter; `_flight_secondary_text()`/`_recent_flight_thumb_html()`'s alt text aliased through `display_airline_name()`; `_status_tiles_html()` rebuilt around `wake.next_wake_status()`/`frame_state.resolve_state()` and `pipeline_detail_html`; `render()`'s `next_wake_iso` migrated to the richer accessor (Task 1); new `_recent_flight_time_html()`, wired into `_recent_flights_html()` (Task 2)
- `companion/static/style.css` — `.home-status-grid` gains `align-items: stretch` (Task 2); `.recent-flight__detail`/`.recent-flight__time`'s shared `overflow-wrap: anywhere` narrowed to `.recent-flight__detail` alone, `.recent-flight__time` gains `white-space: nowrap` (Task 2); `img.recent-flight__thumb` joins the `.now-showing__image`/`.preview-frame__image` shared rule; `.recent-flight__thumb--placeholder`'s own dashed-border/canvas-fill rule kept standalone, reusing `.airline-card__placeholder`'s values (Task 2)
- `companion/i18n_fr/home.py` — new `"Check-ins"` -> `"Connexions"` entry; comments documenting the reuse of health.py's own `"Asleep for quiet hours"`/`"No detection yet"` entries for the new `"off"` keys, and that `"Frame"`/`"Cadre"` stays defined for the strip's own heading even though `home_page.py` no longer reads it directly
- `companion/test_view_pages.py` — 10 new checks across the two tasks (the nightly-held regression's strip/tile clock equality, the late-flip-together check, the Flight-data one-verdict/verdict-free-detail check, the airline-alias check, the exactly-one-"Frame" check; the one-line/no-mono time-cell check, the `.home-status-grid`/`.recent-flight__time`/thumbnail CSS scans, the single-`@supports` guard); one existing check (`_home_status_card_localises_real_health_state_timestamps_under_french`) retargeted in place (see Deviations). `EXPECTED_CHECK_COUNT`: 116 -> 121 (Task 1) -> 126 (Task 2), each re-derived by running the harness

## Decisions Made

See `key-decisions` in the frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Selector-sharing `.airline-card__placeholder` with `.recent-flight__thumb--placeholder` broke a pinned check in a file this plan may not edit**
- **Found during:** Task 2's own full-suite verification pass (`scripts/run-all-tests.sh`)
- **Issue:** The first implementation literally shared `.airline-card__placeholder`'s selector with `.recent-flight__thumb--placeholder` (a comma-separated list), splitting the rule into a shared partial plus an `.airline-card__placeholder`-only extension — mirroring `.now-showing__image`/`.preview-frame__image`'s own established "shared declarations only" pattern. This broke `companion/test_status_pages.py`'s own `_phase14_task2_new_css_selectors_exhaustive()` check, which pins the literal substring `".airline-card__placeholder {"` as a STANDALONE selector whose own rule body alone must carry all five of its declarations (border/border-radius/background/margin-bottom/display) — that file is owned by plan 22-06 this wave and may not be edited here.
- **Fix:** Reverted `.airline-card__placeholder`'s own rule to be byte-identical to its pre-plan form (a single, standalone selector, all five declarations). `.recent-flight__thumb--placeholder` instead gets its own separate rule declaring the same three values (`border: 1px dashed var(--color-border)`, `background: var(--color-canvas)`, plus `border-radius` from the shared 40x40-box rule it also joins) — reused BY VALUE, never by sharing the pinned selector.
- **Files modified:** `companion/static/style.css`, `companion/test_view_pages.py` (the corresponding new check was rewritten to assert value-equality rather than selector-sharing)
- **Verification:** `companion/test_status_pages.py` — the only remaining failure is the documented root-sandbox `anomaly_active()` case; `companion/test_view_pages.py` — 126/126.
- **Committed in:** `75f2b36` (Task 2)

**2. [Rule 1 - Bug] A bare-class shared white-backing selector would have tied in specificity with the placeholder's own dashed rule**
- **Found during:** Task 2, while implementing the real-thumbnail white-backing join
- **Issue:** The dashed placeholder `<span>` carries BOTH `recent-flight__thumb` (bare class, for its own 40x40 sizing) and `recent-flight__thumb--placeholder`. A bare `.recent-flight__thumb` addition to the shared white-backing rule would have matched the placeholder too (via its shared class), tying in specificity (0-1-0) with the dashed rule and letting SOURCE ORDER — not intent — decide which border/background the placeholder actually shows.
- **Fix:** Tag-qualified the addition (`img.recent-flight__thumb`, specificity 0-1-1) so it matches the real `<img>` only, never the placeholder `<span>` (a tag mismatch, not merely a losing specificity battle). The thumbnail's own dedicated 40x40-box rule was tag-qualified to match (`img.recent-flight__thumb, .recent-flight__thumb--placeholder { ... }`) so it still overrides the shared rule's `width:100%/height:auto` for the real image by equal-specificity source order.
- **Files modified:** `companion/static/style.css`
- **Verification:** Manual render inspection of both the real-thumbnail and placeholder markup against the resulting cascade; `companion/test_view_pages.py`'s new CSS-scan checks.
- **Committed in:** `75f2b36` (Task 2)

**3. [Rule 1 - Bug] `_home_status_card_localises_real_health_state_timestamps_under_french` (a pre-existing pinned check) asserted the exact multi-clause-join behaviour Task 1's own B2 fix removes**
- **Found during:** Task 1's own full-suite verification pass
- **Issue:** This existing check asserted the Flight-data row's detail joined 2+ clauses with `" · "` — exercising the OLD `pipeline_html` re-embedding this plan's own B2 fix removes. Once Home reads `pipeline_detail_html` (a single, verdict-free clause, never three), the assertion's own premise no longer holds — a real re-derivation of what the fixed code renders (confirmed directly: 0 occurrences of `" · "` in that row after the fix), not a criterion that "evaluated differently than predicted" by any acceptance criterion this plan's own task text stated.
- **Fix:** Retargeted the assertion to require ZERO `" · "` occurrences (the correct post-fix shape) and added a companion assertion that none of Health's own `PIPELINE_STATE_TEXT` verdict wording appears inside the row (the actual B2 acceptance this check now pins).
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** `companion/test_view_pages.py` — 121/121 (Task 1), 126/126 (Task 2).
- **Committed in:** `3f6bdde` (Task 1)

---

**Total deviations:** 3 auto-fixed (2 CSS specificity/file-ownership corrections discovered during Task 2's own verification, 1 pre-existing test retarget whose premise Task 1's own fix directly invalidates). No scope creep; no architectural changes; no file outside this plan's `files_modified` was edited.

## Issues Encountered

**`companion/test_i18n.py`'s `_FRAME_STATE_AWAITING_CONSUMERS` — deliberately UNCHANGED, and why (critical constraint 8).** That frozenset's own comment names this plan ("Home's own tile (22-07)") as `frame_state.HEADLINE_HELD`'s ("Next wake around %s · quiet hours") expected real consumer, instructing removal of the key (and the frozenset entirely, once empty) once wired. This plan's Frame tile deliberately does NOT render that template sentence — it mirrors `health_page._device_section()`'s own already-shipped shape instead (a state-naming verdict paragraph plus a BARE clock detail, no "Next wake around... quiet hours" prose), which is the established sibling precedent from 22-04-PLAN.md Task 3, and is what the plan's own truths require literally ("the same clock time and the same state", not "the same sentence"). Since no `i18n.t(HEADLINE_HELD-equivalent)` call site exists in `home_page.py`, this plan is not `HEADLINE_HELD`'s consumer, and `_FRAME_STATE_AWAITING_CONSUMERS` is left exactly as it was — `companion/test_i18n.py` still exits 0 (22/22), confirming no orphaned-translation regression. This is flagged here per critical constraint 8's own instruction to record the observation, not silently proceed.

**Acceptance criterion that evaluated as a trivial pass, not a real fix (critical constraint 5).** `grep -c 'row\["airline"\]' companion/pages/home_page.py` outputs `0` both BEFORE and AFTER this plan's edits — the source never used bracket-notation `row["airline"]` at all (it used `.get("airline")`, which the grep pattern does not match). This criterion is satisfied trivially regardless of whether the real fix (routing the value through `display_airline_name()`) was applied. The real fix is independently verified by the dedicated `_home_recent_flights_use_display_airline_name_matching_flights` behavioural check (seeding "CCM Airlines", asserting "Air Corsica" renders and the raw string does not) and by direct source inspection (`.get("airline")` is now wrapped in `panel_render.display_airline_name(...)`). No code or criterion was altered to compensate — recorded here as instructed rather than silently treated as confirmation of the fix.

**Every other acceptance criterion evaluated exactly as the plan predicted**, confirmed by running each command literally:
- `grep -c "pipeline_detail_html" companion/pages/home_page.py` -> `2`. Confirmed.
- A held fixture (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris) renders zero `dot--warn`/`dot--error`/`stat-tile--warn` tokens anywhere on the page, with `battery_state`/`pipeline_state` pinned `"ok"` in the fixture so the scan is unambiguously about the Frame signal. Confirmed.
- The strip's and the tile's clock strings are equal for that same fixture (`re.search` against both `.time-value.time-value--primary` and bare `.time-value` spans). Confirmed byte-equal (`"07:00"`).
- `companion/test_view_pages.py` reports M/M at each new pin (121/121, then 126/126); `companion/test_i18n.py` exits 0 (22/22). Confirmed.
- `ruff check .` clean at every commit boundary. Confirmed.
- `grep -c '@supports selector(:has(\*)) {' companion/static/style.css` -> `1`, unchanged. Confirmed.
- The recent-flight time cell markup contains no monospace class and carries the nowrap pair. Confirmed by direct render inspection and by the new pinned check.
- `.home-status-grid` declares `align-items: stretch`. Confirmed.
- `companion/test_config_page.py` still reports M/M (223/223) — the `:has()` gate untouched, this plan never edits that file.
- `scripts/run-all-tests.sh` shows no new failure and coverage stays at or above 83 (93% total). Confirmed at both task boundaries.

## Root-sandbox Failure Check (Critical Constraint 6/7)

Ran `PYTHON=.../python bash scripts/run-all-tests.sh` after both commits: exactly 3 harnesses fail (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`), and every failing check's own name/message was inspected directly — all match the documented read-only-directory root-sandbox reproduction cases (`ADD_FAILED`/`manual_save_failed`/`manual_delete_failed` expecting a write failure that cannot trip as root, and `test_status_pages.py`'s own `anomaly_active()` case). None of these three harnesses were touched by this plan's own changes. No new failure was introduced or masked by either task's commit.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None — every consumer this plan wires (`frame_state.resolve_state()`, `pipeline_detail_html`, `display_airline_name()`) reads a real, already-computed value; nothing renders a hardcoded placeholder.

## Threat Flags

None — this plan introduces no new network endpoint, auth path, file-access pattern, or schema change. The two mitigations named in the plan's own threat register (`display_airline_name()`'s output still crossing `escape_html()` at its interpolation site; Home deriving nothing for its own frame state, only rendering the shared resolution) are both confirmed in the implementation above.

## Next Phase Readiness

- **CFG-26 is now complete.** Per each contributing plan's own frontmatter `requirements:` field, exactly three plans serve it: 22-02 (`[CFG-26]`), 22-04 (`[CFG-26, CFG-30, CFG-31]`), and this plan, 22-07 (`[CFG-26, CFG-30]`) — all three are now landed. `REQUIREMENTS.md` is updated to check off CFG-26 and its traceability row.
- **CFG-30 remains open** (served by nine plans total: B2-B18/X3-X9) — this plan closes its B2 (Home half)/B18/X4 sub-items only; the rest are other plans' work in this same phase.
- Home's Frame tile, Flight-data tile, airline naming and recent-flight time are now settled surfaces for the phase-closing sweep (plan 22-16): the `<human-check>` items this plan's own `<verification>` block names (three equal-height tiles on a 390px phone, one-line recent-flight time, matching airline names between Home and Flights) are ready for that visual pass.
- The hero redesign, the day timeline, the countdown and the self-refresh remain untouched and out of scope (D1/D4/D13, Phase 23) — `_hero_figure_html()`'s own composition, element order and picture are byte-identical to before this plan, confirmed by the pre-existing `_hero_figure_precedes_status_card_with_flight_one_liner_when_known` check passing unmodified.
- No blockers for the rest of Phase 22's wave-4 plans or the phase-closing wave.

---
*Phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co*
*Completed: 2026-09-13*

## Self-Check: PASSED

- FOUND: `.planning/phases/22-companion-audit-round-4-fix-the-blocking-display-save-bar-co/22-07-SUMMARY.md`
- FOUND: commit `3f6bdde` (Task 1)
- FOUND: commit `75f2b36` (Task 2)
