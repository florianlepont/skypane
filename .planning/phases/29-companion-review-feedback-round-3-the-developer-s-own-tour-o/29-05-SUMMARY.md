---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
plan: 05
subsystem: ui
tags: [i18n, editorial-floor, config-page, settings, companion]

requires:
  - phase: 29-04
    provides: "Quiet hours as one visual object (CFG-80) — the segmented preset row and the
      QUIET_TIMES_ROW_CLASS layout this plan's caption edits render inside, unchanged."
provides:
  - "Ten over-length caption constants on /display and /device shortened to one sentence of at
    most twelve words, in English and French"
  - "The apply-timing clause removed from every card caption that carried it (Runway, LED); the
    Frame strip is the one remaining home for that sentence"
  - "The Quiet hours card's caption no longer appends a computed delay sentence — one sentence,
    full stop — with the delay_sentence parameter and its call-site computation deleted outright"
  - "config_page.ASPECT_CAPTION_EXEMPTIONS — a 4-tuple naming the Display Aspect captions
    Phase 30 owns, expected to empty when that phase lands"
  - "A render-level settings-pages editorial floor check in test_config_page.py, mutation-proven
    three ways, that Plan 29-06 generalises to all six routes"
affects: [29-06]

tech-stack:
  added: []
  patterns:
    - "Render-level word-count floor: measure rendered .section-caption text (tags stripped,
      entities unescaped, leading em dash trimmed), not a source-level constant scan"
    - "Exclude computed-quantity readouts (extra CSS class token beyond text-label/
      section-caption, e.g. wake-gauge) from an editorial-copy floor by selector, not by
      exemption-list membership"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/notifications.py
    - companion/test_config_page.py

key-decisions:
  - "quiet_hours_group()'s delay_sentence parameter is DELETED outright (not merely left unread) — nothing else in config_page.py consumed it after Task 2, confirmed by grep before deleting"
  - "_QUIET_HOURS_DELAY_DUE_TEXT/_QUIET_HOURS_DELAY_HELD_TEXT scanner-visibility copies are DELETED — companion/layout.py's own _FRAME_DELAY_* aliases already keep both CATALOG keys scanner-visible, confirmed by test_i18n.py staying 24/24"
  - "wake_gauges_html()'s two elements are excluded from the floor's measured-caption set by selector (an extra 'wake-gauge' class token), not folded into ASPECT_CAPTION_EXEMPTIONS — they are computed quantities, not editorial prose, and folding them in would let the exemption's own reachability assertion stop proving what it claims"
  - "The once-per-page apply-timing relationship is enforced as a REGION invariant (zero matches outside the Frame strip's own slice) rather than a literal 'at most one element' count — the Frame strip's own two switch cells (Screen, Quiet hours) legitimately share one computed sentence by design, pre-dating and untouched by this plan"
  - "Fixed three French translations (QUIET_HOURS_SECTION_CAPTION, WAKE_INTERVAL_SECTION_CAPTION, LED_SECTION_CAPTION) that exceeded 12 words on their own — a gap RESEARCH.md's English-only offender table could not see, surfaced only once Task 3's bilingual render-level check existed"

requirements-completed: [CFG-79]

coverage:
  - id: D1
    description: "Ten over-length caption constants on /display and /device shortened to at most 12 words in both languages"
    requirement: CFG-79
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#the settings-pages editorial floor, measured on the RENDERED page"
        status: pass
    human_judgment: false
  - id: D2
    description: "Apply-timing clause removed from Runway/LED captions; Quiet hours caption no longer appends a computed delay sentence; Frame strip remains the one place per page"
    requirement: CFG-79
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#with a due result, the Frame strip carries the DUE delay sentence exactly twice"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#the settings-pages editorial floor, measured on the RENDERED page"
        status: pass
    human_judgment: false
  - id: D3
    description: "Notifications URL hint's storage/replacement sentence moved into a 'How it works' disclosure, present in the render"
    requirement: CFG-79
    verification:
      - kind: unit
        ref: "companion/test_config_page.py (notifications_group render checks, unchanged count)"
        status: pass
    human_judgment: false
  - id: D4
    description: "ASPECT_CAPTION_EXEMPTIONS pins exactly the four Display Aspect captions Phase 30 owns, proven reachable, with the check passing against their current un-shortened copy"
    requirement: CFG-79
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#the settings-pages editorial floor, measured on the RENDERED page"
        status: pass
    human_judgment: false

duration: ~2h
completed: 2026-09-22
status: complete
---

# Phase 29 Plan 05: Editorial floor on Display and Device Summary

