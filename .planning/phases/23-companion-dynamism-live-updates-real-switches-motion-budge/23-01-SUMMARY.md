---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 01
subsystem: ui
tags: [css, custom-properties, keyframes, prefers-reduced-motion, view-transitions, accessibility, motion, harness]

requires:
  - phase: 22-14
    provides: "the stray-comment-terminator guard in test_status_pages.py, which constrains every comment this plan writes into style.css"
  - phase: 22-15
    provides: "the two-block reduced-motion count this plan freezes, and the precedent that a rotating chevron carries no block of its own"
provides:
  - "--motion-fast (180ms) and --motion-slow (2s): the phase's entire motion duration vocabulary, mode-independent, in :root"
  - "@keyframes skypane-pulse: the app's first and only keyframes, cycling opacity 1 -> 0.35 -> 1, shared by D14's breathing dot and D22's pulse"
  - "a stylesheet-resident note recording the one gap the global reduced-motion override does not reach (the ::view-transition pseudo-element tree), naming 23-04 as the plan that closes it"
  - "EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS = 2 and EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS = 0: the reduced-motion floor as two named constants"
  - "the motion-budget guard in test_companion_app.py: one comment-stripped source scan every later Phase 23 plan is measured against"
affects: [23-04, 23-05, 23-06, 23-08, 23-09, 23-10, 23-11]

tech-stack:
  added: []
  patterns:
    - "a CSS vocabulary defined in one plan and consumed in later ones, made safe by a guard that asserts every reference resolves — so an unused definition costs nothing and a dangling one cannot ship"
    - "a source scan that strips /* ... */ comments BEFORE measuring, because this stylesheet's comments quote every token the scan counts"
    - "a pinned count expressed as a named module-level constant whose comment names the one plan permitted to move it, so the next plan's edit is an anticipated one-line change"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/test_companion_app.py

key-decisions:
  - "--motion-fast is 180ms and --motion-slow is 2s, an order of magnitude apart, because the two tokens are two CATEGORIES rather than two speeds: reaction (the user caused it and is watching for confirmation) and ambient (the page runs it on its own with nobody waiting). A self-initiated FADE on a refreshed region is deliberately filed as REACTION, not ambient — somebody is waiting to read the new value — which is what lets --motion-slow be long enough that the live dot breathes instead of strobing."
  - "The interpolate-size / calc-size() ban is measured on COMMENT-STRIPPED source, not raw. The plan's behaviour list says 'appear nowhere in the file' and its last line says comment text must not break any check; the second governs, so a future plan may write down WHY they are banned without failing the ban. The mutation that proves the check adds a real declaration, which is what the ban is actually about."
  - "The @media (prefers-reduced-motion: ...) blocks are REMOVED from the source the token rule scans. The global override's `animation-duration: 0.01ms !important` is a bare literal on purpose — it exists to CANCEL motion, so binding it to a motion token would invert its purpose. Their counts are asserted separately, before the removal."
  - "The view-transition gap note deliberately avoids the literal strings `@view-transition` and `view-transition-name`, because 23-04's own acceptance criteria grep the RAW file for both and expect 1 and 3. A comment containing either would have made 23-04 fail for the wrong reason — the exact defect class this phase's standing constraints name."
  - "The keyframes comment deliberately avoids the literal string `@keyframes` for the same reason: this task's own criterion greps the raw file and expects exactly 1."

patterns-established:
  - "When writing prose into a file whose counts are grepped, check every literal the prose contains against BOTH this plan's criteria and the criteria of every downstream plan that greps the same file."

requirements-completed: [CFG-32]

duration: ~50min
completed: 2026-09-13
---

# Phase 23 Plan 01: The motion budget — vocabulary and guard Summary

**The app gains two duration tokens, its first and only `@keyframes`, a written record of the one place `prefers-reduced-motion` genuinely does not reach, and a machine that fails a later plan for overspending any of it.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 2/2
- **Files modified:** 2 (0 created), +323 lines, −0

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | `3264fc6` | feat(23-01): the motion vocabulary — two duration tokens and the app's one keyframes |
| 2 | `7f4d361` | test(23-01): make the motion budget executable — one guard, five mutations |

