---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 06
subsystem: ui
tags: [i18n, css, testing, honesty-contract, copywriting]
requires:
  - phase: 27-01
    provides: "the surface-agreement/shortening/inventory helpers (_assert_shorter_and_still_refuses, _markup_inventory) and the 7/3/2 title-form + three copy baselines (220/254/188 chars) this plan measures against"
  - phase: 27-05
    provides: "the runway-map removal — Task 1's inventory ran against this tree's current shape, not the pre-27-05 one"
provides:
  - "the title-form inventory conclusion: Outcome 2 — one title form for settings cards already, no conversion made"
  - "a source-level AST guard proving no settings-card builder ever calls layout.section_intro_html()"
  - "three shortened copy regions (wake-interval caption, wake gauges, Quiet hours paragraph) with D18's battery honesty contract intact"
affects:
  - "27-09 (the phase gate — CFG-65/CFG-67/CFG-71 tracking happens there, not here)"
tech-stack:
  added: []
  patterns:
    - "when a research document's provisional split turns out to be a grammar distinction rather than an inconsistency, say so and guard the invariant at the source level instead of converting markup to manufacture a change"
    - "shortened copy keeps every honesty-contract clause verbatim in meaning, cutting only the mechanism/reason clauses around it"
    - "one read of a rendered region, all assertions (length + refusal, or length + survival) made against that same read"
key-files:
  created: []
  modified:
    - companion/test_config_page.py
    - companion/pages/config_page.py
    - companion/i18n_fr/display.py
decisions:
  - "Outcome 2 (CFG-65): the 7-vs-3 title-form split is a supersection-intro-vs-card-title grammar distinction, not an inconsistency — no markup or CSS was converted"
  - "the substitute for Task 2's markup conversion is a source-level AST guard (zero card-builder functions call layout.section_intro_html()), not a CSS/markup change"
  - "CFG-67's three cuts each remove only the mechanism/reason clause; every honesty-contract or live-state clause (the refusal, the ≈ marker, the delay sentence) survives verbatim in meaning"
requirements-completed: []
metrics:
  duration: ~2h 40m
  completed: 2026-09-15
---

# Phase 27 Plan 06: One title form (Outcome 2, no conversion) + three explanatory-text cuts Summary

**The title-form inventory overturned its own provisional recommendation — there was already one title form for cards, so nothing was converted; the wake-interval, gauge and Quiet-hours copy got materially shorter while the battery honesty contract and the delay sentence survived, both mutation-tested.**

## Performance

- **Duration:** ~2h 40m (most of it the title-form investigation)
- **Tasks:** 3 of 3
- **Files modified:** 3 (`companion/test_config_page.py`, `companion/pages/config_page.py`, `companion/i18n_fr/display.py`)

## Task Commits

1. **Task 1: the title-form inventory** — `837bddf` (test)
2. **Task 2: the source-level "one form" guard** — `3c415e2` (test)
3. **Task 3: cut the three texts** — `7a00c04` (feat)

_No plan-metadata commit yet — this SUMMARY and the state-update commit follow._

## Part 1 — the title-form inventory (CFG-65)

### The inventory's actual result

Re-derived by running `config_page.render()` for both `SCOPE_DISPLAY` and `SCOPE_DEVICE` and counting directly against the server-rendered HTML (no browser needed for this — the counts are in the strings config_page.py itself produces):

| | Display | Device | Total |
|---|---|---|---|
| `class="text-heading"` (all) | 8 | 4 | 12 |
| form A (`[data-dirty-section] > h2`) | 4 | 3 | **7** |
| form B (`.section-intro > h2`) | 3 | 0 | **3** |
| unclassified | 1 | 1 | **2** |

This reproduces 27-01-SUMMARY.md's own browser-driven inventory (7/3/2) exactly, confirming it (not 27-RESEARCH.md's provisional 8/3/2 — the eighth grep hit is a form-A call site neither settings route renders).

**Every one of the 12 instances, classified by name:**