**Ten over-length settings-page captions cut to one sentence of at most twelve words in both languages, the apply-timing clause confined to the Frame strip, the Quiet-hours caption's delay-sentence append deleted along with its now-dead parameter, and a mutation-proven render-level floor check added that also caught three French translations RESEARCH.md's English-only offender table never saw.**

## Performance

- **Tasks:** 3/3 completed
- **Files modified:** 4 (`companion/pages/config_page.py`, `companion/i18n_fr/display.py`, `companion/i18n_fr/notifications.py`, `companion/test_config_page.py`)

## Accomplishments

- Shortened `DEVICE_PAGE_PURPOSE`, `DEVICE_POLL_INTRO`, `POLL_SECTION_CAPTION`, `WAKE_INTERVAL_SECTION_CAPTION`, `LED_SECTION_CAPTION`, `NOTIFICATIONS_SECTION_CAPTION`, `NOTIFICATIONS_URL_HINT`, `RUNWAY_SECTION_CAPTION` — eight constants, one sentence each, ≤12 words in English and French, with the apply-timing clause deleted from Runway and LED.
- Moved `NOTIFICATIONS_URL_HINT`'s storage/replacement sentence into a new "How it works" `<details>` disclosure on the Notifications card, reusing `CALENDAR_HOW_IT_WORKS_SUMMARY`'s existing label.
- Removed `quiet_hours_group()`'s `delay_sentence` keyword outright; the Quiet hours caption is now exactly `QUIET_HOURS_SECTION_CAPTION`'s own translated text, in both languages, with the render()-side computation and two now-dead scanner-visibility copies deleted alongside it.
- Added `config_page.ASPECT_CAPTION_EXEMPTIONS`, a 4-tuple naming the Display Aspect captions Phase 30 owns, and a new render-level floor check in `test_config_page.py` that measures every non-exempt `.section-caption` element on `/display` and `/device`, in both languages, proves the exemption reachable, and enforces the once-per-page apply-timing relationship against `frame_state.py`'s own constants.
- That new bilingual check surfaced (and this plan fixed) three French translations that exceeded 12 words on their own — a defect RESEARCH.md's English-only measurement method could not have found.

## Task Commits

1. **Task 1: Device's six over-length captions, and the Notifications URL hint moved into its disclosure** - `69116ba` (feat)
2. **Task 2: the quiet-hours caption becomes one sentence** - `4479adf` (feat)
3. **Task 3: the settings-pages floor check, with Aspect pinned as an exemption** - `454b203` (feat)

_No separate plan-metadata commit exists yet — this SUMMARY and the tracking-file updates land in the closing `docs(29-05)` commit that follows this file._

## Files Created/Modified

- `companion/pages/config_page.py` — eight caption constants shortened; `NOTIFICATIONS_URL_HOW_IT_WORKS_BODY` added; `quiet_hours_group()`'s `delay_sentence` parameter and its render() call-site computation deleted; `_QUIET_HOURS_DELAY_DUE_TEXT`/`_QUIET_HOURS_DELAY_HELD_TEXT` deleted; the now-unused `frame_state` import deleted; `ASPECT_CAPTION_EXEMPTIONS` added.
- `companion/i18n_fr/display.py` — French twins for every shortened constant, plus fixes to three translations (`QUIET_HOURS_SECTION_CAPTION`, `WAKE_INTERVAL_SECTION_CAPTION`, `LED_SECTION_CAPTION`) that exceeded 12 words on their own.
- `companion/i18n_fr/notifications.py` — French twins for the shortened notifications caption/hint and the new disclosure body.
- `companion/test_config_page.py` — five existing checks retargeted (see table below); one new check added; `EXPECTED_CHECK_COUNT` 273 → 274.

## Old-count → new-count table (naive whitespace split, after substitution)

| Constant | Old (words) | New EN (words) | New FR (words) | i18n_fr module |
|---|---|---|---|---|
| `DEVICE_PAGE_PURPOSE` | 14 | 7 | 6 | `display.py` |
| `DEVICE_POLL_INTRO` | 14 | 6 | 7 | `display.py` |
| `POLL_SECTION_CAPTION` | 14 | 5 | 6 | `display.py` |
| `WAKE_INTERVAL_SECTION_CAPTION` | 19 | 6 | 7 (was 9 before the Task 3 French-only follow-up fix) | `display.py` |
| `LED_SECTION_CAPTION` | 20 | 8 | 8 (was 10 before the Task 3 follow-up fix) | `display.py` |
| `NOTIFICATIONS_SECTION_CAPTION` | 15 | 9 | 11 | `notifications.py` |
| `NOTIFICATIONS_URL_HINT` | 26 | 9 | 10 | `notifications.py` |
| `RUNWAY_SECTION_CAPTION` | 14 | 6 | 5 | `display.py` |
| `QUIET_HOURS_SECTION_CAPTION` | 12 (EN unchanged) / 16 (FR, Task 3 fix) | 12 (unchanged) | 11 (Task 3 fix) | `display.py` |

