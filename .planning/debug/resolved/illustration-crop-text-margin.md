---
status: resolved
passes: 2 (vertical aircraft-to-text gap fixed + user-confirmed 2026-08-28; horizontal centering + previous-card alignment fixed 2026-08-28, awaiting on-glass confirmation)
trigger: "Ce que je vois sur ma liseuse, enfin sur mon écran Inc [e-ink], c'est que la marge entre l'avion visible et l'écriture du dessous n'est jamais la même et je suspecte que la boxe et le crop transparent qui entoure l'avion varie d'une image à l'autre, ce qui fait qu'on dirait que l'écriture est décalée différemment en fonction du type d'avion."
created: 2026-08-28T00:00:00Z
updated: 2026-08-28T10:05:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

hypothesis: CONFIRMED and FIXED. Root cause was a measurement mismatch, not a logic error: `draw_illustration()` returned the full source rectangle while itself erasing a soft drop-shadow band (alpha 1..127) that sits 37-174px tall below every aircraft. Both text blocks anchored to that rectangle, so the visible gap swung 17-154px by airline. Full detail in Resolution below.
test: Fix verified. Gap measured across all 43 vendored illustrations through the real two-flight layout: main gap is exactly {54} and previous gap exactly {47} for every file, while per-file opaque padding still spans 37-152px / 21-86px. Two mutation tests confirm the new regression checks are real guards, not tautologies. The Air France reference render is byte-identical to before the fix.
expecting: On the physical panel, the aircraft-to-text spacing should now look identical for every airline, and should match what an Air France render looked like before (that render is unchanged, byte for byte). Illustrations that previously looked loosest - ASL Airlines France, Air Europa, the generic-a320/a330/b737 shapes, Tunisair, Pegasus - tighten by up to 100px; the tightest, Iberia, loosens by 37px.
next_action: PASS 1 CLOSED - user reviewed the before/after previews and confirmed 2026-08-28: "Ca regle le probleme, mais j'aimerais que tu les corriges aussi le, les centrale horizontale." Fix committed as cea4984; session filed to .planning/debug/resolved/ per this project's convention. The same confirmation explicitly extended scope to the horizontal-centering finding this session had measured and deliberately left open - continued as PASS 2 below rather than opened as a new session, because it is the same root cause (layout anchored to the padded rectangle instead of the painted pixels) on the other axis.
reasoning_checkpoint:
  hypothesis: |
    draw_illustration() returns the full placement rectangle of the resized PNG. Every
    vendored file carries a soft drop-shadow band (alpha 1..127) below the aircraft that
    draw_illustration()'s own `p > 127` threshold erases before paste(). The rectangle's
    bottom therefore sits 37-174px below the last painted pixel, varying per file, and
    both text blocks anchor to that rectangle - so the visible gap varies per file.
  confirming_evidence:
    - "All 43 vendored PNGs measured with the renderer's exact threshold: post-resize
      bottom padding 37-174px at MAIN_W=992 (spread 137px), 21-99px at PREV_W=565."
    - "Effective main-block gap computed per file: 17px (iberia-airlines) to 154px
      (asl-airlines-france) - a 9.1x variation, directly matching the reported symptom."
    - "Naive Image.getbbox() vs thresholded bbox differ by a 5-261px soft-shadow band;
      six files (air-france.png among them) report naive bottom padding of exactly 0."
    - "Both sketch-era files at commit 73a6eb2 (air-france.png, vueling-airlines.png)
      report naive bottom padding 0 - explaining the false docstring/UI-SPEC claim."
  falsification_test: |
    A uniform or zero thresholded bottom padding across the file set would refute this.
    Measured: no file has zero, and the spread is 137px. Refuted comprehensively.
    Post-fix falsification: if the measured gap between the opaque bottom and the drawn
    text top is NOT identical across illustrations with widely different padding, the
    fix does not address the root cause.
  fix_rationale: |
    Anchoring text to the opaque-pixel bbox (computed with the renderer's own threshold)
    removes the varying quantity from the layout entirely - the gap becomes a constant by
    construction, not by per-file luck. This is the root cause, not a symptom: no
    per-file tuning is introduced, and the quantity used for layout becomes the same
    quantity that is actually painted. Constants 54px (main) / 47px (previous) are the
    measured real gaps in the render the developer confirmed at D-26, so the approved
    look is preserved rather than redesigned.
  blind_spots: |
    - Not verified on real Spectra 6 glass (this is exactly what the human checkpoint is
      for); preview PNGs only, same limitation D-26 itself carries.
    - Horizontal padding is also non-zero and asymmetric (left 3-32px, right 5-29px after
      resize), so the aircraft is off-centre by up to ~4px and the previous card's
      right-alignment is off by its right padding. Deliberately NOT changed - it is a
      separate visual change the developer has not asked for. Documented, not fixed.
    - prev_w still derives from the main illustration's full rendered width (992), keeping
      03-UI-SPEC.md's documented 565px. Switching it to the opaque width would resize the
      previous card, which is out of scope for the reported bug.
    - Assumes the D-26 sketch used the CLI's default preview route (Air France main +
      Vueling previous). Strongly supported (those are render.py's own _PREVIEW_ROUTE /
      _PREVIEW_PREVIOUS_ROUTE defaults) but not directly witnessed.
