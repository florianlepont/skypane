---
phase: 23-companion-dynamism-live-updates-real-switches-motion-budge
plan: 11
subsystem: docs
tags: [design-system, skill, requirements, coverage-ledger, phase-gate, motion, accessibility, no-js-floor]

requires:
  - phase: 23-01
    provides: "the two duration tokens, the keyframes block and the executable motion guard — the values this plan reads live and writes into the design system"
  - phase: 23-02
    provides: "the browser-harness helpers whose three clauses CFG-38 is ticked against"
  - phase: 23-04
    provides: "the no-preference wrapper that closes the reduced-motion floor's first named exception"
  - phase: 23-07
    provides: "the switch component this plan adds to the touch-target register, and the notifications finding it carries forward"
  - phase: 23-08
    provides: "the sticky-day-header decision and the one-directional height animation whose CFG-37 clause this plan declines to tick"
  - phase: 22-16
    provides: "the worked example this plan follows — supersessions marked IN PLACE with a stated reason, nothing deleted, verified by diff, and a row that cannot be written truthfully recorded as a finding rather than applied mechanically"
provides:
  - "sketch-findings-skypane updated in step with Phase 23: a motion contract, a view-transition entry, a live-refresh convention, a relative-time entry, the switch component, and the reduced-motion floor's first named exception"
  - "the Phase 23 coverage ledger in .planning/REQUIREMENTS.md: seven D-items walked, three findings carried forward, three struck items with their grounds"
  - "five requirements ticked with per-clause evidence and two deliberately left unticked with the unmet clause named"
  - "the phase gate: the full suite green serially and in parallel against the exact 5-name sandbox baseline, with companion/test_browser_ux.py proven to have RUN"

tech-stack:
  added: []
  patterns:
    - "a design-system row that cannot be written truthfully becomes a FINDING rather than a row — 22-16's precedent, applied twice here"
    - "a requirement clause knowingly contradicted by a shipped decision leaves the box unticked and names the clause, rather than being ticked and un-ticked a phase later"
    - "a phase gate asserted by failing-check NAMES and by a real runtime, never by a failing-file count or by the absence of an error"

key-files:
  created:
    - .planning/phases/23-companion-dynamism-live-updates-real-switches-motion-budge/23-11-SUMMARY.md
  modified:
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
    - .claude/skills/sketch-findings-skypane/references/control-density.md
    - .claude/skills/sketch-findings-skypane/references/data-density.md
    - .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "CFG-34 and CFG-37 are deliberately NOT ticked. Each has one clause the shipped code knowingly contradicts — 'EVERY relative age on screen is live' (four are not) and 'the detail row opens AND CLOSES with measured motion' (it closes instantly, on an accessibility argument that is correct). This is the CFG-28 situation of Phase 22, caught before the tick rather than a phase after it."
  - "The accent-reservation list gap is RECORDED, not repaired. Two Phase 23 accent consumers landed without the style.css header comment being extended. This plan writes documentation only and must not touch companion/; more importantly, the discipline that the list lives in exactly one place is worth more than closing this one gap in the wrong place."
  - "The floating-overlay shadow exception count moves four -> FIVE as a genuine APPEND, not a correction. It was re-derived by reading every resting box-shadow in the live stylesheet; Phase 22's four are all still there and .quick-toast is new."
  - "The 'zero new custom properties' claim is broken in the paragraph that carries it, not quietly. Phases 20, 21 and 22 each held it; Phase 23 added two duration tokens deliberately, because a motion budget with no named durations is a budget in prose and the guard cannot exist without something to point at."
  - "The phase gate is asserted by failing-check NAMES. The container runs as root, so exactly five checks fail here and pass in CI; a sixth would be this plan's. Both runs were checked against the five names, never against the count of failing files."

requirements-completed: [CFG-32, CFG-33, CFG-35, CFG-36, CFG-38]

duration: ~3h
completed: 2026-09-14
---

# Phase 23 Plan 11: The design system in step, the coverage ledger, the phase gate Summary

**The authority now carries a motion contract with values read live from the stylesheet rather than recalled, the reduced-motion floor has its first named exception after eleven phases of reading as universal, and the ledger hands the developer three decisions and two un-ticked boxes instead of a phase reported as complete — with the browser harness proven to have RUN, 54/54 in 154 real seconds, not skipped.**

## Performance

- **Duration:** ~3 h
- **Tasks:** 3/3
- **Files:** 1 created, 6 modified — **no file under `companion/`, `server/` or `deploy/` was opened for writing**, which is this plan's own `<files_owned>` constraint and is visible in `git show --name-only` on both commits

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | `dd485e1` | docs(23-11): the design system gains a motion contract |
| 2 | `f150916` | docs(23-11): the coverage ledger, and the three questions it hands back |
| 3 | *(this SUMMARY + state)* | docs(23-11): complete the phase-closing plan |

---

## Task 1 — what the design system now records

Six new or widened entries in `SKILL.md`, plus four reference files. **Every value was read from the code during the task**, and every one is reproduced by a command in the table further down.

### The motion contract (new)