New body constant (moved, not counted against the floor — a disclosure body, not a caption): `NOTIFICATIONS_URL_HOW_IT_WORKS_BODY`, French twin in `notifications.py`.

Not touched (measured, found already ≤12 words, per the plan's own instruction): `DISPLAY_PAGE_PURPOSE`, `DISPLAY_WATCHES_INTRO`, `DISPLAY_ON_INTRO`, `DEVICE_WAKES_INTRO`, `DEVICE_TELLS_INTRO`.

**The `(next wake ≈ HH:MM)` suffix interaction, which is why WAKE_INTERVAL/LED's French counts moved twice.** `_with_next_wake()` appends a 4-token suffix (`(next wake ≈ %s)` / `(prochain réveil ≈ %s)`) to `RUNWAY_SECTION_CAPTION`/`LED_SECTION_CAPTION`/`WAKE_INTERVAL_SECTION_CAPTION` whenever the next-wake value is known. English stayed within 12 words including that suffix (LED lands exactly at 12); the French translations, measured for the first time by this plan's own bilingual render-level check (Task 3), did not — see Deviations below.

## Harness before/after (all re-derived by RUNNING)

| Harness | Before | After |
|---|---|---|
| `companion/test_config_page.py` | 273/273 | 274/274 |
| `companion/test_i18n.py` | 24/24 | 24/24 |
| `companion/test_companion_app.py` | 316/316 | 316/316 |
| `companion/test_view_pages.py` | 168/168 | 168/168 |
| `companion/test_status_pages.py` | 312/312 | 312/312 |
| `scripts/run-all-tests.sh` (full suite) | — | `Result: PASS`, coverage 93%, `test_browser_ux.py` reported SKIPPED (playwright not installed), never as a pass |

## Decisions Made

**The `delay_sentence` parameter and `render()`'s computation: deleted outright (option (b)).** `quiet_hours_group()` no longer accepts a `delay_sentence` keyword. Before deleting, `grep -rn "quiet_hours_delay_sentence\|quiet_hours_delay_template"` across `companion/` confirmed the only reader of `render()`'s own computed value was the single `quiet_hours_group(...)` call site — no other function or test read it. `render()`'s `next_wake_iso`/`next_wake_clock` computation is unaffected (both still feed the Frame strip and the Runway/LED/Wake-interval "next wake" suffixes); only the delay-sentence-specific branch (`quiet_hours_delay_template`/`quiet_hours_delay_sentence`) was removed, and the triple's now-unused second/third elements are unpacked as `_, _` with a comment recording why. `grep -c 'delay_sentence' companion/pages/config_page.py` returns 9 — all nine are in comments/docstrings recording the history of the removal, none in executable code (verified line by line: 43, 575, 3440, 3443, 3458, 5388, 5391, 5392, 5548).

**The two scanner-visibility copies: deleted, per the harness's own verdict.** `_QUIET_HOURS_DELAY_DUE_TEXT`/`_QUIET_HOURS_DELAY_HELD_TEXT` had no reader left in `config_page.py` once the delay-sentence computation was deleted. `companion/layout.py`'s own `_FRAME_DELAY_DUE_TEXT`/`_FRAME_DELAY_HELD_TEXT` aliases (byte-identical text, `frame_strip_html()`'s own `i18n.t()` call sites) already make both CATALOG keys scanner-visible independently — confirmed by running `companion/test_i18n.py` after the deletion: 24/24, unchanged. The now-fully-unused `from companion import frame_state` import was deleted in the same commit (confirmed unused by grep: every remaining `frame_state` occurrence in `config_page.py` is prose).

**`wake_gauges_html()`'s two computed-quantity readouts are excluded from the floor by selector, not by adding them to `ASPECT_CAPTION_EXEMPTIONS`.** Both carry an extra `wake-gauge` CSS class token beyond `text-label section-caption`; the floor check's own selector requires the class list to be a subset of `{"text-label", "section-caption"}`, so these two are never in the measured set at all. This was necessary, not a convenience: the battery gauge's combined static text (the "not enough history" sentence plus the always-rendered screen-off cadence sentence) measures 23 words on its own — a real, pre-existing, unrelated-to-this-plan property of a *computed data readout*, not editorial copy CFG-79 was ever meant to regulate. Folding it into `ASPECT_CAPTION_EXEMPTIONS` would have broken that tuple's own reachability assertion (exactly 4 skips on Display, exactly 0 on Device — the gauges are Device-only) and mixed two structurally different kinds of exemption into one list the plan requires to name exactly four Aspect captions.

**The once-per-page apply-timing relationship is enforced as a region invariant, not a literal element count — a necessary, documented deviation from the plan's literal acceptance-criteria wording.** The plan's Task 3 text says "the number of elements whose text contains an apply-timing sentence... is at most one, and when it is one, that element is inside the Frame strip's own markup slice." Measured directly: the Frame strip's Screen switch cell and Quiet-hours switch cell both render `delay_caption_html` — the SAME computed sentence, in two separate `<p class="text-label section-caption">` elements, by a pre-existing design this plan does not touch (`git diff --stat companion/layout.py` is empty). So a correct `/display` render legitimately contains **two** apply-timing elements, not "at most one," both inside the Frame strip. The check instead asserts: zero apply-timing matches ever render **outside** the Frame strip's own slice, and at least one match is proven to fire **inside** it (so the assertion cannot vacuously pass by never matching at all). This is the CFG-79 property that actually matters ("said in exactly one place per page" — one *place*, the Frame strip, not one *element*) and is what Task 2's own change (removing the Quiet-hours card's copy) makes true.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Three French translations exceeded 12 words on their own, independent of anything this plan's English cuts touched**

- **Found during:** Task 3, while building and verifying the render-level floor check against a realistic (next-wake-known) fixture.
- **Issue:** `QUIET_HOURS_SECTION_CAPTION`'s French translation ("Met en pause le réveil, la vérification et l'affichage du cadre pendant la plage horaire ci-dessous.") was 16 words — over the floor by itself, with no delay sentence appended at all. Separately, `WAKE_INTERVAL_SECTION_CAPTION`'s and `LED_SECTION_CAPTION`'s French translations, each already ≤12 words alone, exceeded 12 once their real `(prochain réveil ≈ HH:MM)` suffix was included (13 and 14 words respectively) — English stayed within 12 in both cases (10 and exactly 12). RESEARCH.md's own offender table explicitly measured English only ("French renders separately and was not re-measured"), so this was invisible until this plan's own bilingual, render-level check existed.
- **Fix:** Shortened all three French translations, preserving meaning: `QUIET_HOURS_SECTION_CAPTION` "Met en pause..." (16 words) → "Suspend le réveil, la vérification et l'affichage du cadre pendant cette plage." (12 words); `WAKE_INTERVAL_SECTION_CAPTION` dropped its colon+NBSP token and one repeated "plus" (9 → 7 words, colon replaced with a comma); `LED_SECTION_CAPTION` dropped the redundant "fenêtre... de réveil... de l'appareil" double-naming (10 → 8 words).
- **Files modified:** `companion/i18n_fr/display.py`.
- **Verification:** `companion/test_config_page.py`'s new floor check passes at 0 over-length matches in both languages on both pages; `companion/test_i18n.py` stayed 24/24.
- **Committed in:** `454b203` (Task 3's own commit — the fix and the check that found it landed together).

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug fix, a genuine floor violation the new check's own bilingual measurement surfaced).
**Impact on plan:** Necessary for correctness — CFG-79 requires the floor to hold "in both languages"; without this fix the plan's own new check would have been red on its own control render. No scope creep: no constant outside this plan's own eight-plus-one (Quiet hours) touched.

## Mutation Proofs (Task 3's floor check)

**Mutation A — the length floor.** Lengthened `LED_SECTION_CAPTION` to a deliberate 18-word (with suffix) sentence:

```
LED_SECTION_CAPTION = "Lit only during the device's brief wake window and nowhere else at all whatsoever."
```

Real failure message:
```
FAIL the settings-pages editorial floor, ... - device/en: a non-exempt section-caption renders
18 word(s) (max 12): "Lit only during the device's brief wake window and nowhere else at all
whatsoever. (next wake ≈ 14:10)"
```
Reverted with `git checkout-index -f -- companion/pages/config_page.py` (after staging the correct version).

**Mutation B — the exemption cannot grow silently.** Added a fifth, unrelated constant to `ASPECT_CAPTION_EXEMPTIONS`:

```
ASPECT_CAPTION_EXEMPTIONS = (
    DISPLAY_LOOK_INTRO, FRAME_COLOURS_CAPTION, CALENDAR_CAPTION, CALENDAR_URL_HINT,
    NOTIFICATIONS_SECTION_CAPTION,
)
```

Real failure message:
```
FAIL the settings-pages editorial floor, ... - display/en: expected exactly 5 Aspect-exemption
skip(s), got 4 — either the exemption is unreachable from this page or it silently swallowed a
caption it should not have
```
(`NOTIFICATIONS_SECTION_CAPTION` never appears on `/display` — it is Device-only — so the skip count could not reach the now-inflated expectation.) Reverted with `git checkout-index -f -- companion/pages/config_page.py`.

**Mutation C — the once-per-page rule.** The plan's own suggested mutation (re-appending the full delay sentence to `QUIET_HOURS_SECTION_CAPTION`'s rendered composition) tripped the LENGTH floor first (20 words), never reaching the relationship assertion — recorded as a real, useful catch in its own right, but not a proof of the relationship logic specifically. A second, targeted mutation isolated that logic: replaced the Quiet-hours caption's composition with the bare delay sentence alone (8 words, safely under the length floor):

```
caption_html = i18n.t("Applies the next time the frame wakes up.")
```

Real failure message:
```
FAIL the settings-pages editorial floor, ... - display/en: the apply-timing sentence rendered
outside the Frame strip's own slice — CFG-79 confines it to exactly one place per page:
display/en at offset 83475 ('Applies the next time the frame wakes up.'): 'Applies the next
time the frame wakes up.'
```
Reverted with `git checkout-index -f -- companion/pages/config_page.py`.

**Control result.** With the correct source in place, the check passes against Aspect's CURRENT, un-shortened copy — `git diff companion/pages/config_page.py` shows none of the four exempt constants changed by this plan, and `CALENDAR_URL_HINT` (22 words) does not fail the check. Confirmed by the full green run: `config-page: 274/274 checks pass`.

## Retargeted-or-retired delay-sentence checks (Task 2)

| Check | What happened |
|---|---|
| `_the_ring_is_an_addition_and_the_four_controls_are_untouched` | Retargeted: the caption assertion changed from "starts with the static sentence, then carries something longer" to exact equality against `QUIET_HOURS_SECTION_CAPTION`'s own escaped text. |
| `_applies_next_wake_sentence_appears_exactly_three_times` | Retargeted and renamed to `_applies_next_wake_sentence_appears_exactly_twice`: the expected count narrowed from 3 to 2 (both occurrences now attributable only to the Frame strip's two switch cells). |
| `_quiet_hours_caption_and_flash_agree_on_the_due_branch` | Retargeted: now asserts the DUE delay sentence appears exactly twice, both inside the Frame strip's own slice, AND that the Quiet hours card's own caption carries none of it. The flash-text assertion (a separate code path, `companion_app._resolve_flash_text()`) is unchanged. |
| `_quiet_hours_caption_and_flash_agree_on_the_held_branch` | Same retargeting, HELD branch. |
| `_quiet_hours_caption_and_flash_agree_on_the_unknown_branch` | Same retargeting, UNKNOWN branch. |
| `_quiet_hours_caption_is_shortened_and_the_delay_sentence_survives_in_both_languages` | Retargeted and renamed to `_quiet_hours_caption_is_shortened_and_carries_no_delay_sentence_in_either_language`: the old call passed a now-nonexistent `delay_sentence` keyword (would raise `TypeError`); the check now asserts the caption renders as EXACTLY `QUIET_HOURS_SECTION_CAPTION`'s own translated text in both languages, still under the 188-char baseline. |

No check was retired outright — every one of the six above still pins a real, surviving property (the Frame strip's own delay sentence, unaffected by this plan) rather than being deleted.

## Issues Encountered

**Two `git checkout-index -f` reverts required redoing uncommitted work.** During the first mutation-proof attempt for Task 3, `git checkout-index -f -- companion/pages/config_page.py` was run before staging the correct (uncommitted) `ASPECT_CAPTION_EXEMPTIONS` addition — this restored the file to the last COMMIT (Task 2's state), silently discarding Task 3's own in-progress edit. Caught immediately (the constant was gone on re-check), the edit was redone, and every subsequent mutation was preceded by `git add` of the correct state before mutating, per the constraint's own instruction ("reverting each with `git checkout-index -f` after staging your correct version").

## Self-Check

- FOUND: commit `69116ba`
- FOUND: commit `4479adf`
- FOUND: commit `454b203`
- FOUND: `companion/pages/config_page.py`
- FOUND: `companion/i18n_fr/display.py`
- FOUND: `companion/i18n_fr/notifications.py`
- FOUND: `companion/test_config_page.py`

## Self-Check: PASSED
