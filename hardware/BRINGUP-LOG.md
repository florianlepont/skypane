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