tdd_checkpoint: null

## Symptoms
<!-- Written during gathering, then immutable -->

expected: The visual gap between the bottom of the aircraft illustration and the flight-info text drawn below it should look visually consistent across every render, regardless of which airline/aircraft-type illustration is shown.
actual: The user observes on the real physical e-ink device that this gap is inconsistent - it appears to vary depending on which aircraft/airline illustration is currently displayed.
errors: None - a pure visual/layout inconsistency, not a crash or logged error.
reproduction: Not a single controlled repro - an ongoing visual observation across different real detections on the deployed device. Reproducible in principle by rendering the same layout with different illustration files and comparing the visible gap.
started: Reported today, 2026-08-28, from live observation of the deployed device. Onset relative to when this behavior was introduced (D-26's two-flight poster / MAIN_TEXT_OVERLAP_PX design) is unknown.

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: 2026-08-28T00:00:00Z
  checked: server/plane/render.py draw_illustration() (lines 431-454)
  found: |
    Returns `(left, top, left + w, top + h)` - the full rectangle of the resized source
    image as pasted onto the canvas - computed purely from `resized_rgba.size`, with no
    reference to which pixels within that rectangle are actually opaque.
  implication: The returned "illustration bounding box" is a geometric placement box, not
    a visual-content box. Any transparent padding baked into a source PNG becomes part of
    this bbox and is therefore inherited by anything anchored to it.
- timestamp: 2026-08-28T00:00:00Z
  checked: server/plane/render.py draw_main_text_block() docstring and body (lines 582-610)
  found: |
    "D-26 main flight text: two centred lines starting at main_bbox's bottom minus
    MAIN_TEXT_OVERLAP_PX (a deliberate slight overlap - the vendored illustration files
    have no transparent bottom padding of their own, confirmed via Image.getbbox() during
    the live sketch pass, so this is the only way to get the text as close as confirmed)."
    Body: `top_y = main_bbox[3] - MAIN_TEXT_OVERLAP_PX`, text drawn from there.
  implication: The text's vertical anchor is explicitly, by design, main_bbox's bottom
    (the FULL rectangle's bottom from draw_illustration()) minus one fixed global
    constant. The "no transparent bottom padding" claim is asserted as a fact about ALL
    vendored files but is attributed to a single "live sketch pass" - i.e. a spot check,
    not a systematic per-file measurement. This is the load-bearing assumption the whole
    fixed-offset design depends on.
- timestamp: 2026-08-28T09:10:00Z
  checked: |
    MEASUREMENT PASS. All 43 vendored PNGs under server/assets/icons/illustrations/
    (including generic-fallback.png). For each: Image.convert("RGBA"), alpha channel
    hard-thresholded with the EXACT expression draw_illustration() uses
    (`.point(lambda p: 255 if p > 127 else 0)`), then Image.getbbox() on that mask.
    Measured on the raw source AND after _resize_illustration() at both real production
    target widths (MAIN_W=992, PREV_W=565, recomputed from FRAME_INSET_FRAC /
    MAIN_ILLUSTRATION_WIDTH_FRAC / PREVIOUS_ILLUSTRATION_WIDTH_FRAC, not hardcoded).
  found: |
    HYPOTHESIS CONFIRMED - and the docstring's claim is false for 43 of 43 files.
    EVERY vendored illustration has substantial transparent bottom padding.

    Source-file bottom padding: min 82px (iberia-airlines) .. max 293px
    (asl-airlines-france); spread 211px. As a fraction of image height:
    11.310% .. 31.137%, mean 23.37%. Not one file has zero bottom padding.

    After resize to MAIN_W=992, bottom padding is 37px .. 174px, spread 137px:
      iberia-airlines.png            37    (thinnest)
      amelia.png                     47
      transavia-france.png           51
      generic-fallback.png           58
      air-france.png                 74
      easyjet.png                   106
      generic-b737.png              165
      asl-airlines-france.png       174    (thickest)

    Resulting EFFECTIVE visual gap between the aircraft's real bottom-most opaque pixel
    and the main text anchor (= resized bottom padding - MAIN_TEXT_OVERLAP_PX(20)):
      +17px  iberia-airlines.png     (smallest)
      +27px  amelia.png
      +31px  transavia-france.png
      +38px  generic-fallback.png
      +54px  air-france.png
      +86px  easyjet.png
      +145px generic-b737.png
      +154px asl-airlines-france.png (largest)
    MAIN effective gap: min 17px, max 154px, SPREAD 137px - a 9.1x variation.

    Previous-flight block, resized to PREV_W=565: bottom padding 21px..99px; effective
    gap (= bottom padding + PREVIOUS_TEXT_GAP_PX(22)) 43px..121px, SPREAD 78px.

    Secondary findings:
    - MAIN_TEXT_OVERLAP_PX's documented "deliberate slight overlap" NEVER overlaps
      anything: even the thinnest-padded file leaves a +17px gap. The constant's stated
      rationale does not describe the behaviour it actually produces.
    - Horizontal padding is also non-zero and ASYMMETRIC after resize: left 3..32px,
      right 5..29px. Per-file left/right asymmetry reaches 8px (french-bee: L14/R6;
      amelia: L18/R25), so `(WIDTH - w) // 2` centres the transparent RECTANGLE, not the
      aircraft - the artwork is off-centre by up to ~4px. Small next to the 137px
      vertical defect, but the same root cause.
    - Source aspect ratios vary 1.78..3.00, so resizing to a fixed target WIDTH yields
      resized heights of 331..558px (MAIN). The padding is therefore scaled by a
      per-file factor as well - the post-resize spread cannot be predicted from the
      source spread alone, which is why post-resize measurement was required.
  implication: |
    Root cause confirmed and quantified. `draw_illustration()` returns a geometric
    placement rectangle whose bottom edge sits 37-174px BELOW the aircraft's real visual
    bottom, varying per file. Both `draw_main_text_block()` and
    `draw_previous_text_block()` anchor to that rectangle, so the visible aircraft-to-text
    gap inherits the full 137px (main) / 78px (previous) spread. This is exactly the
    symptom reported from the device. The alternate hypotheses named in `test` are not
    needed: aspect-ratio scaling in _resize_illustration() is a contributing MULTIPLIER on
    the per-file padding, not an independent cause, and the previous-flight block shows
    the same defect from the same shared bbox contract.
- timestamp: 2026-08-28T09:35:00Z
  checked: |
    ORIGIN OF THE FALSE ASSUMPTION. 03-CONTEXT.md line 170 words the claim in the
    SINGULAR - "confirmed *this specific illustration file* has zero transparent bottom
    padding of its own, verified via Image.getbbox()". Tested what `Image.getbbox()`
    actually reports versus what draw_illustration()'s `>127` hard threshold paints,
    for all 43 files. Also extracted the sketch-era file versions from commit 73a6eb2
    (the D-26 commit that introduced MAIN_TEXT_OVERLAP_PX, 2026-08-26) and measured those.
  found: |
    The two measurements disagree by an entire SOFT-SHADOW BAND of alpha 1..127 pixels
    sitting below each aircraft - a drop shadow baked into the art. `Image.getbbox()`
    counts those faint pixels as content. `draw_illustration()` hard-thresholds them to
    fully transparent (`p > 127`) and never paints a single one of them.

    Soft-band size (naive bbox bottom vs thresholded bbox bottom): 5px .. 261px,
    mean 143px. Six files report a naive bottom padding of EXACTLY 0 while their real
    painted padding is large:
      air-france.png             naive 0  -> thresholded 150   (soft band 150)
      generic-fallback.png       naive 0  -> thresholded 120
      iberia-airlines.png        naive 0  -> thresholded  82
      transavia-france-a320.png  naive 0  -> thresholded 105
      tuifly-belgium.png         naive 0  -> thresholded 174
      wizz-air.png               naive 0  -> thresholded 155

    Sketch-era versions at commit 73a6eb2 (air-france.png is byte-identical to today's;
    vueling-airlines.png was later replaced by 56543f8 on 2026-08-27):
      air-france.png       src 2008x783  naive bottom pad = 0  -> resized@992: opaque pad 74
      vueling-airlines.png src 2135x736  naive bottom pad = 0  -> resized@565: opaque pad 25

    Both files the developer had on screen during the D-26 sketch pass reported naive
    bottom padding of exactly ZERO. The claim was truthfully recorded and truthfully
    measured - it just measured a quantity the renderer does not use.
  implication: |
    The bug is a measurement mismatch, not a logic error: the layout was tuned against
    `Image.getbbox()` while the renderer paints against a `>127` alpha threshold that was
    introduced for an unrelated reason (03-RESEARCH.md Pitfall 2 - a soft alpha mask
    blends palette INDEX INTEGERS during paste() and produces illegal in-between
    indices). The threshold silently erases the drop shadow the bbox check was counting.

    This also yields the grounded anchor for the corrected constants. In the render the
    developer actually confirmed:
      main block:     opaque bottom pad 74 - MAIN_TEXT_OVERLAP_PX(20) = 54px real gap
      previous block: opaque bottom pad 25 + PREVIOUS_TEXT_GAP_PX(22) = 47px real gap
    54px and 47px are therefore the developer-approved gaps, measured against the pixels
    that are actually painted - not invented numbers.

## Resolution

root_cause: |
  `draw_illustration()` returns the full placement rectangle of the resized source PNG,
  but every vendored illustration carries a soft drop-shadow band (alpha 1..127) below
  the aircraft that `draw_illustration()` itself erases via its `p > 127` hard threshold.
  The rectangle's bottom edge therefore sits 37-174px below the aircraft's last painted
  pixel, by a per-file amount. `draw_main_text_block()` and `draw_previous_text_block()`
  anchor their text to that rectangle, so the visible aircraft-to-text gap inherits the
  full per-file spread: 17-154px (main, 9.1x variation) and 43-121px (previous). The
  design constant `MAIN_TEXT_OVERLAP_PX = 20` was tuned against `Image.getbbox()`, which
  counts the soft shadow the renderer discards - the two sketch-era files both reported a
  naive bottom padding of exactly 0, which is how the "no transparent bottom padding"
  claim entered the docstring and 03-UI-SPEC.md as fact.
fix: |
  Make the layout measure the same pixels the renderer paints.

  1. `render.py`: added `ILLUSTRATION_ALPHA_THRESHOLD = 127`, `_threshold_alpha()`
     and `_opaque_bbox()`. The paste mask and every bbox measurement now derive from
     one named threshold, so "what we paint" and "what we measure" cannot drift.
  2. `draw_illustration()` now returns an `IllustrationPlacement` carrying BOTH boxes:
     `.rect` (full placement rectangle, unchanged semantics) and `.content` (tight bbox
     of the pixels actually painted, absolute canvas coords). Falls back to `.rect` when
     nothing is painted; never raises.
  3. `draw_main_text_block()` anchors to `.content[3] + MAIN_TEXT_GAP_PX`.
     `draw_previous_text_block()` anchors to `.content[3] + PREVIOUS_TEXT_GAP_PX`, while
     keeping its horizontal right-alignment on `.rect[2]` (the edge the previous
     illustration was itself positioned against - moving only one of the two would pull
     text and art apart).
  4. Retired `MAIN_TEXT_OVERLAP_PX = 20` (its "deliberate slight overlap" never
     overlapped anything) in favour of `MAIN_TEXT_GAP_PX = 54`; `PREVIOUS_TEXT_GAP_PX`
     22 -> 47. Both values are the REAL measured gaps in the render D-26 confirmed:
     air-france.png 74px opaque padding - 20 = 54; vueling-airlines.png 25px + 22 = 47.
  5. Deliberately NOT changed: `_assert_within_canvas()` still bounds `.rect` (it is a
     "falls off the canvas" guard, so the conservative footprint is correct), and
     `prev_w`/`prev_left` still derive from the main `.rect`, preserving
     03-UI-SPEC.md's documented 992 x 0.57 = 565px previous-card width.
verification: |
  - Gap constancy, all 43 vendored illustrations rendered through the real two-flight
    layout: distinct main gaps observed = {54}, distinct previous gaps = {47}, while the
    underlying per-file opaque bottom padding still spans 37-152px / 21-86px. Before the
    fix the same measurement gave 17-154px / 43-121px.
  - D-26 reference render preserved EXACTLY: `render.py --state departing --callsign
    AF1380` (Air France) is byte-identical before and after -
    sha256 63ef385ce58a1692280d0a41dfd07b381d258612d8d9c798e3031263b1c25eb7.
    The approved look was reproduced, not redesigned.
  - Mutation test 1 (re-anchor both blocks to `.rect`): the two new gap-constancy checks
    FAIL, reporting the original {17, 54, 154} spread. Guard is real, not tautological.
  - Mutation test 2 (`_opaque_bbox()` reduced to a naive `getbbox()`): three checks FAIL,
    including the fixture-triviality guard. The specific mistake that caused this bug is
    now caught.
  - No canvas overflow: lowest text anchor across all 43 files is y=1387 of 1600; no
    `_assert_within_canvas()` assertion trips.
  - Full suite `scripts/run-all-tests.sh`: PASS, 247 checks, zero failures
    (render 50/50, illustrations 47/47, enrich 45/45, plane-detection 37/37,
    poll-loop 22/22, poll-cycle 20/20, runway-config 14/14, dither 6/6, e2e 6/6).
  - HUMAN-VERIFIED 2026-08-28: the user reviewed the asl-airlines-france and
    iberia-airlines before/after previews and confirmed the vertical gap problem is
    solved ("Ca regle le probleme"). Committed as cea4984.
files_changed:
  - server/plane/render.py: threshold/opaque-bbox helpers, IllustrationPlacement return
    contract, both text blocks re-anchored, gap constants corrected
  - server/test_render.py: updated the contract assertion in the Pitfall-2 check; added
    4 checks (2 illustration-file-agnostic gap-constancy guards, 1 naive-getbbox guard,
    1 structural placement guard); EXPECTED_CHECK_COUNT 46 -> 50
  - .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md: corrected items 4 and
    6 and the constants row, with an explicit note on what the old text claimed and why
    it was false
  - server/assets/icons/illustrations/HANDOFF.md: new "Framing / transparent margin"
    requirement row plus a "framing is not load-bearing" note warning future art
    deliveries against trimming margins or verifying padding with Image.getbbox()

---

# PASS 2 — horizontal centering and alignment (2026-08-28)

Scope extension, not a new bug: the user's confirmation of pass 1 ("Ça règle le
problème") came with "mais j'aimerais que tu les corriges aussi le, les centrale
horizontale." Same root cause — layout anchored to the padded rectangle instead of the
painted pixels — on the other axis, so it continues in this file rather than opening a
new session.

## Evidence (pass 2)

- timestamp: 2026-08-28T11:00:00Z
  checked: |
    Re-measured horizontal padding across all 43 vendored files post-resize with the
    renderer's own threshold, at both MAIN_W=992 and PREV_W=565. Pass 1's blind-spot note
    ("off-centre by up to ~4px") was treated as a preliminary observation and re-derived
    from scratch, not reused. Also measured the previous card's VERTICAL centering error,
    which pass 1 had not examined at all.
  found: |
    Pass 1's preliminary estimate was TOO LOW. Real figures:

    MAIN horizontal (rect is centred on the canvas, so the visible aircraft is displaced
    by (L-R)/2):
      left padding  3..32px (mean 11.4)
      right padding 5..29px (mean 12.1)
      centering error -4.0 .. +7.5px, |error| mean 1.5px, worst 7.5px
      worst files: generic-beechcraft1900d +7.5, generic-atr72 +5.0, french-bee +4.0,
                   lot-polish-airlines -4.0
    So the true worst case is 7.5px, not the ~4px estimated in pass 1.

    PREVIOUS right-alignment: the card's RECT right edge was pinned to the main card's
    RECT right edge, so each aircraft's visible right edge fell short by its OWN right
    padding - main 5..29px, previous 3..17px. The quantity the eye actually compares is
    the difference between the two, across (main, previous) file pairings:
      worst real pairing = km-malta-airlines.png (main, 29px) vs transavia-france.png
      (previous, 3px) = 26px of visible misalignment.

    PREVIOUS vertical centering - a THIRD instance, not previously examined. prev_top
    centres the RECT on PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC. Because the drop-shadow band
    makes bottom padding always exceed top padding, the error is systematically signed:
      top padding    3..71px (mean 27.4)
      bottom padding 21..99px (mean 59.3)
      vertical centering error -5.5 .. -28.5px - ALWAYS negative, mean -15.9, spread 23px
    Every previous aircraft rendered high, by a per-file amount.

    Visible-width spread (for the sizing decision): MAIN 933..984px, PREV 532..560px.
  implication: |
    Three distinct placement anchors were all reading `.rect`. All three are the same
    defect as pass 1. The vertical-centering one was not in the user's request and not in
    pass 1's blind spots either - it surfaced only because pass 2 measured the previous
    card's vertical geometry for the first time.

## Resolution (pass 2)

root_cause: |
  Same as pass 1, on the remaining axes. `_build_active_canvas()` centred the main
  illustration with `(WIDTH - w) // 2`, right-aligned the previous card with
  `main_rect[2] - prev_w`, and centred it vertically with
  `round(HEIGHT * FRAC - prev_h / 2)` - all three operate on the padded source
  rectangle. `draw_previous_text_block()` likewise right-aligned to `prev_placement.rect[2]`.
fix: |
  Three placement helpers, all measuring painted pixels via the pass-1 `_opaque_bbox()`,
  each falling back to the full rectangle when nothing would be painted, none raising:
  `_left_for_centered_content()`, `_left_for_right_aligned_content()`,
  `_top_for_centered_content()`.

  - main illustration: centred on its visible horizontal midpoint (canvas centre)
  - previous illustration: its visible right edge placed on the MAIN aircraft's visible
    right edge; its visible vertical midpoint placed on CENTER_Y_FRAC
  - previous text: right-aligned to `prev_placement.content[2]`, i.e. that same shared
    visible line
  - PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC re-derived 0.76 -> 0.7528, the value at which the
    sketch-era vueling-airlines.png card lands on the identical row (prev_top = 1118
    both ways), preserving the confirmed D-26 composition

  DELIBERATELY UNCHANGED - `prev_w` still derives from the main illustration's `.rect`
  width. Re-decided with fresh eyes now that centring is in scope: `.rect` width is a
  constant 992 for every file, so the previous card's size is stable. Deriving it from
  the main's opaque width (933-984px) would make the previous card's SIZE depend on which
  airline is in the MAIN slot - the same previous aircraft rendering up to 5% larger or
  smaller depending on what flew before it. That is a new per-file coupling and strictly
  worse than the ~28px visible-width variation it removes. Sizing stays stable; only
  position follows the painted pixels.
verification: |
  - 47 (main, previous) file pairings rendered through the real layout, including every
    file as main paired with a rotating partner plus the extreme-padding combinations:
      I1 main visible horizontal midpoint vs canvas centre: {-0.5, 0.0, +0.5}
         (was -4.0 .. +7.5)
      I2 previous visible right edge minus main visible right edge: {0} (was up to 26)
      I3 previous visible vertical midpoint vs the CENTER_Y line: {-0.5, 0.0}
         (was -5.5 .. -28.5)
      I4 previous text anchor x minus previous visible right edge: {0} (was 3..17)
      I5 pass-1 gaps still exactly {54} / {47}
    The +-0.5px residuals are integer-pixel-grid rounding, i.e. optimal.
  - 4 mutation tests, one per reverted anchor (M3 main centring, M4 previous
    right-alignment, M5 previous vertical centring, M6 previous text alignment): each
    fails exactly the intended new check with the measured error in the message - M4
    reports the predicted 26px, M5 reports 29.0px.
  - Full suite scripts/run-all-tests.sh: PASS, 250 checks (render 53/53), ruff clean,
    check-attribution.sh clean.
  - NOT yet human-verified on glass - annotated before/after previews produced for the
    worst pairing (magenta = main aircraft's right edge, cyan = previous aircraft's).
files_changed:
  - server/plane/render.py: _left_for_centered_content(), _left_for_right_aligned_content(),
    _top_for_centered_content(); main/previous placement re-anchored;
    draw_previous_text_block() right-aligns to .content[2];
    PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC 0.76 -> 0.7528
  - server/test_render.py: _PlacementSpy and _forced_illustration_pair helpers; 3 new
    checks (main centring, previous right-alignment + text, previous vertical centring);
    _measured_gaps() now reads real placements instead of re-deriving geometry;
    EXPECTED_CHECK_COUNT 50 -> 53
  - .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md: items 3, 5 and 6
    corrected, including the explicit "sizing stays stable, position follows painted
    pixels" rationale
