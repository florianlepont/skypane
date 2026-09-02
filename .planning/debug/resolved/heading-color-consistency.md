---
status: resolved
trigger: "Audit et corrige l'ensemble des règles CSS de heading (typographie) et de couleur dans companion/static/style.css (et tout usage dans companion/pages/*.py / companion/layout.py) pour la cohérence, avant de passer à un travail page par page. Contexte : le développeur vient de tester en direct l'app companion (Config/Health/Airlines/History/Preview) et juge le résultat catastrophique d'un point de vue UI/UX après les phases 06.6.2/06.6.3. Le skill projet sketch-findings-skypane documente la direction de design déjà validée en 06.6.1 : headings en serif chaud (jamais sur le contenu tabulaire/dense), accent terracotta (#E8622C en light, assombri intentionnellement en #B13F16 pendant 06.6.2 pour corriger un contraste WCAG AA — UXA-04, testé/pinné dans companion/test_contrast_check.py, à NE PAS annuler sans revalider le contraste), cartes avec --shadow-card au lieu de bordures hairline, espacement généreux. Objectif : que TOUTE règle de heading et TOUTE règle de couleur soit cohérente et conforme à cette direction validée, en gardant les déviations volontaires et testées mais en corrigeant les oublis/incohérences réelles. Ne pas toucher au contenu/layout au-delà de heading/couleur — le reste (grilles cassées, densité) sera traité page par page dans une étape suivante séparée."
created: 2026-08-31T16:48:39Z
updated: 2026-08-31T19:20:00Z
resolved: 2026-08-31T19:20:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

