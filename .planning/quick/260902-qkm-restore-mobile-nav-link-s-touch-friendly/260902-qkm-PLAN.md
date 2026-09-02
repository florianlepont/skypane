---
phase: quick-260902-qkm
plan: 260902-qkm
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/static/style.css
  - companion/test_companion_app.py
  - .claude/skills/sketch-findings-skypane/SKILL.md
  - .claude/skills/sketch-findings-skypane/references/mobile-navigation.md
  - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
autonomous: false
requirements: [QUICK-260902-qkm]

must_haves:
  truths:
    - "The root cause is confirmed verbatim in the current source, not assumed. `companion/static/style.css` lines 591-603 define `.mobile-nav__link` with `height: 32px` and `font-size: var(--font-label-size)`; line 83 defines `--font-label-size: 14px` and line 84 defines `--font-body-size: 16px`. `git log -L 591,603:companion/static/style.css` shows commit 5d54087 (`feat(06.6.4-04): tighten both nav renderers to 32px single-signal pills (D-05/D-05a)`) changing exactly `min-height: 44px` to the 32px fixed height and `var(--font-body-size)` to the Label-size token in this rule. The pre-D-05 values are therefore `min-height: 44px` (a minimum, not a fixed height) and `var(--font-body-size)`, read off the actual diff rather than inferred from the 44px/16px shorthand."
    - "The two nav renderers are NOT symmetric in reach, which is why one D-05 edit produced one correct outcome and one wrong one. `.dashboard-sidebar` (style.css line 852) is `display: none` at base and only revealed inside the `@media (min-width: 960px)` block (line 3127), so `.sidebar-link`'s compaction is structurally desktop-only. `.mobile-nav__link` has no breakpoint scoping anywhere in the file — greps place it at lines 591, 610, 621, 902 (comment), 911, 916, 1222 (comment), 1382 (comment) and none of those sit inside a media query — so its 32px applied at every viewport width, including the 375px phone case where it is the ONLY nav."
    - "The fix is a two-property revert inside one rule: `height: 32px` becomes `min-height: 44px` and the Label-size font token becomes `var(--font-body-size)`. Nothing else in that rule changes — D-05a's `border-radius: var(--radius-control)` (which replaced the old `border-left: 3px solid transparent`) is the single-signal pill idiom shared with `.sidebar-link--active` and is correct, so the revert stops short of it. `.sidebar-link` (lines 862-874), `.mobile-nav__link--active` (610-615), the `:not()`-scoped hover (621-623) and the WR-01 colour pair (910-918) all stay byte-identical."
    - "`companion/layout.py` needs NO change, and this is verified rather than assumed. `_mobile_nav_html()` (lines 750-776) builds each link as `'<a class=\"%s\" href=\"%s\">%s%s</a>'` — label text plus the optional health dot, with NO `icon_html()` call (unlike `sidebar_nav()` at line 670, which does prefix an `icon-nav-*` glyph). There is no inline style, no fixed-size wrapper and no 32px-tuned literal anywhere in the mobile nav markup path, so a taller row needs no compensating markup change."
    - "The panel's fixed `max-height: 420px` clip (style.css line 552, `.js .mobile-nav--open`) still has headroom after the change, and it is measured live rather than only computed. Arithmetic: `.mobile-nav__nav` contributes 8px+8px padding with no row gap, four NAV_TABS links (Settings, Health, Airlines, History) go 4x32=128px to 4x44=176px, so the nav region goes 144px to 192px; `.mobile-nav__footer` (8px+8px padding, 8px gap, 1px hairline, theme row plus Sign out) adds roughly 85px, for a total near 277px against the 420px ceiling. The live check confirms the open panel's `scrollHeight` does not exceed its rendered height, so no link and no footer control is clipped."
    - "No test in the repo hardcodes this rule's geometry, verified by grep before editing: the only `.mobile-nav__link` reference in `companion/test_companion_app.py` is line 942's serif-boundary forbidden-selector list (which asserts the rule does NOT use `--font-serif`, and stays true because the revert keeps `font-family: var(--font-ui)`), and the only `32px` hit across all Python files is `companion/test_status_pages.py:1469`, which is about the 240px sidebar plus `--space-xl` gutter and is unrelated. There is no stale assertion to retarget, so a NEW guard is added instead of an edited one."
    - "A regression guard lands in `companion/test_companion_app.py` alongside the existing stylesheet-contract checks, pinning both halves at once: the mobile dropdown link carries the 44px minimum at Body size AND the desktop sidebar link still carries its 32px Label-size compaction. Pinning both is what makes the guard un-satisfiable by a future pass that simply re-shrinks the mobile link, and equally un-satisfiable by one that 'restores' the desktop sidebar. `EXPECTED_CHECK_COUNT` moves 107 to 108 with a dated provenance comment in the file's own idiom."
    - "The stylesheet's own touch-target floor register (lines 1220-1234) stops claiming a floor-loss that no longer exists. Its traded-away enumeration is corrected to name only the desktop sidebar selector, its kept-the-floor clause gains the mobile dropdown link, and the entry count stays at four (text buttons, desktop sidebar nav links, theme-picker segments, filter input) so the closing 'four named selectors' criterion sentence remains accurate. `.sidebar-link`'s own place in the traded list is untouched."
    - "The design skill is corrected in the same commit series, because it is the artifact a future UI phase reads instead of the stylesheet. Two lines currently state the wrong geometry: `references/mobile-navigation.md` line 17 ('Link geometry') plus its CSS excerpt at lines 56-60, and `SKILL.md` line 39's floor register. `references/accessibility-contrast.md` line 23's 'four named selectors (buttons, nav links, ...)' is narrowed to the desktop sidebar. `references/control-density.md` needs NO change: its two `.mobile-nav__link` mentions (lines 7 and 17) are about the 4.5% hover wash and the 12% active pill, both still true."
    - "The restored geometry is proven by live measurement in a real running `companion/app.py` at a real 375px mobile viewport with the dropdown actually open, not by computed-style inspection of a desktop window alone — this bug class already escaped a computed-style-only check once on this project. Every `.mobile-nav__link` reports a bounding-rect height of at least 44px and a computed `fontSize` of 16px at 375px, a 375px screenshot of the open dropdown is captured, and the same session at 1280px confirms `.sidebar-link` still measures 32px at 14px."
    - "`scripts/run-all-tests.sh` reports `==> Result: PASS` with ZERO failing harnesses — the state it was in immediately before this task. No harness that passed before this task fails after it."
  artifacts:
    - path: "companion/static/style.css"
      provides: "`.mobile-nav__link` restored to `min-height: 44px` at `var(--font-body-size)`, with a rewritten head comment recording why D-05's trade did not belong on this selector, and a corrected touch-target floor register"
      contains: "min-height: 44px"
    - path: "companion/test_companion_app.py"
      provides: "A stylesheet-contract check pinning the mobile dropdown link's restored 44px/Body-size geometry together with the desktop sidebar link's surviving 32px/Label-size compaction, plus EXPECTED_CHECK_COUNT at 108"
      contains: "EXPECTED_CHECK_COUNT = 108"
    - path: ".claude/skills/sketch-findings-skypane/references/mobile-navigation.md"
      provides: "The Link geometry paragraph and the CSS excerpt corrected to the restored 44px minimum at Body size, with the reason the two nav renderings are no longer dimensionally identical"
    - path: ".claude/skills/sketch-findings-skypane/SKILL.md"
      provides: "The touch-target floor register naming only the desktop sidebar link in its traded-away nav entry"
    - path: ".claude/skills/sketch-findings-skypane/references/accessibility-contrast.md"
      provides: "The 'floors that survived' paragraph narrowed from 'nav links' to the desktop sidebar links"
  key_links:
    - "`.mobile-nav__link`'s restored `min-height` and the `.js .mobile-nav--open { max-height: 420px }` clip — the panel grows about 48px taller; if the clip were exceeded, the Sign out control and theme picker would silently disappear behind `overflow: hidden` and the fix would trade one mobile-navigation bug for a worse one."
    - "`.mobile-nav__link` and `.sidebar-link` share a head comment lineage and an active-pill idiom but must now diverge on size — the regression guard asserting BOTH geometries in one check is what keeps a future density pass from re-coupling them."
    - "The stylesheet's floor register and the design skill's floor register are two copies of one audit; both must move the mobile selector out of the traded list, or the next UI phase reads a register that contradicts the CSS it describes."