## What landed

### Task 1 — the vocabulary

Two custom properties in `:root`, placed with the radii rather than with the
themed colours because they are mode-independent structural tokens, which is the
block's own ordering convention:

- **`--motion-fast: 180ms`** — REACTION motion. A state change the user just
  caused and is watching for confirmation of, so it has to read as the control
  responding rather than as an animation playing. Named intended surfaces: the
  Flights detail row and its rotating chevron (23-08), the save bar's entrance
  and its counting label (23-09), selection scale, wash fade, preview crossfade
  and dialog entrances (23-10), and the fades on a self-refreshed region (23-06).
- **`--motion-slow: 2s`** — AMBIENT motion. The one loop the page runs on its own
  with nobody waiting on it: the live/paused indicator's breathing dot (23-05,
  D14 + D22).

**Why the gap between them is an order of magnitude, not a factor of two.** The
plan's own framing filed "a fade-in" and "a pulse cycle" together as ambient. On
the concrete surfaces this phase actually ships, those two want durations three
seconds apart: a refreshed region's fade wants ~180ms because somebody is waiting
to read the new value, and a status-dot cycle wants ~2s or it strobes. Rather
than split the difference and produce one token that is wrong for both, the two
tokens were made two *categories* — is anyone waiting on this? — and 23-06's
self-initiated fades were filed under REACTION. Both facts are written into the
tokens' own comments so a later plan does not have to re-derive them. Neither
token is a timing function; an easing token would have been a third custom
property and the budget is two, so easing is written at the call site.

**`@keyframes skypane-pulse`** — the app's first and only keyframes. It cycles
opacity `1 → 0.35 → 1` and nothing else. Never `transform: scale()` on a dot:
these indicators are ~6px, so scaling one repaints a layout box sixty times a
second for a movement nobody can see. The floor is 0.35 rather than 0 because a
dot that vanishes outright reads as a rendering fault, not as a heartbeat. Its
comment states in the file that D14's breathing dot and D22's pulse are the same
animation sharing one block, and that two near-identical blocks is the specific
failure this single definition exists to prevent.

**The view-transition gap note**, placed immediately after the global reduce
block — a comment, not a rule. `*, *::before, *::after` matches ELEMENTS; the
`::view-transition` root and the group/old/new tree beneath it form a separate
pseudo-element tree that none of those three selectors match, so a cross-document
view transition is not switched off by the global override. The note names 23-04
as the plan that closes it, with a `prefers-reduced-motion: no-preference`
wrapper rather than by zeroing the pseudo-elements' duration, and says why: the
wrapper prevents the transition being SET UP at all instead of setting one up and
running it fast — the same reasoning `.js .mobile-nav`'s narrow `none` override
already rests on.

**Nothing was edited, only added.** `git diff` on Task 1 reported 92 insertions
and 0 deletions, which is the byte-identity of the global reduce block and the
`.js .mobile-nav` override proven mechanically rather than by inspection. No
`animation:` is declared on any selector, no per-rule reduce block was added, and
the `@supports selector(:has(*))` block was not touched.

### Task 2 — the guard

One check in `companion/test_companion_app.py`, reading `style.css` from disk and
stripping `/* ... */` comments before measuring anything. It asserts:

1. every `@keyframes` name is defined exactly once;
2. every `animation:` / `animation-name:` value resolves to a keyframes defined
   in the same file;
3. every `animation:` / `animation-duration:` value takes its duration from
   `var(--motion-*)`, with a bare time literal named in the failure message;
4. the live `reduce` block count equals `EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS`;
5. the live `no-preference` wrapper count equals
   `EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS`;
6. neither `interpolate-size` nor `calc-size(` is declared.

