---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 03
subsystem: ui
tags: [i18n, value-controls, mutation-testing, playwright-browser-testing, python]

# Dependency graph
requires:
  - phase: 28-01
    provides: "companion/layout.py and companion/test_companion_app.py ownership for Wave 2 (icon-gear appended to ICON_IDS)"
  - phase: 28-02
    provides: "companion/static/style.css's button:not(.value-control__handle):active fix and companion/test_browser_ux.py ownership for Wave 2 (CFG-73 Bug B, the handle-collapse fix); this plan's own checks read from THAT file's already-widened EXPECTED_CHECK_COUNT baseline of 89"
provides:
  - "layout.DURATION_ATTRS/DURATION_*_TEXT — the duration ladder's four bucket wordings as translated, #-marked attributes, mirroring RELATIVE_PAST_*/RELATIVE_PAST_ATTRS"
  - "layout.VALUE_CONTROL_READOUT_FORMAT_ATTR — a readout-scoped clock-format signal, since readouts are resolved by field name, never by wrapper containment"
  - "quiet_dial_readout_html() emits data-value-readout-format=\"clock\" on both endpoint spans and all four DURATION_ATTRS (translated) on the duration span, replacing the deliberately-empty template — initial server-rendered caption stays byte-identical"
  - "value-controls.js: paintReadouts() paints clock-format readouts through numberToField()'s own zero-padded codec (minutesToClock(), extracted and shared) and computes a live duration from the CFG-62 pair seam's wrapped difference, worded from the server's own DURATION_ATTRS — no French, no second ladder, no copy of any kind"
  - "the caption decoder (_quiet_caption_minutes) rewritten to parse \"HH:MM\" tokens instead of bare digit runs, raising with the caption text quoted when the form is unparseable, rather than silently decoding the bug's own broken output as if it were correct"
