---
phase: quick/260905-bba
plan: 01
type: execute
wave: 1
depends_on: []
branch: claude/reconcile-ui-spec-drift   # STAY HERE. Do not create or switch branches.
files_modified:
  - .claude/skills/sketch-findings-skypane/SKILL.md
  - .planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md
autonomous: true
requirements: []          # Decision-point-tracked quick task, same precedent as every 06.x plan and
                          # every recent quick task in this repo (see 260904-e92-PLAN.md). Traceability
                          # is via the `decisions` key below, cited inline in every task action.
decisions:
  - DP-1  # DOCUMENTATION ONLY — zero edits under companion/, server/, or any test_*.py. Hard boundary.
  - DP-2  # SUPERSEDED convention — replaced values are MARKED in place, never deleted. Reader must see both.
  - DP-3  # Post-approval amendments are visibly attributed to the phase/quick task that made them, in the
          # style of the two 260902-* amendments already in the file. Do NOT rewrite history so the spec
          # appears to have always specified what shipped later.
  - DP-4  # SKILL.md's phase-status claim is re-worded to POINT AT ROADMAP.md as the live source, not to
          # re-freeze a status into prose (this class of statement has now gone stale twice: cde14f1, then again).
  - DP-5  # Frontmatter records the amendment (status + reviewed_at). The 2026-09-01 checker sign-off block
          # is NOT re-opened, re-ticked, or re-dated — it stays a historical record of what was approved then.
  - DP-6  # Every factual claim written into either file is verified against live code / live ROADMAP.md at
          # execution time, and the source read is cited inline (file:line or commit/PR).
  - DP-7  # Real code defects surfaced by reconciliation are RECORDED AS FINDINGS for the developer, never fixed here.
  - DP-8  # An Amendment Ledger section enumerates every post-approval batch reviewed and its outcome
          # (amended, or no UI-SPEC change needed) — this makes the "sweep the rest of the file" claim auditable.

must_haves:
  truths:
    - "The sketch-findings-skypane skill no longer asserts that Phase 06.6.4.1 is unclosed; it points the reader at .planning/ROADMAP.md as the live record of phase status, so the claim cannot rot a third time (DP-4)"
    - "06.6.4.1-UI-SPEC.md's Color section's accent-reservation list agrees with companion/static/style.css's own header comment, which is authoritative — including the selected theme chip and the 260904-bbi live-:has() re-keying (DP-2, DP-3, DP-6)"
    - "06.6.4.1-UI-SPEC.md's Typography section states the shipped 22px/32px sizes and the Iowan Old Style/Charter-leading serif stack, with the 20px/30px/Georgia-first values marked SUPERSEDED and attributed to 06.6.4.1.1 (DP-2, DP-3)"
    - "Every UI-SPEC section describing something that has since been retired (History's Now showing section, History's Recent renders disclosure, the pre-06.6.4.1.1 16-radio theme picker, the zero-new-icon-symbols claim) says so in place, attributed to the batch that retired it, with the original text still legible (DP-2, DP-3)"
    - "A reader can still read the document as the design contract of Phase 06.6.4.1 as approved on 2026-09-01 — every post-approval amendment is visibly dated and attributed, none is silently folded into the original prose (DP-3, DP-5)"
    - "The Amendment Ledger names every post-approval batch that touched companion UI and states, for each, whether the UI-SPEC needed amending — so 'the rest of the file was swept' is a checkable claim, not an assertion (DP-8)"
    - "git status shows zero modified paths under companion/ and server/ — no production code, no test changed (DP-1)"
  artifacts:
    - ".claude/skills/sketch-findings-skypane/SKILL.md — two stale phase-status statements (the <context> 'Current as of' paragraph and the <metadata> Folded-In Work entry for 06.6.4.1) replaced with a ROADMAP.md pointer; no design value anywhere else in the file moves"
    - ".planning/phases/06.6.4.1-.../06.6.4.1-UI-SPEC.md — frontmatter amended (status, reviewed_at, amended-by trail); system-level sections (Design System, Spacing Scale, Typography, Color, Component Reuse Contract) reconciled; per-page Component Specs (§5, §7, §8) reconciled; a new Post-Approval Amendment Ledger appended before the Checker Sign-Off"
  key_links:
    - "companion/static/style.css's header comment -> UI-SPEC §Color's 'Accent reserved for' list — the UI-SPEC claims this list is verbatim from that comment, so the two must agree literally, not approximately"
    - "companion/static/style.css:109-132 (the four --font-* size tokens and --font-serif) -> UI-SPEC §Typography's five-role table"
    - ".planning/ROADMAP.md's 06.6.4.1 / 06.6.4.1.1 plan checkboxes -> SKILL.md's <context> phase-status sentence (the thing that keeps going stale)"