**Why stripping comments is the whole point, stated in the check's own comment.**
This stylesheet's comments quote every token the check counts — including this
plan's own explanatory paragraphs, which name the keyframes block, both
`--motion-*` tokens, the reduced-motion media features and the view-transition
pseudo-elements in prose. A scan over raw source would be *satisfied* by a comment
promising a rule nobody wrote, and *broken* by a comment explaining one correctly.

**The two constants carry their own governance.**
`EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS = 2` is frozen for the whole phase, with
the `accessibility-contrast.md` "dead code, not a safety net" verdict quoted in
its comment. `EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS = 0` names **23-04**
as the one plan permitted to raise it, and to exactly 1 — so that plan's edit is
an anticipated one-line change rather than a surprise failure.

**The asymmetry with `transition:` is stated as a decision, not left as an
omission.** The token rule binds `animation` only. The file's fifteen
`transition:` declarations predate this phase with bare literals and converting
them would open exactly the stylesheet-wide refactor `22-CONTEXT.md`'s D-08/T16
forbids; every `animation` declaration, by contrast, is new by construction, so
the rule can be absolute there.

## Acceptance criteria — every one run literally

All ran and returned exactly what the plan predicted. Nothing was adjusted to fit.

**Task 1** (pre-task value → post-task value):

| Criterion | Expected | Got |
|---|---|---|
| `grep -c '@keyframes' style.css` | `1` (was `0`) | `1` (pre-task `0` confirmed on the live tree) |
| `grep -cE '^\s*animation(-name)?:' style.css` | `0` | `0` |
| `grep -cE '^\s*--motion-(fast\|slow):' style.css` | `2` | `2` |
| `grep -cE '^\s*--motion-' style.css` | `2` | `2` |
| `grep -v '^ *[*/]' style.css \| grep -c 'prefers-reduced-motion'` | `2`, unchanged | `2` |
| `grep -c 'interpolate-size\|calc-size(' style.css` | `0` | `0` |
| `grep -c '@supports selector(:has(\*)) {' style.css` | `1` | `1` |
| `grep -c 'transition:' style.css` | `15`, unchanged | `15` |
| `test_config_page.py` / `test_contrast_check.py` | M/M at existing pins | `233/233` and `43/43` |
| `ruff check .` | clean | `All checks passed!` |

**Task 2:**

| Criterion | Expected | Got |
|---|---|---|
| `test_companion_app.py` new pin, only the two documented root-sandbox FAILs | — | `271/273`, both FAILs are the WR-11 read-only pair |
| `grep -c 'EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS\|EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS'` | `4` or more | `11` |
| Comment-stripping proof: `@keyframes fake-name` inside a CSS comment | harness still passes | still `271/273` |
| `ruff check .` | clean | `All checks passed!` |

**Every plan-supplied interface measurement was re-verified on the live tree
before editing and matched exactly** — keyframes 0, animation 0, transition 15,
comment-stripped reduced-motion 2, view-transition 0, `:has()` block 1,
`wc -l` 7698. No drift.

## Mutation tests

Baseline before each mutation: **271/273**. Each mutation was appended to
`style.css`, the full harness run, and the file restored from a backup; the final
`git diff` against `HEAD` for `style.css` was empty, confirming every mutation was
reverted. Every mutation produced **exactly one additional failure** (270/273) —
none was vacuous.