A paragraph of its own in `<design_direction>`, beside spacing and controls:

- **The two tokens with their real values** — `--motion-fast: 180ms`, `--motion-slow: 2s` — and the test that sorts them, which is the part worth carrying forward: they are two **categories**, not two speeds, and the question is *"is anyone waiting on this?"* A self-initiated fade on a refreshed region is filed as REACTION, because somebody is waiting to read the new value; that is what leaves `--motion-slow` free to be long enough that the live dot breathes instead of strobing.
- **The four `@keyframes` blocks and their consumers** — `skypane-pulse` → `.is-breathing`, `skypane-fade-in` → `.is-fading-in`, `skypane-row-arrive` → `.is-new-row`, `skypane-bar-arrive` → `.dirty-bar` — and the convention that makes the count stay honest: **the classes name the MOTION, not the component**, which is what lets one rule serve two unrelated surfaces and is why a plan wanting "a value just changed" spends `.is-fading-in` rather than declaring a fifth block.
- **The standing rule**, named the way the colour-separation contract names `contrast_check.py`: `companion/test_companion_app.py`'s `_motion_budget_is_enforced_in_the_stylesheet()`, which strips comments **before** measuring (this stylesheet's comments quote every token the scan counts, so a raw scan would be satisfied by a comment promising a rule nobody wrote and broken by a comment explaining one correctly), and which additionally exempts the `@media (prefers-reduced-motion: …)` blocks from the token rule on purpose — the global override's `animation-duration: 0.01ms !important` is a bare literal because it exists to CANCEL motion, and binding it to a motion token would invert its purpose.
- **Why the rule binds `animation` and not `transition`** — 26 `transition:` declarations predate this phase with bare literals, and converting them is the stylesheet-wide refactor `22-CONTEXT.md`'s D-08/T16 forbids.
- **The one-directional entrance rule**, recorded once at the level where it now applies twice on two different mechanisms: where an element animates out of `display: none`, opening animates and closing is instant, because `allow-discrete` leaves a "closed" element focusable and in the accessibility tree for its whole exit, and a `<dialog>` that has not reached `display: none` is an invisible sheet in the top layer.
- **`::backdrop` is deliberately not animated**, for the same structural reason the view-transition tree needed its own mechanism.

### "Zero new custom properties", broken in the place the claim is made

Phases 20, 21 and 22 each carried that achievement in their own Folded-In Work entries. Phase 23 broke it **by exactly two**, deliberately, and the motion paragraph says so where a future implementer will read it rather than only in a changelog: a motion budget with no named durations is a budget in prose, and the guard above cannot exist without something to point at. Zero new colour literals, zero new families, zero new sizes.

### Three further new entries