---

<objective>
Restore the mobile hamburger dropdown's nav links to their pre-D-05 touch-friendly size, reverting a mistaken side effect of 06.6.4-04's D-05 desktop-compactness decision.

Purpose: D-05 was a desktop Linear-style density pass. It correctly compacted `.sidebar-link` (structurally desktop-only) but also landed on `.mobile-nav__link`, which is unconditionally the mobile-only nav at every viewport below 960px. The developer reports the result makes phone navigation harder — a 32px row at 14px is a worse tap target than the 44px/16px it replaced, and on mobile there is no compactness argument to trade against.

Output: `.mobile-nav__link` back to `min-height: 44px` at `var(--font-body-size)`; the desktop sidebar's compaction untouched; both floor registers (stylesheet and design skill) corrected; a regression guard pinning the two geometries apart; live proof at 375px and 1280px.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@companion/static/style.css
@companion/layout.py
@companion/test_companion_app.py
@.claude/skills/sketch-findings-skypane/references/mobile-navigation.md

Design-system skill: `Skill("sketch-findings-skypane")` is the companion app's living design reference and is maintained continuously across phases. It currently documents the WRONG mobile geometry in two places; Task 2 corrects it.

Local run recipe: `scripts/run-local-verify.sh` starts a real `companion/app.py` on port 8643 with `SKYPANE_COMPANION_PASSWORD=local-verify-only` against `/tmp/skypane-prod-state`. Nav routes come from `companion/layout.py`'s `NAV_TABS`: `/settings`, `/health`, `/airlines`, `/history` (D-26 renamed `/config` to `/settings`; the old path 404s by design). Login is `/login`.

