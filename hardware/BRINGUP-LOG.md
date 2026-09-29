# SkyPane — Hardware Bring-Up Log

This log records the physical assembly, first flash, and first-light
verification of the XIAO ESP32-S3 Plus + EE02 driver board + 13.3" Spectra 6
panel, per plan `01-06-PLAN.md`.

## Arrival

Both packages physically arrived the week of **2026-08-17 to 2026-08-23**
(the calendar week before this log entry, 2026-08-25) — the developer did
not track the exact day within that week. This falls within
`hardware/BOM.md`'s estimated delivery windows for both orders (Seeed EE02
kit: 2026-08-14 to 2026-08-26; Kubii battery+cable order: estimated
2026-08-08, so that order likely arrived earlier in the window than the
EE02 kit did) — no delivery-window overrun to flag.

| Item | Order | Arrived on |
|---|---|---|
| XIAO ePaper DIY Kit EE02 (board + panel bundle) | Seeed order <seeed-order-ref> | Week of 2026-08-17 to 2026-08-23 (exact day not tracked) |
| LiPo battery pack + USB-C data cable | Kubii order <kubii-order-ref> | Week of 2026-08-17 to 2026-08-23 (exact day not tracked) |

`hardware/BOM.md`'s `## Order Tracking` table is updated to match (see that
file's own note on elapsed lead time).

## Assembly

The XIAO ESP32-S3 Plus module seated cleanly onto the EE02 driver board,
and the 13.3" panel's flat-flex cable seated into its connector without
issue. No deviation from Seeed's documented assembly steps for the EE02
kit was needed — no crooked seating, no latch that had to be reopened, no
missing part.

## USB Connection

The USB-C cable used is the one purchased specifically for this project
and recorded in `hardware/BOM.md`'s `## Required Now` table — "USB-C data
cable (USB 3, carries data — not power-only)", Kubii SKU "Cable USB 3
Type-C vers USB-A", part of order <kubii-order-ref>. This is a data-capable cable
by the vendor's own listing (explicitly not a charge-only cable), matching
the BOM's own warning that a charge-only cable is the most common cause of
"the board does not appear at all."

## Serial Device Path

Before plugging in, `ls /dev/cu.*` was run and the existing device list
noted. After plugging the board in via the cable above, the same command
was re-run and the newly appeared entry was identified as the board:

```
/dev/cu.usbmodem1301
```

This exact path — no wildcard — is what `firmware/flash.sh` (Task 2) is
invoked against. This connection has been observed to be flaky across
sessions (dropped once already), so the path is re-verified with a fresh
`ls /dev/cu.*` immediately before every flash attempt rather than trusted
from this log alone.

## Battery

The battery pack (Kubii "Batterie 3000mAh Li-Po", JST-PH 2.0mm 2-pin) is
physically present and has **not** been connected to the board. Per this
plan's own instructions ("Do not plug it in during this task; plan 01-08
does that"), no connection is made in this plan — first bring-up runs on
USB power only, exactly as designed.