- **7 SETTINGS-CARD titles (form A)** — each is the first thing inside its own bordered tile: Frame colours, Calendar, Runway, Quiet hours (Display); Diagnostic LED, Wake interval, Notifications (Device).
- **3 SUPERSECTION intros (form B)** — `layout.section_intro_html()`, shared byte-identical with `health_page.py`: Look, What it watches, When it is on. Confirmed structurally distinct from a card title, not just by selector: "Look" alone introduces **two** cards (Frame colours **and** Calendar — `render()`'s own 5029/5183 ordering), which a card title, naming exactly one card, cannot do. Rendered via `<div class="section-intro">` (no border, no card surface) — measured directly with Playwright at 360px, its own h2 is 22px serif, and it sits flush (0px gap) against its first following card.
- **2 unclassified** — neither a card nor a supersection: the Frame strip's own live-status heading (`layout.frame_strip_html()`, Display only, an unrelated preview widget) and the Poll card's own bare-`<section class="page-section">` heading (`poll_trigger_section()`'s wrapper, Device only — it carries no `[data-dirty-section]` attribute only because it holds no persisted field for dirty-tracking to watch; its role is otherwise identical to form A).

### Did this confirm or overturn "7 vs 3" as a real inconsistency?

**Overturned — Outcome 2.** There is already exactly one title form for settings cards. The investigation went further than the plan strictly required, because the first candidate substitute cause (heading SIZE) looked promising and had to be run to ground before being ruled out:

- Playwright measurement (360px, both routes) showed nested cards under a supersection (Frame colours/Runway/Quiet hours/Calendar) render their own `<h2>` at **16px sans-semibold**, while un-nested Device cards and the supersection intros themselves render at **22px serif** — a real, measurable difference that could produce exactly the "title above vs inside" impression.
- But `companion/static/style.css`'s own comment on that rule (`.page-section--nested > h2` etc.) states this is **the third and final state of a three-round developer-reviewed decision**, validated against a full Health composition (sketch 005, variant B), and says explicitly: *"This is the third state of the round trip, not a mistake to second-guess."* It is also shared verbatim with `health_page.py`'s `.battery-trend-section > h2`.
- The D-12 structural restructure that created the three supersections (20-07-PLAN.md) is still pinned by two passing checks in this same file (`_display_render_carries_three_section_intros_in_locked_order`, `_every_grouped_card_under_a_display_supersection_carries_nested_class`) — reversing it to "convert" form B into form A would mean undoing a whole prior phase's deliverable across ~10+ existing tests, not a one-file cleanup edit.
- The "spacing above a supersection's first card" (0px, vs. 24px between cards) is real but is a **universal, cross-page convention** — the same `.section-intro` rule Health uses identically — with no comment or test anywhere flagging it as wrong.
- "A caption that reads like a title" did not hold up: every caption (`.section-caption`) is muted, small, and carries no size/weight override that would let it compete with a heading.

So: no markup or CSS conversion was made. Converting either direction (form A → B, or B → A) would either edit `layout.section_intro_html()`'s call sites away from a shape `health_page.py`'s own structural checks match literally, or reverse a validated, developer-confirmed, three-round-trip design decision this plan does not have standing to reopen. The honest conclusion is what Task 1 asked for if that turned out to be true: **the developer's impression is almost certainly about the presence of the supersection pattern itself on Display (three group headings) versus its total absence on Device — a real, intentional structural difference between the two settings pages, not a per-card title inconsistency.**

### Which form was chosen, and why

Neither form was "chosen" over the other because there was nothing to convert — form A stays the only card-title form, form B stays the only supersection-intro form, exactly as measured. Where the plan asked for a cost comparison anyway: converting B→A (removing 3 supersection call sites) would be far cheaper mechanically than A→B (restructuring 7 card builders and risking the `DIRTY_SECTION_ATTR` dirty-tracking contract), but even the cheaper direction costs reversing D-12's whole restructure — which is why neither was done.

### The check that proves the losing form's count is zero

Since there is no conversion, "the losing form" is reframed as what Task 2 explicitly permits under Outcome 2: a structural guarantee that a card's own title can never, going forward, be produced through the supersection-intro shape. `_no_card_builder_function_ever_calls_section_intro_html()` (AST-based) asserts, by walking the source of all 7 card-builder functions, that **zero** of them call `layout.section_intro_html()`. Its message on failure names the count and the offending function(s).

Mutation-tested — a spurious call inserted into `led_group()`:

```
expected ZERO of the 7 settings-card builder functions to call layout.section_intro_html()
(form B) for their own <h2> — found it called from ['led_group']. A card's own title must
stay form A, never borrow the shared supersection builder
```

Reverted; `companion/pages/config_page.py` shows no diff after revert (`git checkout-index -f`).

Task 1's own inventory check was also mutation-tested (a vocabulary-overlap regression: setting `DISPLAY_LOOK_HEADING = "Frame colours"`):

```
expected the settings-card vocabulary and the supersection-label vocabulary to share no
text — found {'Frame colours'} in both, which would mean a card's own identity and a
group's own label had collapsed into the same word
```

`git diff` after both commits names neither `companion/layout.py` nor `companion/pages/health_page.py`.

## Part 2 — the three explanatory-text cuts (CFG-67)

All three baselines are 27-01-SUMMARY.md's own (360px, seeded fixture). Each is now proven strictly shorter in **both** languages by one check per region, one read, all assertions against that same read.

### Wake-interval caption (`#wake-interval-caption`, `/device`)

**Before (220 chars):** *"How often the frame wakes to poll for updates. Shorter means fresher info and more battery drain; longer means more battery life and staler info at a glance. Applies on the next scheduled poll. (next wake ≈ 31 Jul 08:05)"*

**After (137 chars, English; well under baseline in French too):** *"Shorter means fresher info and more battery drain; longer means more battery life and staler info at a glance. (next wake ≈ 31 Jul 08:05)"*

Cut: the mechanism sentence ("How often the frame wakes...") and the apply-timing sentence ("Applies on the next scheduled poll.") — the latter made redundant by the derived `(next wake ≈ ...)` suffix, which is untouched (a real, derivable timestamp, never an invented figure).

### Wake gauges (`.wake-gauge`, 2 elements, `/device`)

**Before (254 chars):** *"A plane reaches the frame at most 5 min after it passes. Not enough battery history yet to say how long a charge lasts — this frame has never measured what one wake costs. While the screen is off the frame wakes every 5m instead, whatever this is set to."*

**After (168 chars):** *"A plane reaches the frame at most 5 min later. Not enough battery history yet to say how long a charge lasts. While the screen is off, the frame wakes every 5m instead."*

Cuts, each scoped to a mechanism/reason clause, never a refusal:
- Freshness: "after it passes" → "later" (word "at most" — the whole bound claim — untouched).
- Battery-unknown: the reason clause ("— this frame has never measured what one wake costs") cut; the refusal itself ("Not enough battery history yet to say how long a charge lasts") **unchanged**.
- Screen-off: ", whatever this is set to" cut; the cadence itself stays named.
- Also lightly cut for consistency (not part of the measured baseline state, but same region): `WAKE_BATTERY_DAY_TEXT`/`DAYS_TEXT` drop "at this interval"; the "≈" marker and "from this frame's own recent readings" attribution are **unchanged**.

### Quiet hours paragraph (`#quiet-hours-caption`, `/display`)

**Before (188 chars):** *"Pauses the frame's wake, poll and display cycle during the schedule below — the Frame strip's Quiet hours switch is what turns it on and off. Applies at the next wake, around 31 Jul 08:05."*

**After (121 chars):** *"Pauses the frame's wake, poll and display cycle during the schedule below. Applies at the next wake, around 31 Jul 08:05."*

Cut: the mechanism clause naming the Frame strip's switch. The delay sentence ("Applies at the next wake, around...") — computed live state from `frame_state`, defaulting to `i18n.t(frame_state.DELAY_UNKNOWN)`, never explanatory text — is **untouched**, and its survival is asserted in the same check as the length.

### The battery-gauge honesty contract — unweakened, quoted

D18's contract, quoted directly from `wake_battery_observed_text()`'s own docstring (unedited by this plan): *"The battery half: an absolute figure ONLY when this frame's own observed history supports one, and the named 'not enough history yet' sentence in every other case."* Nothing in this plan's edits touches the condition under which a figure prints — only the wording around it. Verified by a dedicated forbidden-pattern check (`≈\s*\d+\s*(?:day|days|jour|jours)\b`, scoped to the days-CLAIM shape, not to "≈" near any digit — 27-01-SUMMARY.md flagged the naive pattern would false-positive on the wake-interval caption's own legitimate `(next wake ≈ 31 Jul 08:05)` text) run against the insufficient-history state in both languages.

### Mutation tests, quoted

1. Restoring the original long wake-interval caption:
   ```
   en: #wake-interval-caption renders 220 character(s), against a recorded baseline of 220
   (27-01-SUMMARY.md). The copy was not cut. It reads 'How often the frame wakes to poll for
   updates. Shorter means fresher info and more battery drain; longer means more battery
   life and staler info at a glance. Applies on the next scheduled poll. (next wake ≈ 31 Jul
   08:05)'
   ```
2. Making the insufficient-history state print a figure (`WAKE_BATTERY_UNKNOWN_TEXT = "≈ 12 days of battery left, probably."`):
   ```
   en: .wake-gauge did get shorter (142 character(s), under the 254 baseline) but the
   insufficient-history state now matches '≈\s*\d+\s*(?:day|days|jour|jours)\b' at '≈ 12
   days' — a shorter sentence that starts claiming a figure this frame's own history cannot
   support is a regression, not a cut. The whole region reads 'A plane reaches the frame at
   most 5 min later. ≈ 12 days of battery left, probably. While the screen is off, the frame
   wakes every 5m instead.'
   ```
3. Deleting `delay_sentence` from the Quiet hours caption construction (`caption_html = "%s" % (i18n.t(QUIET_HOURS_SECTION_CAPTION),)`):
   ```
   en: #quiet-hours-caption lost its own computed delay sentence ('Applies at the next wake,
   around 31 Jul 08:05.') — expected it to survive the caption cut untouched, and it reads
   "Pauses the frame's wake, poll and display cycle during the schedule below." instead
   ```
   A check does catch it — no fallback needed.

All three reverted (`git checkout-index -f`), `__pycache__` cleared, re-confirmed clean (261/261).

## Re-derived counts (by RUNNING)

| Harness | Count | Result |
|---|---|---|
| `companion/test_config_page.py` | **261/261** (was 256; +2 Task 1/2, +3 Task 3) | PASS |
| `companion/test_browser_ux.py` | **83/83** (unchanged by this plan — no new checks added there) | PASS, 255.7s |
| `companion/test_i18n.py` | **24/24** | PASS |
| `ruff check .` | — | All checks passed |

`companion/test_browser_ux.py`'s count (83) and `companion/test_config_page.py`'s count (256, pre-this-plan) were both confirmed by running before this plan's own edits, matching the plan's Standing Constraint 6.

## Full suite — `./scripts/run-all-tests.sh`, PYTHON pinned

3 harnesses failed, 255.7s wall (JOBS=4). Every failing check re-run standalone and matched **by name** against the sandbox baseline:

1. `POST /airlines/resolve redirects with the manual_save_failed flash key …` (WR-11, `companion/test_companion_app.py`)
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key …` (WR-11, `companion/test_companion_app.py`)
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created …` (WR-11, `server/test_manual_resolutions.py`)
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write …` (WR-11, `server/test_manual_resolutions.py`)
5. `anomaly_active() runs on every page render and must never raise …` (`companion/test_status_pages.py`)

Exactly the 5 baseline failures. No sixth.

## Decisions Made

- **Outcome 2 (CFG-65):** there is already one title form for settings cards. No markup/CSS conversion — see Part 1 above for the full evidence trail (three-round-trip validated heading ladder, shared Health CSS, D-12's own still-pinned tests).
- **The substitute for Task 2's conversion check:** a source-level AST guard, not a rendered-markup check, because there is no markup difference left to assert against.
- **CFG-67 cuts are scoped to mechanism/reason clauses only:** every clause carrying the battery honesty contract, the "at most" bound, or live computed state (the delay sentence) survives verbatim in meaning.

## Deviations from Plan

None triggering Rules 1–4. The extensive title-form investigation (Playwright measurement of computed heading styles, reading `style.css`'s own multi-round-trip decision history) was necessary due diligence for Task 1's own explicit instruction to run the inventory and classify each instance rather than assume the provisional recommendation — not scope creep, and it changed the plan's outcome (Outcome 2 instead of the provisionally-expected Outcome 1).

## Issues Encountered

None blocking. The one real risk (accidentally reopening a validated, developer-confirmed CSS decision, or touching Health's shared rendering) was identified and avoided before any markup was edited.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

CFG-65 and CFG-67 are both functionally addressed (one title form confirmed and guarded; three texts cut with the honesty contract intact) but **not ticked** in STATE.md/ROADMAP.md/REQUIREMENTS.md per this plan's Standing Constraint 11 — that bookkeeping belongs to 27-09, the closing plan. No blockers for 27-07/27-08.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*

## Self-Check: PASSED

- `companion/test_config_page.py` — FOUND.
- `companion/pages/config_page.py` — FOUND.
- `companion/i18n_fr/display.py` — FOUND.
- `.planning/phases/27-companion-review-feedback-the-defects-and-the-noise-the-deve/27-06-SUMMARY.md` — FOUND.
- Commits `837bddf`, `3c415e2`, `7a00c04` — all FOUND in `git log`.
