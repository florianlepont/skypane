---
phase: quick-260902-l9w
plan: 260902-l9w
subsystem: companion-web-app
tags: [css, accessibility, touch-target, runway-picker, wcag-2.5.5]
dependency_graph:
  requires: []
  provides:
    - "input.visually-hidden, select.visually-hidden CSS rule (companion/static/style.css)"
    - "hidden-form-control-floor regression check (companion/test_companion_app.py, EXPECTED_CHECK_COUNT=107)"
    - "exempt-by-delegation touch-target floor category (sketch-findings-skypane skill)"
  affects:
    - companion/pages/config_page.py (consumer, not modified — the runway_fieldset() markup that made this fix necessary)
tech_stack:
  added: []
  patterns:
    - "Clearing a global min-height/min-width touch-target floor for hidden form controls via a class+type-qualified selector (input.visually-hidden), the same pattern .led-checkbox input and .filter-bar__field input already use"
key_files:
  created: []
  modified:
    - companion/static/style.css
    - companion/test_companion_app.py
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
    - .claude/skills/sketch-findings-skypane/references/control-density.md
decisions: []
metrics:
  duration: "~1h10m"
  completed: "2026-09-02"
status: incomplete
---

# Quick Task 260902-l9w: Fix the Runway picker's hidden native radio touch-target leak Summary

One-liner: cleared the site-wide 44px WCAG 2.5.5 touch-target floor off `.visually-hidden` form controls with a new `input.visually-hidden, select.visually-hidden` rule, so the three Runway-picker radios shrink to their intended 1x1px off-screen box instead of painting a real 44x44px native radio dot on mobile browsers.

## What shipped

**The bug, confirmed against live source before any edit:** `companion/pages/config_page.py`'s `runway_fieldset()` emits each Runway radio with `class="visually-hidden"`. `.visually-hidden` declares `width: 1px; height: 1px`, but the site-wide `input, select { min-height: 44px; min-width: 44px; ... }` rule clamps that back up to a real 44x44px box, because a `min-height`/`min-width` from another rule is a layout-time floor, not a cascade competitor that specificity can resolve. Some mobile browsers then paint their native radio-dot theming inside that 44x44 box, visible on or beside each Runway tile — the bug the developer saw on their own phone.

**The fix (`companion/static/style.css`):** a new rule, `input.visually-hidden, select.visually-hidden`, placed directly after the `.visually-hidden` utility block, clears `min-height`/`min-width` to `0` and removes native control theming (`appearance: none` + `-webkit-appearance: none`). It wins over the global `input, select` rule on specificity (a class plus a type selector beats a bare type selector), independent of source order. Neither the `.visually-hidden` block nor the global `input, select` rule was touched — both are byte-identical before and after. This is the third site in this stylesheet needing the same clearing (`.led-checkbox input[type="checkbox"]`, `.filter-bar__field input` already carry it); the fix's comment cross-references both precedents instead of restating the mechanism a third time.

**The regression check (`companion/test_companion_app.py`):** one new check, `_hidden_form_control_floor_and_global_floor_both_survive()`, registered as a sibling of `_health_nav_notification_dot()`. It fails if either half of the contract breaks: the new `input.visually-hidden` rule going missing, OR the global `input, select` rule losing either of its 44px minimums. `EXPECTED_CHECK_COUNT` moved from 106 to 107 with a provenance comment in the file's stacked-comment format. 107/107 checks pass.

**The design-skill registers (`sketch-findings-skypane`):** `references/accessibility-contrast.md`'s `.visually-hidden` entry gained the form-control clamping caveat, naming the runway radio as the shipped instance. `references/control-density.md`'s touch-target floor register gained a fourth category, **exempt-by-delegation** — an off-screen control with no hit area of its own, whose wrapping label is the real activation target — explicitly stated as not a fifth entry in the traded-away list, since no accessibility floor was actually given up. `SKILL.md`'s one-line floor-register summary was extended to match, in one clause, pointing to `control-density.md` for the reasoning.