**Polarity check status:** the visual polarity check against the board's
silkscreen (JST connector, negative pin nearest the USB-C port per
`hardware/BOM.md`'s `## Battery Connector Verification` section) has
**not yet been performed**. This plan's acceptance criteria for Task 1
only requires the battery to be "recorded as present and not yet
connected" — it does not require the polarity check to happen in this
plan, and the plan's own how-to-verify text assigns the actual connection
event to plan 01-08, not this one. The polarity check is therefore
explicitly deferred and tracked here as a **blocking prerequisite for plan
01-08**: before 01-08 connects the battery for the first time, the
JST housing orientation must be visually confirmed against the board's
silkscreen marking (and per BOM.md's own fallback, checked with a
multimeter if there is any doubt), since a reversed-polarity connection
destroys the board and is not recoverable.

## Board Profile Verification

**Status: VERIFIED — 2026-08-25**

The EE02 board profile's eight panel pin values, vendored verbatim from
upstream in plan 01-05 (`firmware/sdkconfig.ee02.defaults`), are now
confirmed against real hardware for the first time — closing the concern
STATE.md tracked about the Spectra 6 dual-controller driver having no
confirmed off-the-shelf ESP-IDF library. The USB Serial/JTAG console
routing (chosen because the panel's master chip-select and power-enable
signals share GPIOs with UART0) is likewise confirmed correct: console
output was captured cleanly on every boot once the capture timing issue
was solved (see `## First-Boot Capture: Diagnosis (resolved)` above).

No pin or configuration value required correction. `sdkconfig.ee02.defaults`
remains byte-identical to upstream (`firmware/VENDOR.md`'s vendored-file
table, `Verbatim? = yes`) — no divergence to record there.

**Outcome of each of the five visual checks (developer-confirmed on the
physical 13.3" Spectra 6 glass, 2026-08-25):**

- **Colour order** — PASS. Six full-height vertical bands, left to
  right: black, white, yellow, red, blue, green, exactly matching
  `make_test_panel.py`'s `palette` pattern and the nibble packing/palette
  mapping in `firmware/main/epd13in3e.c`.
- **Seam continuity** — PASS. The vertical midline where the panel's two
  controllers (master driving the left 600px, slave driving the right
  600px) meet shows no offset, no duplication, and no blank/stale half —
  the master/slave chip-select assignment in `sdkconfig.ee02.defaults` is
  correct.
- **Full coverage** — PASS. The whole panel refreshed top to bottom, no
  partial-refresh artefacts — the busy/reset line handling in
  `epd13in3e.c`'s `busy_wait()` is correct.
- **Orientation** — PASS. Bands run vertically (portrait), matching the
  portrait-native panel and the image's authored orientation — no
  row-order or rotation problem.
- **Sleep entry** — PASS. Console output stopped cleanly after the
  `sleep enter sleep_s=300` line and the device went fully quiet — see
  `## First-Boot Capture: Diagnosis (resolved)` above for why the USB
  connection dropping at that point is the device correctly cutting
  power for deep sleep, not a fault.

This is the Walking Skeleton's first correct picture on real e-paper
glass, produced end to end by the device polling its own local stub
server — the phase's single largest hardware unknown (an EE02 board
profile its own authors never drove against real hardware) is retired
with no corrections needed.

## Panel Observations

Input to Phase 2's rendering work, measured against the actual 13.3"
Spectra 6 panel on this board:

- **Full-refresh duration:** measured twice from two independent live
  boots, both driving a real (non-hash-skip) blit of a 960,000-byte
  image. Panel GPIO configuration began at firmware uptime t=+11976ms
  (first measurement) / t=+11473ms (second), and `epd13in3e: refresh
  complete` logged at t=+43516ms / t=+43013ms respectively — **31.54s and
  31.54s**, i.e. a consistent **~31.5 second full refresh**, well inside
  `epd13in3e.c`'s 60-second `DRF` busy-wait timeout with plenty of
  margin.
- **Colour rendition vs nominal:** the six colours (black, white,
  yellow, red, blue, green) render as clean, visually distinct solid
  bands on the physical glass with the expected left-to-right order and
  no cross-band bleed at any of the five internal band boundaries or the
  two-controller seam.
- **Ghosting/artefacts:** none observed after the refresh settles — no
  visible remnant of a prior image, no banding or streaking within a
  band.
- **Practical implication for Phase 2:** a ~31.5s refresh means any
  Phase 2 rendering-cadence decision should budget for the panel being
  visibly "in progress" (redrawing) for roughly half a minute after each
  poll that changes the image — not instantaneous, and worth accounting
  for in any UX expectations around how quickly the frame reflects a
  changed flight/train state.

### Phase 7 On-Glass Verification (2026-08-28, plan 07-01)

**This is the first time the shipped Phase 3 design (PT Serif Regular
typography, flat single-color state background, per-airline dithered
illustrations, two-flight composition) has been judged against the real
13.3" Spectra 6 panel rather than a monitor preview.** Everything below was
driven from the production render CLI's new `--airline`/`--city`/`--out`
flags (07-01 Task 1) against the live production host, with `inkframe-poll.timer`
(operationally `skypane-poll.timer` on the actual VPS — see the naming-drift
note at the end of this entry) stopped for the session and restarted at the
end.

**D-13 calibration method (full account, for anyone weighing how much
these numbers are worth).** Both of D-13's authoritative colorimetric
sources were read in full during Phase 3 and publish no colorimetric data
for the Spectra 6 panel — a confirmed negative result, not an unexplored
gap. The starting `PALETTE_RGB` values were therefore a LOW-confidence
community estimate gathered by eye against a different branded product.
This Phase 7 pass is an informal visual side-by-side against the real
panel: no colorimeter, no instrumentation — the developer compared the
monitor-rendered `--calibration-preview` swatches and full-panel renders
directly against the physical glass by eye and verbal description, plus one
real photo of the six-band calibration test panel. The accuracy target is
nearest-neighbour hue placement across six fixed inks, not measurement-grade
precision.

**Yellow and Red — confirmed close enough, no change.** Both inks were
judged against the real panel and reported as reading noticeably better
than Blue/Green (see below) — no mismatch direction was reported for
either, so neither triple changed this session. Yellow stays
`(240, 224, 80)`, Red stays `(160, 32, 32)`.

**Blue and Green — CHANGED, not left unchanged (deviation from this
plan's own original acceptance criterion, developer-approved live — see
07-01-SUMMARY.md's Deviations section for the full Rule 4 write-up).**
D-21 had only ever confirmed Blue/Green against in-chat monitor mockups,
never real glass; this session was the first real-glass check of that
decision. The developer reported, with a real photo of the six-band
calibration panel as evidence, that both inks rendered "beaucoup plus
terne et sombre" (much duller/darker) than the on-screen preview. Two
darkening passes were made, each re-confirmed against the real panel:

| Ink | D-21 (locked, monitor-only) | Pass 1 | Pass 2 (final, "c'est parfait") |
|---|---|---|---|
| Blue (index 4) | (110, 180, 225) | (70, 125, 185) | **(45, 95, 155)** |
| Green (index 5) | (140, 195, 130) | (80, 140, 95) | **(50, 105, 65)** |

`server/panel_format.py`'s `PALETTE_RGB` carries the Pass 2 values today,
with this session's rationale recorded in that file's own comment block.

**Background field lightening — a second, separate real-glass finding,
not part of the original D-13 calibration scope.** Independently of the
calibration-swatch mismatch above, the developer found the flat single-index
background field (`panel_format.new_canvas(bg_idx)`, D-21) reads far darker
again at full-panel coverage than the same ink does in a thin calibration
band — simultaneous contrast makes a large solid field of dark ink read
darker than a swatch of the same ink surrounded by other colours. Since
Spectra 6 has only six fixed physical inks (no software value changes the
real ink), the only way to visually lighten a fixed ink is to dither a blend
of it toward White. `server/plane/dither.py` gained
`dithered_state_background(bg_idx, lighten_fraction=0.4)`, and
`_build_active_canvas()` now calls it instead of the flat `new_canvas()`
fill. The developer confirmed both the departing (blue) and arriving
(green) fields "parfait" after this change. A real bug was caught and fixed
within the same iteration: quantizing the lightened blend against the full
6-color palette (rather than a dedicated 2-color `{bg_idx, White}` palette)
occasionally picked the wrong ink once Blue and Green were both darkened
close together in RGB space — fixed by building a dedicated 2-entry palette
per call, documented in `dither.py`'s own comments.

**Text-backing-plate fix — a direct bug-style correction, not a design
change.** The dithered background's scattered White speckle landed
directly behind white-ink text and hurt legibility, specifically flagged by
the developer for the top-left state label and the previous-flight card's
text. `render.py` gained `_paint_text_backing()`, which paints a small flat
`bg_idx` rectangle (4px pad) behind every text bbox before drawing it, so
text keeps a clean undithered backdrop while the surrounding field stays
lighter. Threaded through `draw_top_labels()`, `draw_main_text_block()`,
`draw_previous_text_block()`, and their three call sites. Developer
confirmed "parfait" on both departing and arriving after this fix.

**PT Serif Regular legibility — fresh finding, does NOT derive from
02-05-SUMMARY.md.** 02-05's "clearly legible" finding covered Inter glyphs
on a flat single-index saturated field with no dithering anywhere on the
panel — a structurally different render (Inter → Zilla Slab → PT Serif
Regular across three fonts, and the composition itself is now a two-flight
poster 02-05 never anticipated). This session's own fresh observation: "tout
est parfait" (everything perfect) across every typographic role tested —
the state label (20px), the top tag (18px), the main text block's two lines
(44px/floor 28px and 22px/floor 16px), and specifically the previous card's
smallest text (28px/floor 18px and, smallest of all ever put on this panel,
16px/floor 12px). No font-weight swap to `PTSerif-Bold.ttf` was needed;
Regular is legible at every role, on both departing and arriving renders,
both before and after the text-backing-plate fix (re-confirmed "parfait"
post-fix).

**Bezel clipping — confirmed clear.** "Les marges sont top" (the margins
are great) — no clipping of the frame, either illustration, or any text
line by the physical bezel.

**State distinction (colour + label only, no nose-direction cue) —
confirmed clear.** Departing (blue field + "DEPARTING" label) and arriving
(green field + "ARRIVING" label) both read clearly using only background
colour and label text, with no nose-direction cue (D-24 dropped mirroring
entirely).

**Two-flight composition — confirmed "parfait."** The previous card reads
as a real second aircraft, not a decorative element or rendering artifact;
the main text block's overlap with the illustration and the previous
card's right-alignment to the main illustration's own edge both read as
intentional.

**Illustration wordmark detail — confirmed "parfait."** Fuselage livery
lettering (e.g. "AIRFRANCE") is readable at both rendered scales — roughly
992px for the main illustration and roughly 565px for the previous card.

**Forced departure/arrival (D-02) — visual path confirmed, threshold
still open.** Departing renders blue-toned with the `DEPARTING` label;
arriving renders green-toned with the `ARRIVING` label, confirmed across
repeated renders this session. This closes only the *visual* DEPARTING
path — the real +200 ft/min vertical-rate threshold remains unvalidated
against real sensor data and stays open until a genuine departure is
observed in production (A-02-02-01, carried forward — see
07-01-SUMMARY.md).

**Long-name stress test (D-04) — confirmed "c'est parfait."** Forced via
`--state arriving --callsign AFR56XX --airline "Compagnie Nationale Royale
Air Maroc Express" --city "Santiago de Compostela–Rosalía de Castro"`: no
clipping, no bezel overrun, no mid-word wrap, shrunken text still readable.
The developer did not name a specific smallest-still-readable point size
beyond confirming it works, so none is invented here.

**Desk-distance composition judgment (D-03) — provisional, not a
wall-mounted verdict.** Stepped back to roughly wall-viewing distance from
the desk where the frame currently sits: the aircraft still reads as a
passenger jet and the whole composition reads as ambient art, not a data
dump. **The frame is on a desk, not yet wall-mounted** — this judgment is
explicitly provisional per D-03 and does not block phase closure; the
wall-mounted re-check of ROADMAP criteria 1 and 4 remains open (carried
forward — see 07-01-SUMMARY.md).

**Teardown — confirmed, not just enabled.** `sudo systemctl start
skypane-poll.timer` was run, `is-active` returned `active`, and a real
poll cycle appeared afterward in the journal: a genuine detection
(hex=39cea9, callsign=TVF64HM), then a second cycle where one provider
(adsb.lol) timed out but the pipeline gracefully held the previous state —
normal multi-provider resilience (D-04's disagreement/timeout handling),
not a bug. Live detection is confirmed resumed, not just the unit enabled.

**Documentation-drift note (observation, not a blocker).** At session
start, the actual production systemd units were found to be
`skypane-poll.timer`/`skypane-byos.service`/`skypane-companion.service`
under `/opt/skypane/...` — not `inkframe-poll.timer`/`/opt/inkframe/...` as
this plan's own Task 2 example commands say throughout. The project was
renamed InkFrame → SkyPane and the VPS was mid-migration when this plan's
text was drafted. Every command actually run this session used the real
`skypane-*` names and `/opt/skypane/...` paths; the plan file's own stale
example commands were left as-is since correcting them was out of scope for
this task.

### Phase 8 On-Glass Verification (2026-08-31, plan 08-06)

**This session put every visual and textual change Phase 8 made — the new
White default, PT Serif Bold replacing the removed text-backing-plate, the
four-tier content ladder, the previous card's 20px nudge, and (well beyond
D-13's stated minimum of one) essentially the full 11-entry theme registry —
in front of the real deployed Spectra 6 panel for the first time.** Driven
interactively over SSH against the live production VPS
(`ubuntu@92.222.92.167`), with `skypane-poll.timer` stopped for each forced
render and restarted at the end, per the same method Phase 7 established.
Method note, same standard as the Phase 7 entry above: these are
uninstrumented visual judgments made by one person, on one panel, under
whatever lighting the room had — not measurement-grade, and not claimed to
be.

**Step A — the White default, both states.** Confirmed clean white with no
visible cast, judged against the empty state's own long-standing white
reference. Departing and arriving remain distinguishable at a glance by the
DEPARTING/ARRIVING label and to/from phrasing alone, even though both states
now share the same background colour — the developer confirmed this
explicitly rather than it being assumed.

**Step B — PT Serif Bold legibility with no backing plate. Not derived from
Phase 7's finding, which judged Regular weight with a plate present.** The
initial universal-Bold render read, in the developer's words, "très
agressif" on real ink — most visible on the White default, where Bold's
extra weight against the highest-contrast combination the panel can produce
felt heavier than intended. This reopened D-05/D-06 with the developer's
explicit instruction and was resolved by decoupling font weight from a
single blanket value into a new per-theme `weight` registry field
(`"regular"` or `"bold"`): every flat, undithered theme (White, Black,
Yellow, Red, Green, Blue) uses Regular; every dithered theme (Grey, Yellow
Light excepted — see below — Red Light, Green Light, Blue Light) keeps Bold,
since the dithered speckle needs the extra weight to stay crisp against it.
Yellow Light is the one deliberate exception: dithered but Regular, because
Bold read too heavy against it specifically. Re-rendered and re-confirmed on
glass after the change ("c'est mieux", then "beaucoup mieux" after an
additional 10%-only reduction to the main card's primary line — every other
text role's size was explicitly restored to its prior value in the same
correction). The previous card's smallest line (its second line, 16px→20px
this phase) was included in this pass and read clean. **Direct answer on
whether the plate is missed: no — "ah non pas du tout."**

**Step C — the Sky theme.** Superseded mid-session, not merely re-confirmed:
Sky (the Blue-departing/Green-arriving two-tone pairing) was retired
outright on the developer's explicit instruction ("Pas de sky, parles de
bleu clair, vert clair" / "thèmes séparés") once Blue and Green were each
individually validated as standalone single-colour themes with their own
pure/light pair. No id named `"sky"` remains in the registry. This is a
locked-decision reopening (theme removal is out of the plan's bounded-
correction scope) done with the developer's own recorded words as the
in-session-correction-scope's own precedent requires.

**Step E — the coloured themes, on dithered ink for the first time. All six
Spectra 6 inks shown, none skipped** — well past D-13's stated minimum of
one:
- **Black (pure, flat)** — "parfait comme ça ! on valide." A real bug was
  caught and fixed here: the flat Black render initially showed visible
  grey, not black. Root cause: `dither.dithered_state_background()`'s fixed
  40%-toward-white blend (tuned for Phase 7's Blue/Green finding) was being
  applied unconditionally to every non-white theme, including ones that
  should render flat. Fixed by making flat-vs-dithered a per-theme registry
  bool (`dithered`) rather than a blanket behaviour. Re-confirmed against
  the real committed registry code after the fix ("confirmé").
- **Grey** — the dithered Black render the bug above had actually produced
  turned out to be independently liked: "Le gris était top aussi (avec
  texte en gras)" — kept as its own explicit, separately selectable theme
  rather than discarded as a bug. Re-confirmed against the real committed
  registry code ("confirmé").
- **Yellow (pure, flat)** — "validé."
- **Yellow Light (dithered)** — initially shown with Bold text, judged "très
  agressif," re-shown with Regular: "c'est beaucoup mieux comme ça."
- **Red (pure, flat)** — "incroyable !"
- **Red Light (dithered)** — "validé."
- **Green (pure, flat)** — "top."
- **Green Light (dithered)** — "ok !"
- **Blue (pure, flat)** — "incroyable aussi."
- **Blue Light (dithered)** — re-confirmed against the real committed
  registry code after the Sky-retirement rewrite ("confirmé").

No livery-against-field failure was reported for any theme; no theme was
reported as technically legible but unwanted. Nine of the eleven colour
entries were validated via direct comparison renders (monkeypatching the
production drawing/dithering functions in a throwaway script, never editing
`render.py` itself, using the exact same palette indices and dithering path
the final registry now wires up) before the registry rewrite landed; Grey
and Blue Light were explicitly re-rendered and re-confirmed against the
final, committed 11-entry registry as a direct sanity check that the
consolidation introduced no wiring bug. The full automated suite (`server/
test_render.py`, 99/99) renders and palette-validates all 11 registered
themes programmatically as a standing regression guard, which is the
remaining assurance for the seven colour entries not individually
re-rendered against the final registry on glass.

**Step F — the content ladder, all four tiers, on the real deployed
renderer.** Tier 1 (identifier + city) and tier 2 (city only, no
identifier) both confirmed. **Tier 3 confirmed as a genuinely absent first
line on both the main card and the previous card** — two separate
observations, since the two cards are positioned by independent code paths.
No raw ADS-B callsign appeared on any of the four tiers. Tier 4 prompted its
own locked-decision reopening: the original title-case state word
("Departing"/"Arriving") was found to duplicate the all-caps DEPARTING/
ARRIVING top-left label with no added information; developer instruction
(given via an explicit choice among options, not a vague ask) replaced it
with a fixed `"Unknown flight"` string, identical for both states, re-
rendered and re-confirmed on glass ("parfait").

**Step D — the previous card's alignment and caption size.** "Tout est
bon" — no outlier illustration was flagged during this session; plan
08-05's own six-airframe spot-check (narrowbody x2, turboprop, small twin,
regional jet, widebody) had already found no outlier and a 5–12px padding
spread with no re-tuning needed, so none was specifically re-tested here.

**Step G — the whole composition, at distance, wall-mounted.** The frame is
mounted on the wall (not a desk judgment) at the time of this check. With
White as the default and no backing plates anywhere, the panel still reads
as ambient art rather than a data dump — confirmed directly, no reservation
recorded per the developer's own instruction.

**Teardown — confirmed, not just enabled.** `sudo systemctl start
skypane-poll.timer` was run, `is-active` returned `active`, and a real poll
cycle appeared afterward in the journal with genuine live-detected data
(hex=39de41, callsign=TVF36VX, theme=white). Live detection is confirmed
resumed, not just the unit enabled.

**Every correction applied in session, before → after → reason:**

| Change | Before | After | Reason |
|---|---|---|---|
| Font weight | One blanket `PTSerif-Bold.ttf` for every text role, every theme | Per-theme `weight` registry field: Regular on every flat theme, Bold on every dithered theme except Yellow Light (Regular) | Uniform Bold read "très agressif" on real ink, most visibly on White |
| Main card's primary line size | Reduced 10% from the post-Bold-fix size | (unchanged from the 10%-reduced value; every *other* text role explicitly restored to its prior size) | Fine-tuning pass on the same legibility concern, developer-directed |
| Background dithering | `dithered_state_background()`'s lighten blend applied unconditionally to every non-white theme | Per-theme `dithered` registry bool — flat themes render flat, dithered themes dither | A flat "Black" theme was rendering visibly grey; the Blue/Green-tuned blend was never meant to apply universally |
| Theme registry shape | 5 entries (white, black, yellow, red, sky) | 11 entries (white, black, grey, yellow, yellow_light, red, red_light, green, green_light, blue, blue_light) | Developer wanted every palette colour as both a pure flat variant and a dithered light variant, each individually validated |
| Sky theme | `"sky"` — Blue departing / Green arriving two-tone pairing | Retired entirely; Blue and Green now exist as fully separate single-colour themes (each with a pure and light variant) | Explicit developer instruction: "Pas de sky, parles de bleu clair, vert clair" / "thèmes séparés" |
| Tier-4 fallback text | Title-case state word, `"Departing"` or `"Arriving"` | Fixed string `"Unknown flight"`, identical for both states | Duplicated the all-caps top-left label with no added information; developer instruction given via explicit choice |

**Backing plate — direct answer, not missed.** "Ah non pas du tout." No
reinstatement of any plate, outline or shadow was requested or applied.

**Open items carried forward, not closed by this session:**
- A-02-02-01's real +200ft/min departure threshold remains unvalidated
  against real sensor data (visual departing/arriving path only) — every
  real detection observed so far across Phase 7 and Phase 8 has still been
  an arrival.
- The digest re-pin this phase required three rounds (08-05, then again
  here) as rendering code kept changing through the on-glass session
  itself; the final pinned value in `server/test_poll_loop.py` was read
  from a real CI run (PR #22, reopened, run 33399696789), not recomputed
  locally, per that file's own standing rule.
- DEVICE-05's unattended multi-day battery discharge run is still deferred
  to end-of-project, unrelated to this phase.
- The wall-mounted re-check Phase 7 left open (D-03, ROADMAP criteria 1/4)
  is **now closed by this session's Step G** — the frame was observed
  wall-mounted, not on a desk.
- ROADMAP Phase 7 success criterion 7 (additional selectable CFG-01 theme
  variants beyond the single corrected "sky" default) is **now discharged,
  and dramatically exceeded** — the criterion envisioned "2-3 alternate
  Blue/Green theme variants"; this phase instead shipped 11 fully separate,
  individually-validated single-colour themes spanning the whole Spectra 6
  palette.

### Phase 9 On-Glass Verification (2026-09-02, plan 09-04)

**This session put every visual and textual decision spike
`003-diagonal-band-theme` made — the diagonal band's 5 colour/treatment
candidates, the split top label, the three-tier flight-identifier hierarchy
on both cards, and the band-aware ink rule — in front of the real deployed
Spectra 6 panel for the first time.** The spike's own README says
explicitly that none of it had been near real ink before this session.
Driven interactively over SSH against the live production VPS
(`ubuntu@92.222.92.167`), with `skypane-poll.timer` stopped for each forced
render and restarted at the end, per the same method Phase 7/8 established.
Method note, same standard as the Phase 7/8 entries above: these are
uninstrumented visual judgments made by one person, on one panel, under
whatever lighting the room had — not measurement-grade, and not claimed to
be.

**Step A — all 5 band colours, both states.** Blue, Blue Light (dithered),
Green Light (dithered), Red, Black all confirmed — final verdicts: Blue
"parfait", Blue Light "looks right", Green Light "c'est parfait comme ça",
Red "c'est super beau", Black "parfait". **Two real findings, both fixed
and re-confirmed in session, neither predicted by the spike's screen
preview:**
- **Black text was illegible on Blue specifically** ("le texte sous
  l'avion principal n'est pas lisible sous le bleu"), not just on Black as
  the spike's round 13 fix anticipated. Extended to Green during Step A too
  ("je pense que l'écriture devrait être blanche également"). White ink is
  now unconditional for every band theme — every one of the 5 registered
  colours needs it, not an enumerated exception list.
- **The dash rule between the flight number and the route line read as too
  short** ("tout short") at its original 24px — doubled to 48px, confirmed
  "c'est parfait" together with the ink fix.

Also tested and rejected in session, real ink verdict overriding a
plausible-sounding hypothesis: black ink was tried specifically on Blue
Light (the dithered, lighter variant) on the theory that its lighter
average luminance would keep black-on-band contrast — direct comparison
render showed white still read better ("non ba c'est mieux en blanc"), so
Blue Light keeps the same unconditional white-ink rule as every other band
colour.

**Step B — all 4 content-ladder tiers, on Blue Light.** Tier 1
(identifier + city), tier 2 (city only, no identifier), tier 3 (airline
only, first line genuinely absent) and tier 4 (nothing resolved) all
confirmed "approved". No raw ADS-B callsign appeared on any of the four
tiers.

**Step C — previous-card band clearance.** Confirmed explicitly across all
5 band colours' two-flight renders: "no [overlap]" — the previous card's
text never visibly collided with the band.

**Step D — the whole composition, at distance.** "C'est parfait" — the
panel still reads as ambient art at typical viewing distance. **The
frame's mounting state (desk vs. wall) was not asked about this session**
— unlike Phase 8's Step G, this is an open gap in this entry, not a
confirmed fact; do not assume wall-mounted from this line alone.

**A third, unplanned finding, caught by the developer stress-testing long
real-world names, not part of the original Step A–E script:** the three
band text roles (flight number, tracked route line, airline·type line)
had no shrink-to-fit at all, unlike every other active-state text role —
confirmed missing by reading the code, not assumed. A long-name render
(reusing Phase 7's own "Compagnie Nationale Royale Air Maroc Express" /
"Santiago de Compostela–Rosalía de Castro" stress fixture) overflowed
visibly. Root-caused to two distinct bugs, both fixed and re-confirmed on
glass:
1. No fit mechanism existed at all — added `_role_fit_tracked_text_size()`
   (tracking-aware, since `font.getlength()` alone under-measures a
   tracked line's real rendered width) alongside the existing
   `_role_fit_text_size()`, wired into both cards. Explicit developer
   instruction was required and given before this was applied, per this
   plan's own in-session-correction-scope (a new fit mechanism is not
   bounded by default).
2. Even after adding the fit mechanism, text still visibly vanished at its
   edges — not a canvas clip (verified: `_assert_within_canvas()` never
   fired). The real bug: text was fit against `SAFE_BOX`'s width, not the
   diagonal band's own (narrower, height-varying) width. White text
   extending past the band's edge onto the plain White field simply
   disappears (white-on-white), which reads as a hard clip. Fixed by
   fitting each line against the band's own width at its actual y
   (`_band_edges()`, factored out of `_band_center_x()`), re-confirmed
   clean on glass with the exact same fixture.

**A fourth finding, from the same stress test, resolved as a data fix
rather than a rendering fix — developer's own diagnosis, confirmed live
against the real API rather than assumed:** even at the smallest legible
route-line size, one real destination (Toulon-Hyères Airport, a genuine
Orly route) still overflowed the band, because `api.adsbdb.com`'s
`municipality` field lists every commune an airport serves
`/`-separated — confirmed live: `"Toulon/Hyeres/Le Palyvestre"`, not a
fabricated string. The developer's instruction was to shorten the name at
its source rather than keep shrinking the font: `enrich._primary_city_name()`
now reduces any `/`-separated municipality to its first segment
("Toulon") before the existing sentence-case pass, applied to both
`origin_city` and `destination_city` in `_parse_route()` — a project-wide
fix (every city shown anywhere benefits), not scoped to this one theme.
Re-confirmed on glass with the real reduced value. With the data-side fix
in place, `BAND_MAIN_ROUTE_MIN_SIZE` was left at its original, more
legible 16px rather than kept at the temporary 12px floor tried mid-session
— real destinations are short enough after the reduction that the lower
floor is no longer needed as a matter of course.

**Teardown — confirmed, not just enabled.** `sudo systemctl start
skypane-poll.timer` was run, `is-active` returned `active`, and a real
poll cycle appeared afterward in the journal (`Finished
skypane-poll.service`, held state on the last known aircraft — no fresh
ADS-B contact during the exact restart window, which is itself normal
between contacts). Live detection is confirmed resumed, not just the unit
enabled.

**Every correction applied in session, before → after → reason:**

| Change | Before | After | Reason |
|---|---|---|---|
| Band text ink colour | White only when `band_idx == IDX_BLACK` | White unconditionally for any band theme | Black text was illegible on Blue and Green too on real ink, not just Black as the spike anticipated |
| Main card dash width | 24px | 48px | Read as "tout short" on real ink |
| Band text centre-x anchor | Computed once at the block's top y | Computed once at the block's vertical midpoint | Lower lines visibly drifted from the band's true centreline as the trapezoid narrows going down |
| Band text roles' fit mechanism | None — fixed size regardless of content length | `_role_fit_text_size()`/new `_role_fit_tracked_text_size()`, same as every other active-state role | A long real name overflowed; every other text role already shrinks to fit |
| Band text fit constraint | `SAFE_BOX`'s width (~1072px) | The band's own width at each line's actual y (`_band_edges()`) | Text fit within the canvas but still overflowed the band itself; white ink past the band's edge is invisible on White, not clipped |
| `BAND_MAIN_ROUTE_MIN_SIZE` | 16px (original) → 12px (mid-session) → | 16px (reverted) | 12px was a stopgap for an extreme name; the real fix (data-side shortening) made the lower floor unnecessary |
| City name formatting | Full `municipality` field value shown as-is | `_primary_city_name()` reduces to the first `/`-separated segment before sentence-casing | Real compound municipality names ("Toulon/Hyeres/Le Palyvestre") don't fit any panel text role, and are noise beyond the primary city anyway |

**Open items carried forward, not closed by this session:**
- The frame's mounting state (desk vs. wall) was not asked about this
  session — Step D's "reads as ambient art" verdict carries no wall-mounted
  claim, unlike Phase 8's Step G.
- The CLI's manual `--callsign` test path has no way to force an
  `aircraft_type` value (no `--aircraft-type` flag exists), so the
  airline·type line's " · {type}" suffix could not be exercised on real
  glass this session — confirmed as a pre-existing test-tooling gap, not a
  regression, by reading `plane/render.py`'s CLI argument construction
  directly. Real production renders (fed by `detect.py`'s real ADS-B type
  data) are unaffected.
- The band-edge-aware fit correction was verified on `band_blue_light` at
  one canvas position (below the aircraft); it was not individually
  re-exercised on all 5 band colours with long names, only with the
  original short fixtures.
- `_primary_city_name()`'s "first segment before the first /" rule was
  checked against 2 real airports found live this session
  (Toulon-Hyères, Toulouse-Blagnac) plus Bordeaux-Mérignac by inference —
  not exhaustively checked against every French/European airport
  `api.adsbdb.com` might return a compound municipality for.

### Phase 12 On-Glass Verification (2026-09-05 → 06, plan 12-06)

**This session put Phase 12's new DISPLAY OFF render state on the real
deployed Spectra 6 panel for the first time, walked the full operator loop
(off from the companion Settings page → dark frame → back on) with the
poll timer live, and — because the developer read the shipped screen on
the panel and asked for something more elegant — redesigned all three hold
screens on glass, in session.** Driven interactively over SSH against the
live production VPS (`ubuntu@92.222.92.167`), `skypane-poll.timer` stopped
for every forced render in steps A–C and restarted for step D, per the
method Phases 7/8/9 established. Each forced render was confirmed taken by
the frame from `skypane-byos`'s journal (the `GET /img/<digest>.bin` line
for that exact render's digest), never assumed from the clock. Method
note, same standard as the entries above: uninstrumented visual judgments
by one person, on one panel, under the room's own lighting — not
measurement-grade. Timings below are journal timestamps, quoted as such.

**Step A — the three hold screens, side by side, and what they became.**
The screen as plan 12-02 shipped it (flat White, 72px Bold `DISPLAY OFF`,
the quiet-hours shape) went up first. Developer, on the panel: *"c'est
parfait ! mais ça manque peut-être d'un retour à la ligne après le 'page.'
Et un petit logo sleep aussi au dessus du texte"*. Both applied in
session — the body became two authored lines breaking after "page.", and
a glyph went above the heading. The glyph choice was put to the developer
explicitly: a moon (what "sleep" suggests) would pull DISPLAY OFF toward
QUIET HOURS, the curfew screen this step exists to keep it distinct from;
the developer's first answer was a misclick on the moon, the question was
re-asked at their request, and the power ring was chosen. On glass: *"c'est
cool ! mais je pense que ça pourrait être un peu plus élégant. tu as des
propositions ?"* Five compositions were then sketched with `render.py`'s
own primitives, each pushed through `_assert_legal_palette()` before being
shown, and the developer asked for a blend of two — the editorial
typography of one (tracked Bold label over a short rule, then the body) on
the dimmed field of the other (Black dithered toward White, the Grey
theme's on-glass-validated recipe, white ink) — keeping the power ring.
That blend went up and was judged on the three points named in advance:

1. **The dimmed field itself** — reads as a soft even grey on the ink, not
   the grain the preview shows (Phase 7's finding about dithered fields,
   reconfirmed): *validé*.
2. **Regular white body text at 40px on a dithered field** — the first
   time this project put Regular white on dither (the Grey theme only ever
   shipped Bold): *validé*, holds.
3. **The Bold-class label, rule and glyph** — crisp: *validé*. *"On
   valide."*

The developer then asked for QUIET HOURS *"travaillé avec sensiblement la
même DA"*. It was reworked onto the same composition through one shared
routine, with a filled crescent as its mark — the moon placed where the
night register belongs. On glass, judged on the crescent, the one-line
`Back at 07:00` in Regular white, and the two screens as a pair: *"c'est
parfait je valide"*. Then the empty screen: *"cet écran n'a pas reçu les
améliorations des 2 autres … et un icon aurait été cool aussi"* — reworked
onto the same composition's white variant with a runway glyph (a first
draft with solid threshold bars read as a battery at glyph size and was
replaced by threshold "piano keys" before going up). On glass the
developer asked for the body to break before "The display" (*"sauf à la
ligne"*) and then for the Phase 2 em dash to go (*"tu as laissé le tiret
moche, remplace par un point"*) — the session's only change to locked
copy — and accepted that final fix from the preview alone by explicit
choice (*"pas besoin de retester, tu valides direct"*).

**What this settled.** The distinguishability question `12-UI-SPEC.md`
flagged — three White/Black centred-text hold screens — was answered by
construction, not wording: **dark means the frame is resting on purpose
(DISPLAY OFF, QUIET HOURS), white means it is working (the empty state,
the flight boards)**, all three now one composition, the two dark ones
told apart by glyph. This revises `12-CONTEXT.md` D-03's "same shape as
quiet hours" default by choice, on glass, not through the UI-SPEC's
escalation ladder; recorded in `12-CONTEXT.md`, `12-UI-SPEC.md` and
`10-UI-SPEC.md`. Tests 120, 129 and 64 retargeted to pin the new fields
and the tracked label, not relaxed. Code: `4885206`, `84f3a62`,
`ab4a3ec`, `24e2ef3`.

**Step B — the body text.** DISPLAY OFF's body wraps to the two authored
lines, centred, comfortably inside the safe box at 40px; tone judged in
the same breath as the screen (*"c'est parfait"*), not read as an apology
or a warning. Not judged as a separate item beyond that.

**Step C — the indicators on the dimmed screen.** `--state display_off
--battery-low --source-fault` forced in one render (taken by the frame
21:18:46 UTC): battery-low icon bottom-left, source-fault badge bottom-
centre, both in white on the dimmed field, clear of the centred block.
Developer: *"c - approuver"*.

**Step D — the real operator loop, timer live. This is the step that
proves the phase.** Timer restarted 21:20:14 UTC; the poll loop held the
last real board (`departing`, `state_source=held`, theme
`band_red_field`, `panel_changed=False`) as expected with nothing on the
runway. The developer then unchecked *Enable display* and saved. Journal
timeline:

- 21:32:25 — last board cycle. **21:32:56 — `hold_state=display_off
  entered=True panel_changed=True`**: the server rendered DISPLAY OFF
  once, on the first 30s cycle after the click.
- 21:35:13 — the frame's next wake; fetched the entry render
  (`53ee1f29…`) at 21:35:15, on the glass ≈21:35:47. **Off latency ≈ 3
  min 07 s from the click** (D-02's "within about 5 minutes").
- **Silent hold, overnight:** the developer went to bed with the display
  off. Between the entry fetch (21:35:16) and the exit (05:27:51 next
  morning) the frame checked in **93 times and fetched 0 images**, at a
  steady **304 s** cadence (D-01's 300 s pin plus wake overhead — note the
  configured `SKYPANE_SLEEP_S` was already 300, so the pin did not
  *change* the cadence here, it held it); the server ran **920 hold
  cycles**, every one `entered=False panel_changed=False`. That is D-07 in
  production for 7 h 52 min: not one repaint. Battery 3918 mV at both
  ends.
- 05:27:35 — a check-in. The developer re-enabled the display ~16 s
  later. **05:27:51 — `hold_exited=True panel_changed=True`**, the board
  repainted on the first cycle after the click — onto a real flight,
  `IBE05GC`, an Iberia A20N, corroborated.
- 05:32:39 — the frame's next wake; fetched the board (`a7cd0abd…`) at
  05:32:41, on the glass ≈05:33:13. **On latency ≈ 5 min 20 s** — the
  worst possible phase alignment (the click landed just after a check-in,
  so a full interval had to elapse), still inside "within about 5 minutes"
  plus the panel's own ~31 s refresh. This is the honest upper bound and
  it is what the Settings caption promises.

**Step E — the overlap. Skipped.** The plan's optional step — with the
toggle off, open a quiet-hours window and confirm no repaint at its start
nor at its end — was not run. `quiet_hours_enabled` stayed `false` all
night, so the overnight hold, long as it was, never exercised the two
mechanisms together. Stated here so it is not mistaken for covered: this
is the D-05/D-07 overlap, and its only evidence remains 12-03's and
12-04's tests with their executed negative controls.

**Step F — teardown, an acceptance criterion.** `display_enabled: true`
(the developer's own re-enable), `skypane-poll.timer` active, real poll
cycles observed after the exit (05:27:51, 05:28:21, 05:28:50). The frame
was left on live detection, showing a real departure — exactly the state
it was in before the session, timer included.

**Not verified this session, stated plainly:**
- **D-05's sleep axis** — `max(300, quiet_hours_remaining)` — did not run
  on real hardware: `quiet_hours_enabled` was `false` overnight, so the
  two mechanisms never overlapped. It remains covered by 12-03's tests and
  their executed negative control only.
- The QUIET HOURS screen's own operator loop (window entry/exit with the
  new composition) was not walked; only its forced render was judged.
- All three glyphs were judged at one size on one panel; the runway
  glyph's final form was accepted with the empty screen's dash fix from
  the preview, at the developer's explicit choice, not re-forced.
- Production was updated for steps A–C by copying `render.py` over SSH
  (the pipeline deploys only from `main`); a clean redeploy from `main`
  after the PR merges is owed, so production stops depending on a
  hand-copied file.

## Flashing Tooling

`esptool` was installed via Homebrew (not pip), keeping Phase 1's
zero-pip-install property intact:

```
esptool v5.3.1
```

(`brew install esptool`; binary at `/opt/homebrew/bin/esptool`, with the
deprecated `esptool.py` alias also present.)

## Console Routing Bug (Rule 3 deviation)

The first flash attempt in this plan's earlier session produced **no
console output at all** after boot. Per this plan's own diagnostic
framing (see `## Board Profile Verification` above), a silent console on
this board points at console routing rather than a dead board: the
panel's master chip-select and power-enable signals share GPIOs with
UART0, so the EE02 profile must route the console to USB Serial/JTAG
instead of the default UART console.

Root cause found: `firmware/build-ee02/sdkconfig` (the generated build
config) did not actually carry `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y`
despite `firmware/sdkconfig.ee02.defaults` specifying it — a stale
generated `sdkconfig` in the build directory did not pick up the defaults
file's routing on an incremental build. Fix: a clean rebuild (removing
`firmware/build-ee02` and re-running `firmware/build.sh`) regenerated
`sdkconfig` correctly. Confirmed post-fix:

```
$ grep -E 'CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG|CONFIG_ESP_CONSOLE_UART' firmware/build-ee02/sdkconfig
# CONFIG_ESP_CONSOLE_UART_DEFAULT is not set
CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y
# CONFIG_ESP_CONSOLE_UART_CUSTOM is not set
CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG_ENABLED=y
CONFIG_ESP_CONSOLE_UART_NUM=-1
# CONFIG_ESP_CONSOLE_UART_NONE is not set
```

This is a build-process gotcha, not a wrong value in
`sdkconfig.ee02.defaults` itself (that file was already correct — see
`firmware/VENDOR.md`'s vendored-file table, `Verbatim? = yes`). No
divergence from upstream was introduced; the fix is "rebuild clean when
`sdkconfig.ee02.defaults` changes and the build directory already
exists," which is generic ESP-IDF build hygiene rather than an EE02-
specific hardware fact. Logged here under Rule 3 (auto-fixed blocking
issue) rather than as a `firmware/VENDOR.md` divergence, since no
vendored file's content changed.

## Flash Attempt (Task 2)

**Working command** (device at `/dev/cu.usbmodem1301`):

```
firmware/flash.sh /dev/cu.usbmodem1301
```

**Attempts needed:** 1 successful flash + read-back verification, on the
first attempt of this session (following the clean rebuild above).

**Result:**

```
Writing '.../build-ee02/bootloader/bootloader.bin' at 0x00000000... Hash of data verified.
Writing '.../build-ee02/partition_table/partition-table.bin' at 0x00008000... Hash of data verified.
Writing '.../build-ee02/ota_data_initial.bin' at 0x0000f000... Hash of data verified.
Writing '.../build-ee02/inkframe.bin' at 0x00020000... Hash of data verified.
Verifying application region (offset=0x20000, size=1050368) against build-ee02/inkframe.bin ...
verify_flash: OK - flashed application region matches build-ee02/inkframe.bin byte-for-byte (1050368 bytes)
flash.sh: SUCCESS
```

Chip identified during flash: ESP32-S3 (QFN56) revision v0.2, 8MB
embedded PSRAM, MAC `<device-mac>`.

**Status: flash byte-verified successful. First-boot console capture
was initially BLOCKED**, then diagnosed and resolved — see
`## First-Boot Capture: Diagnosis (resolved)` below.

## First-Boot Capture: Diagnosis (resolved)

**Symptom as reported:** the device "appears quickly in the USB list and
then disappears" repeatedly. Across several sessions this looked exactly
like a boot loop — a possible brownout during panel power-up, or a
firmware panic, given the EE02 profile's own authors never drove this
board on real hardware (see `## Board Profile Verification` below).

**Investigation method.** Plain `ls /dev/cu.*` polling was too coarse to
catch a connection window measured in single-digit seconds. Three
independent evidence sources were used together instead of guessing:

1. **macOS kernel-level USB log** (`/usr/bin/log show --predicate
   'eventMessage contains "303a" ...'` — note: `log` is a zsh builtin
   that shadows `/usr/bin/log`; the full path must be used). This
   surfaced every `IOUSBHostFamily` enumerate/terminate event for the
   board's native VID/PID (`0x303a/1001`, "USB JTAG/serial debug unit"),
   with real timestamps, independent of whether any capture script
   happened to be polling at that instant.
2. **The stub server's own request log**
   (`/private/tmp/inkframe-bringup/byos_server.log`, already running
   with stdout redirected there from an earlier session). This showed
   `/device/v1/setup` enrollment for the real device MAC
   (`<device-mac>` — matching the MAC esptool reports), followed by
   repeated authenticated `/device/v1/display` polls carrying real
   telemetry (`X-Boot-Reason`, `X-Rssi` between -42 and -64 dBm,
   `X-Fw-Version=0.1.0-p1`) — proof Wi-Fi and HTTP were working, well
   before any console bytes were ever captured.
3. **A race-capture script** (`ls /dev/cu.usbmodem*` polled every
   ~150 ms; the instant the port appeared, a background `cat` was
   attached and teed to a scratch file) — the fallback that finally
   caught real serial text once the timing/tooling issues below were
   fixed.

**Two tooling bugs found and fixed along the way (Rule 3):**
- `timeout` (GNU coreutils) is not present on stock macOS; a background
  `cat <port> &` + poll-and-`kill` loop was used instead in the
  race-capture script.
- `log` used bare is a zsh builtin (a math/logarithm command), not
  `/usr/bin/log` — commands must invoke `/usr/bin/log` explicitly.

**Finding: this was never a boot loop.** The very first real console
capture (during a hash-skip cycle, no download needed) read, in full:

```
I (6001) fp_wifi: clock set via SNTP
I (6571) inkframe: image unchanged, skipping download
I (6571) inkframe: poll ok sleep_s=300 hash_skip=1
I (6581) wifi:state: run -> init (0x0)
...
I (6631) inkframe: sleep enter sleep_s=300
```

No panic, no `Brownout detector was triggered`, no `Guru Meditation
Error` — the device printed a clean "poll ok" / "sleep enter" pair and
then the USB connection dropped, because `esp_deep_sleep_start()`
powers off the USB Serial/JTAG peripheral along with everything else
outside the RTC domain. **"Appears then disappears" is the device
correctly finishing its wake cycle and cutting power for deep sleep —
by design, not a fault.** The kernel log's `terminateDevice: ...
hardware connection lost` line is simply what a clean power-off looks
like from the host's side; it is indistinguishable at that layer from
an actual crash, which is why direct serial capture (not USB
enumeration events alone) was necessary to close this out.

The mixture of `X-Boot-Reason=power-on` and `X-Boot-Reason=rtc` visible
across the stub server's historical log lines is fully explained by the
several rounds of manual reflash/reconnect troubleshooting in earlier
sessions (each reflash forces a fresh power-on-reason boot); it does not
indicate repeated uncontrolled resets.

**Forcing and capturing a real (non-hash-skip) cycle.** Because NVS
already held the palette image's hash from an earlier successful blit,
a later poll would hash-skip and never reach the blit path this task's
acceptance criteria needs literal log text for. `/tmp/panel.bin` (the
file the stub server re-reads on every request) was temporarily swapped
to the repository's own `quadrants` test pattern via
`stub-server/make_test_panel.py --pattern quadrants` — a different,
still-valid 960,000-byte image with a different hash, existing
specifically for this purpose per that script's own docstring
("Used as the second distinct test image for the stub server's
hash-change check"). `firmware/flash.sh` was re-run (same
already-verified binary; this also forces an immediate fresh boot) and
the console was captured live. Result, captured in full to
`hardware/logs/first-light.log`:

```
I (746) inkframe: wake reason=power-on boot_count=17
...
I (986) wifi:connected with [home network], aid = 6, channel 6, BW20, ...
I (986) wifi:security: WPA2-PSK, phy: bgn, rssi: -48
...
I (43516) epd13in3e: refresh complete
I (43616) inkframe: blit ok bytes=960000 sha256_ok=1
I (43626) inkframe: refreshed to sha256:f7581d2c607ed6d5...
I (43626) inkframe: poll ok sleep_s=300 hash_skip=0
I (43626) inkframe: sleep enter sleep_s=300
```

The real blit (GPIO configure -> panel power-on -> refresh) took from
t=+11976ms to t=+43516ms, roughly **31.5 seconds** — comfortably inside
`epd13in3e.c`'s 60-second `DRF` busy-wait timeout, and a first real
measurement of this panel's full-refresh duration (see
`## Panel Observations` in Task 3's section below). No brownout, no
panic, across this or the two-earlier-download boot recorded in the
stub server's log.

`/tmp/panel.bin` was restored to the `palette` pattern immediately
after this capture (`make_test_panel.py --pattern palette`, hash
`62360cd7...`, matching the original), and the device was woken again
(another `firmware/flash.sh` reflash) so the panel redraws the correct
six-band image before the Task 3 human visual check — the quadrants
image was a diagnostic-only detour and never the intended first-light
picture.

**Conclusion:** no hardware defect, no firmware bug, no EE02 profile
correction needed for this finding. The board profile's pin values
drove a real 31.5-second refresh end to end without incident. The only
artifacts of this investigation are the two tooling fixes above and this
written record, so a future session does not have to re-discover that
"appears then disappears" is expected deep-sleep behavior.

## User LED Bring-Up (GPIO21)

**Status: NOT YET CONFIRMED ON THIS BOARD**

**The claim.** The XIAO ESP32-S3 module carries a built-in "User LED" on
**GPIO21**, active-low, distinct from the module's separate charge-status
LED. GPIO21 is unclaimed by this project's thirteen-entry pin map (SCK=7,
MOSI=9, CS_M=44, CS_S=41, DC=10, RST=38, BUSY=4, EN=43, KEY0=5, KEY1=3,
KEY2=2, BATTERY_ADC=1, BATTERY_ADC_EN=6).

**Provenance.** Web aggregation of Seeed community and board-reference
sources, per `.planning/seeds/bring-up-debug-led-remote-toggle.md` —
explicitly **not** an official schematic for this exact board combination,
unlike the panel pins, which came from a vendor header. This is the same
confidence posture the battery-sense pins (`CONFIG_FP_PIN_BATTERY_ADC`)
started from above, and it gets the same cheap resolution: flash and look.

**Procedure.** Flash, then watch the board through one full wake cycle and
into deep sleep. No tool, no soldering, no purchase.

| Observation | Expected | Result |
|---|---|---|
| LED lit within a second of reset/power-on | lit | |
| LED lit continuously through the poll and any panel refresh | lit | |
| LED dark for the whole deep-sleep interval | dark | |
| Panel still renders correctly with no new artefact | correct, no artefact | |

**What each failure outcome means, decided before the flash rather than
after:**

- **Nothing lights either way** — the GPIO21 claim is wrong. The firmware
  is harmless as-is: GPIO21 is unclaimed, so at worst an unconnected pad
  toggles once per wake. Re-source the pin later; no urgency.
- **Dark while awake, lit while asleep** — polarity is inverted, which is
  the one outcome that actually costs battery (an LED left lit through
  deep sleep would cost DEVICE-05 an order of magnitude of battery life).
  Set `CONFIG_FP_LED_ACTIVE_LOW=n` in `firmware/sdkconfig.ee02.defaults`
  and reflash. Outcome 3 above is the one that matters most and must be
  treated as a defect fixed before any DEVICE-05 discharge run.
- **A panel artefact appears** — the pin is claimed by something on the
  EE02 driver board after all. Change `CONFIG_FP_PIN_LED` to an
  unclaimed value, or drop the feature; do not leave it driving a shared
  line.

## ADC Battery-Sense Bring-Up (Phase 5, DEVICE-04)

**Status: CONFIRMED — 2026-08-28**

Plan `05-03` Task 3's whole open question was narrow: `05-RESEARCH.md` rated
the EE02's factory battery-sense circuit MEDIUM-HIGH confidence, because the
Seeed EE0x driver-board cookbook's applicability banner names EE02 by name
but its worked example says "EE04". This section closes that out on the
record, with the real device's own numbers.

**Step 1 — flash and read the number.** `firmware/build.sh` was rebuilt
fresh (a Docker daemon was started for this session), flashed via
`firmware/flash.sh`, and byte-verified via the same post-write read-back
`hardware/logs/first-light.log` already documents the shape of. Console
output captured via `firmware/monitor.sh` read:

```
fp_batt: battery mv=4156 pin_mv=2078
```

`2078 * 2 = 4156` — the sense pin reads *exactly* half the reported pack
voltage, which is precisely what a working 2:1 factory divider produces.
**This confirms the EE02 shares the same factory battery-sense circuit the
EE0x cookbook documents for the EE04 worked example** — Assumption A1 in
`05-RESEARCH.md` is closed as TRUE, at HIGH confidence, on this exact board.
No polarity inversion, no wrong settle delay, and no divider-ratio mismatch
were observed — `battery_math.c`'s `FP_BATTERY_DIVIDER_NUM`/`_DEN` constants
needed no correction, and `battery.c`'s enable-line polarity and
`FP_BATTERY_SETTLE_MS` needed no correction either.

The same console capture also carried the normal wake cycle, unaffected by
the two newly driven GPIOs: `poll ok sleep_s=30 hash_skip=1` and
`sleep enter sleep_s=30` both appeared exactly as they do without this
change, and the panel showed no garbling and no stuck refresh. This is the
practical proof `T-05-03-02`'s pin-collision guard was checking for on
paper — on real glass, the battery-sense GPIOs (`CONFIG_FP_PIN_BATTERY_ADC`
= GPIO1, `CONFIG_FP_PIN_BATTERY_ADC_EN` = GPIO6) collide with nothing the
panel or the keys already own.

Beyond the single captured line, the reading proved stable and repeatable,
not a one-off: over the following ~40 minutes, real polls from the live
device landed in the production server's `battery_state.json` and
`journalctl` with plausible, consistent values in the 4150-4200mV range
(e.g. 4192mV, 4196mV) — a live device, on its own schedule, reporting a
real pack voltage that never drifted outside a physically sane band.

**Step 2 — optional multimeter cross-check.** Skipped by the developer's
own choice. Per this plan's own framing, Step 1 alone already answers the
question this plan needs answered (the sense circuit exists and reads
correctly), so skipping the optional cross-check is not a gap — it is
recorded here as skipped, not as a failure.

**Step 3 — the icon on real glass.** Confirmed twice, at two different
icon sizes, via direct authorized server-side injection into the live
production server's `battery_state.json` (`battery_mv=3400`, below the
3500mV D-01 threshold) rather than draining the real pack or crafting a
synthetic device HTTP request — this exercises the exact same server-side
hysteresis and render code path plan `05-02` built, end to end, with a real
device fetching the result on its own next poll.

1. **First pass, original (pre-shrink) icon geometry.** Server logs showed
   `battery_low=True panel_changed=True`, and the real device's own next
   poll (visible in `skypane-byos` journalctl as a `GET /img/...` matching
   the low-battery render hash) downloaded the new image. The developer
   directly confirmed seeing the battery glyph appear in the bottom-left
   corner on the physical panel ("oui !"). It disappeared again on the
   following refresh, roughly 60-90 seconds later, once the device's own
   real (healthy, ~4190mV) telemetry overwrote the forced value and cleared
   the hysteresis (`battery_low=False`, confirmed both in server logs and
   by the developer watching the icon vanish).
2. **Feedback and correction.** The developer's read on pass 1 was that the
   icon was too large. A separate quick task (`260828-0qo`, already
   committed and already deployed to the same production server before this
   checkpoint's Step 3 was considered complete) reduced every icon geometry
   constant by 30% (`round(original * 0.7)`): the bounding box moved from
   `(64,1504,136,1536)` to `(64,1514,115,1536)`.
3. **Second pass, post-shrink icon geometry.** Same forced-injection method,
   same server. The developer directly confirmed seeing the smaller glyph
   on the physical panel and approved the new size ("c'est parfait").

Both passes confirmed the same four things: the glyph sits in the
bottom-left corner; it renders in the correct ink color for the active
state (White/Ivory on the Blue/departing or Green/arriving field); it reads
recognizably as a battery (outline body, small solid tab on the right,
mostly-empty interior with a small solid fill block); and no other poster
element — the state label, the `ORY · RWY 3` tag, either illustration,
either text block, or the previous-flight card — moved or changed across
either pass. The appear-then-disappear transition was directly observed
both in server logs and by the developer's own eyes on the physical glass,
in both passes.

**No production code change resulted from Step 1** — the polarity, settle
delay, and divider ratio in `battery.c`/`battery_math.c` all worked
correctly on the very first flash, so `battery.c`, `battery_math.c`, and
`test_battery_math.c` are unchanged from what Task 2 already committed. The
only production code change to land from this bring-up session is the
already-separately-committed icon-size quick task (`260828-0qo`), which is
outside this task's own file scope.

**No soldering, no external component, and no hardware modification** was
involved anywhere in this bring-up — every step above was firmware
flashing, console reading, and a forced server-side value, exactly as
`05-RESEARCH.md`'s corrected hardware paragraph and this plan's own "What
this plan explicitly does NOT do" section required. `hardware/BOM.md` gains
no new line item.

---
*Log opened: 2026-08-25, Task 1 of plan 01-06. Task 2 flash+verify
recorded 2026-08-25 21:38 UTC; first-boot capture diagnosed and resolved
2026-08-25 22:1x UTC (see `## First-Boot Capture: Diagnosis (resolved)`
above) — root cause was the device's own correct deep-sleep USB
power-off, not a fault. User LED Bring-Up section (GPIO21) opened
2026-08-27, plan `260827-wo4` Task 4, pre-registered before the board is
flashed for this feature. ADC Battery-Sense Bring-Up section (Phase 5,
DEVICE-04) recorded 2026-08-28, plan `05-03` Task 3 — sense circuit
confirmed on the first flash attempt, no code correction needed; icon
confirmed on real glass across two passes (original and 30%-shrunk
geometry).*

## OTA hardware session

The one hardware session for remote firmware updates (OTA) on the real
EE02 frame. It proves what no host test can: the bootloader's rollback
state, the signature check on a real image, the interaction with deep
sleep, and the real GitHub tag, signing and deploy path. Every expectation
below was written before the session, against the code as merged at
`c9acfb51`. The developer runs the session; the "Result" and "Observed"
columns are filled in afterwards and the expectations are never edited to
match what happened. A row that does not match its expectation is a FAIL,
recorded honestly.

Row IDs `H42-00a` .. `H42-12` are this session's own labels. `H42-01` ..
`H42-12` follow the phase's plan in order; `H42-00a` and `H42-00b` are two
extra bench checks that must run before the first release tag exists.

**Outcome (session run 2026-09-29):** every row passed except `H42-00b`,
which is not measurable without a code change. Four real defects surfaced
and are listed under "Deviations and not observed". The "Pass when"
criteria and the expected results were not edited to fit what happened.
The procedure text (setup, commands, signing steps) was corrected
afterwards wherever the session showed it to be wrong, so the sheet is
right for the next run.

**Every `espefuse.py burn_*` command is forbidden in this session, and nothing here runs one: the only eFuse command is the read-only `espefuse.py summary`, run before and after (H42-02, H42-12) and compared.**

### Preflight (checked 2026-09-29, before the session)

- All fifteen earlier plan summaries of the phase exist.
- The phase code is on `main` at `c9acfb51` (the phase PR plus the deploy
  fix that passes `--state-dir` where `firmware_cli` accepts it). The
  production deploy of that commit succeeded: firmware import ran, the
  release swap happened, the probes passed.
- The companion's `/update` route exists: an unauthenticated request is
  answered with a 303 redirect to `/login`.
- The 13 hardware-free firmware suites (`sh firmware/tests/run_host_tests.sh`)
  pass on this checkout. The full pytest suite and the firmware host tests
  were green in CI on the merged code; they were not re-run for this sheet.
- The signing key exists only as the `FW_SIGNING_KEY` secret of the
  `firmware-signing` GitHub environment (required reviewer, `fw-v*` tags
  only) and as a gpg-encrypted offline backup. The public half is
  `firmware/signing/skypane-signing-pubkey.pem`. The `PRODUCTION_HOST`
  secret is set (checked only for being present: during the session its
  value turned out to name the wrong host and was corrected, see
  Deviations).
- No `fw-v*` tag exists on `origin` yet.

### Ground rules

- **Placeholders only.** Commands use `$PORT`, `$SSID`, `$HOST` and
  `$VPS`. No secret, password or token is ever typed into a command line,
  a capture or this file. The Wi-Fi password is entered at
  `provision.sh`'s no-echo prompt.
- **The developer runs every VPS step** (`ssh`, `sudo -u skypane ...`,
  `journalctl`). `sudo systemctl` over SSH is blocked for Claude sessions;
  this session needs no service restart, and Claude runs none of it.
- **The private key never enters the repository.** Every step that needs
  it (H42-09a, H42-10) uses the "Signing with the offline key" recipe
  below: gpg decrypt into a private temporary directory outside the repo,
  sign in a container with `--network none`, `rm -P`, all in one command.
  H42-09b uses a throwaway key that is generated and destroyed inside the
  row.
- **Builds run in a clean detached checkout, never in the working
  tree that holds the captures.** `firmware/build.sh` refuses
  `SKYPANE_RELEASE_TAG` unless HEAD carries exactly that tag on a tree
  with nothing uncommitted, and untracked capture files count as
  uncommitted. Every tagged build below runs from `$BW`; captures are
  written into `hardware/logs/phase42/` of the working checkout.
- **Literal commands.** Commands launched from an app's "Run" buttons open
  a new terminal tab, and shell variables do not carry over to it. Paste
  each command with its values written out (port, host, paths), or
  re-export the variables in that tab first.
- **The board has only a RESET button**, no BOOT button. `esptool` enters
  the ROM loader over USB-Serial/JTAG by itself, so no button sequence is
  needed to flash. `esptool --after no-reset read-mac` (or any
  `--after no-reset` command) leaves the chip parked in the loader: press
  RESET, or finish with `--after hard-reset`, before expecting the
  firmware to run.
- **Which host is which.** The device host (byos) is
  `vps-1440bce3.vps.ovh.net`; that is what `$HOST` and the `PRODUCTION_HOST`
  secret must hold. `cortege.algernon.ovh` is an unrelated app on the same
  VPS and must not be used as the api-base. The companion is
  `https://skypane.algernon.ovh`, and the SSH target is
  `ubuntu@skypane.algernon.ovh`.
- **Serial captures.** `firmware/monitor.sh "$PORT" <file>` tees the
  console. The USB console loses the first ~0.5 s of every boot while the
  host re-enumerates the port, and the port disappears during deep sleep
  and returns at each wake, which ends `monitor.sh`. Start it again
  before the next wake, into a new numbered file (`-01`, `-02`, ...). If a
  line that a row needs fell into the lost window, record "not observed"
  for that line rather than inferring it. Re-check `ls /dev/cu.*` for the
  port before every flash (the connection has dropped before).
- **Battery.** Every OTA needs the frame's own battery reading above 3500
  mV (below that the device refuses, and the server withholds the offer
  while the battery-low alert is active). Charge the LiPo first.
- **Wake interval.** The companion's wake interval sets how long each row
  takes. Note the current value, shorten it for the session, restore it
  afterwards. Rows that end in a refused or crashing image go through the
  normal failure path, so expect backoff sleeps (300, 600, 1200 s) between
  the three attempts; check `sleep enter sleep_s=` in the capture. A full
  power cycle (USB and battery) clears the backoff counter, which lives in
  RTC memory; using it is acceptable if recorded as a deviation.
- **Redaction.** Nothing is committed until the record-and-close step
  scans `hardware/logs/phase42/`. Do not save `provision.sh`'s `Registry
  line`, its printed `ssh` command or any bearer token or Wi-Fi password;
  SHA-256 digests of images are expected and allowed.

### Session setup

Run every command from the repository root.

```
PORT=<serial-port>          # ls /dev/cu.* before and after plugging in
SSID=<wifi-ssid>
HOST=vps-1440bce3.vps.ovh.net   # the byos/device host, no scheme (not cortege.algernon.ovh)
VPS=ubuntu@skypane.algernon.ovh
WORK=~/skypane-ota-session  # scratch outside the repo: release assets, bench images, bench key
BW="$WORK/build-tree"       # clean detached checkout for every tagged build
# `ubuntu` cannot `cd /opt/skypane/current`, so the change of directory runs
# inside the service user's shell, not in the ssh login shell.
FWCLI="sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec /opt/skypane/venv/bin/python3 -m server.firmware_cli --state-dir /opt/skypane/state \"\$@\"' firmware_cli"
mkdir -p "$WORK" hardware/logs/phase42

# Publish one locally built bench image on the VPS (H42-00a, H42-08..H42-10).
bench_import() {            # bench_import <local .bin> <version>
    scp "$1" "$VPS:/tmp/bench.bin" &&
    ssh "$VPS" "$FWCLI import-bench --file /tmp/bench.bin --version $2 --commit $(git -C "$BW" rev-parse HEAD)"
    ssh "$VPS" "rm -f /tmp/bench.bin"
}
```

`$FWCLI list` is used as `ssh "$VPS" "$FWCLI list"`. Both `FWCLI` and
`bench_import` are shell definitions: in a new terminal tab (see "Literal
commands") paste the definitions again, or write the commands out.

`import-bench` refuses a bare release tag as a version: a bench version
must carry a suffix, and it must be exactly the `Firmware version:` line
that `build.sh` printed, because the device checks the image's own
descriptor version against the offered one.

### Signing with the offline key (H42-09a, H42-10)

Set `IN` and `OUT` to the paths, relative to `$BW/firmware`, of the
unsigned image and the signed output (`build-ee02/skypane.bin` and
`build-ee02/skypane-signed.bin` for a production build;
`build-ee02-dev/...` for the dev-profile crash image). The passphrase is
typed at gpg's own prompt, never on a command line.

```
IN=build-ee02/skypane.bin
OUT=build-ee02/skypane-signed.bin
KEYDIR=$(mktemp -d)        # mode 0700 under $TMPDIR, never inside the repo
(
    umask 077
    trap 'rm -P "$KEYDIR/key.pem" 2>/dev/null; rmdir "$KEYDIR"' EXIT
    gpg --output "$KEYDIR/key.pem" \
        --decrypt ~/skypane-signing/skypane-signing-key.pem.gpg &&
    docker run --rm --network none \
        -v "$KEYDIR/key.pem:/key.pem:ro" \
        -v "$BW/firmware:/project" \
        -u "$(id -u):$(id -g)" \
        espressif/idf@sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d \
        espsecure.py sign_data --version 2 --keyfile /key.pem \
            --output "/project/$OUT" "/project/$IN"
)
[ ! -e "$KEYDIR" ] && echo "decrypted key removed"
espsecure.py verify_signature --version 2 \
    --keyfile firmware/signing/skypane-signing-pubkey.pem "$BW/firmware/$OUT"
```

The container image is the same digest the release workflow signs with.
The container sees the key read-only and has no network. The last two
lines must print `decrypted key removed` and a successful verification.
Only the signed image lands under `$BW`; the key exists only inside
`$KEYDIR` and is overwritten and deleted when the subshell exits, even if
a step failed.

### Signing bench images with a throwaway bench key (H42-00a)

An unsigned image does not boot at all: the running app checks its own
signature block at startup (`CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT`)
and aborts with `secure_boot_v2: No signatures were found for the running
app`, rebooting in a loop. `firmware/flash.sh` therefore refuses an
unsigned image in every profile (see `firmware/SIGNING.md`). The two
H42-00a bench images (the running one and the offered one) are signed with a
throwaway bench key, never the real key, and the running one is flashed
with `SKYPANE_BENCH_PUBKEY` pointing at that key. A frame running a
bench-key image accepts OTA images signed with the same bench key only.

Generate the bench key inside the pinned container, under `$WORK` (outside
the repository), and delete it with `rm -P` after H42-00a:

```
docker run --rm --network none -v "$WORK:/work" -u "$(id -u):$(id -g)" \
    espressif/idf@sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d \
    espsecure.py generate_signing_key --version 2 --scheme rsa3072 /work/bench-key.pem
```

Sign a built `skypane.bin` with it, replacing `skypane.bin` (that is the
file `flash.sh` reads), and check the result:

```
docker run --rm --network none \
    -v "$WORK/bench-key.pem:/key.pem:ro" -v "$BW/firmware:/project" -u "$(id -u):$(id -g)" \
    espressif/idf@sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d \
    espsecure.py sign_data --version 2 --keyfile /key.pem \
        --output /project/build-ee02-dev/skypane-signed.bin /project/build-ee02-dev/skypane.bin
mv "$BW/firmware/build-ee02-dev/skypane-signed.bin" "$BW/firmware/build-ee02-dev/skypane.bin"
espsecure.py verify_signature --version 2 --keyfile "$WORK/bench-key.pem" "$BW/firmware/build-ee02-dev/skypane.bin"
```

### Run order

1. **H42-02 first**: the read-only eFuse baseline, before anything is
   flashed.
2. **H42-00a and H42-00b** next: bench checks on a dev build over USB.
   They come first because they can stop the whole session. The Wi-Fi
   stop-then-connect fix has never run on hardware, and an abort on the
   OTA path would otherwise show up only after `fw-v1.0.0` has been
   tagged, signed and flashed into `factory`, and every release is kept
   forever. `H42-00b` shares `H42-00a`'s captures.
3. **H42-01** (tag and release), then **H42-03** through **H42-12** in
   order.

### Results

| ID | Requirement | Pass when | Result | Observed | Evidence |
|---|---|---|---|---|---|
| H42-00a | OTA-02, OTA-07 | Wi-Fi stopped for the UPDATING screen, restarted, HTTPS request succeeds, all in one wake, with no `assert` or abort | PASS (deviation: bench images signed, see Deviations) | Cycle 01: `ota updating screen drawn`, then Wi-Fi driver re-init and a fresh `sta ip:`, then `ota step=begin/desc/download/hash/finish result=ok`, "Signature verified successfully", `ota switched version=fw-v9.9.9-bench restarting`; no assert or abort. Server: offered 13:24:27, trial 13:26:04, installed 13:27:40; glass back to the normal view, installed push received | `hardware/logs/phase42/H42-00a-bench-cycle-01.log` (`-02`, `-03`), `H42-00a-first-boot.log`, `H42-00a-first-boot-signed.log`, `H42-00a-first-poll.log`, `H42-00a-first-poll-2.log`, `server-evidence.txt` |
| H42-00b | OTA-02 | Main-task stack high-water mark recorded during an OTA download | N/A: not measurable without a code change (the firmware logs no stack high-water mark) | Indirect only: no stack-overflow fault in any capture, including the signature-verifying downloads | `hardware/logs/phase42/H42-00a-bench-cycle-01.log`, `H42-09b-wrongkey-02.log`, `H42-10-crash-01.log` |
| H42-01 | OTA-10 | `fw-v1.0.0` released through the gated pipeline, present in the store and in the companion with generated notes | PASS | Tag `fw-v1.0.0` on `c9acfb51`; release run 36575555701 (guard job, then gated signing job) success; 5 assets; image sha256 `e9f25b7f20bba3ff...` = `release.json`, 1118208 bytes; `espsecure.py verify_signature` with the committed public key: "Signature block 0 verification successful"; deploy run 36575975888 printed "added fw-v1.0.0" on a same-sha redeploy; `firmware_cli list` shows `fw-v1.0.0`; developer saw it in the companion with generated notes | `hardware/logs/phase42/H42-01-release.txt` |
| H42-02 | OTA-04 | Baseline eFuse summary saved | PASS | 192 lines, ESP32-S3, no security eFuse burned | `hardware/logs/phase42/efuse-before.txt` |
| H42-03 | OTA-12 | Frame provisioned, secret registered on the VPS | PASS (deviation: done during H42-00a) | Final provisioning used api-base `https://vps-1440bce3.vps.ovh.net`; each re-provision re-registered the device with `devices_cli.py ... --replace`; the H42-04 USB flash does not touch the `secret` partition | `hardware/logs/phase42/H42-00a-first-boot-signed.log`, `H42-00a-first-poll-2.log`, `H42-04-next-wake.log` |
| H42-04 | OTA-04, OTA-12 | Signed `fw-v1.0.0` flashed once into `factory` and `ota_0`; first boot polls as `fw-v1.0.0`, `ota boot outcome=none` | PASS (`ota boot outcome=none` not observed) | `write-flash` of bootloader, partition table, otadata, and the app at 0x20000 and 0x270000; both read-backs "matches"; server: first poll as `fw-v1.0.0` at 13:53:24; the capture ends at the bootloader (the first ~0.5 s and the boot outcome line fell into the USB re-enumeration window); the next wake polls OK. Free heap not logged | `hardware/logs/phase42/H42-04-first-boot.log`, `H42-04-next-wake.log`, `server-evidence.txt` |
| H42-05 | OTA-11 | "Firmware CA chain guard" dispatch run is green | PASS | Run 36578611110 success (after the `PRODUCTION_HOST` fix); served chain leaf, Let's Encrypt YE2, ISRG Root YE, ISRG Root X2, ISRG Root X1 | `hardware/logs/phase42/H42-05-chain-guard.txt` |
| H42-06 | OTA-02, OTA-03, OTA-07, OTA-09 | `fw-v1.0.1` installs; UPDATING screen on glass; `ota confirmed` before `sleep enter` in the same wake | PASS on server and developer observation; serial capture not taken (deviation) | Tag `fw-v1.0.1` on `4be7351c`; release run 36581150646, deploy run 36581557153; battery 3984 mV before; server: offered 14:29:48, trial 14:31:26, installed 14:33:02; developer saw UPDATING on the glass, the glass returned to the planes, "installed" push received. The confirm-before-deep-sleep ordering was not observed on serial; indirect proof: H42-07 (a trial image not confirmed before its deep sleep is rolled back by the bootloader at the next wake) | `hardware/logs/phase42/server-evidence.txt` |
| H42-07 | OTA-03 | The next wake still runs `fw-v1.0.1`, reset reason `deepsleep`, `ota boot outcome=none` | PASS (server evidence; serial lines not captured) | After 14:33:02 the frame kept reporting `fw-v1.0.1` over many deep-sleep wakes (for example 15:28:52 and 15:40:03), no rollback event. `reset reason=deepsleep` and `ota boot outcome=none` were not captured on serial | `hardware/logs/phase42/server-evidence.txt`, `H42-06-ota-01.log` (an ordinary poll wake after the install; the log does not print the running version) |
| H42-08 | OTA-04, OTA-06 | Unsigned image refused at `step=finish`, never booted, release reaches Failed after three attempts | PASS | Bench `fw-v1.0.1-unsigned` (built from tag `fw-v1.0.1`, label `unsigned`). Server: fail-image at 15:51:22, 16:02:13, 16:22:56; schedule failed after 3 attempts at 16:23:42. Capture: `ota step=hash result=ok`, then `ota step=finish result=fail err=ESP_ERR_OTA_VALIDATE_FAILED`, `poll fail step=ota ... sleep_s=300`; device stayed on `fw-v1.0.1`. Failure push: sent, not seen by the developer (see Deviations) | `hardware/logs/phase42/H42-08-unsigned-01.log` .. `-06.log` (`H42-06-ota-02.log` .. `-04.log` are the same wakes saved under the earlier name) |
| H42-09a | OTA-04 | Tampered signed image refused at `step=finish`, Failed after three attempts | PASS | Signed with the real offline key (gpg decrypt, container with `--network none`, `rm -P`; no key left behind, verified); byte at offset 65536 flipped and `verify_signature` then failed ("Signature block image digest does not match"). Device: `ota step=hash result=ok`, then esp_image "Checksum failed", `ota step=finish result=fail`; schedule failed after 3 attempts at about 17:09 (fail-image 17:06:24, 17:08:27 plus the first). The flipped byte is caught by the image checksum before the signature check; the signature-only refusal is H42-09b. RESET used to skip backoff | `hardware/logs/phase42/H42-09a-tampered-01.log` .. `-05.log`, `server-evidence.txt` |
| H42-09b | OTA-04 | Intact image signed with the wrong key refused at `step=finish`, Failed after three attempts | PASS | Throwaway key generated and deleted inside the command; the real public key refuses the image. Device: "Secure boot signature verification failed", "image valid, signature bad", `ota step=finish result=fail`. Server: fail-image at 17:15:08, 17:16:20, 17:19:07, then failed after 3 attempts | `hardware/logs/phase42/H42-09b-wrongkey-01.log` .. `-05.log` (decisive: `-02`), `server-evidence.txt` |
| H42-10 | OTA-03, OTA-07 | Crash on the trial image rolls back to `fw-v1.0.1`; rollback banner in the companion; UPDATING screen also with quiet hours or display off | PASS; the panic line and the `ota boot outcome=rollback` boot not captured; the display-off UPDATING check moved to H42-11 | Bench `fw-v1.0.1-crash` (dev profile, `SKYPANE_FAULT=panic`, signed with the real key). Each attempt downloaded, verified the signature and logged `ota switched version=fw-v1.0.1-crash restarting`. Server: rollback at 17:22:54, 17:29:31, 17:32:32, then failed after 3 attempts; developer saw the companion's rollback banner; the device stayed on `fw-v1.0.1` | `hardware/logs/phase42/H42-10-crash-01.log` .. `-06.log` (`-05`, `-06` are the chip parked in the ROM loader), `server-evidence.txt` |
| H42-11 | OTA-12 | Erased `otadata` boots `factory` (`fw-v1.0.0`); installing `fw-v1.0.1` from there works | PASS (UPDATING screen with the display off not confirmed on glass) | `esptool erase-region 0xf000 0x2000` plus hard reset: the server shows the frame on factory `fw-v1.0.0` at 17:35:18. With the display OFF, Install `fw-v1.0.1` from the companion: offered 17:42:13, trial 17:43:50, installed 17:44:52 (installing from factory works, and an OTA runs with the display off). The developer did not visually confirm the UPDATING screen during this display-off install | `hardware/logs/phase42/server-evidence.txt` (no serial capture) |
| H42-12 | OTA-04 | `efuse-after.txt` identical to `efuse-before.txt` | PASS | 192 lines each; all 112 fuse lines identical, and the two files are byte-identical after redaction | `hardware/logs/phase42/efuse-after.txt` |

### Measured facts

| Fact | Value |
|---|---|
| Commit under test | `fw-v1.0.0` on `c9acfb51`; `fw-v1.0.1` on `4be7351c` (which adds the flash.sh unsigned-image refusal, #159) |
| Device MAC | 94:a9:90:cf:80:08 |
| Date of the session | 2026-09-29 (UTC times in the rows) |
| OTA wake duration (uptime at `ota switched`) | about 62 s from wake to `ota switched` (H42-00a cycle 01: 62062 ms; H42-09b: 62973 ms to `step=finish`). The trial boot's `wake timing total_ms` was not captured |
| Battery mV | 4188 mV on USB at first boot; 3984 mV before H42-06; the value after the OTA was not recorded |
| Free heap during or after an OTA wake | not logged by the firmware (no heap figure is printed anywhere) |
| Main-task stack high-water mark | not measurable without a code change; no stack-overflow fault in any capture |
| eFuse before/after `diff` | empty: `efuse-before.txt` and `efuse-after.txt` are identical (192 lines, 112 fuse lines); no `burn_*` command was run |
| Wake interval before the session, and restored to | the value before the session was not recorded; the developer restored the wake interval and the display setting afterwards |

### Deviations and not observed

Real defects the session found:

1. **An unsigned image does not boot at all** (H42-00a). With
   `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT` the running app checks
   its own signature at startup: `E secure_boot_v2: No signatures were found
   for the running app`, `abort()`, and a reboot loop (74 reboots in
   `H42-00a-first-boot.log`). The sheet had assumed an unsigned dev image was
   exempt. Fixed in `firmware/flash.sh` and `firmware/SIGNING.md` by PR #159
   (`4be7351c`), which refuses an unsigned image in every profile. H42-00a
   was redone with both bench images signed by a throwaway bench key
   (generated in the container under `~/skypane-ota-session`, outside the
   repository, and deleted with `rm -P` after the row) and flashed with
   `SKYPANE_BENCH_PUBKEY`. The procedure text is corrected.
2. **Wrong device host and secret.** The api-base was first set to the wrong
   host (HTTP 404 "Cannot GET", `H42-00a-first-poll.log`) and the
   `PRODUCTION_HOST` GitHub secret held that wrong host too. The device host
   is `vps-1440bce3.vps.ovh.net`; `cortege.algernon.ovh` is an unrelated app
   on the same VPS. The secret was corrected during the session (before
   H42-05) and the sheet now names the hosts.
3. **`firmware_cli` invocation in the sheet failed.** `ubuntu` cannot `cd
   /opt/skypane/current`, so `FWCLI` and `bench_import` as written did not
   work. The working form runs the `cd` in the service user's shell
   (`sudo -u skypane /bin/sh -c 'cd ... && exec ...' firmware_cli <sub>`);
   the sheet is corrected.
4. **The UPDATING screen stays on the glass after a failed OTA attempt**
   until the next successful poll redraws. Not fixed; follow-up.

Other deviations:

- **First provisioning stored a truncated Wi-Fi password** (the join failed,
  `H42-00a-first-boot-signed.log`) and the api-base was wrong
  (`H42-00a-first-poll.log`); the frame was re-provisioned twice, each time
  re-registered with `devices_cli.py --replace`. Final api-base
  `https://vps-1440bce3.vps.ovh.net`.
- **H42-03 was done during H42-00a** (order deviation; the H42-04 USB flash
  does not touch the `secret` partition); the
  `H42-03-provision.txt` extract the procedure asks for was not saved, and
  the provisioning output was deliberately kept out of the repository.
- **H42-00b is not measurable** without a code change (the firmware logs no
  stack high-water mark); no stack-overflow fault appeared in any capture.
- **Backoff skipped with RESET.** After a crash rollback, the rolled-back
  `fw-v1.0.1` sees `reset reason=panic` and backs off (sleeps) without
  polling, so the rollback is reported only at the next wake (300, 600 or
  1200 s later). The developer pressed RESET to skip the waits, and did the
  same for the refusal rows' backoff. Accepted; the sheet allows shortening
  the backoff.
- **Commands from the app's "Run" buttons open new terminal tabs**, which
  lose shell variables; the sheet now says to use literal commands. The
  board has only a RESET button, and `esptool --after no-reset read-mac`
  parks the chip in the ROM loader (`H42-10-crash-05.log` is that state).
- **Capture naming.** The monitor left running through the install and the
  unsigned-image rows saved some wakes under `H42-06-ota-*`; `-02` to `-04`
  are the same wakes as `H42-08-unsigned-01` to `-03`, and `-01`, `-05`, `-06`
  are ordinary polls.

Not observed:

- H42-04: `ota boot outcome=none` on the first boot (lost in the USB
  re-enumeration window; the capture ends at the bootloader). The next wake
  polls OK.
- H42-06: no serial capture (USB was unplugged), so the
  confirm-before-deep-sleep ordering (`ota confirmed` before `sleep enter`)
  was not seen on serial; H42-07 is the indirect proof. The battery mV after
  the OTA wake was not recorded.
- H42-07: `reset reason=deepsleep` and `ota boot outcome=none` were not
  captured on serial; the server shows the frame on `fw-v1.0.1` over many
  wakes with no rollback event.
- H42-08: the failure push ("Update failed, back on fw-v1.0.1") was not
  checked by the developer on the phone. The poll journal shows no
  notification error and no "firmware reconcile failed" (`notify.py` logs
  only on failure), so it is recorded as sent, not seen by the developer.
- H42-10: the `SKYPANE-FAULT-INJECT panic` line and the `ota boot
  outcome=rollback` boot are not in the captures (they happen within about
  2 s of the restart, during USB re-enumeration). The rollback is proven by
  the server's rollback events and the companion banner. The
  quiet-hours/display-off UPDATING check was moved to H42-11.
- H42-11: the UPDATING screen during the display-off install was not
  confirmed on the glass by the developer.
- Free heap and main-task stack high-water mark: not logged by the firmware.

Cleanup: the throwaway keys are deleted and no `fw-v*` tag exists other than
`fw-v1.0.0` and `fw-v1.0.1`; the wake interval and the display setting were
restored by the developer. The bench releases (`fw-v9.9.9-bench`,
`fw-v1.0.1-unsigned`, `-tampered`, `-wrongkey`, `-crash`) remain in the VPS
store and the companion's release list by design, because every release is
kept.

### Procedures

#### H42-00a: bench check of the Wi-Fi stop-then-connect fix

The OTA path draws the UPDATING screen, which stops Wi-Fi, then reconnects
Wi-Fi and makes an HTTPS request, all within one wake. The fix that makes
the second connect safe compiles and its logic is reviewed, but no host
test can run it.

There is no dev hook that forces this path. `SKYPANE_FAULT` offers only
`panic`, `task_wdt`, `int_wdt`, `slow_wake` and `nvs`, none of which
touches OTA, and no dev-profile option starts an update. The nearest
honest procedure is to let a real offer drive the path: publish a bench
image with `import-bench`, schedule it from the companion, and watch the
wake that follows.

Two constraints shape it. The server offers only to a frame whose
reported version parses as `fw-vX.Y.Z` at or above the floor, and
`build.sh` produces such a version only from an exact tag on a clean tree.
So both the running image and the offered image need a throwaway local
tag, created and deleted around each build, never pushed. Both images are
dev builds signed with a throwaway bench key ("Signing bench images with a
throwaway bench key"), because an unsigned image does not boot. The offered
image is signed with the same bench key as the running one, so the final
`step=finish` is expected to succeed and the frame to switch to it; the
row covers the whole cycle, including the restart.

1. Run H42-02 now, if not already done.
2. Clean build tree and the running image (dev profile, signed with the
   bench key):

   ```
   git fetch origin main
   git worktree add --detach "$BW" origin/main
   git -C "$BW" tag fw-v9.9.8
   ( cd "$BW" && SKYPANE_PROFILE=dev SKYPANE_RELEASE_TAG=fw-v9.9.8 SKYPANE_VERSION_LABEL=bench ./firmware/build.sh )
   git -C "$BW" tag -d fw-v9.9.8
   # generate the bench key and sign build-ee02-dev/skypane.bin as described above
   ( cd "$BW" && SKYPANE_PROFILE=dev SKYPANE_BENCH_PUBKEY="$WORK/bench-key.pem" ./firmware/flash.sh "$PORT" )
   ```

   `flash.sh` prints `Signature check: ... verified` and, after its
   byte-for-byte read-back, `flash.sh: SUCCESS`. It refuses an unsigned
   image in every profile.
3. Provision the frame, then register it. Provisioning asks for the Wi-Fi
   password at a no-echo prompt and prints the MAC and a registry line.
   Run the `devices_cli.py ... add ... --replace` command it prints on the
   VPS yourself:

   ```
   firmware/provision.sh "$PORT" --wifi-ssid "$SSID" --api-base "https://$HOST"
   ```

   Check the api-base host against "Which host is which" and type the
   password in full: in the session a truncated password and a wrong
   api-base each cost a re-provision (Deviations). If the capture shows the
   join failing or the server answering `Cannot GET`, provision again and
   re-register with `--replace`.

4. Build the image to be offered (a different version from the running
   one), publish it, and check no tag was left behind:

   ```
   git -C "$BW" tag fw-v9.9.9
   ( cd "$BW" && SKYPANE_PROFILE=dev SKYPANE_RELEASE_TAG=fw-v9.9.9 SKYPANE_VERSION_LABEL=bench ./firmware/build.sh )
   git -C "$BW" tag -d fw-v9.9.9
   # sign build-ee02-dev/skypane.bin with the same bench key, as described above
   cp "$BW/firmware/build-ee02-dev/skypane.bin" "$WORK/bench-offered.bin"
   git tag --list 'fw-v*'          # must print nothing
   bench_import "$WORK/bench-offered.bin" fw-v9.9.9-bench
   ```

5. Let the frame poll once so the companion shows it running
   `fw-v9.9.8-bench`. In the Update page, Install `fw-v9.9.9-bench`.
6. Capture the wake that follows:
   `firmware/monitor.sh "$PORT" hardware/logs/phase42/H42-00a-bench-cycle-01.log`.
   Each attempt is one more stop-then-connect cycle; capture all three
   (`-02`, `-03`). With correctly signed bench images the first attempt
   installs (`ota switched`) and the release ends Installed; if an
   attempt fails instead, the release stays scheduled and the frame keeps
   retrying, so wait until the companion shows it Failed, and expect a
   "failed" push, before going on: otherwise the frame would still be
   offered this bench image after it is reflashed in H42-04.

**Pass when**, on one wake, the capture shows in order: `ota updating
screen drawn` (or `... deferred err=...`), a fresh Wi-Fi connect after it
(a `sta ip:` line), then `ota step=begin result=ok`, `ota step=desc
result=ok`, `ota step=download result=ok` and `ota step=hash result=ok`.
`ota step=finish result=fail` and `poll fail step=ota` afterwards are
expected here when the offered image does not verify; with an image
signed by the bench key, `step=finish result=ok` followed by `ota switched`
is the healthy outcome. **Fail if** any capture shows `assert failed`, `abort()
was called`, `Guru Meditation Error`, a next boot with `reset
reason=panic`, or `ota step=begin result=fail` (the HTTPS request after
the restart did not work). A fail stops the session: do not tag
`fw-v1.0.0`.

#### H42-00b: stack headroom during an OTA wake

`uxTaskGetStackHighWaterMark` is not called or logged anywhere in
`firmware/main`, so the main task's headroom during an OTA download is
**not measurable without a code change**, and this row is marked that way
in the table. The main task's stack is 12288 bytes
(`CONFIG_ESP_MAIN_TASK_STACK_SIZE`), and the OTA hash buffer was moved off
the stack for this reason. The only evidence available is indirect: read
the H42-00a captures (download and hash steps) and the H42-06 capture
(which also runs the RSA signature check, the heaviest stack path) and
record whether any stack-overflow fault appears. No code change is made
for this session.

#### H42-01: release `fw-v1.0.0` through the gated pipeline

After H42-00a has passed:

```
git fetch origin main
git tag fw-v1.0.0 origin/main
git push origin fw-v1.0.0
```

1. In GitHub Actions, approve the `firmware-signing` environment for the
   "Firmware release" run. It builds, signs, verifies against the
   committed public key and publishes the GitHub Release.
2. That run dispatches `ci.yml` on `main`; approve its `production`
   deployment. The `Download firmware releases` step and `activate.sh`
   import the release into the VPS store.
3. Confirm the release has five assets, download them, and check the
   image against its manifest and public key:

   ```
   gh release download fw-v1.0.0 --dir "$WORK/rel-fw-v1.0.0"
   ls "$WORK/rel-fw-v1.0.0"
   shasum -a 256 "$WORK/rel-fw-v1.0.0/skypane-fw-v1.0.0.bin"
   python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['sha256'])" "$WORK/rel-fw-v1.0.0/release.json"
   ```

   Then, from the repository:
   `espsecure.py verify_signature --version 2 --keyfile firmware/signing/skypane-signing-pubkey.pem "$WORK/rel-fw-v1.0.0/skypane-fw-v1.0.0.bin"`.
4. On the VPS: `ssh "$VPS" "$FWCLI list"` prints a `fw-v1.0.0` line.
5. In the companion Update page, `fw-v1.0.0` appears as available with
   generated notes.

**Pass when** the assets are `skypane-fw-v1.0.0.bin`, `release.json`,
`bootloader-fw-v1.0.0.bin`, `partition-table-fw-v1.0.0.bin` and
`ota_data_initial-fw-v1.0.0.bin`; the two SHA-256 values match (ignoring
a `sha256:` prefix); the signature verifies; and the store and the
companion both list `fw-v1.0.0`. Save the run URLs, the `list` line and
the two digests in `hardware/logs/phase42/H42-01-release.txt`.

#### H42-02: eFuse baseline

```
espefuse.py --port "$PORT" summary > hardware/logs/phase42/efuse-before.txt
```

**Pass when** the file exists and is non-empty. Read-only.

#### H42-03: provision the frame and register it

Re-provision even if H42-00a already did, with the main `nvs` partition
erased so no bench-run state (image hash, OTA markers, bearer token)
survives. A new secret is generated, so the registry entry is replaced.
In the session H42-00a's re-provisioning already left the frame in a
correct state (right api-base, full Wi-Fi password, freshly registered),
and the USB flash of H42-04 does not touch the `secret` partition, so this
row was satisfied there and not repeated (Deviations).

```
firmware/provision.sh "$PORT" --wifi-ssid "$SSID" --api-base "https://$HOST" --reset-device-state
```

Run the `devices_cli.py ... add --mac <mac> --secret-sha256 <hash>
--replace` command it prints, on the VPS, yourself, then
`devices_cli.py --state-dir /opt/skypane/state list`.

**Pass when** the script ends with `Secret partition verified
byte-for-byte.` and `Provisioned <mac>`, and `list` shows the MAC. Save
only those two lines and the MAC line of `list` (hash truncated) in
`hardware/logs/phase42/H42-03-provision.txt`.

#### H42-04: one-time USB flash of the signed release

This is the only USB flash of the signed image, into `factory` and
`ota_0`. Offsets come from `firmware/partitions.csv`: `otadata` 0xf000,
`factory` 0x20000 (size 0x250000), and `ota_0` with no fixed offset, which
follows `factory` at 0x270000. The bootloader (0x0), partition table
(0x8000) and app offsets are the ones in a build's `flasher_args.json`.
Re-derive them if the partition table has changed since this sheet was
written:

```
awk -F, '/^[a-z_0-9]+,/ {gsub(/ /,""); print $1, $4, $5}' firmware/partitions.csv
```

```
REL="$WORK/rel-fw-v1.0.0"
esptool --chip esp32s3 --port "$PORT" write-flash \
    --flash-mode dio --flash-freq 80m --flash-size keep \
    0x0     "$REL/bootloader-fw-v1.0.0.bin" \
    0x8000  "$REL/partition-table-fw-v1.0.0.bin" \
    0xf000  "$REL/ota_data_initial-fw-v1.0.0.bin" \
    0x20000 "$REL/skypane-fw-v1.0.0.bin" \
    0x270000 "$REL/skypane-fw-v1.0.0.bin"

SIZE=$(stat -f%z "$REL/skypane-fw-v1.0.0.bin")
for OFF in 0x20000 0x270000; do
    esptool --chip esp32s3 --port "$PORT" --after no-reset read-flash $OFF $SIZE "$WORK/readback.bin" &&
    cmp "$WORK/readback.bin" "$REL/skypane-fw-v1.0.0.bin" && echo "$OFF matches"
done
esptool --chip esp32s3 --port "$PORT" --after hard-reset read-mac
```

`--after no-reset read-mac` parks the chip in the ROM loader; the last
command above uses `--after hard-reset` so the firmware runs, and RESET
does the same (there is no BOOT button, and none is needed).

Start `firmware/monitor.sh "$PORT" hardware/logs/phase42/H42-04-first-boot.log`
right after the reset. **Pass when** both read-backs print `matches`, the
first boot polls successfully, the companion (or the byos `telemetry:`
line) shows `X-Fw-Version` `fw-v1.0.0`, and the capture shows `ota boot
outcome=none`. The firmware prints no heap figure, so free heap is recorded
as not logged.

#### H42-05: chain guard

```
gh workflow run firmware-chain-check.yml
gh run list --workflow firmware-chain-check.yml --limit 1
```

**Pass when** that run concludes `success`. Save the `gh run list` output
in `hardware/logs/phase42/H42-05-chain-guard.txt`.

#### H42-06: a signed update installs and survives the confirm

1. Get a firmware change onto `main` through a normal pull request (any
   harmless change under `firmware/`, so the release notes list a firmware
   commit), then:

   ```
   git fetch origin main
   git tag fw-v1.0.1 origin/main
   git push origin fw-v1.0.1
   ```

   Approve both gates as in H42-01, and check `ssh "$VPS" "$FWCLI list"`
   shows `fw-v1.0.1`.
2. In the companion Update page click Install on `fw-v1.0.1`, read the
   confirmation page, confirm. Status says Scheduled with the next wake
   time and a Cancel button.
3. Note the battery mV of the last wake before the OTA (companion or the
   byos `telemetry:` line), then capture the OTA wake:
   `firmware/monitor.sh "$PORT" hardware/logs/phase42/H42-06-ota-wake-01.log`
   (restart it for the trial boot into `-02` if the port dropped).

**Pass when**, in order: the UPDATING screen is on the glass; the capture
shows `ota step=begin`, `desc`, `download`, `hash`, `finish` each with
`result=ok`, then `ota switched version=fw-v1.0.1 restarting`; the trial
boot logs `ota boot outcome=trial` and a successful poll; `ota confirmed
version=fw-v1.0.1` appears **before** the `sleep enter` line of that same
boot. The companion shows In progress, then Installed, and the "Firmware
fw-v1.0.1 installed" push arrives; the installed result is recorded at the
confirm and reported by the next poll at the latest (H42-07's wake), so
record on which wake each arrived. Record the OTA wake duration (uptime at
`ota switched` plus the trial boot's `wake timing total_ms`) and the
battery mV before and after.

#### H42-07: the update survives deep sleep

Capture the next scheduled wake:
`firmware/monitor.sh "$PORT" hardware/logs/phase42/H42-07-next-wake.log`.

**Pass when** it still runs `fw-v1.0.1` (companion Running version,
`X-Fw-Version`), logs `reset reason=deepsleep` and `ota boot
outcome=none`. A healthy update is not rolled back by the bootloader on
the following wake.

#### H42-08: an unsigned image is refused

Build an unsigned production image from the `fw-v1.0.1` tag in the clean
tree, publish it as a bench version, install it:

```
git -C "$BW" switch --detach fw-v1.0.1
( cd "$BW" && SKYPANE_RELEASE_TAG=fw-v1.0.1 SKYPANE_VERSION_LABEL=unsigned ./firmware/build.sh )
cp "$BW/firmware/build-ee02/skypane.bin" "$WORK/bench-unsigned.bin"
bench_import "$WORK/bench-unsigned.bin" fw-v1.0.1-unsigned
```

Use the version `build.sh` printed if it differs. In the companion, Install
`fw-v1.0.1-unsigned`. Capture into `hardware/logs/phase42/H42-08-*.log`.

**Pass when**, at each attempt, the capture shows `ota step=finish
result=fail` and no `ota switched`; the frame keeps running `fw-v1.0.1`;
the companion shows the failed attempt count rising; after three attempts
the release is Failed and the "Update failed, back on fw-v1.0.1" push
arrives. Cancel is gone once the first offer was served, by design, so
wait the attempts out. Wait for Failed before the next row.

#### H42-09a: a tampered signed image is refused

Uses the private key: follow "Signing with the offline key" exactly.

```
( cd "$BW" && SKYPANE_RELEASE_TAG=fw-v1.0.1 SKYPANE_VERSION_LABEL=tampered ./firmware/build.sh )
# IN=build-ee02/skypane.bin  OUT=build-ee02/skypane-signed.bin  -> sign as above
cp "$BW/firmware/build-ee02/skypane-signed.bin" "$WORK/bench-tampered.bin"
printf '\x55' | dd of="$WORK/bench-tampered.bin" bs=1 seek=65536 conv=notrunc
espsecure.py verify_signature --version 2 \
    --keyfile firmware/signing/skypane-signing-pubkey.pem "$WORK/bench-tampered.bin"
bench_import "$WORK/bench-tampered.bin" fw-v1.0.1-tampered
```

The verification after the flip must now **fail**. If it still succeeds,
the flipped byte was already `0x55` or fell outside the signed region:
choose another `seek` offset. Because the image's hash is computed from
the tampered file, the SHA-256 gate passes and only the signature check
can refuse it. Install it and capture into
`hardware/logs/phase42/H42-09a-*.log`.

**Pass when** each attempt shows `ota step=hash result=ok` then `ota
step=finish result=fail`, the frame stays on `fw-v1.0.1`, and after three
attempts the release is Failed. Wait for Failed before the next row.

#### H42-09b: an image signed with the wrong key is refused

Does not use the real key. The image is intact; only the signature check
can refuse it.

```
( cd "$BW" && SKYPANE_RELEASE_TAG=fw-v1.0.1 SKYPANE_VERSION_LABEL=wrongkey ./firmware/build.sh )
TK=$(mktemp -d)
docker run --rm --network none -v "$TK:/work" -u "$(id -u):$(id -g)" \
    espressif/idf@sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d \
    espsecure.py generate_signing_key --version 2 --scheme rsa3072 /work/throwaway.pem
docker run --rm --network none \
    -v "$TK/throwaway.pem:/key.pem:ro" -v "$BW/firmware:/project" -u "$(id -u):$(id -g)" \
    espressif/idf@sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d \
    espsecure.py sign_data --version 2 --keyfile /key.pem \
        --output /project/build-ee02/skypane-signed.bin /project/build-ee02/skypane.bin
rm -P "$TK/throwaway.pem"; rmdir "$TK"
cp "$BW/firmware/build-ee02/skypane-signed.bin" "$WORK/bench-wrongkey.bin"
espsecure.py verify_signature --version 2 \
    --keyfile firmware/signing/skypane-signing-pubkey.pem "$WORK/bench-wrongkey.bin"   # must FAIL
bench_import "$WORK/bench-wrongkey.bin" fw-v1.0.1-wrongkey
```

Install it and capture into `hardware/logs/phase42/H42-09b-*.log`.

**Pass when** each attempt shows `ota step=hash result=ok` then `ota
step=finish result=fail`, the frame stays on `fw-v1.0.1`, and after three
attempts the release is Failed. Wait for Failed before the next row.

#### H42-10: a crash on the trial image rolls back

Build a dev-profile image that panics right after Wi-Fi connects, sign it
with the offline key (`IN=build-ee02-dev/skypane.bin`,
`OUT=build-ee02-dev/skypane-signed.bin`, following "Signing with the
offline key" exactly), publish it and install it:

```
( cd "$BW" && SKYPANE_PROFILE=dev SKYPANE_FAULT=panic SKYPANE_RELEASE_TAG=fw-v1.0.1 SKYPANE_VERSION_LABEL=crash ./firmware/build.sh )
# sign as above with IN/OUT under build-ee02-dev
cp "$BW/firmware/build-ee02-dev/skypane-signed.bin" "$WORK/bench-crash.bin"
bench_import "$WORK/bench-crash.bin" fw-v1.0.1-crash
```

The version to publish is exactly the one `build.sh` printed
(`fw-v1.0.1-crash`). Capture into `hardware/logs/phase42/H42-10-*.log`.

Quiet hours: before installing, turn the display off (or set quiet hours
to cover the next wake) in the companion, so the UPDATING screen is
checked under that condition. This can instead be done in H42-06; record
which row covered it.

**Pass when** the device switches and restarts, logs `SKYPANE-FAULT-INJECT
panic` before its first poll, and the bootloader rolls back; the boot
after the crash runs `fw-v1.0.1` and logs `ota boot outcome=rollback` (it
may also log `reset reason=panic` and a `poll fail step=reset` backoff, as
in the earlier fault runs); the companion shows the rollback warning
banner; and the UPDATING screen is seen on the glass with quiet hours or
display off active. A rollback counts as a failed attempt, so the crash
image is offered again until three attempts are used, each with a longer
backoff; the release then reaches Failed. The rolled-back `fw-v1.0.1`
sees `reset reason=panic` and backs off (it sleeps) without polling, so
the rollback is reported to the server only at the next wake (300, 600,
1200 s later). Pressing RESET skips the wait; record it as a deviation.
The `SKYPANE-FAULT-INJECT panic` line and the rollback boot happen within
about two seconds of the restart, inside the USB re-enumeration window,
and are usually lost from the capture: expect "not observed" for them and
rely on the server's rollback events and the companion banner.

#### H42-11: recovery from `factory`

Restore the display setting changed in H42-10 first. Then erase only
`otadata`:

```
esptool --chip esp32s3 --port "$PORT" erase-region 0xf000 0x2000
```

The frame resets, boots `factory` (`fw-v1.0.0`) and polls. Capture into
`hardware/logs/phase42/H42-11-*.log`.

**Pass when** the capture shows the frame booting and polling, and the
companion shows `fw-v1.0.0` running. Then, in the companion, Install
`fw-v1.0.1`: this returns the frame to the latest release and also
exercises installing from `factory`; it should behave as in H42-06 (trial,
confirm before sleep, Installed).

#### H42-12: eFuse unchanged

```
espefuse.py --port "$PORT" summary > hardware/logs/phase42/efuse-after.txt
diff hardware/logs/phase42/efuse-before.txt hardware/logs/phase42/efuse-after.txt
```

**Pass when** `diff` prints nothing. If it prints only the connection
banner lines that precede the summary table (chip detection, port), compare
from the summary table onward and record that; any difference inside the
table is a FAIL.

### After the session

- Restore the companion's wake interval and display settings.
- `git worktree remove --force "$BW"` and check `git tag --list 'fw-v*'`
  shows only the real releases. No local throwaway tag (`fw-v9.9.8`,
  `fw-v9.9.9`) may remain, and none was ever pushed.
- Delete the bench images under `$WORK`. The bench entries stay in the
  VPS store and the companion's release list, marked bench, because every
  release is kept.
- Record results, evidence and the measured facts above, and scan
  `hardware/logs/phase42/` for secrets before committing anything.