| # | Mutation | Result | Failure message (verbatim, after the check name) |
|---|---|---|---|
| M1 | a second `@keyframes skypane-pulse` | 270/273 | `@keyframes 'skypane-pulse' is defined 2 times in companion/static/style.css — the motion budget is ONE shared definition per animation (D14's breathing dot and D22's pulse are the same animation and share one block); two near-identical keyframe blocks is the specific failure this check exists to catch` |
| M2 | `animation: skypane-pulse 400ms linear infinite` | 270/273 | `` `animation: skypane-pulse 400ms linear infinite` takes its duration from the bare literal '400ms' — every animation duration in this file must come from var(--motion-fast) or var(--motion-slow), the whole of the phase's two-token motion budget. A plan that needs a third duration states why in its own SUMMARY instead of inlining one`` |
| M3 | a third `@media (prefers-reduced-motion: reduce)` block | 270/273 | ``companion/static/style.css carries 3 live `@media (prefers-reduced-motion: reduce)` block(s), expected 2 (EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS). The global override plus `.js .mobile-nav`'s narrow `none` are the only two; a per-rule block for a plain colour/border/shadow/transform transition is dead code, not a safety net, and the global block already covers it for free. Moving this number is a deliberate two-file edit, never a side effect`` |
| M4 | `interpolate-size: allow-keywords` | 270/273 | ``companion/static/style.css declares 'interpolate-size' — Chromium-only and Baseline limited, so it animates for some visitors and silently does nothing for the rest. Use `grid-template-rows: 0fr -> 1fr`, which 23-RESEARCH.md's own Baseline table picks for exactly this job`` |
| M5 | `animation: skypane-shimmer var(--motion-slow) linear infinite` (dangling reference — the fifth item in the plan's success criteria, beyond the four its action text lists) | 270/273 | ``  `animation: skypane-shimmer var(--motion-slow) linear infinite` names 'skypane-shimmer', which no @keyframes block in companion/static/style.css defines — a dangling animation reference renders as no animation at all and no browser reports it`` |
| M6 | `/* @keyframes fake-name */` (comment-stripping proof — must NOT fail) | **271/273, unchanged** | — |

## `EXPECTED_CHECK_COUNT`

Re-derived by **running** the harness, never by arithmetic: `272 → 273`, appended
as a new last assignment with a comment citing `23-01-PLAN.md Task 2`. The real
on-disk `check(...)` call count at execution time is 273, of which 271 pass. No
pre-existing check was retargeted, so the delta is a clean `+1`.

## Harness counts after this plan

| Harness | Before | After | Failing checks |
|---|---|---|---|
| `companion/test_companion_app.py` | 270/272 | **271/273** | 2 × WR-11 read-only (documented root-sandbox) |
| `companion/test_config_page.py` | 233/233 | 233/233 | — |
| `companion/test_contrast_check.py` | 43/43 | 43/43 | — |
| `companion/test_status_pages.py` | 267/268 | 267/268 | 1 × `anomaly_active()` (documented root-sandbox) |
| `companion/test_browser_ux.py` | 26/26 | 26/26 | — |
| `server/test_manual_resolutions.py` | 21/23 | 21/23 | 2 × WR-11 read-only (documented root-sandbox) |

`PYTHON=… bash scripts/run-all-tests.sh` reports three FAILED harnesses carrying
**exactly the documented 5-failing-check root-sandbox baseline** (4 × WR-11,
1 × `anomaly_active()`). No new failure. `ruff check .` clean. No test exception
was added anywhere.

## Deviations from Plan

**None that changed code.** Two judgement calls were made inside the latitude the
plan grants, and both are recorded rather than silent:

**1. The two token values are 180ms and 2s, not two neighbouring durations.** The
plan says "Pick the two values" and describes `--motion-slow`'s category as
covering "a fade-in, a pulse cycle". Those two want durations three seconds apart
on the surfaces this phase actually ships. Rather than pick a value wrong for
both, the categories were drawn by "is anyone waiting on this?", which puts
23-06's self-initiated fades under `--motion-fast` and leaves `--motion-slow`
free to be a calm 2s breathing cycle. Recorded here and in the tokens' own
comments. **Consequence for later plans:** 23-06 should reach for
`--motion-fast`, not `--motion-slow`, for its refresh fades.

**2. The `interpolate-size` / `calc-size(` ban is measured on stripped source.**
The plan's behaviour list says "appear nowhere in the file", and its final
behaviour says comment text must not satisfy *or break* any of the checks. The
two cannot both hold literally. The second was taken as governing, so a later
plan may document *why* the primitives are banned without failing the ban. The
mutation that proves the check (M4) adds a real declaration, which is what the
ban is about. Raw-file count is `0` today either way.

## Findings the plan did not anticipate

**1. `grep -c 'view-transition'` on `style.css` moves from 0 to 5, by design.**
The plan's `<interfaces>` measured it at 0 and then instructed the gap note to
name the `::view-transition-*` tree in the file, which necessarily raises it. No
acceptance criterion pins it, so this is not a failure — but it is worth stating,
because the note was written to avoid the literal strings **`@view-transition`**
and **`view-transition-name`** specifically. 23-04's own acceptance criteria grep
the **raw** file for both and expect `1` and `3`; a comment containing either
would have made 23-04 fail for a reason that had nothing to do with 23-04. Both
are currently `0` in the raw file and verified as such. **23-04 must keep its own
prose free of a second `@view-transition` literal for the same reason.**

**2. The keyframes comment cannot contain the string `@keyframes`,** and the
token comments cannot contain the string `transition:` — this task's own criteria
grep the raw file for both and expect `1` and `15`. Both constraints were
designed around, not discovered by a failure. This is the same trap the standing
constraints name (eight plans have hit it), extended: here the prose had to be
checked against a *downstream* plan's greps as well as its own.

**3. The global reduce block would have failed this plan's own token rule.** Its
`animation-duration: 0.01ms !important` is a bare literal. That is correct — the
block exists to cancel motion — but it means the token scan cannot simply run
over the whole file. The guard removes every `@media (prefers-reduced-motion: …)`
block by brace matching before applying the token rule, and asserts their counts
*before* that removal. The plan's behaviour list did not mention this exemption;
without it the check would have failed on the very rule it exists to protect.

**5. `CFG-32` does not exist in `.planning/REQUIREMENTS.md`.** The plan's
frontmatter claims `requirements: [CFG-32]` and `ROADMAP.md`'s Phase 23 entry
names CFG-32 through CFG-38, but `REQUIREMENTS.md` stops at CFG-31 — so
`requirements.mark-complete CFG-32` returns `not_found` and there is no checkbox
or traceability row to tick. This is a phase-setup gap that predates this plan and
sits outside its `<files_owned>`, so no row was invented. **Phase 23 needs its
seven requirement rows added to `REQUIREMENTS.md` before 23-11's coverage ledger
can be honest.** Logged to the phase's `deferred-items.md`.

**4. No markup change was needed.** The `<files_owned>` clause asked for a
finding if a token could not be introduced without one. None was: every token and
the keyframes are pure CSS, and no selector declares the animation.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-01 | mitigate | The global reduce block is byte-identical (92 insertions, 0 deletions), and its live count is now pinned by `EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS`, mutation-proven at M3. A later plan cannot weaken the floor silently. |
| T-23-02 | mitigate | Re-asserted rather than assumed: the `:has()` block count is still `1`, and `test_status_pages.py`'s zero-stray-comment-terminator guard passes with ~90 new lines of block comment in the file. |
| T-23-03 | accept | Unchanged — two durations and one opacity cycle, no user data, no secret. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. |

## Known Stubs

None. This plan ships vocabulary that is deliberately unconsumed, which is not a
stub: the guard asserts every animation reference resolves, so an unused
definition is safe by construction and a dangling reference cannot ship. 23-05 is
the keyframes' first and only consumer.

## Notes for later plans

- **23-04** raises `EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS` from `0` to `1`
  — one line in `test_companion_app.py`, already anticipated in the constant's
  comment. It must also keep its own prose free of a second `@view-transition`
  literal, since its own criterion greps the raw file for exactly one.
- **23-05** is the first consumer of `@keyframes skypane-pulse`. Its duration must
  be `var(--motion-slow)`; the guard rejects a bare literal.
- **23-06** should use `--motion-fast` for its refresh fades, not `--motion-slow`
  — see deviation 1.
- **23-11** should add the motion row to `SKILL.md`'s token register that
  `23-RESEARCH.md` item 5 calls for; this plan owns neither the skill files nor
  the design-system update.

## Self-Check: PASSED

Both modified files exist on disk; both commit hashes (`3264fc6`, `7f4d361`)
resolve in `git log`.