---

<objective>
Reconcile the two design-contract documents with what actually shipped on the companion app after 2026-09-02: fix one stale phase-closure claim in the `sketch-findings-skypane` skill, and bring `06.6.4.1-UI-SPEC.md` (last touched 2026-09-02, `status: approved`) into agreement with the eight batches of UI work that landed since.

Purpose: the UI-SPEC is the phase's design contract AND, by the project's own convention (quick tasks `260902-ep7` and `260902-gjj` both amended it post-approval — commits `2cb56a7`, `34eaad8`, `6a0680b`), a document that is kept current rather than frozen. That convention lapsed. A future reader currently gets a document that confidently describes a theme picker, a "Now showing" section, a Recent-renders disclosure, a type scale, and an accent-reservation list that no longer exist as written.

Output: two amended documentation files. Zero code change.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@./.claude/CLAUDE.md

The two sources of truth, both of which are CURRENT and neither of which is edited by this plan:
@companion/static/style.css
@.claude/skills/sketch-findings-skypane/SKILL.md

The document being reconciled:
@.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md

Post-approval batches to reconcile against (all merged, all on this branch's ancestry):
- PR #37 `acad031` — UIR-10 / UIR-11, Health's two data tables made usable on mobile (quick task `260903-ghy`)
- PR #40 `dfb24ce` — UIR-14 / UIR-16 / UIR-17 / UIR-18 / UIR-19 (quick task `260903-peo`)
- PR #42 `bd03368` — **phase 06.6.4.1.1**, the phase that revised this very contract and produced no UI-SPEC of its own
- PR #43 `92bc660` — UIR-08, Airlines illustration frame halved to 450x132 (quick task `260904-e92`)
- quick `260902-w4t` `a76201f`/`a8cc897` — History table content, corroboration label, scroll-edge affordance
- quick `260902-v26` / `260903-df3` / `260903-btu` — the Airlines illustration replace control, its framed action zone, and its move into the shared lightbox (`260903-df3` added an `icon-upload` symbol to the sprite — commit `65e8ec4`)
- quick `260903-c4o` `ee74386`/`460d911` — History's live panel folded into the render gallery, `/preview.png` route retired
- quick `260903-etm` `7db8e74`/`fc39bcc` — History's render-gallery section DELETED outright, colour caveat rehomed, three orphaned `.gallery-grid` rules retired
- quick `260904-bbi` — selected-state treatment re-keyed to live `:has(input:checked)` state
</context>

<tasks>

<task type="auto">
  <name>Task 1: Retire the stale phase-closure claims in the sketch-findings-skypane skill</name>
  <files>.claude/skills/sketch-findings-skypane/SKILL.md</files>
  <action>
Read `.planning/ROADMAP.md` and confirm the current recorded plan-completion state of Phase 06.6.4.1 and Phase 06.6.4.1.1 before writing anything (DP-6). At the time this plan was written, ROADMAP.md showed all nine 06.6.4.1 plans checked, including its closing plan — verify that is still what the file says, and cite the line range you read in your SUMMARY.

Two statements in SKILL.md are falsified by that record. Both must go.

First, in the `<context>` block's "Current as of" paragraph (around line 11): the trailing clause that asserts the parent Phase 06.6.4.1 has not closed, that its closing plan 09 is still outstanding, and that the reader should not conflate the two phases' statuses. Second, in the `<metadata>` block's Folded-In Work entry for 06.6.4.1 (around line 103): the leading parenthetical that states a partial plan count and an outstanding closing plan.

Replace both with wording that POINTS AT the roadmap rather than restating a status (DP-4). This is the second time this class of statement has gone stale here — commit `cde14f1` already had to correct a phase-closure claim in this same file once — so the replacement must not carry a status that can rot. Each replacement must contain the literal string `.planning/ROADMAP.md is the live record` so the pointer is unambiguous and greppable. Keep the genuinely durable half of the original `<context>` sentence: that 06.6.4.1.1 is a closed INSERTED phase which revised the visual contract its parent 06.6.4.1 shipped, and that the two are distinct phases. That relationship is a fact about the work, not a status, and does not rot.

Do NOT touch anything else in this file (DP-1 spirit): no token value, no `<design_direction>` bullet, no reference-file pointer, no other Folded-In Work entry. Do NOT add a new Folded-In Work entry for this quick task — the Folded-In list records design-system changes, and this task changes no design value. The `260904-bbi` entry's own parenthetical (which says the roadmap does not show either phase closing *as a result of that work*) is a statement about causation, not status, and is still accurate — leave it alone.
  </action>
  <verify>
    <automated>bash -c 'S=.claude/skills/sketch-findings-skypane/SKILL.md; test "$(grep -c "remains open" "$S")" = "0" && test "$(grep -c "8/9 plans" "$S")" = "0" && test "$(grep -c "\.planning/ROADMAP\.md is the live record" "$S")" -ge 2 && test "$(git diff --numstat -- "$S" | cut -f1)" -le 4 && test "$(git diff --numstat -- "$S" | cut -f2)" -le 4 && echo PASS'</automated>
  </verify>
  <done>
SKILL.md contains the ROADMAP pointer literal at least twice, contains neither of the two stale status claims, and `git diff --numstat` shows at most 4 added and 4 removed lines (proving the edit was surgical and no design value moved). The ROADMAP line range actually read is cited in the SUMMARY.
  </done>
</task>

<task type="auto">
  <name>Task 2: Reconcile the UI-SPEC's frontmatter and system-level sections against live style.css</name>
  <files>.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md</files>
  <action>
Before writing a single amendment, read the live sources and cite them (DP-6): `companion/static/style.css`'s full header comment (its accent-reservation paragraph is authoritative for the Color section — the skill explicitly defers to it), the `:root` token block carrying the four `--font-*` size tokens and `--font-serif` (around lines 103-132), and `companion/layout.py`'s `ICON_IDS` tuple and its later extensions (around lines 132-190). Correct nothing from memory or from this plan's prose alone — this plan's own drift list is a starting point that was assembled by one pass.

Study the amendment style already in the file before writing: §5.3 carries a bolded, named, in-place amendment paragraph ("quick task 260902-ep7 (BUG 4) update, superseding the two sentences this replaces: ..."), and the Color table carries inline parenthetical attributions ("quick task 260902-gjj"). Match that style exactly (DP-3). Additionally use the literal token `SUPERSEDED` beside each replaced value, the way the `sketch-findings-skypane` skill does, so a reader can see both the old value and what replaced it (DP-2). Never delete a superseded value; never silently edit an original sentence so it reads as if it always said the new thing.

Amend these sections:

**Frontmatter (DP-5).** `status:` moves off the bare `approved` to a value that records both facts — that it was approved 2026-09-01 and amended since (e.g. `approved-amended`). Add a `last_amended: 2026-09-05` key. Leave `reviewed_at: 2026-09-01` as the record of when the checker signed off; do not move it, and do not re-tick or re-date the Checker Sign-Off block at the bottom of the file. Add an `amended_by:` list naming the batches that amended it, `260902-ep7` and `260902-gjj` included (they are amendments too and the frontmatter has never recorded them).

**Design System table, Font row.** It states a Georgia-first serif stack. `--font-serif` now leads `"Iowan Old Style", Charter, ...` (06.6.4.1.1 D-08 / UIR-20). It also lists `.stat-tile__caption` inside the serif set — that exception was retired outright by 06.6.4.1.1 D-13/UIR-23, which moved every label-shaped element onto one 12px sans-semibold uppercase voice. Amend both, attributed.

**Design System table, Icon library row + Component Reuse Contract's "Icon reuse (zero new symbols)" block.** Both assert the phase adds zero new icon symbols and that no need falls outside the then-14-member `ICON_IDS` whitelist. Verify the live tuple: quick task `260903-df3` (commit `65e8ec4`) added an `icon-upload` symbol for the Airlines replace control. Record that the zero-new-symbols claim held for Phase 06.6.4.1's own work and was subsequently broken by a named later batch — that is the honest framing, and it is exactly the escalation path the block's own closing sentence asks for.

**Spacing Scale table + its Exceptions paragraph.** 06.6.4.1.1-03 made a real spacing pass: D-14/UIR-24 unified every sibling-card gap (grid or stacked) at `--space-lg` 24px, superseding a wider 32px grid gap; D-15/UIR-24 gave `.page-section`, `.theme-status` and `.battery-trend-section` 24px padding at `>=960px` dropping to 16px below; D-16 capped one-line card text; D-19/UIR-24 made `.section-intro` a mobile-first column; D-18/UIR-26 grew buttons to 36px/14px below 960px as a stated extension of 06.6.4 D-01. The table's `lg`/`xl` usage cells and the Exceptions paragraph's "buttons 30px" both need amending — note that 30px is still correct at `>=960px` and is extended, not reopened, below it.

**Typography table and the paragraphs under it.** `--font-heading-size` is 22px (was 20px) and `--font-page-title-size` is 32px (was 30px), both 06.6.4.1.1 D-10; the page title also gained its own semibold weight and `-0.015em` tracking, which the table's "400 (regular)" cell contradicts. Read the live tokens rather than trusting these numbers. Also amend: the "Exactly 2 weights" sentence is still true, but the five-role table's weight column is not; `.site-title` became its own 24px serif-semibold brand role (D-11) that the table does not cover; the sub-scale exception tier gained entries and lost others when the 12px label voice absorbed `.data-table th` (which the table cites at 11px with a `style.css:1265-1266` line reference that will no longer be accurate — re-read or drop the line reference rather than leaving a wrong one).

**Color section.** The "Accent reserved for" list claims to be verbatim from `style.css`'s header comment and claims the phase adds zero new consumers. Reconcile it against the live header comment literally (DP-6), which is authoritative. At minimum it is missing: the selected theme chip's border and check glyph (06.6.4.1.1-05), the 12%-accent background wash both selected cards gained (06.6.4.1.1-06), and quick task `260904-bbi`'s re-keying of that whole treatment from the server-rendered `--selected` class onto live `:has(input:checked)` state inside an `@supports selector(:has(*))` block. Preserve the header comment's own framing for each item — it carefully distinguishes a genuine broadening from a clarification from a re-keying, and that distinction is the point of the list. Also amend the "Explicit ruling for this phase's new components" paragraph below it: its claim that the list "stays exhaustive and unchanged" was true of this phase's own components and is what later batches changed.

Every amendment cites the file and line range (or commit/PR) it was verified against.
  </action>
  <verify>
    <automated>bash -c 'U=".planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md"; test "$(grep -c SUPERSEDED "$U")" -ge 6 && test "$(grep -c Charter "$U")" -ge 1 && test "$(grep -c "theme.chip" "$U")" -ge 1 && test "$(grep -c ":has(input:checked)" "$U")" -ge 1 && test "$(grep -c "icon-upload" "$U")" -ge 1 && test "$(grep -c "260904-bbi" "$U")" -ge 1 && test "$(grep -c "06\.6\.4\.1\.1" "$U")" -ge 5 && test "$(grep -c "last_amended: 2026-09-05" "$U")" = "1" && test "$(grep -c "reviewed_at: 2026-09-01" "$U")" = "1" && test "$(git status --porcelain -- companion/ server/ | wc -l | tr -d " ")" = "0" && echo PASS'</automated>
  </verify>
  <done>
The UI-SPEC's frontmatter records the amendment without disturbing `reviewed_at`; the Design System, Spacing Scale, Typography and Color sections each agree with live `style.css`/`layout.py`; every replaced value is marked `SUPERSEDED` in place and attributed to the phase or quick task that replaced it; `git status` shows nothing modified under `companion/` or `server/`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Reconcile the UI-SPEC's per-page Component Specs and append the Amendment Ledger</name>
  <files>.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md</files>
  <action>
Same discipline as Task 2: verify each claim against live code before amending it, cite what was read, mark superseded text in place with attribution, never rewrite an original sentence to read as if it always said the new thing (DP-2, DP-3, DP-6).

**§5.0 / §5.1 Settings.** The theme picker this spec describes is the pre-06.6.4.1.1 one — §5.1's stacked Theme→Runway→Save order and the "Theme section — unchanged, is the wrapper pattern Runway now copies" row in the Component Reuse Contract both describe sixteen native radios. It shipped as a `.theme-chip-grid` of real-rendered-preview chips inside the same `.theme-status` card (06.6.4.1.1-05, D-01/D-02/D-03/D-07/D-08). Verify against `companion/pages/config_page.py` and `companion/test_config_page.py`'s own shape check. Also verify how many groups the Settings form now carries — the harness check names five (Theme, Runway, Diagnostic LED, Quiet hours, Wake interval); the last two arrived with Phases 10 and 11, after this spec, and the ROADMAP records them as a drift finding disclosed at 06.6.4.1-09's developer checkpoint. Record them as out-of-scope-but-present rather than pretending the page still has three groups.

**§5.x Health.** Check §5.6's migrated full-width cards and §5.2's two-section restructure against PR #37 (`acad031`, UIR-10/UIR-11, Health's two data tables made usable on mobile) and PR #40 (`dfb24ce`, UIR-14 gave the pipeline tile a real second line, UIR-18 added a persistent freshness note to the page header). §5.3's battery-chart paragraph already carries the `260902-ep7` amendment — verify it is still accurate and leave it alone if so.

**§7 Airlines.** §7.1's `.airline-card__image` markup and §7.3's illustration route predate quick task `260904-e92` (PR #43), which halved the normalization frame to 450x132, and quick tasks `260902-v26`/`260903-df3`/`260903-btu`, which added an illustration-replace control, restyled it as a framed action zone, and moved it into the shared lightbox. §7.1's `.airline-card__chip` block also states an 11px chip label; verify whether the 12px label voice (06.6.4.1.1 D-13) absorbed it.

**§8 History — the largest divergence.** §8.1 describes a "Now showing" section and §8.2 a collapsed "Recent renders" disclosure. Verify both against `companion/pages/history_page.py`: quick task `260903-c4o` (`ee74386`) folded the live panel into the render gallery and retired the `/preview.png` route (`460d911`), then quick task `260903-etm` (`7db8e74`, `fc39bcc`) deleted the render-gallery section outright, rehomed the colour caveat, and retired three orphaned `.gallery-grid` stylesheet rules. Both sections are gone. Mark both as retired in place, attributed, with the original spec text intact and legible — the ROADMAP records the "Now showing" retirement as a drift finding disclosed during 06.6.4.1-09, so cite that too. §8.0's claim that `/preview.png` and `/gallery/{name}.png` are "unchanged — still needed as `<img src>` targets from History" is falsified by the same pair of batches. §8.3's lightbox now does double duty (History's panel lookup and Airlines' replace form, per `260903-btu`); §8.4 and the desktop copy-button behaviour are touched by `260902-w4t` and UIR-17 (`260903-peo`) — verify each.

**Sweep the rest.** Re-read every remaining section (Copywriting Contract, Registry Safety, the rest of the Component Reuse Contract, Interaction/Accessibility Notes) against the batch list in `<context>`. The Interaction/Accessibility Notes' closing claim — no new accent consumers, no new spacing tokens, no new type roles or weights — needs the same treatment as §Color's: true of this phase, changed by later ones.

**Append a Post-Approval Amendment Ledger (DP-8).** Immediately before the Checker Sign-Off block, add a `## Post-Approval Amendment Ledger` section: a short paragraph stating that this document is amended after approval by convention (citing `260902-ep7` and `260902-gjj` as precedent), then a markdown table with columns Batch | What it changed | UI-SPEC section(s) | Outcome. One row per batch in `<context>`'s list plus the two 260902 ones, and every row's Outcome is either `amended` (naming the section) or `no UI-SPEC change needed` (with a one-clause reason). A batch you checked and found harmless still gets a row — that is what makes the sweep auditable rather than asserted.

**Findings (DP-7).** If reconciling surfaced a real code defect — a rule the spec requires that the code does not implement, an orphaned selector, a broken contract — do NOT fix it. Add a `### Findings for the developer` subsection under the ledger recording each one with the evidence, or a single line stating none were found. Report the same list in the SUMMARY.

Do not touch `companion/`, `server/`, or any test file for any reason (DP-1).
  </action>
  <verify>
    <automated>bash -c 'U=".planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md"; test "$(grep -c "Post-Approval Amendment Ledger" "$U")" = "1" && test "$(grep -c "Findings for the developer" "$U")" = "1" && test "$(awk "/^### .8\.1/,/^### .8\.3/" "$U" | grep -c SUPERSEDED)" -ge 2 && test "$(grep -c "theme-chip-grid" "$U")" -ge 1 && for b in 260902-ep7 260902-gjj 260902-w4t 260902-v26 260903-ghy 260903-peo 260903-c4o 260903-df3 260903-btu 260903-etm 260904-bbi 260904-e92; do grep -q "$b" "$U" || { echo "MISSING $b"; exit 1; }; done && test "$(grep -c "approved 2026-09-01" "$U")" = "1" && test "$(git status --porcelain -- companion/ server/ | wc -l | tr -d " ")" = "0" && echo PASS'</automated>
  </verify>
  <done>
Every per-page Component Spec section agrees with live code or carries an attributed in-place amendment saying what replaced it; §8.1 and §8.2 are marked retired with their original text still readable; the Amendment Ledger has a row for all twelve named batches; a Findings subsection exists (populated or explicitly empty); the 2026-09-01 Checker Sign-Off approval line is byte-unchanged; `git status` shows nothing modified under `companion/` or `server/`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| none crossed | Documentation-only change. No route, handler, template, session gate, or served asset is touched (DP-1). No input crosses a trust boundary as a result of this plan. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260905-bba-01 | Tampering (integrity of a security-relevant contract) | UI-SPEC §Color's accent-reservation list and the colour-separation contract it implies | medium | mitigate | The list is reconciled against `companion/static/style.css`'s own header comment, which is the declared authority, rather than rewritten from this plan's prose — so the executable contrast/hue-separation gate in `contrast_check.py` and the prose contract cannot diverge (DP-6) |
| T-260905-bba-02 | Information disclosure | Amendment Ledger and Findings subsection | low | accept | Both record only file paths, commit SHAs and PR numbers already present in this repo's own git history and ROADMAP; no credential, host, or state-dir path is introduced |
| T-260905-bba-SC | Tampering | npm/pip/cargo installs | n/a | accept | Zero package installs. This plan runs no package manager and adds no dependency; the repo is stdlib-only Python by constraint |
</threat_model>

<verification>
- `git status --porcelain -- companion/ server/` is empty — the documentation-only boundary (DP-1) held.
- `git diff --numstat` shows exactly two modified paths: the skill and the UI-SPEC.
- `grep -c 'remains open' .claude/skills/sketch-findings-skypane/SKILL.md` is 0 and the ROADMAP-pointer literal appears at least twice.
- The UI-SPEC's Amendment Ledger names all twelve post-approval batches; every row has an Outcome.
- The UI-SPEC's `reviewed_at: 2026-09-01` and its Checker Sign-Off approval line are both unchanged (DP-5).
</verification>

<success_criteria>
- A reader who opens `06.6.4.1-UI-SPEC.md` cold can tell, for every section, what was contracted on 2026-09-01 and what has replaced it since — with each replacement attributed to the phase or quick task that made it.
- No claim in either file is falsified by the live `companion/` tree or by `.planning/ROADMAP.md` as of execution time.
- The `sketch-findings-skypane` skill's phase-status statement now points at the roadmap instead of restating it, so it cannot go stale a third time.
- Any real code defect surfaced by the reconciliation is recorded for the developer, not fixed.
</success_criteria>

<output>
Create `.planning/quick/260905-bba-reconcile-06-6-4-1-ui-spec-md-and-the-sk/260905-bba-SUMMARY.md` when done, including the Findings list (or an explicit "none") and the file:line / commit citations backing each amendment.
</output>