hypothesis: CONFIRMED AND FIXED (revised from the initial theory; fix visually
confirmed against the real running app 2026-08-31). The design contract for both headings and colours is written only as prose inside style.css comments, with no executable enforcement, and BOTH prose rules have a coverage hole. (a) The colour rule names exactly one pair to keep separated — accent vs --color-status-warn — so when 06.6.2 darkened the accent to #B13F16 for WCAG AA, nothing noticed it had moved to ΔE 22.9/16° from --color-status-error, closer than the ΔE 28.6 warn separation the direction had validated. (b) The serif-heading allow-list omits `legend` and names a `.sidebar-title` rule that does not exist, so `<legend>` renders sans-serif semibold while its sibling `<h2 class="text-heading">` renders serif regular on the same page, and per-page implementers reached for four different section-heading roles across five pages.
test: Apply the fix set below, then re-run all five companion suites plus the new hue/perceptual-separation checks added to test_contrast_check.py.
expecting: 246 pre-existing checks stay green; new separation checks pass at the new token values and would FAIL at the old ones (proving they actually enforce the guarantee).
next_action: DONE. Fix set applied, committed (01235a6) and visually confirmed.
Session closed. One item deliberately left open and carried forward, not closed
here: SYMPTOM 2 (the Health banner's redundant detail text) is a head-on
conflict between two validated decisions — see deferred_to_follow_up below — and
goes to the upcoming page-by-page pass on Health.

reasoning_checkpoint:
  hypothesis: "The heading and colour drift is not five independent oversights but one failure mode with two instances: the design contract lives only in CSS prose comments, and each prose rule has an unchecked gap (colour rule covers only the accent-vs-warn pair; heading allow-list omits `legend`)."
  confirming_evidence:
    - "Measured, not inferred: accent-vs-error is ΔE76 22.9 / hue 15.9° in light and 22.3 / 16.9° in dark — nearer than the accent-vs-warn pair (28.6 / 16.3° and 47.0 / 26.3°) that the direction explicitly validated as acceptable. The accent is closest to error in BOTH themes."
    - "`grep -rn \"hue\" companion/*.py` returns nothing: test_contrast_check.py pins 16 WCAG luminance ratios and zero separation assertions. The guarantee was never executable."
    - "`legend` is absent from the `h1, h2, h3, .text-heading` serif selector and uses --weight-semibold where every serif heading uses --weight-regular — so Config stacks a sans-semibold `<legend>Diagnostic LED</legend>` directly above a serif-regular `<h2 class=\"text-heading\">Poll</h2>` at the identical 20px size."
    - "`.sidebar-title` appears in the allow-list comment and in layout.py:842's markup but has no CSS rule in the file — the contract comment describes a rule that was never written."
    - "--color-destructive and --color-status-error hold identical values in all four token blocks and are used interchangeably for the same concept in five rules."
  falsification_test: "If the hypothesis is wrong, restoring `legend` to the serif/regular heading treatment and re-separating --color-status-error from the accent would leave the pages still visibly inconsistent, and the new separation assertions would pass just as readily at the OLD token values as at the new ones. Concretely: the new checks MUST fail when fed #DC2626/#F87171 and pass when fed the replacements — if they pass for both, they are not measuring the thing that broke."
  fix_rationale: "Every change either (1) closes a gap in a prose contract by making it executable (new hue_separation/perceptual_distance functions + pinned separation checks), or (2) brings an outlier into the treatment the contract already specifies (legend -> serif regular; --color-destructive folded into --color-status-error; .page-section/.login-card hairline+shadow -> transparent border + shadow per D-02; data-table separator off the surface token onto --color-border). The accent is NOT touched, so UXA-04's WCAG AA fix is preserved intact; separation is restored by moving --color-status-error to a crimson that is simultaneously farther from the accent AND contrast-safer than the red it replaces."
  blind_spots: "1) ΔE76 (not ΔE2000) is the metric used — adequate for 'are these two signal colours confusable', not a perceptual gold standard. 2) No real-browser render was performed by this agent; the fix is verified by unit tests and colour math, and this project's own MEMORY.md records that computed-style checks alone previously missed a real mobile bug — human visual sign-off is required. 3) Symptom 2 (banner detail text) is a genuine conflict between two validated decisions (06.6.1 sketch vs 06.6.3 UXA-06) and is deliberately NOT resolved here. 4) Whether a crimson #BE123C still reads as 'error' rather than 'brand pink' to this developer is a judgement call the numbers cannot settle."
tdd_checkpoint: null

## Symptoms
<!-- Written during gathering, then immutable -->

expected: Every heading (h1 page titles, h2/h3 section labels, card/tile titles) and every color usage (accent, status ok/warn/error, text, background) across companion/static/style.css and companion/pages/*.py is internally consistent across all five pages (Config/Health/Airlines/History/Preview) and matches the validated 06.6.1 sketch-findings design direction — warm serif headings (never on tabular/dense content), a terracotta/coral accent kept visually distinct from status colors, card shadows instead of hairline borders, generous spacing — with only deliberate, tested exceptions (e.g. the WCAG AA contrast-driven accent darkening).

actual: Real, concrete inconsistencies found in a pre-pass across 3 of the 5 pages:
1. Config has no visible section heading above the Runway selection cards (only "Theme" labels the section above it) — a user cannot tell what the three runway cards represent from heading structure alone.
2. Health's anomaly banner still renders the full detail-text list ("ADS-B pipeline run is stale, aDS-B sources disagreed on the selected aircraft recently...") even though the 06.6.1 sketch decision (documented in .claude/skills/sketch-findings-skypane, visual-direction-typography reference) explicitly says to drop this redundant list since the Overview stat tiles below already carry the same information via color/status. Never implemented in 06.6.2/06.6.3.
3. The generated banner text on Health contains a capitalization bug: "aDS-B" with a lowercase leading a mid-sentence ago, appears to be two messages joined without re-capitalizing the second clause.
4. The light-mode accent color (--color-accent: #B13F16, changed from the sketch's #E8622C in commit a3bfd7d for WCAG AA / UXA-04) visually reads too close to --color-status-error (#DC2626) in real screenshots — e.g. the Config "Save Settings" button and the Health error banner's left border look like near-identical shades of brick-red, blurring the "primary action" vs. "something is wrong" distinction even though the two hues are ~16deg apart on paper.
5. Heading-hierarchy consistency across pages has not been fully audited yet — Config/Health/Airlines were spot-checked in a pre-pass; History and Preview were not.

errors: None — no crash, no exception. This is a visual/design-consistency defect, not a functional failure. The "aDS-B" capitalization issue (item 3 above) is a real text-generation bug but non-fatal.

reproduction: Log into the companion web app locally (companion/app.py, any seeded state dir) and visually inspect the Config, Health, and Airlines pages — the missing Runway heading, the undropped Health banner detail list, the "aDS-B" capitalization, and the accent/error color similarity are all visible immediately on page load, no special interaction required.

started: Surfaced 2026-08-31 during the developer's own real-browser verification pass for Phase 06.6.3's closing checkpoint (06.6.3-08 Task 2), immediately after phases 06.6.2 (shared-foundation hardening) and 06.6.3 (per-page redesign) were both implemented and automated-tested green. The developer had not done a real end-to-end visual pass across all five pages together before this session — automated tests and the orchestrator's own structural review both missed these issues, consistent with this project's own established pattern that computed-style/structural checks alone are insufficient for real visual verification.

## Additional scope (from conversation, not a classic symptom field)

**Fix scope for this debug session:** ALL heading (h1/h2/h3, section labels, card/tile titles) and ALL color CSS rules in `companion/static/style.css`, plus their usage across `companion/pages/*.py` and `companion/layout.py` — brought into cross-page consistency with the validated `sketch-findings-skypane` design direction.

**Explicitly OUT of scope for this session** (deferred to a separate page-by-page follow-up the developer has already signaled they want next): layout/grid problems, spacing/density issues, and content/copy changes that are not directly a heading or color rule — e.g. Config's misaligned Runway-card grid, Airlines' contradictory "No resolution data yet" empty-state next to real data, nested horizontal scroll inside narrow cards. Do not fix these here even if noticed; note them for the follow-up instead.

**Hard constraint:** do not revert the light-mode accent from #B13F16 back toward #E8622C (or otherwise lighten it) without re-validating text contrast — `companion/test_contrast_check.py` pins both the WCAG AA contrast ratio and the hue separation from `--color-status-warn`. If the accent/error visual-similarity symptom (item 4 above) needs a fix, it must come from a different lever (e.g. adjusting how/where the accent and error colors are juxtaposed, additional non-color signal, or adjusting the error/warn palette instead) — re-verify against the pinned contrast test either way.

**User-approved process:** fix headings + colors globally first; once the developer has validated that pass for consistency, a second, separate `page par page` iteration (referencing sketches) will follow — do not attempt to fix everything in one pass.

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: 2026-08-31T18:10Z
  checked: baseline test run — all five companion suites
  found: contrast 16/16, companion-app 85/85, config-page 46/46, status-pages 58/58, view-pages 41/41 (246 checks green)
  implication: any regression after the fix is caused by the fix, not pre-existing

- timestamp: 2026-08-31T18:12Z
  checked: `test_contrast_check.py` full contents vs the debug file's assumption that it "pins hue separation"
  found: it pins ONLY WCAG luminance ratios (8 formula fixtures + 8 live text-on-surface pairs). There is zero hue/perceptual-separation assertion anywhere in the repo (`grep -rn "hue" companion/*.py` → no match). The hue-separation guarantee exists solely as prose inside `style.css`'s header comment and the `--color-accent` comment.
  implication: the design system's central colour guarantee has never been machine-checkable. This is the enforcement gap that let symptom 4 happen.

- timestamp: 2026-08-31T18:15Z
  checked: numeric hue / CIE-Lab distance between --color-accent and every status token, both themes
  found: LIGHT accent #B13F16 (H 15.9) — warn #D97706 (H 32.1): hue 16.3°, ΔE76 28.6 | error #DC2626 (H 0.0): hue 15.9°, ΔE76 22.9. DARK accent #FF8A5C (H 16.9) — warn #FBBF24: hue 26.3°, ΔE76 47.0 | error #F87171 (H 0.0): hue 16.9°, ΔE76 22.3.
  implication: SYMPTOM 4 ROOT CAUSE. In BOTH themes the accent's nearest neighbour is `--color-status-error`, not `--color-status-warn` — and error is *closer* than the warn separation the 06.6.1 direction validated as acceptable (22.9 < 28.6 light; 22.3 << 47.0 dark). The design direction (D-04) and every CSS comment only ever guarded the accent-vs-warn pair; the accent-vs-error pair was never named, never checked, and was silently degraded when 06.6.2 darkened the accent from #E8622C to #B13F16 for WCAG AA.

- timestamp: 2026-08-31T18:17Z
  checked: whether the light error token is even contrast-safe today
  found: `#DC2626` scores min 3.96:1 against the three light surfaces (#F7F4EF / #FFFFFF / #EEE8DE) — passes the 3.0 UI-component bar, fails the 4.5 normal-text bar. It is currently only ever used as a fill/border/icon stroke, never as text, so this is latent rather than live.
  implication: any replacement error hue should clear 4.5:1 so the token stops being a trap.

- timestamp: 2026-08-31T18:20Z
  checked: `--color-destructive` vs `--color-status-error` across all four token blocks
  found: identical values in every block (light #DC2626 / #DC2626, dark #F87171 / #F87171). Two token names, one concept, used interchangeably: `.banner--anomaly` and `.page-section.banner--anomaly` read `--color-destructive`; `.dot--error`, `.stat-tile--error`, `.stat-tile--error .stat-tile__icon` read `--color-status-error`. No Python, JS or test file references `--color-destructive`.
  implication: guaranteed future drift — changing "the error colour" requires remembering to change two tokens. Real colour-consistency defect.

- timestamp: 2026-08-31T18:24Z
  checked: every section-heading treatment across all five pages (grep for h1/h2/h3/legend/text-heading)
  found: FOUR different treatments, three of them on the Config page alone. Config: Theme = `<p class="text-label">Theme</p>` (14px sans), Runway = *nothing at all*, Diagnostic LED = `<legend>` (20px sans SEMIBOLD), Poll = `<h2 class="text-heading">` (20px SERIF regular). Health: `<h2 class="text-heading">` ×3 (consistent). Preview: `<h2 class="text-heading">` ×2 (consistent). History: no section heading. Airlines: no section heading.
  implication: SYMPTOM 1 + 5 ROOT CAUSE. History's and Airlines' absences are deliberate and test-pinned (Airlines' "Coverage" heading was dropped by 06.6.3-06/D-18 in favour of the promoted headline — `test_status_pages.py:1561` forbids its return). The real defect is Config, where four sibling groups on one page use four different heading roles.

- timestamp: 2026-08-31T18:26Z
  checked: `legend`'s CSS rule vs the serif heading rule
  found: `legend { font-size: var(--font-heading-size); font-weight: var(--weight-semibold); padding: 0 var(--space-xs); }` — it is NOT in the `h1, h2, h3, .text-heading` serif selector, and it uses `--weight-semibold` where every serif heading uses `--weight-regular`.
  implication: `<legend>Diagnostic LED</legend>` and `<h2 class="text-heading">Poll</h2>` are the same section-heading role at the same 20px size, rendered in two different families AND two different weights, stacked one above the other on the Config page. This is the single clearest heading-consistency defect and it is a pure CSS fix.

- timestamp: 2026-08-31T18:28Z
  checked: the serif allow-list in style.css's own comment (h1/h2/h3/.text-heading/.site-title/.sidebar-title/.stat-tile__caption) against actual rules
  found: `.sidebar-title` is emitted by `layout.py:842` but has NO CSS rule anywhere in the file — it only inherits serif because it is co-classed with `.site-title`. `legend` is a heading role the allow-list never mentions.
  implication: the allow-list comment is the contract, and it is both incomplete (no `legend`) and inaccurate (names a rule that does not exist). Same "prose contract, no enforcement" failure mode as the colour finding above.

- timestamp: 2026-08-31T18:30Z
  checked: heading vertical rhythm
  found: there is no margin rule for `h1`/`h2`/`h3`/`.text-heading` anywhere in style.css — they fall through to UA defaults. Because `.text-heading` is applied both to real `<h2>` elements (Health/Preview/Config) and to `<p>` elements (`layout.empty_state()`, `airlines_page.py:208`, `history_page.py:336`), the same visual heading role gets `0.83em` margins as an h2 and `1em` margins as a p.
  implication: identical-looking headings space differently depending on which tag they happen to sit on. Real typography inconsistency.

- timestamp: 2026-08-31T18:33Z
  checked: card-relief treatment across every card-like component (D-02: "shadow carries the edge instead of a hairline border")
  found: `.stat-tile` and `.battery-trend-section` = `border: 1px solid transparent` + `--shadow-card` (correct). `.page-section` and `.login-card` = `border: 1px solid var(--color-border)` + `--shadow-card` — a visible hairline AND a shadow, exactly what the `.stat-tile` comment says never to do. `.runway-card` and `.history-card` = shadow, no border property at all.
  implication: four different card edge treatments for one card concept. Also: the dark-mode "restore a visible edge" override lists only `.stat-tile, .page-section, .battery-trend-section` — `.runway-card`, `.history-card` and `.login-card` get no dark-mode edge, so cards on Config/History/Login lose their boundary in dark mode while Health's keep theirs.

- timestamp: 2026-08-31T18:35Z
  checked: `--color-border` vs `--color-secondary` used as border colours
  found: `input`, `select` and `.theme-form .theme-option` draw their 1px border with `var(--color-secondary)` (a *surface* token); `.site-nav-toggle`, `.logout-form button` and `.dirty-bar__cancel` draw theirs with `var(--color-border)`. Separately `.data-table td { border-bottom: 1px solid var(--color-secondary) }` while `.data-table tr.row-alt { background: var(--color-secondary) }` — the row separator and the alternating row background are literally the same colour, so every alternate row's bottom rule is invisible.
  implication: two competing conventions for "quiet control edge", plus a straightforward colour bug in the data table that affects History, Airlines and Health.

- timestamp: 2026-08-31T18:37Z
  checked: surface tokens used as foreground colours
  found: `button[type="submit"] { color: var(--color-dominant) }` and `.skip-link { color: var(--color-dominant) }` paint text on an accent fill using the *card-surface* token. There is no on-accent foreground token. `test_contrast_check.py`'s "primary-button label on accent fill" pin uses the literal `#FFFFFF`, which is what `--color-dominant` happens to resolve to in light mode.
  implication: the pinned test and the stylesheet agree only by coincidence of a surface token's current value.

- timestamp: 2026-08-31T18:39Z
  checked: muted/secondary text treatment
  found: no `--color-text-muted` token (deliberately, per a documented rationale). Muting is done with three different opacity values for overlapping roles: `.cell-secondary` 0.7, `.cell-inline-sep` 0.7, `.history-card__secondary` 0.85, `.filter-bar__field .icon` 0.6. `.cell-secondary` and `.history-card__secondary` carry the *same* secondary-data role in the desktop table and the mobile card respectively.
  implication: the same data reads at two different strengths depending on viewport width.

- timestamp: 2026-08-31T18:42Z
  checked: `_anomaly_category_text()` in health_page.py (symptom 3, "aDS-B")
  found: line 605 — `phrase = phrase[0].lower() + phrase[1:]` lower-cases the first character of every anomaly phrase after the first, to make them read mid-sentence. Applied to `"ADS-B pipeline run is stale."` it produces `"aDS-B pipeline run is stale"`. Two of `collect_anomalies()`'s four literal strings begin with the proper noun/initialism "ADS-B".
  implication: confirmed root cause of symptom 3. The transformation is correct in intent but has no guard for a phrase whose first word is an acronym/proper noun.

- timestamp: 2026-08-31T18:45Z
  checked: symptom 2 (Health banner still shows the detail list)
  found: 06.6.1-03 DID remove the bulleted `<ul>` detail markup as the sketch decision required — `collect_anomalies()`'s docstring documents this. 06.6.3-04 (UXA-06) then re-introduced the same information as prose inside the banner text itself via `_anomaly_category_text()`, because UXA-06 required the banner to "name its real failing category instead of a generic 'check the tiles below'".
  implication: NOT drift/oversight — this is a genuine head-on conflict between the 06.6.1 sketch decision (drop the redundant detail, the tiles carry it) and the later 06.6.3 UXA-06 audit requirement (name the categories). Both are validated decisions. Resolving it is a product call, not a bug fix, so it is surfaced at the checkpoint rather than decided unilaterally.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  One failure mode with two instances, not five independent oversights.

  The companion app's design contract for both headings and colours is written
  only as prose inside `companion/static/style.css`'s comments, with nothing
  executable enforcing it — and each prose rule has a coverage hole:

  (a) COLOUR. The separation guarantee names exactly one pair to keep apart:
      `--color-accent` vs `--color-status-warn`. So when 06.6.2 darkened the
      accent #E8622C -> #B13F16 to fix UXA-04's WCAG AA failure, it moved the
      accent to ΔE76 22.9 / 15.9° from `--color-status-error` — CLOSER than
      the ΔE76 28.6 warn separation the direction had examined and accepted —
      and all 16 contrast checks stayed green, because contrast and separation
      are orthogonal questions. Same collision in dark mode (22.3 / 16.9°).
      In both themes the accent's nearest neighbour was the one status colour
      nobody had ever measured it against.

  (b) HEADINGS. The serif allow-list omits `legend`, which is a
      section-heading role (config_page.py's D-06 uses `<legend>` *instead of*
      an `<h2>` so a group is never named twice). `legend` therefore kept the
      browser's sans-serif plus this file's own `--weight-semibold`, stacking
      a sans-semibold `<legend>Diagnostic LED</legend>` directly above a
      serif-regular `<h2 class="text-heading">Poll</h2>` at the identical 20px
      size. With no single enforced heading role, per-page implementers
      reached for four different treatments — three of them on Config alone,
      where the Runway group ended up with no name at all.

  The same "written down, never enforced" pattern explains the rest of the
  audit's findings: `--color-destructive` duplicating `--color-status-error`
  in four token blocks; `.page-section` never updated when 06.6.2 split the
  two-level surface model into three, so it kept a hairline+shadow edge and no
  card background; the dark-mode card-edge override naming three of six card
  components; `.data-table td`'s separator drawn in the same token as
  `.row-alt`'s background, making it invisible on alternate rows.

fix: |
  HEADINGS
  - `legend` added to the `h1, h2, h3, .text-heading` serif selector; the
    standalone `legend` rule's `font-weight: var(--weight-semibold)` removed
    (equal specificity, later in source order — it silently beat the serif
    rule's --weight-regular, which is the mechanism of the defect).
  - Explicit heading rhythm (`margin: 0 0 var(--space-sm)`) for
    h1/h2/h3/.text-heading, so the role spaces identically whether it lands on
    an `<h2>` or on a `<p class="text-heading">` (empty_state()).
  - config_page: Runway group given `<h2 class="text-heading">Runway</h2>`
    (SYMPTOM 1 — it had no name at all); Theme's `<p class="text-label">Theme</p>`
    promoted to the same `<h2 class="text-heading">`. Not `<legend>`, because
    D-04/D-05 deliberately dropped both groups' `<fieldset>` and a legend
    outside a fieldset is invalid. Config now names all four groups once, at
    one level.
  - Serif allow-list comment corrected: `legend` added, `.sidebar-title`'s
    non-existent rule explained (it inherits via `.site-title`).
  - AUDIT RESULT for the two unaudited pages: History and Preview are both
    CORRECT as-is. Preview uses `<h2 class="text-heading">` for both sections.
    History deliberately has no section heading — it has a single content
    group already named by the page title plus its purpose sentence, the same
    reasoning that dropped Airlines' "Coverage" heading (06.6.3-06 / D-18,
    pinned by test_status_pages.py:1561). No change made to either.

  COLOUR
  - `--color-status-error` re-separated from the accent WITHOUT touching the
    accent, so UXA-04's WCAG AA fix is untouched: light #DC2626 -> #BE123C
    (ΔE76 22.9 -> 29.3, hue 15.9° -> 30.5°), dark #F87171 -> #FB7185
    (ΔE76 22.3 -> 32.2, hue 16.9° -> 25.6°). Side benefit: the light token's
    worst-case contrast on the three light surfaces rises 3.96 -> 5.16, so it
    is now text-safe and not only fill-safe.
  - Banners gain a 10% wash of their own severity colour over
    --color-secondary (color-mix, the idiom .sidebar-link--active already
    uses). Previously all three severities shared one flat surface and
    differed only in a 4px stripe, so "something is wrong" was a thin red line
    competing with the accent-filled primary button rather than reading as its
    own region. This is the second lever on SYMPTOM 4, and matches the sketch
    source's own `.banner--anomaly{background:#FEF2F0;...}`.
  - `--color-destructive` deleted; its two consumers read
    `--color-status-error`. One concept, one token.
  - `.page-section.banner--anomaly` now restates border-left WIDTH as well as
    colour (the shorthand reset meant Health's source-fault block — the most
    severe state the page can show — drew a 1px alert edge while every other
    anomaly banner drew 4px) and restates the severity wash (cascade).
  - `.page-section` given `background: var(--color-dominant)` and a
    transparent border: it was the only card still on the pre-06.6.2 two-level
    surface model, rendering Config's Poll/LED and both Preview sections as
    shadowed canvas-coloured blocks with a hairline+shadow edge D-02 forbids.
    `.login-card` likewise de-haired.
  - `.runway-card` / `.history-card` given `border: 1px solid transparent`,
    and all six card components added to the dark-mode card-edge override
    (it listed three), so no card loses its boundary in dark mode.
  - `.data-table td` separator moved --color-secondary -> --color-border (it
    was the exact colour of `.row-alt`'s background, so it vanished on every
    alternate row of History, Airlines and Health).
  - `input`/`select`/`.theme-form .theme-option` borders moved
    --color-secondary -> --color-border, matching .site-nav-toggle /
    .logout-form button / .dirty-bar__cancel. One "quiet control edge" role,
    one token.
  - New `--color-on-accent` token (#FFFFFF light / #151922 dark — the values
    these rules already resolved to) replaces `--color-dominant` doing
    foreground duty in `button[type="submit"]` and `.skip-link`. Zero visual
    change; the pinned contrast test now points at a real token instead of
    agreeing with the stylesheet by coincidence.
  - `.history-card__secondary` opacity 0.85 -> 0.7, matching `.cell-secondary`
    (identical History data, rendered as a card below 960px and as a table
    cell above it, previously at two different strengths).
  - `.theme-swatch__chip` given a --color-border hairline: its fill is a raw
    e-ink PALETTE_RGB inline style the stylesheet cannot reason about, and the
    panel palette includes white.
  - style.css header comment rewritten: the "accent is reserved to exactly
    these uses" list was stale (it named 6 uses; there are 13), and the
    colour-separation contract now points at the test that enforces it.

  COPY (SYMPTOM 3)
  - health_page `_anomaly_category_text()` lower-cased the first character of
    every phrase after the first, rendering "ADS-B ..." as "aDS-B ...". New
    `_starts_with_acronym()` guard skips any phrase whose first word carries a
    capital after its first character — no hard-coded acronym list, so it
    cannot go stale when a fifth anomaly string is added. Ordinary phrases
    ("A battery reading..." -> "a battery reading...") still lower-case.

verification: |
  All five companion suites green: 266 checks (246 before, +20 new).
    contrast-check 31/31 (was 16), companion-app 88/88 (was 85),
    config-page 47/47 (was 46), status-pages 59/59 (was 58),
    view-pages 41/41 (unchanged).
  `server/test_poll_loop.py`'s panel.bin digest mismatch is the pre-existing,
  unrelated failure documented throughout STATE.md — `git status` confirms
  zero `server/` files were touched.

  FALSIFICATION TEST EXECUTED (the one written in the reasoning checkpoint
  before any code changed): the old error tokens were temporarily restored in
  test_contrast_check.py's theme table. Result — 27/31, with exactly the four
  new separation checks failing and reporting the real measured numbers
  (ΔE76 22.9 and 22.3, hue 15.9° and 16.9°). The checks therefore measure the
  thing that broke rather than merely passing at whatever the current values
  happen to be. Four further "discrimination guard" checks assert the same
  property permanently, so the floors can never be loosened into decoration.

  ENFORCEMENT ADDED (this is what stops the recurrence, not the token values):
  - companion/contrast_check.py: `hue_degrees()`, `hue_separation()`,
    `perceptual_distance()` (CIE76), `MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0`
    (calibrated to the accent-vs-warn pair the direction validated),
    `MIN_SIGNAL_HUE_SEPARATION = 24.0` (accent-vs-error only, with the reason
    it does not apply to warn documented in the code). Still zero imports.
  - test_contrast_check.py section 3: every accent/status pair in both themes,
    plus the discrimination guards and a wrap-around fidelity check.
  - test_companion_app.py: the serif-heading contract asserted in BOTH
    directions (every heading role shares the one serif rule and `legend` does
    not restate its weight; `--font-serif` never reaches table/body/mono/nav
    rules), plus "there is exactly one error-signal token".
  - test_config_page.py: all four Config groups named exactly once at one
    heading level.
  - test_status_pages.py: acronym-safe anomaly-category joining, driven
    through the real `collect_anomalies()` strings so it cannot drift from the
    copy it protects.

  HUMAN VISUAL CONFIRMATION (2026-08-31, against the real running app after
  restarting the server to pick up 01235a6). Performed by the orchestrator
  rather than the end developer directly, and recorded as such — this project's
  own MEMORY.md notes that computed-style checks alone previously missed a real
  mobile nav bug, which is why this step exists at all.
  - Health: the banner reads "ADS-B" correctly everywhere — the "aDS-B"
    capitalisation bug is gone.
  - Health: the crimson error banner/border is now CLEARLY distinguishable from
    the accent-coloured "Save Settings" button. This is the symptom-4 fix
    landing in practice, not just in the ΔE/hue numbers.
  - Config: the "Runway" heading is present for the first time. It renders
    awkwardly positioned next to "Theme", but that is the pre-existing broken
    grid, explicitly out of this session's scope and already logged for the
    page-by-page pass. Expected, not a regression from this fix.
  - Colour judgement call settled by the developer: #BE123C reads fine as
    "error", NOT as brand pink. Confirmed — no further colour change needed,
    and the accent stays at #B13F16 with UXA-04's WCAG AA fix intact.

files_changed:
  - companion/static/style.css
  - companion/contrast_check.py
  - companion/pages/config_page.py
  - companion/pages/health_page.py
  - companion/test_contrast_check.py
  - companion/test_companion_app.py
  - companion/test_config_page.py
  - companion/test_status_pages.py

deferred_to_follow_up:
  - "SYMPTOM 2 — NOT FIXED, needs a product decision. The 06.6.1 sketch says
     drop the banner's redundant detail (the Overview tiles carry it); 06.6.3's
     UXA-06 audit requires the banner to name its real failing categories.
     06.6.1-03 did remove the bulleted <ul>; 06.6.3-04 re-added the same
     information as prose inside the banner text. Both decisions are validated
     and tested. Reverting UXA-06 unilaterally would undo an audited
     requirement, so this is surfaced rather than decided.
     DEVELOPER VERDICT 2026-08-31: left unresolved BY DESIGN. Not closed here
     and not a defect of this fix — carried forward into the upcoming
     page-by-page pass on Health, where the two decisions can be reconciled
     with the rest of that page's redesign in view. Whichever way it lands,
     the losing decision's pinned test must be updated in the same change so
     the conflict cannot silently reappear."
  - "Out-of-scope layout items noted during the audit, for the page-by-page
     pass: Config's Runway-card grid alignment (adding the Runway <h2> may
     have changed how it reads — worth a look); the LED <fieldset>'s visible
     border nested inside a shadowed .page-section reads as redundant chrome
     now that the section has a real card surface; Airlines' contradictory
     'No resolution data yet' empty state beside real data; nested horizontal
     scroll inside narrow cards."
  - "`.empty-state__heading`, `.empty-state__body` and `.freshness-refresh`
     are emitted by markup but have no CSS rule — harmless unused hooks today,
     either style them or drop them."