Line numbers below were read from the current working tree during planning. Re-confirm each before editing — do not edit by line number alone.
</context>

<tasks>

<!-- planner-discipline-allow: 32px -->
<!-- planner-discipline-allow: height: 32px -->
<!-- planner-discipline-allow: font-label-size -->

<task type="auto">
  <name>Task 1: Restore the mobile dropdown link's 44px/16px geometry and correct the stylesheet's floor register</name>
  <files>companion/static/style.css</files>
  <read_first>
    - `companion/static/style.css` lines 583-623 (the `.mobile-nav__link` rule, its head comment, the active modifier and the `:not()`-scoped hover)
    - `companion/static/style.css` lines 527-553 (`.mobile-nav`, the `.js`-gated clip, and the `max-height: 420px` open state)
    - `companion/static/style.css` lines 856-918 (`.sidebar-link` and every nav rule that must stay byte-identical)
    - `companion/static/style.css` lines 1220-1234 (the 44px touch-target floor register)
  </read_first>
  <action>
    Change exactly two declarations inside the `.mobile-nav__link` rule and nothing else in it.

    First, replace the fixed 32-pixel `height` declaration with `min-height: 44px`. Use the minimum form, not a fixed height — that is what the rule declared before commit 5d54087 changed it, and a minimum lets the row grow if a label ever wraps at a narrow width, which a fixed height would clip.

    Second, replace the Label-size font token with `font-size: var(--font-body-size)` (16px, defined at line 84).

    Leave every other declaration in the rule alone, including `border-radius: var(--radius-control)`. That radius is NOT part of what is being reverted: commit 5d54087 also swapped a `border-left: 3px solid transparent` for it, but that was D-05a's single-signal pill idiom, shared with the active modifier and with `.sidebar-link--active`, and it is correct. Reverting it would resurrect a double "you are here" cue that D-05 deliberately removed.

    Do not touch `.sidebar-link` (lines 862-874). Its compaction is the half of D-05 that was right: `.dashboard-sidebar` is `display: none` at base and only revealed inside the `@media (min-width: 960px)` block, so that rule never reaches a phone. Do not touch the active modifier, the `:not()`-scoped hover rule, or the WR-01 colour pair at lines 910-918.

    Then rewrite the rule's head comment (currently lines 583-590). It presently states the 44px floor was traded away here; that is now false and must not survive. The replacement should record: that D-05 (06.6.4-04) was a desktop compactness pass whose trade belonged only on the desktop sidebar renderer; that this selector is the mobile-only nav below the 960px breakpoint with no compensating override, so the trade reached the one place it had no argument; and that quick task 260902-qkm restored the floor on the developer's report that it made phone navigation harder. Cite the task id `260902-qkm` literally, matching the file's existing provenance idiom. Keep the existing final sentence about `--font-ui` being D-03's stated boundary (the sketch prototype's serif-at-18px was deliberately not carried into the contract) — that is still true and still load-bearing.

    Finally, correct the touch-target floor register comment (lines 1220-1234). Its traded-away enumeration currently names both nav selectors together in one entry. Rewrite that entry to name only the desktop sidebar selector, in the exact form `desktop sidebar nav links (.sidebar-link, 32px — D-05, plan 06.6.4-04)`, and keep the substring `.sidebar-link, 32px` on a single physical comment line — do not let the comment wrap between the selector name and the size, or the automated check will not find it. Then extend the register's "Kept the floor" clause to include the mobile dropdown link, noting it was restored by quick task 260902-qkm after D-05 reached it by mistake. The register's entry count stays at four (text buttons, desktop sidebar nav links, theme-picker segments, filter input), so the closing sentence about "the four named selectors" remains accurate and needs no edit. Leave the theme-picker, filter-input, `.copy-btn` and kept-floor-for-`input`/`select` entries exactly as they are.

    When rewriting the register, describe the correction in your own words; do not reproduce the old slash-joined two-selector token anywhere in the file, or the automated check that proves it is gone will fail on your own prose.
  </action>
  <verify>
    <automated>test "$(awk '/^\.mobile-nav__link \{/,/^\}/' companion/static/style.css | grep -c 'min-height: 44px')" = "1" && test "$(awk '/^\.mobile-nav__link \{/,/^\}/' companion/static/style.css | grep -c 'font-size: var(--font-body-size)')" = "1" && test "$(awk '/^\.mobile-nav__link \{/,/^\}/' companion/static/style.css | grep -c 'font-size:')" = "1" && test "$(awk '/^\.sidebar-link \{/,/^\}/' companion/static/style.css | grep -c 'height: 32px')" = "1" && test "$(awk '/^\.sidebar-link \{/,/^\}/' companion/static/style.css | grep -c 'font-size: var(--font-label-size)')" = "1" && test "$(grep -c '\.sidebar-link/\.mobile-nav__link' companion/static/style.css)" = "0" && test "$(awk '/44px touch-target floor register/,/^button \{/' companion/static/style.css | grep -c '\.sidebar-link, 32px')" = "1" && test "$(awk '/44px touch-target floor register/,/^button \{/' companion/static/style.css | grep -c 'mobile-nav__link')" -ge 1 && test "$(grep -c '260902-qkm' companion/static/style.css)" -ge 1 && test "$(git diff -- companion/static/style.css | grep -c '^[+-].*mobile-nav__link--active')" = "0"</automated>
  </verify>
  <done>
    The `.mobile-nav__link` block declares `min-height: 44px` and exactly one `font-size`, which resolves to `var(--font-body-size)`. The `.sidebar-link` block still declares its 32px height at Label size, byte-identical. No line anywhere in the stylesheet joins the two nav selectors with a slash. The floor register's traded-away list names `.sidebar-link, 32px` on one line and its kept clause names the mobile dropdown link. The task id `260902-qkm` appears in the file. The diff adds and removes no line mentioning the active modifier, proving the surrounding nav rules were not disturbed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Pin the two geometries apart with a regression guard, and correct the design skill's floor register</name>
  <files>companion/test_companion_app.py, .claude/skills/sketch-findings-skypane/references/mobile-navigation.md, .claude/skills/sketch-findings-skypane/SKILL.md, .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md</files>
  <behavior>
    - The new check PASSES against Task 1's corrected stylesheet.
    - The new check FAILS if the mobile dropdown link's 44px minimum is removed or reduced.
    - The new check FAILS if the mobile dropdown link's font size drops back to the Label token.
    - The new check FAILS if the desktop sidebar link's 32px compaction is "restored" to 44px — the guard defends both directions, not one.
    - `companion/test_companion_app.py` exits 0 with 108 of 108 checks passing.
  </behavior>
  <action>
    Add ONE new check to `companion/test_companion_app.py`, placed with the other stylesheet-contract checks (near `_serif_never_reaches_dense_content`, around lines 932-957) and written in that file's established idiom: read `os.path.join(HERE, "static", "style.css")`, slice the rule block with the same `css.find("\n%s {" % selector)` then `css.index("}", index)` pattern that check already uses, then register it with `check("<description>", <fn>)`.

    Assert all four facts in the one check, returning a specific failure message for each: the `.mobile-nav__link` block contains `min-height: 44px`; the same block's font size is `var(--font-body-size)`; the `.sidebar-link` block still contains its 32px height; and the `.sidebar-link` block's font size is still the Label token. Slicing by rule block (not scanning the whole file) is what keeps the two selectors' assertions from cross-contaminating, since both blocks otherwise share most of their declarations verbatim.

    Word the check description so it states the invariant rather than the values — the two nav renderings are deliberately different sizes now: the mobile dropdown keeps a real tap target, the desktop sidebar stays compact, and neither may drift into the other.

    Bump `EXPECTED_CHECK_COUNT` (line 65) from 107 to 108, appending a dated provenance comment naming quick task 260902-qkm in the same style as the existing 260902-l9w note on that line.

    Then correct the design skill, which currently documents the wrong geometry as the shipped contract:

    In `references/mobile-navigation.md`, rewrite the "Link geometry" paragraph (line 17). It currently asserts the link is 32px at Label size, does not carry a 44px tap-target floor, and is dimensionally identical to the sidebar. All three claims are now false. State instead that the link carries `min-height: 44px` at `var(--font-body-size)` (16px); that this is a deliberate divergence from `.sidebar-link`, which stays at its 06.6.4 D-05 compaction because it is structurally desktop-only (`.dashboard-sidebar` is hidden below the 960px breakpoint); and that D-05's density trade was reverted here by quick task 260902-qkm because a compactness argument that holds on a pointer-driven desktop sidebar does not hold on the only nav a phone has. Keep the existing `font-family: var(--font-ui)` sentence about the sketch prototype's serif-at-18px boundary — still true. Then update the CSS excerpt at lines 56-60 to show the restored declarations.

    In `SKILL.md`, correct the touch-target floor register sentence (line 39). Its nav-links entry names both selectors; narrow it to the desktop sidebar link only. The count stays four (buttons, desktop sidebar links, theme-picker segments, filter input), so "exactly four selectors" remains correct — and add, in the kept/restored part of that same register, that the mobile dropdown link regained the 44px floor via quick task 260902-qkm. Leave line 83's 06.6.4 phase-log entry describing what that phase did at the time; if you touch it at all, append a SUPERSEDED marker in the file's own established idiom rather than rewriting history.

    In `references/accessibility-contrast.md`, narrow line 23's parenthetical "four named selectors (buttons, nav links, theme segments, filter input)" so the nav entry reads as the desktop sidebar nav links specifically.

    Leave `references/control-density.md` alone. Its two `.mobile-nav__link` mentions (lines 7 and 17) are about the 4.5% hover wash and the 12% accent active pill, and both remain accurate — do not edit them just because the selector appears there.

    After editing, no single line anywhere under the skill directory may mention this selector and the 32px figure together; the automated check proves that, and it is the whole point of the doc pass.
  </action>
  <verify>
    <automated>test "$(grep -c 'EXPECTED_CHECK_COUNT = 108' companion/test_companion_app.py)" = "1" && server/.venv/bin/python3 companion/test_companion_app.py >/dev/null && test "$(awk '/^\.mobile-nav__link \{/,/^\}/' .claude/skills/sketch-findings-skypane/references/mobile-navigation.md | grep -c 'min-height: 44px')" = "1" && test "$(awk '/^\.mobile-nav__link \{/,/^\}/' .claude/skills/sketch-findings-skypane/references/mobile-navigation.md | grep -c 'font-label-size')" = "0" && test "$(grep -rn 'mobile-nav__link' .claude/skills/sketch-findings-skypane/ | grep -c '32px')" = "0" && test "$(grep -rc 'mobile-nav__link' .claude/skills/sketch-findings-skypane/references/control-density.md)" = "2"</automated>
  </verify>
  <done>
    `companion/test_companion_app.py` runs green at 108/108 with the new four-fact guard present, and the guard demonstrably fails if any of the four declarations is changed (confirm by temporarily flipping one and re-running, then restoring). The skill's mobile-navigation reference shows the restored `min-height: 44px` in its CSS excerpt with no Label-size token in that block. No line under the skill directory co-locates the selector with the 32px figure. `references/control-density.md` still carries its two untouched mentions.
  </done>
</task>

<task type="auto">
  <name>Task 3: Prove the restored tap target live at 375px and the untouched sidebar at 1280px, then run the full suite</name>
  <files>(no source edits — measurement, screenshots and full-suite run only)</files>
  <action>
    Start a real instance: run `scripts/run-local-verify.sh` in the background and wait for port 8643 to accept connections. If that script is unavailable, run the equivalent directly: `SKYPANE_COMPANION_PASSWORD=local-verify-only server/.venv/bin/python3 companion/app.py --state-dir /tmp/skypane-prod-state`.

    Using the Chrome DevTools MCP, set the viewport to 375x812, navigate to `http://127.0.0.1:8643/`, sign in with the password `local-verify-only`, and land on an authenticated page (`/health` is fine). Force a stylesheet reload (hard reload, or append a cache-busting query string to the stylesheet request) before measuring — a cached stylesheet has already produced a false "fix confirmed" reading on this project.

    Open the dropdown by clicking the toggle button (the one carrying `aria-controls="mobile-nav"`), then measure and report, as a table rather than prose:

    - For each `.mobile-nav__link`: `getBoundingClientRect().height` and `getBoundingClientRect().width`, plus computed `fontSize`, `minHeight` and `height`. All four links must report a rect height of at least 44 and a computed font size of 16px.
    - For the panel itself (`#mobile-nav`): computed `maxHeight`, rendered `getBoundingClientRect().height`, and `scrollHeight`. `scrollHeight` must not exceed the rendered height — this is the clipping check. The panel grows roughly 48px taller than before (four links at 44px instead of 32px) against a fixed 420px ceiling, and if that ceiling were exceeded the theme picker and Sign out control would silently vanish behind `overflow: hidden`.
    - The footer region: confirm the theme picker's three segments and the Sign out control are all inside the panel's visible box, not below its clipped edge.

    Also confirm visually at 375px, and say which you confirmed individually: all four labels (Settings, Health, Airlines, History) are on one line each with no wrap or truncation; the active link's tinted pill still spans the full row height with no gap or overlap against its neighbours; the Health notification dot (if the local state renders one) still sits inline after its label rather than floating; and no link overflows the panel's horizontal edge. Capture a screenshot of the open dropdown at 375px — the reported symptom is a felt/tactile one, so numbers alone are not the whole proof.

    Then set the viewport to 1280x900, reload, and confirm the desktop half is untouched: every `.sidebar-link` reports a rect height of 32 and a computed `fontSize` of 14px, and the mobile header and dropdown are not rendered at all (the `>=960px` block hides `.site-header`). Report those numbers in the same table.

    Finally run `scripts/run-all-tests.sh` and report its full result line plus the per-harness outcome. Every harness that passed immediately before this task must still pass.
  </action>
  <verify>
    <automated>scripts/run-all-tests.sh 2>&1 | tee /tmp/qkm-suite.log | tail -5 && grep -q '==> Result: PASS' /tmp/qkm-suite.log</automated>
    <human-check>The 375px measurement table shows all four mobile dropdown links at a rect height of at least 44px and a computed font size of 16px, with the panel's scrollHeight within its rendered height; the 1280px table shows every sidebar link still at 32px/14px with the mobile header absent; a 375px screenshot of the open dropdown is captured.</human-check>
  </verify>
  <done>
    A single before/after-style measurement table covers the four mobile dropdown links and the panel at 375px, and the sidebar links at 1280px, all sourced from a real browser against a real running companion process with a cache-busted stylesheet. The panel is confirmed unclipped with its footer controls visible. A 375px screenshot exists. All four labelled visual confirmations are individually stated. `scripts/run-all-tests.sh` prints `==> Result: PASS` with zero failing harnesses.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Checkpoint: developer confirms the restored tap target on a real phone</name>
  <action>Stop and present the verification steps below to the developer. Do not close the task, and do not treat Task 3's headless measurements as sufficient, until they reply with an approval or a description of what still feels wrong.</action>
  <what-built>
    The mobile hamburger dropdown's nav links are back to a real tap target: `min-height: 44px` at 16px, reverting the half of 06.6.4's D-05 density pass that should never have reached the phone. The desktop sidebar keeps its 32px/14px Linear-style compaction, untouched. Both floor registers (the stylesheet's own audit comment and the design skill's) now record the restoration, and a test guard pins the two geometries apart so a future density pass cannot silently re-couple them.
  </what-built>
  <how-to-verify>
    Automated measurement already confirmed the numbers at 375px in a headless browser, but this exact bug class escaped a computed-style-only check on this project once before — a real thumb on a real phone is the acceptance test.

    1. Make the companion app reachable from your phone (run `scripts/run-local-verify.sh` and hit the machine's LAN address on port 8643, or deploy to the VPS as you normally would).
    2. On your phone, open any authenticated page and tap the hamburger.
    3. Confirm the menu rows feel comfortably tappable again — roughly the size they were before the 06.6.4 pass, not the tight rows you flagged.
    4. Confirm nothing is cut off at the bottom of the open menu: all four links (Settings, Health, Airlines, History), the Auto/Light/Dark theme picker, and Sign out should all be reachable without the panel clipping them.
    5. Confirm the labels still fit on one line each and the highlighted current-page pill still looks right.
    6. If you have a desktop browser handy, confirm the left sidebar nav is unchanged — it should still look exactly as compact as it did before this fix.
  </how-to-verify>
  <resume-signal>Type "approved", or describe what still feels wrong (too small, too tall, clipped, misaligned) and it will be adjusted before the task is closed.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> companion HTTP server | Authenticated companion UI; this change is presentation-only CSS plus documentation and test code, and crosses no new boundary |
| local verify instance -> LAN | The optional phone sign-off exposes a real companion process on the LAN with a throwaway password |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qkm-01 | Denial of Service | `.js .mobile-nav--open` 420px clip | medium | mitigate | A taller row could push the panel past its fixed ceiling and hide Sign out and the theme picker behind `overflow: hidden`, denying access to those controls on mobile. Task 3 measures the open panel's `scrollHeight` against its rendered height at 375px, and the human checkpoint confirms every footer control is reachable |
| T-qkm-02 | Tampering | scope creep into `.sidebar-link` and sibling nav rules | medium | mitigate | The change is scoped to two declarations in one rule. Task 1's gates assert `.sidebar-link` still declares its 32px height at Label size and that the diff adds or removes no line touching the active modifier |
| T-qkm-03 | Repudiation | floor registers contradicting the CSS | low | mitigate | Both registers (stylesheet comment and design skill) are corrected in the same commit series and gated, so a future 2.5.5 audit cannot read a stale claim that this selector traded its floor away |
| T-qkm-04 | Information Disclosure | LAN-exposed local verify instance | low | accept | `scripts/run-local-verify.sh` uses a throwaway password against a scratch state dir, is run only for the duration of the sign-off, and is the project's already-established real-device verification idiom |
| T-qkm-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package installs of any kind in this task — no dependency is added, removed or upgraded. Nothing to audit |
</threat_model>

<verification>
- `.mobile-nav__link` declares `min-height: 44px` and `font-size: var(--font-body-size)`; every other declaration in that rule, and every sibling nav rule, is byte-identical.
- `.sidebar-link` is untouched at 32px/Label size, confirmed both by grep and by live 1280px measurement.
- No line in `companion/static/style.css` joins the two nav selectors as a single traded-away register entry; the kept clause names the mobile link.
- No line under `.claude/skills/sketch-findings-skypane/` co-locates `.mobile-nav__link` with the 32px figure.
- `companion/test_companion_app.py` passes 108/108 with the new four-fact guard, which fails in both directions.
- Live 375px measurement shows all four dropdown links at a rect height of at least 44px and 16px computed font size, in an unclipped panel, with a screenshot captured.
- `scripts/run-all-tests.sh` prints `==> Result: PASS` with zero failing harnesses.
- The developer approves the restored feel on a real phone.
</verification>

<success_criteria>
The mobile hamburger menu's rows are tappable again at their pre-D-05 size, the desktop sidebar's Linear-style compaction is preserved exactly, the project's two touch-target floor registers tell the truth, a regression guard makes the divergence explicit and defended, the full test suite stays green with zero failures, and the developer confirms the fix on their own phone.
</success_criteria>

<output>
Create `.planning/quick/260902-qkm-restore-mobile-nav-link-s-touch-friendly/260902-qkm-SUMMARY.md` when done, including the 375px and 1280px measurement tables verbatim and the full-suite result line.
</output>