**View transitions** (the media-wrapped at-rule, the three names, why each is in a rule of its own — `.preview-frame__image`'s declarations sit on a four-selector rule shared with two thumbnails that render once **per row**, so a name there would collide dozens of times on a page the picture is not even on), **live refresh** (one loop, one registry keyed by `nav_slug()`, the four swap skips, **announce-and-re-derive**, and **identity before position**) and **relative time** (the element, the machine instant on Europe/Paris, copy-as-data, and `static_text` as the sanctioned way to keep a no-JS floor honest under a live element).

### The reduced-motion floor's first named exception

`references/accessibility-contrast.md`'s floor entry read as universal — *"every later rule's … transition inherits this for free"* — and after eleven phases that is no longer true. Recorded with the boundary stated precisely (`*, *::before, *::after` are element selectors and name exactly two pseudo-elements; the `::view-transition` tree is a separate pseudo-element tree that none of them matches), the mechanism that closes it, and **why the media wrapper beats zeroing the pseudo-elements' durations**: the wrapper prevents the transition being SET UP, an override sets one up and runs it fast. Those are different outcomes, and the wrapper is also the strictly stronger guarantee — a transition that was never set up has no tree to acquire a future property on. Four new "What to Avoid" entries travel with it, including the one that matters most for the next reader: **do not write a reduced-motion assertion as a bare `matchMedia()` call**, because that is a statement about the browser rather than about this app and passes on the exact defect it claims to catch.

### Registers widened

| Register | Where it lives | Move |
|---|---|---|
| Floating-overlay resting shadow | `SKILL.md`, Cards | **four → FIVE**, `.quick-toast` appended; re-derived by reading every resting `box-shadow` in the live stylesheet, and the stacking order is now three deep and declared upward (tab bar 20, save bar 30, toast 40) |
| `.dot--off` consumers | `SKILL.md`, Navigation | **five → SIX**, the freshness line's live dot — also the app's only moving dot, and the entry records the two properties that make it honest (DERIVED from the loop's own two variables, synced from the four functions that change them) |
| Touch-target floor | `references/control-density.md` | **two met-directly additions**: the `role="switch"` control (44px floor on the **button**, not on the 52 × 32 track, and why that placement is load-bearing) and the Flights card face as its own `<summary>` (312 × ~120px at 360px) — neither is a trade, both are hit-area gains |
| Save-bar history | `references/settings-page-patterns.md` | **fifth entry**, and the first that is not a correction: an entrance as an `animation` rather than a transition (an `@starting-style` entry would move for some visitors and silently do nothing for the rest), no fill mode, the count's four write sites collapsed to one gated site, and the relabel made safe by the control's SHAPE |
| Sticky header | `references/data-density.md` | the Phase 22 entry's forward pointer *"sticky day headers are Phase 23"* **SUPERSEDED in place by its outcome** — Phase 23 ran, rendered both variants on the real page and declined it, with the revisit condition stated |

### Two rows that could not be written truthfully, and became findings instead

This is 22-16's precedent, which found two §4 rows wrong against the code and corrected them rather than applying them mechanically. Two here:

**1. `style.css`'s accent-reservation list is no longer exhaustive, and its own header comment says it is.** The plan's `<interfaces>` said to verify whether this phase added a consumer — *"it should not have"*. It did, twice, and the header comment was extended by nothing:

| Occurrence | Verdict |
|---|---|
| `.switch[aria-checked="true"] .switch__track { background: var(--color-accent); border-color: var(--color-accent); }` (23-07) | **NEW consumer.** Not covered by the list's "native `accent-color` of radios/checkboxes" entry — that is a native property on a native control; this is an author fill on a custom `<button>`. |
| `@keyframes skypane-row-arrive`'s `color-mix(in srgb, var(--color-accent) 22%, transparent)` (23-08) | **NEW consumer.** Not covered by the selected-card wash entry: that signals SELECTION, this signals ARRIVAL — a use the list has never carried. |
| `.history-card__summary::before { color: var(--color-accent) }` (23-08) | **NOT new** — a restatement of the already-listed `<summary>` disclosure-marker accent on a summary whose inherited text colour changed. |

Both new uses look defensible on their merits. The defect is that a list whose stated purpose is to let *"a future reader tell an intended use from an accidental one"* has quietly stopped being able to — **which is exactly how the Disconnect button's accidental accent fill survived for a phase and a half**. Recorded in `SKILL.md`'s Colour entry and in the ledger; the repair belongs in `style.css`'s own header comment and in `06.6.1-UI-SPEC.md`, and this plan owns neither.

**2. The Flights desktop table's relative age does not tick while the same row's phone card does.** The plan's `<interfaces>` credits 23-03 with the `<time>` convention and 23-08 with the list; walking the code found that `history_page._when_cell_html()` still composes from `relative_age_text()` directly. **This also corrects a stale entry of record:** 23-03's inventory routed that site to 23-08 while describing it as *"the mobile card's relative-age secondary line"* — it is the **desktop** cell, and it was not converted. Written into `references/data-density.md` as a correction, not a quiet overwrite.

### The diff is additions and in-place supersessions only

```
 5 files changed, 90 insertions(+), 14 deletions(-)
```

**All 14 deleted lines are lines amended in place**, proven mechanically rather than by reading: each removed line's text was searched for in the post-edit tree, and

- **8 survive verbatim** inside a longer line (the four `Origin` lines, the reduced-motion floor paragraph, the save-bar history's closing paragraph, and two others);
- **4 are `findings_index` table rows** whose only lost characters are the trailing ` |` — a pure append, measured at 768/770, 221/222, 810/812 and 491/493 characters surviving contiguously;
- **2 are deliberate in-place supersessions with a stated reason** — the `Current as of` line (the Phase 22 parenthetical survives verbatim, confirmed by `grep -c`) and the floating-overlay count, which carries the literal string `was FOUR SUPERSEDED`.

**No entry was deleted. No supersession was made by overwriting.**

---

## Task 2 — the ledger, and what was deliberately not ticked

### Requirement spans, re-run rather than recalled

```
$ cd .planning/phases/23-*/ && for id in CFG-32 … CFG-38; do grep -l "$id" 23-*-PLAN.md; done

CFG-32: 23-01 23-04 23-05 23-08 23-09 23-10 23-11
CFG-33: 23-04 23-11
CFG-34: 23-03 23-05 23-06 23-11
CFG-35: 23-06 23-11
CFG-36: 23-07 23-11
CFG-37: 23-08 23-11
CFG-38: 23-02 23-11
```

The same grep over the **SUMMARYs** returns a smaller set for two IDs, and both are recorded on their rows rather than papered over: **CFG-32** is echoed by 23-01/23-04/23-05/23-08/23-09 but not by 23-10, which spends the budget without restating the ID; **CFG-38** is echoed by 23-02 and by 23-01, which mentions it without claiming it.

### Ticked — five, each with its evidence on the row

| ID | Why it is genuinely met |
|---|---|
| **CFG-32** | All four clauses checked against the live stylesheet, not the plans: two shared tokens with all four `animation:` declarations spending them; four keyframes blocks, each name defined once (mutation-proven); no dangling reference (mutation-proven); and the clause that needed real work — *including pseudo-elements the global `*` selector cannot reach* — closed by 23-04's wrapper and proven in a browser in both context modes, with `::backdrop` verified live to declare no motion at all. |
| **CFG-33** | Served in full by 23-04. Per-route uniqueness proven from COMPUTED values on every element of all six routes (a source scan can only prove a declaration appears once); degradation proven by the mutation evidence itself, since M1/M3/M4 each changed only whether the at-rule is set up and every pre-existing browser check stayed green throughout. |
| **CFG-35** | Registry, page key, and all three named skips, each proven in a browser **with a control proving the opposite outcome** — including the repair of a source clause that mutation found vacuous *after it had shipped in a commit*. Zero requests from a hidden tab, proven by counting requests rather than by reading the DOM. |
| **CFG-36** | Every clause, and the commit order is part of the evidence: the absent-field fix lands **before** the control moves, so no commit in history has the LED's control absent while an absent field still means `False`. Scripts-blocked operation proven by **SAVING and reading back from disk** at 360px in both languages, for all three switches. |
| **CFG-38** | All three clauses: one no-JS helper that is now the file's **only** `java_script_enabled=False` call site (3 → 1), a named 360px viewport constant with the width ladders derived from it, and a disclosure sweep made motion-proof through the app's own override — proven still to see its own defect by reproducing 260913-eab's mutation in both its forms at byte-identical numbers. Its sibling exposure, which 23-02 recorded and deliberately left alone, was closed by 23-08. |

### NOT ticked — two, with the unmet clause named

**This is the phase-22 CFG-28 error, caught before the tick instead of a phase after it.** In Phase 22, CFG-28 was marked complete and then had to be un-ticked when 22-12 found Health's clock rendering a raw UTC ISO in its `title`, failing the "every tooltip" clause.

**CFG-34 — "Every relative age on screen is live."** Three of four clauses hold (the convention, the one-second ticker, visibility-awareness — all mutation-proven). The first does not. Four visible ages do not tick, and they were **not left static by decision** — three were simply unowned, and one was explicitly routed to a plan that did not convert it:

| Site | Status |
|---|---|
| Flights **desktop** When cell | convertible, unowned — the age ticks below 960px and is frozen above it, on the same row |
| Display's Calendar status detail | convertible, unowned |
| Health's unresolved-prefix registry cells | convertible, unowned |
| Health's battery `when` text | **structurally blocked** — `battery-trend.js` writes it into a `title` with `setAttribute`, markup in a `title` renders as literal angle brackets, and a shipped check pins that the script does no client-side date math |

The requirement's own final clause allows static ages *"that deliberately stay static"* to be enumerated — but "deliberately" is the word that fails here, and the enumeration is this plan's, written after the fact.

**CFG-37 — "the detail row opens *and closes* with measured motion."** Two of three clauses hold. It opens with a real height; **it closes instantly, on purpose**, because `allow-discrete` keeps a closed row's controls in the tab order and the accessibility tree for the whole of its exit — measured, 4 of 4 focusable. **The code's trade is right; the requirement's wording is what is wrong.**

### The three findings carried forward

1. **D2's fourth switch (notifications) is not built.** The mechanism is available (`save_device_config()` takes `notifications` as a whole-dict replacement); what is missing is a decision about the card, whose two checkboxes share space with a Save-governed URL field. Converting only the checkboxes makes a card that is half instant and half Save; converting the field too means an instant-apply text input the save bar exists to avoid; keeping the checkboxes *and* adding switches is two controls for one setting — the X1/D-04 defect Phase 22 removed. Settled as **option A** on the ROADMAP; verified untouched at close (`grep -c 'quick/notifications' companion/app.py` → **0**).
2. **D7's sticky day headers are not built** — and this one is **already decided**, carried forward so it is not re-proposed rather than because it is open. Both variants were rendered on the real page with seeded data at the same scroll offset, and **every flight row already carries its own date**, so a pinned title repeats what is on every line — while the sticky variant shrinks the list to a ~7-row box in a half-empty page. Verified at close: `grep -cE 'position: *sticky'` → **3**, its pre-phase value, two of them prose. Revisit condition stated and narrow: only if the per-row date is removed.
3. **Two requirement clauses are knowingly contradicted by shipped decisions** (CFG-34 and CFG-37, above). Each needs the same call: amend the clause to match the shipped choice, or schedule the work that makes the clause true.

Plus one design-system finding: **the accent-reservation list gap**, recorded above.

### The three struck items, with their grounds

Recorded so a future audit meets the reasoning rather than the idea.

- **D9 (SSE) — rejected, not deferred**, because the events it would emit originate in `server/poll_loop.py`, which runs `Type=oneshot` under a 30-second timer: **the process exits every cycle, so there is no hook to register**, and an SSE endpoint would have to poll the database itself. **The thread cost is not the reason, and the brief's original premise was WRONG:** the research measured the connections (~29–46 KB RSS each, returning to baseline on disconnect), found the ~1 s burst-latency tail to be the `request_queue_size = 5` accept backlog present at N=0, and corrected the assumption that companion streaming could starve the frame — the device's poll is served by a **separate** systemd unit on its own port with its own Caddy block. The correct reason is recorded; the original one is recorded as corrected.
- **D12 (service worker) — out of scope on a verified security finding.** In the project's own harness Chromium, `cache.put()` stores a `Cache-Control: no-store` body **verbatim**; every HTML response here is `no-store` precisely because every page is session-gated, so a service worker would persist authenticated content past sign-out. **Reopening requires a tested de-registration path first, because a 404 leaves the registration live** — retirement is not deletion.
- **D3's overlay drawer — struck on its third proposal.** It contradicts `22-CONTEXT.md`'s D-10 and three recorded design-system rejections, one of them established by real-device testing, and `references/mobile-navigation.md` already warns that this exact reopening happened once before. It also targets a component Phase 22 retired.

---

## Task 3 — the phase gate

### The browser harness RAN, and did not skip

This is the gate's own point: a `SKIP` line means this phase's interaction contracts were never checked, and this phase is almost entirely interaction.

```
$ time companion/test_browser_ux.py
browser-ux: 54/54 checks pass
REAL_SECONDS=154.136020015
```

- **Last line of output, verbatim:** `browser-ux: 54/54 checks pass`
- **`grep -c SKIP` over the whole output: `0`**
- **Real runtime: 154.1 s standalone**, **155.4 s** inside the final serial suite, ~160 s inside the parallel one. A skipped harness returns in well under a second; **154 seconds of real wall clock is the strongest available evidence that 54 real browser checks ran.** For scale, the harness is now **65% of the serial suite's entire wall time** (155.4 s of 240 s).

### The failing set, by NAME

The sandbox baseline is exactly **five** failing checks because this container runs as root; they pass in CI. **Verified by name, never by failing-file count** — a sixth failure would be this plan's.

1. `POST /airlines/resolve redirects with the manual_save_failed flash key … when add_entry() cannot write because the state dir is read-only … (WR-11)`
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)`
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created … (WR-11)`
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write … (WR-11)`
5. `anomaly_active() runs on every page render and must never raise — missing/empty/file/corrupt-db inputs all degrade safely`

Four × WR-11 read-only, one × `anomaly_active()`. **The same five names in the serial run and in the parallel run.** No new failure.

### Both runs, over the final committed tree

| Run | Result | Wall time | `browser_ux` inside it |
|---|---|---|---|
| `PYTHON=… JOBS=1 bash scripts/run-all-tests.sh` | 3 FAILED harnesses carrying **exactly the 5-name baseline** | **240 s** | 54/54, 155.4 s, `grep -c SKIP` = **0** |
| `PYTHON=… bash scripts/run-all-tests.sh` (JOBS=4) | the **same 5 names** | **160.6 s** | 54/54, `grep -c SKIP` = **0** |
| `ruff check .` | `All checks passed!` | — | — |
| Coverage | `TOTAL 6927 490 93%` — floor 83, in **both** runs | — | — |

Per-harness, identical in both runs: `browser-ux 54/54`, `companion-app 289/291`, `status-pages 286/287`, `config-page 240/240`, `view-pages 153/153`, `contrast-check 43/43`, `i18n 24/24`, `manual_resolutions 21/23`. The two failing totals and the one failing total are the five baseline names and nothing else.

An earlier serial/parallel pair was run mid-task and reported the same five names, the same counts and the same 93% at 239.6 s / 159.1 s; the figures above are the re-run over the committed tree.

### Every harness's count, against its Phase 22 starting value

Re-derived **by running**, never by arithmetic; every delta attributed to the plan that claimed it. **There is no unattributed delta.**

| Harness | Phase 22 end | Phase 23 end | Δ | Attributed to |
|---|---|---|---|---|
| `test_browser_ux.py` | 26 | **54** | +28 | 23-02 +0 (a refactor at zero net checks, proven by AST-comparing every description against HEAD), 23-04 +2, 23-05 +4, 23-06 +6, 23-07 +4, 23-08 +5, 23-09 +3, 23-10 +4 |
| `test_companion_app.py` | 272 | **291** | +19 | 23-01 +1, 23-05 +8, 23-07 +9, 23-09 +1 |
| `test_status_pages.py` | 268 | **287** | +19 | 23-03 +5, 23-05 +3, 23-06 +7, 23-07 +2, 23-08 +2 |
| `test_config_page.py` | 233 | **240** | +7 | 23-06 +2, 23-07 +2, 23-09 +2, 23-10 +1 |
| `test_view_pages.py` | 143 | **153** | +10 | 23-03 +3, 23-08 +6, 23-10 +1 |
| `test_i18n.py` | 24 | **24** | 0 | net zero by design — 23-03 and 23-05 added catalogue entries, 23-07 removed one orphaned by the retired LED checkbox; each recorded in place rather than by a new assignment |
| `test_contrast_check.py` | 43 | **43** | 0 | **no colour moved in the entire phase** |

### The stylesheet's structural pins, re-derived at close

Every number this plan wrote into the design system, with the command that produces it:

| Value | Command | Result |
|---|---|---|
| `--motion-fast` / `--motion-slow` | `grep -oE '\-\-motion-(fast\|slow): *[0-9a-z]+' style.css` | `180ms` / `2s` — **diffed against the skill's own text, not read**: MATCH |
| keyframes blocks | `grep -c '@keyframes' style.css` | **4** |
| animation declarations | `grep -nE '^\s*animation:' style.css` | **4**, all spending a token |
| reduce blocks | `grep -v '^ *[*/]' style.css \| grep -c 'prefers-reduced-motion: reduce'` | **2** |
| no-preference wrappers | `grep -v '^ *[*/]' … 'no-preference'` | **1** |
| `@starting-style` blocks | `grep -v '^ *[*/]' style.css \| grep -c '@starting-style'` | **2** |
| `view-transition-name` | `grep -cE '^\s*view-transition-name:' style.css` | **3** |
| `@view-transition` | `grep -c '@view-transition' style.css` | **1** |
| `:has()` feature query | `grep -c '@supports selector(:has(\*)) {' style.css` | **1** — unchanged, the phase's single largest cascade risk |
| `transition:` | `grep -c 'transition:' style.css` | **26** |
| `position: sticky` | `grep -cE 'position: *sticky' style.css` | **3** — its pre-phase value, two of them prose |
| deferred-script pin | `grep -n '_fourteen_deferred_scripts_before_closing_body' test_companion_app.py` | **14** |
| switch geometry | the `.switch` / `.switch__track` / `.switch__thumb` rules, read verbatim | `min-width`/`min-height` **44px**; track **52 × 32**; thumb **24 × 24**, `translateX(20px)` |
| fixed-overlay stacking | `grep -n 'z-index' style.css` | tab bar **20**, save bar **30**, toast **40** |
| floating-overlay resting shadows | every non-hover `box-shadow` declaration, read | **5** (`.lightbox`, `.dirty-bar`, `.mobile-nav`, `.tab-bar`, `.quick-toast`) |
| `.dot--off` consumers | `grep -rn 'dot--off' companion/*.py companion/pages/*.py companion/static/*.js` | **6** |

### The no-JS floor, re-asserted phase-wide rather than per plan

The phase-level claim is only true if someone checked it after all ten plans landed. Machine-checkable half, at close:

- **Display still saves with scripts blocked**, at **360px**, in **both** languages, through the fallback Save, with the value read back from `device_config.load_device_config()` **on disk** — not from the DOM. This is the assertion that would catch the Phase 22 P0 recurring.
- **All three switches save with scripts blocked**, same conditions, all three read back from disk.
- **The fallback Save is proven VISIBLE with a real box**, not merely present — the distinction is precisely the shape B1 took.
- **The Flights detail rows are all open with scripts blocked** (`.flight-detail-row--collapsed` count is 0), and the entry animation is **structurally unavailable** to that reader, since both it and its `@starting-style` block are scoped to a class only the script adds.
- **The whole-card tap works with scripts blocked** — it is the same native `<details>` the card already contained.
- **Nothing this phase added renders a control that does nothing without script.**

The visual half is the human sweep below.

---

## The human sweep — six checklists, walkable in one pass

Drawn from every plan's own `<human-check>` line and grouped so the developer walks it once rather than eleven times. **This is the other half of wave 9 and is not this plan's to perform or to claim.**

**1. Motion, default settings.**
- Navigate Home → Display → Flights and watch the page transition (the sidebar, the page title and the frame picture are the three named participants).
- Change a setting on Display: the save bar should **arrive** (sliding up ~16px) rather than appear. Change a second: the count moves, and moves again.
- Press Save: the button says its in-flight word in your language, then the landing page carries the confirmation banner.
- Click through several theme chips: the selection answers with a scale and a wash, and the live preview **cross-fades** rather than cutting. Press Cancel mid-fade — the preview must settle on the **saved** theme, not the discarded one.
- Open and close both dialogs (a Flights panel picture and the Airlines gallery) and a Flights detail row.

**2. Motion, reduce-motion on** (OS setting, then reload). Repeat all of the above: **navigation is instant** (no cross-fade at all — the transition is never set up, so you should see today's behaviour exactly), the live dot is **static**, nothing animates, and **everything still works**. The save bar still appears, the detail row still opens, the preview still changes.

**3. Live.**
- Leave Home open for two minutes: the countdown falls, the tiles update, **the page does not jump** and nothing moves under your cursor.
- Leave Flights open until a detection lands: the new row should be obvious **once** and then settle. A row that was already there must never flash.
- Watch Health's freshness age tick and the dot breathe.
- **Stop the server**: the dot stops breathing and a **neutral** (not orange) Reconnecting badge appears. Restart it and watch it recover.

**4. Switches.** On a phone-sized window, flip Screen, Quiet hours and the LED: the state changes **under your finger**, before the server answers. Stop the server and flip one: it **comes back** and says so, in a sentence, in French too.

**5. The floor — scripts blocked, 360px, both languages.** Save a setting on Display. Save one on Device. Flip all three switches. Open a Flights detail row and tap a phone card's face. Read Home. **Everything must work, and nothing may render a control that does nothing.**

**6. Layout.** Hard-reload Home on a **throttled** connection, at a **desktop** width, and confirm nothing jumps when the picture arrives — this is the one with a measured before/after, and it was broken by ~500px at 1280px until 23-10 found it. Then look at **Display's and Flights' headers at 360px**: both now carry a freshness line above their captions, and the "Updating…" pill shares the header's top-right corner. Confirm it reads as a caption under the title rather than as a competing header row.

---

## Deviations from Plan

**1. [judgement] Two requirements were left unticked that the plan's frontmatter lists as this plan's to complete.** `requirements: [CFG-38, CFG-32, CFG-33, CFG-34, CFG-35, CFG-36, CFG-37]` names all seven. CFG-34 and CFG-37 each have one clause the shipped code knowingly contradicts, and the standing instruction for this wave is explicit that a requirement whose clauses are only partly met must not be ticked. Recorded on each row with the clause named and the decision it needs. **Ticking them would have repeated the exact error Phase 22 made with CFG-28**, which had to be un-ticked a plan later.

**2. [scope] The accent-reservation gap was recorded, not repaired.** The plan's `<interfaces>` says to extend the list in `style.css`'s header comment *"first"* if this phase added a consumer. It did, twice — but `<files_owned>` forbids this plan from editing a single file under `companion/`, and the plan's own instruction for this case is that a row which cannot be written truthfully becomes a finding. Both instructions point the same way once the list turns out to be wrong rather than merely incomplete: the repair is a stylesheet edit with its own verification, and the discipline that the list lives in exactly one place is worth more than closing the gap in the wrong file.

**3. [judgement] `data-density.md`'s sticky entry was already half-written.** Commit `c9628b4` ("record the developer's two decisions on the open findings") had converted the **day-separator** paragraph's sticky sentence into a settled decision before this plan ran. What was still stale were the *other two* sticky mentions: the Phase 22 SUPERSEDED entry's forward pointer (*"sticky day headers are Phase 23 (D7)"*) and the "What to Avoid" entry's closing clause (*"that is D7, Phase 23, not a token swap"*). Both were superseded in place with the outcome rather than a third copy of the decision being appended.

**4. [process] `REQUIREMENTS.md` was re-read immediately before editing, and it had changed.** A parallel agent planning Phase 26 committed `ba6a25e` during this plan's window, adding CFG-53…CFG-61 and moving every Phase 23 row down by nine lines. The edits were applied by matching on row content rather than on line number, and the resulting diff is **12 deletions: the seven Phase 23 rows this plan rewrote and the five checkboxes it ticked, and nothing else** — verified before staging. Only `.planning/REQUIREMENTS.md` was staged, by explicit path; no `git add -A`, no `git add .`, no `git commit -a`.

**5. [judgement] `gsd-sdk query requirements.mark-complete` was NOT run.** Its two jobs — ticking the checkboxes and updating the traceability table — were both done by hand in Task 2, with far more evidence per row than a generated line carries, and re-running it over a file a parallel agent is also writing risks overwriting exactly the evidence this plan exists to record. The state verbs that do not touch `REQUIREMENTS.md` (`state.update-progress`, `state.record-metric`, `state.add-decision`, `state.record-session`, `roadmap.update-plan-progress`) were all run normally. `state.advance-plan` returned `{"advanced": false, "reason": "last_plan", "status": "ready_for_verification"}`, which is the correct edge case for the last plan of a phase.

**6. [Rule 1 — Bug, caused by a tool this plan invoked] A state verb rewrote a line inside `STATE.md`'s explicitly-preserved historical block, and it was restored.** That file carries a demoted, superseded YAML block introduced by a note saying it is *"Kept verbatim, as data, no longer parsed as state"*. One of the SDK state verbs matched the **second** `status:` occurrence in the file and rewrote that block's `status: Ready to execute` to `Phase complete — ready for verification` — silently editing a historical record whose only value is being verbatim. Restored to its original string, with the live frontmatter's own `status: verifying` left exactly as the verb set it. Worth knowing before the next phase closes: **this is a tool behaviour, not a one-off, and any file with a second `status:` key is exposed to it.**

**7. [process] The full suite was run four times, not twice.** Once standalone for the browser harness (to get its real runtime in isolation), once serially and once in parallel while Task 1's edits were in flight, and once more serially-then-in-parallel over the final committed tree. The re-run is belt-and-braces: the only files this plan changes are under `.claude/` and `.planning/`, and the three harnesses that read anything under `.planning/` read `06.6.3-CONTEXT.md`, `20-UI-SPEC.md` and `21-UI-SPEC.md` — none of which this plan touches. Verified rather than assumed.

## Findings the plan did not anticipate

**1. The `.dot--off` register was a consumer short before this plan, and Phase 23 made it two short.** `SKILL.md` recorded the nav reminder plus four further consumers; the live code carries six, the sixth being the freshness line's own live dot — which `layout.py` renders from the promoted `freshness_line_html()` on all four refreshing pages. Recorded as a widening, with the count stated.

**2. `.quick-toast` is a floating overlay nobody filed as one.** 23-07 shipped it with `box-shadow: var(--shadow-card-hover)` at rest and `z-index: 40`, which makes it the fifth member of a list `SKILL.md` describes as exhaustive and which was *already* found stale by one before Phase 22. This time the count was re-derived by reading every resting `box-shadow` in the stylesheet rather than by adding one to the recorded total — which is what turns "append a fifth" into a claim worth trusting.

**3. The one-directional entrance rule was discovered twice, independently, by two plans, and neither knew it was a rule.** 23-08 argued it for the Flights detail row (a closed row's controls stay focusable) and 23-10 argued it again for `<dialog>` (an un-hidden modal is an invisible sheet in the top layer), each writing its reasoning into the stylesheet at its own declaration. It is now recorded once, at the level where it applies to both, which is the kind of thing this closing plan exists to notice.

**4. `test_browser_ux.py` more than doubled, and every one of the 28 added checks is attributable.** The harness went 26 → 54 and its runtime 52 s → 154 s. That is ~100 seconds of new real wall clock in one phase, almost all of it deliberate waits (a forced refresh is a real HTTP round trip plus a settle, and a "the user sees it change" assertion cannot be faster than the thing it watches). Worth knowing before Phase 24 adds more: **this file is now 65% of the serial suite's wall time.**

**5. `deferred-items.md` carries three entries addressed to "whichever plan next edits" a file this plan does not own**, and they are still open: the two scripts-blocked checks that fail by a 30-second Playwright timeout rather than a message, `test_i18n.py`'s Check 6 comment promising an exclusion it does not implement, and the dead `.now-showing__image` selector. None is a correctness gap; all three are cheap. Left where they are rather than closed from a documentation plan.

## Threat model

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-23-40 | mitigate | Every value written into the skill was read live at execution time and is reproduced by a command in the table above; the two token values were **diffed** against `style.css` rather than read. Two rows that could not be written truthfully became findings instead of rows, following 22-16's precedent. |
| T-23-41 | mitigate | The coverage ledger walks all seven D-items against the ten SUMMARYs and the code, and the walk is recorded. Two requirements were left **unticked** with the unmet clause named, three findings carry forward with the decision each needs, and three struck items carry their grounds. Nothing was reported as shipped that is not. |
| T-23-42 | accept | Unchanged — documentation only. No code, no route, no runtime change; no file under `companion/`, `server/` or `deploy/` was opened for writing. |
| T-23-SC | n/a | Zero packages installed in any ecosystem. No `npm`, `pip` or `cargo` command was run. |

**Threat flags:** none. This plan adds no endpoint, no auth path, no file access pattern and no schema change.

## Known Stubs

**None.** This plan ships documentation, and every claim in it is either reproduced by a command recorded beside it or explicitly marked as a finding, a decision needed, or a human-sweep item. The two unticked requirement boxes are **not** stubs — they are the honest state of two clauses, recorded as such.

## Notes for later plans

- **Phase 24 inherits a motion budget with a guard.** Four keyframes blocks, two tokens, a reduce count pinned at 2 and a no-preference count pinned at 1 and frozen. CFG-45's "spends only from the existing motion budget" is enforced by `_motion_budget_is_enforced_in_the_stylesheet()`, and a fifth keyframes block needs the same kind of written argument the second, third and fourth each carry in the stylesheet.
- **Whichever plan next edits `companion/static/style.css`** owes the accent-reservation list two entries — the switch's on-state track fill and the new-row arrival wash — with the reasoning in `SKILL.md`'s Colour entry.
- **Whichever plan next owns `history_page.py`, `config_page.py` or `health_page.py`** can close three-quarters of CFG-34 by converting three call sites; the fourth needs `battery-trend.js`'s transport changed first.
- **The design system's two new conventions are the ones most likely to be re-derived from scratch:** announce-and-re-derive (a script that swaps regions dispatches one event and knows nothing about its listeners) and identity-before-position (a row's own database key beside, never instead of, the render index). Both are in `SKILL.md`'s Live refresh entry.
- **Do NOT mark the PR ready or merge.** The developer reviews Phase 23 visually first; the six checklists above are that review, and it is the other half of this wave.

## Self-Check: PASSED

Run, not asserted:

```
FOUND: .claude/skills/sketch-findings-skypane/SKILL.md
FOUND: .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
FOUND: .claude/skills/sketch-findings-skypane/references/control-density.md
FOUND: .claude/skills/sketch-findings-skypane/references/data-density.md
FOUND: .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
FOUND: .planning/REQUIREMENTS.md
FOUND: .planning/phases/23-.../23-11-SUMMARY.md
FOUND: dd485e1   FOUND: f150916
```

`git show --name-only` over both commits lists **exactly those six files and nothing else** — **no file under `companion/`, `server/` or `deploy/` was touched**, which is this plan's binding `<files_owned>` constraint proven mechanically rather than by inspection. No `git stash`, no `git clean`, no `git reset --hard`, no blanket `git checkout --`; every stage was by explicit path, and `REQUIREMENTS.md` was re-read immediately before editing because a parallel agent writes it too.