**Blast-radius audit (production code, excluding tests):** 8 actual `<input>` emitters, 0 `<select>` emitters, exactly ONE input carrying the `visually-hidden` utility class (`config_page.py`'s runway radio). The Theme radio (`config_page.py:229`) does **not** carry the class — confirmed unchanged. Note: the plan's own pre-computed blast-radius list said "nine emitters"; the actual count is eight — the plan double-counted `history_page.py:641`, which is a **docstring line** describing the filter bar, not a second `<input>` emission (the filter input's only real emitter is `history_page.py:656`). This is a harmless off-by-one in the plan's own accounting, not a new hidden control or a markup regression, and does not change the fix's scope.

## Live before/after measurement table (real browser, real running companion process)

Captured via the `chrome-devtools` CLI (headless Chrome, isolated context) against a real `companion/app.py` instance on port 8643 (`scripts/run-local-verify.sh`). **Pre-fix** numbers were captured by temporarily serving the pre-fix `style.css` (checked out via `git show <fix-commit>^:companion/static/style.css`, written to the working tree, never committed, then restored via `git checkout -- companion/static/style.css` before continuing) — the actual committed fix (`556cd03`) landed in git *before* browser tooling was confirmed working in this session, so the "before" state was reconstructed from git history rather than measured prior to the code change; both states were exercised against the identical real server process and browser. Every reload used `navigate_page --type reload --ignoreCache true` to defeat stylesheet caching.

### `/settings` (formerly `/config`) — the three `tracked_runway` radios

| Viewport | Metric | Pre-fix | Post-fix |
|---|---|---|---|
| 375px | computed width / height | 44px / 44px | **1px / 1px** |
| 375px | computed min-width / min-height | 44px / 44px | **0px / 0px** |
| 375px | computed appearance | auto | **none** |
| 375px | bounding-rect width / height | 44 / 44 | **1 / 1** |
| 1280px | computed width / height | 44px / 44px | **1px / 1px** |
| 1280px | computed min-width / min-height | 44px / 44px | **0px / 0px** |
| 1280px | computed appearance | auto | **none** |
| 1280px | bounding-rect width / height | 44 / 44 | **1 / 1** |

All three radios (all three runway options) reported identical numbers to each other at each width/state; the table above is representative of all three, and each was individually checked in the raw JSON captures.

### Control group — every other input/select on `/settings`, both viewport widths

16 Theme radios, 1 LED checkbox, all measured `name`/`className`/computed `width`/`height`/`minWidth`/`minHeight`/`appearance`/bounding-rect `width`/`height`. A Python diff of the full 20-element pre-fix vs. post-fix arrays at 375px and again at 1280px reports **zero differences** for every element except the three `tracked_runway` radios. Representative entries:

| Field | Pre-fix | Post-fix (375px and 1280px) |
|---|---|---|
| Theme radio (`name=theme`) | w/h 44px/44px, min 44px/44px, appearance auto, rect 44x44 | byte-identical |
| LED checkbox (`name=led_enabled`) | w/h 16px/16px, min 0px/0px, appearance auto, rect 16x16 | byte-identical |

### `/login` — password field

| Viewport | Metric | Pre-fix | Post-fix |
|---|---|---|---|
| 375px | w/h, min-w/min-h, appearance, rect | 193px/44px, 44px/44px, auto, 193x44 | byte-identical |
| 1280px | w/h, min-w/min-h, appearance, rect | 193px/44px, 44px/44px, auto, 193x44 | byte-identical |

### `.runway-card` behavior, verified live post-fix

All five confirmed at 375px; layout and click/focus mechanics also spot-checked at 1280px.

1. **Diagram image renders inside each tile** — confirmed via screenshot (`evidence/settings-375px-postfix-runway-section.png`, `evidence/settings-1280px-postfix-runway-section.png`); all three runway diagrams render correctly.
2. **Selected tile shows its 2px accent border + check glyph; unselected show neither** — confirmed via screenshot: Piste 3 (the persisted `tracked_runway` value) shows the terracotta border and check mark; Piste 4 and Piste 2 show neither.
3. **Clicking anywhere on a tile still selects it, form goes dirty** — clicked the diagram image inside the "Piste 4" tile (not the now-1px input itself). Accessibility snapshot confirmed the underlying radio's checked state moved (Piste 4 became `checked focusable focused`; Piste 3 lost its "Selected" accessible-name suffix), and the dirty-state bar appeared with "Runway changed" / Save settings / Cancel. Note: the visual border/check-glyph placement is driven by a server-rendered static class (`.runway-card--selected`, baked in from the persisted `tracked_runway` value at page-load time) rather than a live `:checked`/`:has()` CSS reaction — confirmed via `grep` that `style.css` has no `:checked` or `:has()` selectors touching `.runway-card`. This is pre-existing app behavior unrelated to this fix: the visual selection only moves after Save + reload, while the underlying input state and dirty-bar are live. Not a regression.
4. **Keyboard focus still reaches the radios and lights the card** — after the click, `getComputedStyle()` on the three `.runway-card` elements confirmed `hasFocusWithin: true` and the `focus-within` box-shadow (`var(--shadow-card-hover)`) applied to exactly the focused, non-selected card. Pressing `ArrowRight` moved focus to the next radio in the native radio group and the shadow followed to the newly focused card — confirming clearing `appearance`/the min-width/min-height minimums did not disturb focus reachability.
5. **Layout** — three tiles wrap into a stacked column at 375px (screenshot) and sit in one horizontal row at 1280px (screenshot).

### Screenshots

- `.planning/quick/260902-l9w-fix-the-runway-picker-s-hidden-native-ra/evidence/settings-375px-postfix-runway-section.png` — 375px, post-fix, initial load (Piste 3 selected, no visible radio dot anywhere)
- `.planning/quick/260902-l9w-fix-the-runway-picker-s-hidden-native-ra/evidence/settings-375px-postfix-after-click-piste4.png` — 375px, post-fix, after clicking the Piste 4 tile (dirty-state bar visible)
- `.planning/quick/260902-l9w-fix-the-runway-picker-s-hidden-native-ra/evidence/settings-1280px-postfix-runway-section.png` — 1280px, post-fix, one horizontal row

## Verification

- `companion/test_companion_app.py`: **107/107** checks pass.
- `scripts/run-all-tests.sh`: **`==> Result: PASS`**, zero failing harnesses, `server/test_poll_loop.py` included and green (ran and inspected its own PASS lines directly, not just the aggregate summary).
- `grep -c 'input.visually-hidden' companion/static/style.css` → 1.
- Global `input, select` rule's two 44px minimums: present, unchanged (2 matches).
- `!important` count in `companion/static/style.css`: 3, unchanged.
- `git diff --name-only -- companion/pages/config_page.py`: 0 — untouched, as required.
- `git status --short` after all commits: clean except pre-existing untracked files unrelated to this task (`.claude/launch.json`, a `.gitkeep`, `scripts/run-local-verify.sh`) that were already present before this task started.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written for the code fix itself (Task 2's three commits).

### Process deviations (not code deviations)

**1. Task 1's blast-radius count off-by-one, reported not fixed.** The plan's own pre-computed blast-radius list said "nine emitters"; live grep found eight. Root cause: the plan's list counted `history_page.py:641` (a docstring describing the filter bar) as a distinct emitter alongside the real emitter at `history_page.py:656`. Reported per Task 1's own instructions ("If you find a second hidden form control the plan did not list, report it") — this is the opposite case (one fewer than listed, and the "extra" line was never a real emitter), so it required no fix, just this note.

**2. Execution order relative to the plan's Task 1/Task 3 split.** Chrome browser automation (the `chrome-devtools` CLI, `chrome-devtools-mcp@1.6.0`, installed globally on this machine) was not immediately known to be available in this session; the code fix (Task 2, all three commits) landed before that tooling was discovered and confirmed working. To still produce a genuine pre-fix baseline against a real running server and browser (not a stale git-history assumption), the pre-fix `style.css` content was reconstructed via `git show <fix-commit>^:companion/static/style.css`, temporarily written to the working tree (never committed), served by a restarted local instance, measured, then restored via `git checkout -- companion/static/style.css` (the sanctioned single-file-restore pattern) before continuing. Both the pre-fix and post-fix measurements were taken against the identical real server process and real headless browser in the same session — the evidentiary content of Task 1 and Task 3 is intact, only the commit-vs-measurement ordering differs from the plan's literal sequence.

**3. `chrome-devtools-mcp` daemon required one implicit restart mid-session** (triggered by a `take_screenshot --filePath` call outside its default OS-temp-dir path restriction), which reset browser/page state and the previously-set viewport emulation. This was caught immediately: an `innerWidth`/`innerHeight` check after the restart showed the viewport had silently reverted to 1200px in a subsequent navigation instead of the intended 375px. All screenshots and the click/keyboard-focus behavioral checks were retaken after explicitly re-confirming `window.innerWidth`/`innerHeight` matched the intended viewport. The earlier numeric `getComputedStyle()`/`getBoundingClientRect()` measurements were not affected by this — `style.css` has exactly one viewport-gated `@media` rule (`@media (min-width: 960px)`, confirmed by grep), and it does not touch `.runway-card`, `.visually-hidden`, the global `input`/`select` rule, `.led-checkbox`, `.filter-bar__field`, or the login password field, so those measurements are viewport-independent regardless of which width was actually in effect at capture time.

## Known Stubs

None.

## Threat Flags

None — this task changes a static stylesheet, a test harness, and design-skill documentation only. No new route, input-parsing path, or trust boundary was introduced, matching the plan's own threat-model disposition (all three registered threats: mitigate/accept, no new surface).

## Status: incomplete (blocking on the developer's real phone)

All three `auto` tasks (Task 1, Task 2, Task 3) are complete, with all their `<done>` criteria met and verified against a real running server and a real (headless) browser. **Task 4 — the `checkpoint:human-verify` gate requiring confirmation on the developer's own physical phone — has not run and cannot be completed by this agent.** Per the plan, this checkpoint is `gate="blocking"` and explicitly states: "Do not self-approve on the strength of Task 3's browser measurements — the symptom is browser-theming-dependent and was reported from a real phone." Status is set to `incomplete` to reflect that the plan's stated success criteria ("no mobile browser paints a radio dot over the tiles on the developer's actual phone") is not yet confirmed, even though every other criterion (code fix, regression test, live desktop-browser measurement/screenshot proof, design-skill documentation, full test suite green) is done.

### What still needs the developer's phone

1. Reach the companion app from the phone: run `scripts/run-local-verify.sh` and hit the machine's LAN address on port 8643, or deploy to the VPS as usual.
2. On the phone, open Settings and hard-reload so it is not showing a cached `/static/style.css`.
3. Scroll to the Runway section. Confirm there is **no** stray radio dot or circle anywhere on or beside the three runway tiles.
4. Tap a runway tile that is not currently selected. Confirm the whole tile is the tap target, selection moves to it with its accent border and check glyph, and the unsaved-changes bar appears.
5. Glance at the rest of Settings on the same screen: the Theme radios and the Diagnostic LED checkbox should look exactly as before this change.
6. If a second mobile browser is available (e.g. Safari and Chrome), check both — the original artefact was browser-theming-dependent.

Report either that the dot is gone on the real device, or exactly what is still visible and in which browser, to close out this quick task.

## Self-Check: PASSED

- `companion/static/style.css` contains `input.visually-hidden` — FOUND (grep confirms 1 occurrence).
- `companion/test_companion_app.py` contains `EXPECTED_CHECK_COUNT = 107` — FOUND.
- `.claude/skills/sketch-findings-skypane/references/accessibility-contrast.md` contains the form-control caveat — FOUND (added text present in file).
- `.claude/skills/sketch-findings-skypane/references/control-density.md` contains "exempt-by-delegation" — FOUND.
- `.claude/skills/sketch-findings-skypane/SKILL.md` contains "exempt-by-delegation" — FOUND.
- Commit `556cd03` (fix) — FOUND in `git log --oneline`.
- Commit `9c25858` (test) — FOUND in `git log --oneline`.
- Commit `666f268` (docs) — FOUND in `git log --oneline`.
- Evidence screenshots at `.planning/quick/260902-l9w-fix-the-runway-picker-s-hidden-native-ra/evidence/` — FOUND (3 files, verified via `ls`).