affects: [companion-app-testing, companion-layout, value-controls]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A ticker-style translated-wordings-as-attributes seam (RELATIVE_QUANTITY_MARK/#) spent a SECOND time for a second ladder (duration_text()) rather than porting a ladder into JavaScript — the same mechanism relative-time.js already uses for its four bucket wordings, applied to a bare-length ladder instead of two tensed ones"
    - "A readout-scoped sibling of an existing wrapper-scoped attribute (VALUE_CONTROL_READOUT_FORMAT_ATTR beside VALUE_CONTROL_FORMAT_ATTR), reusing the SAME clock-format value rather than a second literal, because readouts are looked up by field name and cannot see the wrapper's own attributes"
    - "A codec's formatting body extracted into a shared helper (minutesToClock()) the moment it got a second caller, rather than a second six-line copy — CONTEXT.md names this explicitly as the risk to avoid"
    - "Mutation-tested against ALREADY-COMMITTED state only, reverted with git checkout-index -f -- — running a mutation against an uncommitted working-tree edit and then reverting with checkout-index silently discards the uncommitted edit too, since checkout-index restores from the INDEX, not from a stash; this plan's own Task 2 was lost once this way mid-execution and had to be reconstructed byte-for-byte before mutation testing could safely continue (see Deviations)"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/i18n_fr/display.py
    - companion/pages/config_page.py
    - companion/static/value-controls.js
    - companion/test_browser_ux.py
    - companion/test_companion_app.py
    - companion/test_config_page.py

key-decisions:
  - "The duration span's readout is still keyed data-value-readout=\"quiet_hours_start\" (unchanged from before this plan), and the client-side duration computation reads BOTH paired values off the CFG-62 pair seam (via the wrapper currently painting, never off the readout element itself, which is a SIBLING of the pair's shared ancestor div, not a descendant of it) rather than off the field the readout happens to be keyed to. This works for every interaction kind because value-controls.js's own notify() dispatches a bubbling change that the document-level listener resolves to a full repaintAll() (every wrapper repainted, not only the one that moved) — confirmed by reading the call sites rather than assumed; see 'which interaction kinds needed wiring' below"
  - "pairedDurationMinutes() reads each paired member's CURRENT VALUE via currentValue()/boundsFor() (the same 'read back off the native input, never a cached number' rule every other read in this file follows) rather than reconstructing the minute value from the pair seam's own published FRACTION — a float round-trip through a fraction was available (fraction * 1440) but the field read is both simpler and exact by construction, with no rounding tail to reason about"
  - "The duration span's own DURATION_ATTRS values are built as a joined string in a Python generator (config_page.py's new duration_attrs_html local) rather than one long %-format string with sixteen positional slots — the readability cost of an even longer format tuple was judged worse than a five-line loop, and the loop's own zip(layout.DURATION_ATTRS, _QUIET_DIAL_DURATION_TEXTS) makes the two tuples' shared ordering contract visible at the call site"

patterns-established:
  - "A client-side duration/length-of-time computation that must never invent language spends the SAME server-rendered-wordings-as-attributes seam a ticker already established, rather than a bespoke mechanism — the second (not the first) time this project has needed 'client substitutes a number into server-translated text with no ladder of its own,' which is what makes it a pattern rather than a one-off"

requirements-completed: [CFG-73]

# Metrics
duration: ~63min (20:30 start, including investigation, to 21:33 final commit)
completed: 2026-09-15
---

# Phase 28 Plan 03: Quiet-hours dial readout format — HH:MM + live duration (CFG-73 Bug A) Summary

**Both quiet-hours dial endpoints now paint as zero-padded HH:MM after every interaction (drag, keyboard, typed field, preset) and the duration reads a live, correctly-computed, correctly-worded phrase instead of going permanently blank — both fixed by handing the client the SAME translated wordings a ticker already uses (server-rendered `#`-marked attributes), never a second HH:MM converter or a second duration ladder in JavaScript.**

## Performance

- **Duration:** ~63 min (20:30 investigation start through 21:33 Task 3 commit)
- **Started:** 2026-09-15T20:30Z (approx, investigation preceded the first commit)
- **Task 1 commit:** 2026-09-15T20:40:26Z
- **Task 2 commit:** 2026-09-15T21:18:47Z
- **Task 3 commit:** 2026-09-15T21:33:45Z
- **Tasks:** 3/3 completed
- **Files modified:** 7

## Accomplishments

- `layout.py` gained `layout.DURATION_ATTRS` (four attribute names, s/m/h/d order) and `layout.DURATION_SECONDS_TEXT`/`_MINUTES_TEXT`/`_HOURS_TEXT`/`_DAYS_TEXT` (`"#s"`/`"#m"`/`"#h"`/`"#d"`) — the duration ladder's own client-side wordings, modelled directly on the `RELATIVE_PAST_*`/`RELATIVE_PAST_ATTRS` block immediately beside it, reusing `RELATIVE_QUANTITY_MARK` rather than a second mark constant. `companion/i18n_fr/display.py` gained the four French translations (`"# s"`/`"# min"`/`"# h"`/`"# j"`), preserving `duration_text()`'s own real U+00A0 between the number and the unit.
- `layout.py` also gained `VALUE_CONTROL_READOUT_FORMAT_ATTR` (`"data-value-readout-format"`) — a readout-scoped restatement of the wrapper's existing `VALUE_CONTROL_FORMAT_CLOCK` value, since a readout is resolved by field name via `document.querySelectorAll`, never by walking up to a containing wrapper.
- `quiet_dial_readout_html()` (`config_page.py`) now emits `data-value-readout-format="clock"` on both endpoint spans and all four `DURATION_ATTRS` (each `i18n.t()`-translated) on the duration span, in place of the deliberately-empty `data-value-readout-text=""` template. The docstring's original empty-template reasoning is kept fully legible, marked SUPERSEDED by this plan, with the replacement's own reasoning stated beside it. The server-rendered caption at rest is byte-identical to what shipped before this task (verified both by the pre-existing exact-text check and by a fresh render read directly).
- `value-controls.js`: `numberToField()`'s zero-padded formatting body was extracted into `minutesToClock(value)`, called by both `numberToField()` itself and the new clock-format readout branch inside `paintReadouts()` — one codec, not two. A new `pairedDurationMinutes(pairAncestor)` computes the window length as the wrapped difference `(end - start + MINUTES_PER_DAY) % MINUTES_PER_DAY` between the CFG-62 pair seam's two members (read via `currentValue()`, never a cached number or the painted fraction), and `paintDurationReadout()` selects the bucket with `_age_bucket()`'s own 60/3600/86400-second boundaries and substitutes the quantity into whichever `DURATION_ATTRS` wording the server rendered. `readoutQuantity()` itself is byte-identical (confirmed via `git diff`); every non-clock, non-duration readout in the app (the wake-interval one included) is painted exactly as before this plan.
- **All four interaction kinds already routed through `paintReadouts()` before this plan — no wiring was needed.** Confirmed by reading the call sites: drag and keyboard both go through `steer()` → `paint()` → `paintReadouts()` directly; a typed field edit and a preset click both reach `paintReadouts()` indirectly via `steer()`'s own `notify()`, which dispatches a bubbling `change` event that the document-level `change` listener (`onValueEvent`) resolves — since the event's target lacks `INPUT_ATTR` — to `repaintAll()`, which paints EVERY wrapper on the page, including the sibling wrapper the duration readout happens to be keyed to. This is also why the bug's own symptom ("480 → 1080 · ", both endpoints showing raw numbers) already updated both endpoints on any single-handle interaction before this plan — the same mechanism was already firing, painting the wrong thing.
- `_quiet_caption_minutes()` (`test_browser_ux.py`) rewritten: its old docstring/regex documented parsing raw digit runs as the CORRECT live-interaction reading — that was the bug, and it is kept fully legible below, marked SUPERSEDED. It now parses `"HH:MM"` tokens (`_CAPTION_TOKEN_RE`), keeps the same canonical `(start_minute, end_minute)` return so `_assert_surfaces_agree()` composes with it unchanged, and **raises** with the caption's actual text quoted when fewer than two tokens are found, rather than silently returning a plausible-looking wrong pair. `_assert_surfaces_agree`, `_quiet_arc_minutes` and `_fraction_pair_minutes` are confirmed untouched (`git diff` shows zero lines changed in any of the three).
- One new browser check, `_the_dial_caption_keeps_its_form_after_every_interaction_kind`: drives drag, keyboard step, typed field edit and preset click, in that order, on one page, in both shipped languages, and after EACH reads the caption's actual displayed text, asserting (i) the decoded endpoints match what the interaction requested, (ii) the duration segment is non-empty and equals the wrapped-difference computation worded from the page's own `layout.DURATION_ATTRS` attributes (read off the DOM, never a hardcoded `"h"`/`"min"` literal), and (iii) the caption's structural shape (a fingerprint with every `"HH:MM"` token and every digit replaced by a placeholder) matches the server-rendered reference captured before any interaction. The preset step (23:00→07:00) crosses midnight, so the wrapped-difference computation is genuinely exercised, not merely stated.
- One new source-level check, `_duration_wordings_equal_the_ladders_own_output` (`test_companion_app.py`): pins each `DURATION_*_TEXT` wording, filled with `_age_bucket()`'s own quantity, equal to `duration_text()`'s own return for a representative value in every bucket, in both languages — modelled directly on the existing `relative-time.js` wording-equality check — and pins all four `DURATION_ATTRS` present in `value-controls.js`'s own source.
- One new server-render check, `_the_quiet_dial_readout_carries_clock_format_and_duration_wordings_in_both_languages` (`test_config_page.py`): proves `quiet_dial_readout_html()`'s output carries the clock-format attribute exactly twice and a non-empty value for each of the four `DURATION_ATTRS` on the duration span, in both languages.
- `EXPECTED_CHECK_COUNT` re-derived by running, for every harness touched: `test_companion_app.py` 315→316 (314/316 pass, the 2 known WR-11 root-sandbox failures); `test_browser_ux.py` 89→90 (90/90 pass); `test_config_page.py` 263→264 (264/264 pass).
- Full suite: `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` → exactly the three known sandbox-baseline failures, by name: `server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — the same root-sandbox read-only-directory-simulation class 28-01-SUMMARY.md already documented, none touching any file this plan modified.

## Task Commits

Each task was committed atomically:

1. **Task 1: The server hands the client the ladder's own words and the readout's own format** - `61fa8a9` (feat)
2. **Task 2: paintReadouts() speaks HH:MM, and the pair speaks its own duration** - `16c2550` (feat)
3. **Task 3: The decoder stops documenting the bug, and one check reads the caption after each interaction kind** - `dbfaa0d` (test)

**Plan metadata:** (this commit, to follow) — STATE.md/ROADMAP.md are intentionally not touched by this worktree agent (orchestrator owns them after the wave).

## Files Created/Modified

- `companion/layout.py` — `DURATION_ATTRS`/`DURATION_SECONDS_TEXT`/`DURATION_MINUTES_TEXT`/`DURATION_HOURS_TEXT`/`DURATION_DAYS_TEXT` added adjacent to the `RELATIVE_*` block; `VALUE_CONTROL_READOUT_FORMAT_ATTR` added adjacent to the other `VALUE_CONTROL_READOUT_*` constants
- `companion/i18n_fr/display.py` — the four `"#s"`/`"#m"`/`"#h"`/`"#d"` French translations added beside the existing `"Quiet hours start"`/`"Quiet hours end"` entries
- `companion/pages/config_page.py` — `quiet_dial_readout_html()`'s duration span rewritten to carry the four `DURATION_ATTRS` (translated) instead of an empty template; both endpoint spans gained the clock-format attribute; the docstring's empty-template paragraph marked SUPERSEDED, original reasoning kept; a small module-level `_QUIET_DIAL_DURATION_TEXTS` tuple added to pair with `layout.DURATION_ATTRS`
- `companion/static/value-controls.js` — `numberToField()`'s formatting body extracted into `minutesToClock()`; `paintReadouts()` branches on a readout's own clock-format attribute and, for a readout carrying no `READOUT_TEXT_ATTR` at all, tries the new duration path (`paintDurationReadout()`/`pairedDurationMinutes()`) before giving up; four new module-level constants (`READOUT_FORMAT_ATTR`, `MINUTES_PER_DAY`, `SECONDS_PER_MINUTE`, `DURATION_ATTRS`, `DURATION_BOUNDARY_SECONDS`)
- `companion/test_browser_ux.py` — `_quiet_caption_minutes()` rewritten to parse `"HH:MM"` tokens (`_CAPTION_TOKEN_RE` replaces `_CAPTION_NUMBER_RE`); three new helpers (`_quiet_caption_shape`, `_quiet_duration_span_text`, `_expected_quiet_duration_text`); one new check (`_the_dial_caption_keeps_its_form_after_every_interaction_kind`); `EXPECTED_CHECK_COUNT` 89→90
- `companion/test_companion_app.py` — one new check (`_duration_wordings_equal_the_ladders_own_output`); `EXPECTED_CHECK_COUNT` 315→316
- `companion/test_config_page.py` — the pre-existing dial-readout server-render check adapted (Task 1, Rule 1) to the widened markup; one new check (`_the_quiet_dial_readout_carries_clock_format_and_duration_wordings_in_both_languages`); `EXPECTED_CHECK_COUNT` 263→264

## Decisions Made

See `key-decisions` in the frontmatter above for the three load-bearing ones (the duration readout's field-key vs. its actual data source; reading the paired value off the field rather than the published fraction; the Python-side loop over `zip()` rather than a longer format tuple).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The pre-existing dial-readout server-render check in `test_config_page.py` needed adapting to Task 1's own widened markup, inside Task 1's own commit**
- **Found during:** Task 1's own verification run (`companion/test_config_page.py` failed 262/263 immediately after the markup change)
- **Issue:** `_the_ring_draws_the_saved_window_from_the_emitted_attributes()` asserted the OLD shape verbatim — both endpoint spans with no format attribute, and the duration span carrying an EMPTY `data-value-readout-text=""` template. Task 1's own markup change (the readout-format attribute on both endpoints, the four `DURATION_ATTRS` replacing the empty template) is exactly the interface Task 1's own acceptance criteria required, so this was the existing check needing a mechanical regex update to the new attribute set, not a new check (Task 3 adds those, separately, later).
- **Fix:** The endpoint-span regex gained the format-attribute clause; the duration-span regex now matches the base attribute plus all four `DURATION_ATTRS` (order-tolerant via alternation, with an explicit per-attribute presence check afterward so a duplicate-and-miss cannot slip through a loose match).
- **Files modified:** `companion/test_config_page.py`
- **Verification:** Re-ran; 263/263 pass. Task 3 later added a further +1 check to this same file for the language-pair contract specifically (264/264).
- **Committed in:** `61fa8a9` (Task 1 commit)

**2. [Rule 1 - Bug] A comment I wrote in `layout.py` accidentally added a second `"clock"` string literal, tripping an acceptance criterion pinning that count unchanged**
- **Found during:** Task 1's own acceptance-criteria self-check (`grep -c '"clock"' companion/layout.py` read 2, not the required 1)
- **Issue:** A prose comment explaining why `VALUE_CONTROL_READOUT_FORMAT_ATTR` reuses the existing clock value quoted the word `"clock"` in quotes, which is indistinguishable from a second code-level literal by a bare grep — exactly the false positive the criterion exists to catch, applied to my own comment rather than to a real second literal.
- **Fix:** Reworded the comment to say "the existing clock-format value" without quoting the bare word.
- **Files modified:** `companion/layout.py`
- **Verification:** `grep -c '"clock"' companion/layout.py` reads 1, matching the pre-edit count exactly (confirmed via `git show HEAD:companion/layout.py`).
- **Committed in:** `61fa8a9` (Task 1 commit; fixed before commit)

**3. [Rule 1 - Bug] Three backtick characters in my own Task 2 comments tripped `value-controls.js`'s existing ES5-safety/no-template-literal scan**
- **Found during:** Task 2's own verification run (`companion/test_companion_app.py` failed 2 checks beyond the known WR-11 baseline: the ES5-safety scan and the served-body scan, both objecting to a literal backtick anywhere in the file)
- **Issue:** Three new comments referred to identifiers/expressions using backtick-quoting (a Markdown habit, not this file's own convention — every existing comment in the file refers to an identifier with bare or parenthesised text, never backticks), and the harness's own no-template-literal guard scans the WHOLE file text, including comments, on the reasonable theory that a backtick anywhere is either a template literal or a sign one is about to be added.
- **Fix:** Reworded the three comments to drop the backticks, matching the file's own existing convention.
- **Files modified:** `companion/static/value-controls.js`
- **Verification:** `grep -n '`' companion/static/value-controls.js` returns nothing; `test_companion_app.py` back to the 2-failure WR-11 baseline.
- **Committed in:** `16c2550` (Task 2 commit; fixed before commit)

### Process Incident (not a deviation from the plan's own instructions — a self-inflicted execution mistake, recorded per the plan's own "record it here" discipline)

**Mutation testing against an uncommitted file silently discarded real work, mid-Task-3.** While running M-A (Task 3's first mutation, against `value-controls.js`), the file had NOT yet been committed as Task 2 — the mutation was applied on top of the uncommitted Task 2 working-tree edit. Reverting with `git checkout-index -f -- companion/static/value-controls.js` (the plan's own mandated revert mechanism, never `git checkout --`) restored the file from the INDEX rather than from any working-tree snapshot — and since Task 2's edits had never been `git add`ed, the index still held the pre-Task-2 (Task 1-commit) content. The revert therefore correctly undid the M-A mutation AND silently discarded the entirety of Task 2's own legitimate work in the same stroke.

Caught immediately (`git diff HEAD` on the file showed zero lines, where dozens were expected) and reconstructed byte-for-byte from this session's own record of the edits, then re-verified against the full suite (`test_companion_app.py` 314/316, `test_browser_ux.py` 90/90) before proceeding — no silent gap in the shipped code. **Corrective action taken for the remainder of this plan:** `git commit` Task 2 BEFORE running any further mutation against `value-controls.js`, so every subsequent `git checkout-index -f --` reverts to the just-committed state rather than to an older one. M-D (the second `value-controls.js` mutation) was run only after this correction and reverted cleanly, confirmed by `git status --short` showing no diff. **Lesson for a future plan doing mutation testing on a file mid-task:** stage or commit the file's real edits before mutating it, every time — `git checkout-index -f --` is not a stash, and a file with uncommitted intentional changes is not yet safe to mutate-and-revert.

**Total deviations:** 3 auto-fixed (all Rule 1, all inside the task that found them, none touching a file outside that task's own scope) plus 1 process incident (self-corrected within Task 3, no shipped-code impact, full test re-verification performed before continuing).

## Mutation Testing (Task 3, quoted verbatim)

All four mutations were applied to already-committed state and reverted with `git checkout-index -f -- <path>`; `git status --short` was confirmed clean after every revert.

**M-A** — reverted `paintReadouts()`'s clock branch, always using `readoutQuantity()`'s raw quantity. Both affected checks failed, and the NEW browser check failed by RAISING (via the rewritten `_quiet_caption_minutes()`) rather than returning a wrong pair, exactly as the plan requires:
> `the dial caption keeps the SAME FORM the server emits at load after EACH of a drag, a keyboard step, a typed field edit and a preset click (CFG-73 Bug A, 28-03-PLAN.md Task 3): ... - exception: AssertionError('_quiet_caption_minutes: en/drag — the caption '480 → 1080 · 10h' on http://127.0.0.1:41839/display carries 0 "HH:MM" token(s), fewer than the two endpoints a pair needs')`

The pre-existing arc/handles/caption agreement check (27-02-PLAN.md Task 4) failed on the identical caption text, confirming the mutation reaches the shared surface, not only the new check:
> `THE arc/handles/caption agreement check ... - exception: AssertionError('_quiet_caption_minutes: light theme, drag path — the caption '480 → 1080 · 10h' on http://127.0.0.1:41839/display carries 0 "HH:MM" token(s), fewer than the two endpoints a pair needs')`

**M-B** — restored the empty duration template (`duration_attrs_html = ""` in `quiet_dial_readout_html()`). The new browser check failed on the non-empty clause, naming the exact regression the developer reported:
> `the dial caption keeps the SAME FORM the server emits at load after EACH of a drag, a keyboard step, a typed field edit and a preset click (CFG-73 Bug A, 28-03-PLAN.md Task 3): ... - en/drag: the duration segment is EMPTY after this interaction — this is the exact regression the developer reported`

**M-C** — changed `DURATION_HOURS_TEXT` from `"#h"` to `"#hrs"`. The new `test_companion_app.py` check failed, naming the bucket, the language and both strings:
> `every one of layout.DURATION_ATTRS' four wordings ... - lang=en hours bucket: layout.DURATION_ATTRS[2]'s wording ('#hrs') fills to '2hrs' but layout.duration_text(7200, lang='en') renders '2h' — the duration readout's copy is the ladder's own output with the number lifted out, never a second wording`

**M-D** — changed `pairedDurationMinutes()`'s wrapped difference to a plain `end - start` (no wrap). The new browser check failed specifically on the midnight-crossing PRESET step (23:00→07:00), which the check's own sequence includes for exactly this reason:
> `the dial caption keeps the SAME FORM the server emits at load after EACH of a drag, a keyboard step, a typed field edit and a preset click (CFG-73 Bug A, 28-03-PLAN.md Task 3): ... - en/preset click: the duration segment reads '0s'; the wrapped-difference computation, worded from the page's own layout.DURATION_ATTRS, expects '8h'`

Every mutation reverted with `git checkout-index -f --`; `git status --porcelain` was clean after each revert and at the end of the plan.

## Verification Evidence

- `companion/test_config_page.py` → 264/264 pass, exit 0
- `companion/test_i18n.py` → 24/24 pass, exit 0
- `companion/test_companion_app.py` → 314/316 pass (the 2 known WR-11 root-sandbox failures, named in 28-01-SUMMARY.md, and no others)
- `companion/test_browser_ux.py` → 90/90 pass, exit 0 (re-run clean after the mutation-testing revert sequence)
- `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` → three named failures, exactly matching the documented WR-11 sandbox baseline: `server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — none touching any file this plan modified
- `ruff check companion/` → All checks passed
- 28-02's own handle-sampling check (`_the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press`) still passes UNCHANGED (confirmed present and PASS in the final full `test_browser_ux.py` run)
- ES5 subset: `grep -nE '=>|\blet \b|\bconst \b|`' companion/static/value-controls.js` returns nothing
- `readoutQuantity()` itself is byte-identical (`git diff` on that function shows no change)
- The non-clock/non-duration readout path is unchanged; every other readout in the app (the wake-interval one included) paints exactly as before this plan

### Note on the French-leak acceptance criterion's own grep pattern

The plan's stated check, `grep -ciE 'heure|minute|jour|il y a|dans ' companion/static/value-controls.js`, is 0 by count of genuine French words/phrases (`heure`, `jour`, `il y a`, `dans ` all return zero hits), but the pattern as literally written also matches the ENGLISH word "minute" case-insensitively as a substring of `MINUTES_PER_HOUR`/`MINUTES_PER_DAY` and of the English word "minute" used correctly in this file's own comments (pre-existing before this plan, e.g. describing `MINUTES_PER_HOUR`). Recorded here rather than silently worked around: the grep's INTENT (no French copy in this script) is fully satisfied — confirmed by the zero hits on every French-specific token — and "minute" being a legitimate English word too is a property of the criterion's own pattern, not a defect in the file.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CFG-73's two bugs are both closed: Bug B (handle collapse) by 28-02, Bug A (readout format/duration) by this plan. 27-02's cross-surface pair seam (`_assert_surfaces_agree`, `_quiet_arc_minutes`, `_fraction_pair_minutes`) is confirmed untouched by `git diff` across all three of this plan's task commits.
- No blockers for later phases. The mutation-testing process incident above is fully self-contained and left no gap in the shipped code — recorded as a lesson for future plans doing mutation testing on a not-yet-committed file, not as an open item.

## Self-Check: PASSED

- FOUND: `companion/layout.py`
- FOUND: `companion/i18n_fr/display.py`
- FOUND: `companion/pages/config_page.py`
- FOUND: `companion/static/value-controls.js`
- FOUND: `companion/test_browser_ux.py`
- FOUND: `companion/test_companion_app.py`
- FOUND: `companion/test_config_page.py`
- FOUND: commit `61fa8a9` (Task 1)
- FOUND: commit `16c2550` (Task 2)
- FOUND: commit `dbfaa0d` (Task 3)

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Completed: 2026-09-15*
