---
title: On-screen fault icon for comm/data outages, pointing to the web interface
status: fulfilled
trigger_condition: >
  Revisit once the companion web interface (CFG-01..04) work starts, since
  CFG-05 depends on it existing as the destination the icon points users
  to. DEVICE-06 (the firmware-local fallback screen) is technically
  independent and could be picked up earlier if device-communication
  outages become a real pain point before the web interface exists.
planted_date: 2026-08-27
resolved_date: 2026-09-24
partially_fulfilled_date: 2026-09-02
fulfilled_date: 2026-09-24
verified_on_glass: 2026-09-25
---

## Fully fulfilled 2026-09-24 — verified on glass 2026-09-25

**On-glass verification (2026-09-25, developer).** The firmware from
`main` (PR #125) was flashed to the EE02 frame and an outage was
provoked. The NO CONNECTION screen appeared on the panel, and once the
connection was restored the real picture came back on its own. That is
the last surface this seed left unverified: the host simulation (wake
sequence through the real `fp_sleep_decide()` +
`fp_fault_screen_should_draw()`, draw on the 2nd failure only, redraw of
the real picture on recovery) and the C-vs-Python pixel comparison
(0 differing pixels) had already passed on 2026-09-25.

The device-local half (DEVICE-06), left open by the 2026-09-02 partial
close-out below, shipped in quick task `260924-u7n`
(`.planning/quick/260924-u7n-device-06-local-no-connection-fault-scre/`).
Both halves of this seed are now built.

**What shipped.** A firmware-local NO CONNECTION hold screen, drawn with
zero server round-trip:

- `server/plane/render.py` gained the artwork source of truth: the
  `NO_CONNECTION_HEADING_TEXT`/`NO_CONNECTION_BODY_LINES` locked copy, a
  `draw_alert_icon()` glyph, and `_build_no_connection_canvas()` — going
  through the exact same shared `_build_hold_canvas()` composition
  DISPLAY OFF/QUIET HOURS/BATTERY EMPTY already use, so it reads as a
  fourth sibling rather than a bespoke screen. `build_canvas()`
  deliberately never dispatches it — the server can only ever fail to
  reach a device during an outage that, by definition, also stops any
  server-rendered image from reaching that device.
- `firmware/tools/gen_fault_screen.py` renders that composition flat,
  extracts its ink mask, and generates the committed
  `firmware/main/fault_screen_mask.h` — a ~24 KB packed mask, not a
  960 KB pre-rendered image (the app partition is only 2.4 MB), with a
  Python port of the on-device dither used only to produce a
  firmware-equivalent preview PNG.
  `server/test_fault_screen_mask.py` proves the committed header can
  never silently drift from the generator.
- `firmware/main/fault_screen.c`/`.h` (pure C11, no ESP-IDF dependency)
  reproduce that exact dither spec on-device and stamp the mask,
  triggered by `fp_fault_screen_should_draw()`: true only when
  `next_backoff_n >= 2` (post-increment — the seed's own `backoff_n >= 2`
  rule, resolved as "the 2nd consecutive failure"), the failed step is
  one of an explicit allow-list (`wifi`, `http`, `status`, `json`,
  `auth`, `enrol`, `secret`, `config`, `download`, `verify`), and the
  screen has not already been drawn for this outage. `blit`, `reset` and
  `deadline` are deliberately excluded: `blit` because the panel itself
  just failed, `reset` because an abnormal reset can be a brownout
  mid-blit and redrawing risks looping the same fault, `deadline`
  because the wake budget is already spent. Wired into
  `firmware/main/app_main.c`'s `fail_and_sleep()`, after the `poll fail
  step=` Log Line Contract line (untouched) and the NVS backoff update,
  before `enter_deep_sleep()`.
- **Sentinel/recovery mechanism**: no new NVS key — the screen is drawn
  once per outage by reusing `FP_NVS_IMAGE_HASH` with a sentinel value
  (`"fault:no-connection"`) that is deliberately never shaped like a real
  `"sha256:<64 hex>"` server hash. That does two jobs at once: it
  suppresses a redraw on every subsequent failing wake during the same
  outage, and it guarantees the first healthy poll after recovery always
  re-downloads and blits the real server picture, since a real server
  hash can never equal the sentinel it's being compared against.

**Open questions resolved:**

- *Whether CFG-05's badge glyph and DEVICE-06's local fallback icon
  should be the same glyph* — **yes**, at hold-glyph scale. `draw_alert_icon()`
  is the same outline-triangle-plus-exclamation shape family as
  `draw_source_fault_badge()`'s small inline badge, scaled up to the
  76 px hold-glyph family every other dimmed-hold screen's glyph uses,
  rather than reused as a literal shared function (the two badges differ
  in size and context, so they stay sibling implementations, not one
  shared call).
- *Whether `backoff_n` resets/re-triggers cleanly across the local-fallback
  path* — **yes, verified**: `fp_sleep_decide()` resets the failure
  counter to 0 on the first healthy wake regardless of which path
  produced the previous failures, and that same healthy poll overwrites
  the `FP_NVS_IMAGE_HASH` sentinel with the real server hash. A future
  outage therefore always needs two fresh consecutive failures before
  this screen reappears — there is no stale-counter or stale-sentinel
  state that could either suppress a real future outage's screen or draw
  it prematurely.

Everything below this section and above "## Context" is the 2026-09-02
partial close-out, kept unchanged as history.

## Partially fulfilled 2026-09-02

This seed always covered two distinct halves, and exactly one of them has
shipped — this dated section is not a full close-out.

**Shipped: the server-side half (CFG-05).** Phase 6, plans `06-02`
(`server/plane/detect.py`'s runway-parameterisation and the diagnostics
signal) and `06-06` (`server/plane/render.py`'s `draw_source_fault_badge()`,
which draws a triangular alert glyph beside the `SOURCE_FAULT_TEXT` caption
reading "ADS-B source unavailable — check the companion page"). The narrow
scoping this seed insisted on genuinely held: plan `06-10`'s
`_classify_source_fault()` in `server/poll_loop.py` derives the alert only
from an all-providers-failed diagnostics report, never from an empty
selection, so the normal Empty state cannot trigger it — the false-alarm
trap this seed was written to avoid. The destination the caption points
users at exists: plan `06-08` shipped `companion/pages/health_page.py`'s
source-fault landing block.

**Two real bugs found later, both fixed.** Phase 8's code review
(`08-REVIEW.md`) found WR-01 — the badge bypassed that phase's per-theme
font-weight resolution contract that every other active-state text role had
been moved onto — and WR-02 — the exclamation mark's dot was drawn as a
degenerate zero-length line, which Pillow paints as a single pixel rather
than expanding it by `width`, leaving the dot all but invisible on the
panel. Both were fixed in commit `9aa217a`. Worth recording because neither
was caught by the render suite at the time.

**Still open: the device-local half (DEVICE-06).** It has not shipped. Its
scope now lives formally as `DEVICE-06` in `.planning/REQUIREMENTS.md`'s
"On-Device Fault Fallback" v2 section — that entry, not this seed, is the
authoritative home for the remaining work, and this seed should not be the
place anyone reads to find out what is left to build. The `backoff_n >= 2`
trigger decided in this seed carried into DEVICE-06 verbatim, and
DEVICE-06's own entry already cites this file for full design rationale, so
the two documents now point at each other.

One of this seed's listed open questions stays genuinely open precisely
because DEVICE-06 is unbuilt: whether CFG-05's badge glyph and DEVICE-06's
local fallback icon should be the same glyph.

Everything below is the original 2026-08-27 record, retained unchanged as
history.

## Context

Explored 2026-08-27 in a continuation of the same-day hardware-capabilities
brainstorm that produced CFG-01..04 and the presence-adaptive-polling seed.
The starting idea: alongside the (not-yet-built) low-battery icon
(DEVICE-04), it'd be useful to have a second small icon that tells the user
"something's wrong, go check the web interface" — rather than the frame
just failing silently.

## Two trigger paths need two different mechanisms

The natural first framing — "one generic fault icon" — splits into two
genuinely different implementations once you follow where each kind of
failure actually happens:

**Device-side communication failure** (WiFi down, server unreachable) is
the harder case, because it's exactly the situation where the normal
render pipeline can't help: `fp_panel_draw()` blits whatever buffer the
*server* already rendered and sent down in a successful poll
(`firmware/main/panel.h`); `state_machine.c` explicitly draws nothing on a
failed poll (comment: "Neither is a failure ... — the panel keeps its
last content"). If the server can never be reached, it can never bake an
alert icon into anything either. The only way to get a real-time signal
during an actual outage is a fallback the *device* can produce entirely on
its own.

**Server-side data-source failure** (adsb.fi/adsb.lol erroring) is the
easier case: as long as the device *can* still reach the server, the
server already controls exactly what gets rendered into the image it
sends back — no new mechanism needed beyond "notice the source failed,
and bake in a small icon instead of / alongside the usual composition."

## Feasibility of the local fallback (DEVICE-06)

Checked against the actual firmware interface, not assumed:

- `fp_panel_draw(const uint8_t *buf)` / `epd_blit()` (`firmware/main/panel.h`,
  `epd13in3e.h`) take a raw, already-composited buffer — `EPD_BYTES`
  = 1200×1600/2 = 960,000 bytes (4 bits/pixel, 6-color packed). There is
  currently **no local drawing/text-rendering capability in firmware at
  all** — every panel update today is a server-rendered blob, blitted
  as-is.
- Embedding a full 960KB pre-rendered fallback image in flash was the
  first instinct, but it's unnecessary and would eat a large slice of the
  2.4MB (`0x250000`) app partition (`firmware/partitions.csv`) for what is
  mostly a blank screen. A solid-color `memset()` fill computed at
  wake-time, plus a small pre-baked icon bitmap blitted at a fixed offset,
  gets the same result for a few KB of flash — no compression, no new
  panel-driver work, same `fp_panel_draw()` call path.
- Natural trigger: `backoff_n` already exists in NVS for exactly this kind
  of escalation (the doubling curve — 300/600/1200/2400/4800s — captured
  live in Phase 1's 01-07). Decided during this session: fire the local
  fallback at `backoff_n >= 2` (~15-20 min of cumulative failure) rather
  than waiting for a later backoff level — favors a responsive signal over
  tolerating a longer transient blip.

## Scoping the "stale data" side (CFG-05) to avoid a false-alarm trap

The project already has a standing decision (STATE.md, 2026-08-11): no
freshness-timestamp / stale-data indicator in v1, despite research
flagging it as a common pitfall. This idea doesn't reverse that decision
wholesale — it was scoped narrowly during this session specifically to
avoid the failure mode that decision was guarding against: the render
pipeline's normal **Empty state** (no aircraft in the deadband right now,
source responding fine) must never trigger this icon. Only a genuine
upstream failure — the server unable to query adsb.fi/adsb.lol at all —
counts as the "stale data" trigger. Conflating "no plane right now" with
"something's broken" would make the icon fire constantly during Orly's
normal quiet periods and train the user to ignore it.

## No conflict with the existing low-battery icon (DEVICE-04)

DEVICE-04 bakes a low-battery icon into the image on the *success* path
(device reports battery voltage via `X-Battery-Mv`, server renders
accordingly). This fault icon only ever appears on a *failure* path
(device-local fallback, or CFG-05's server-side outage render) — the two
never compete for the same rendered frame.

## Open questions, not resolved during this brainstorm

- Exact visual design of the local fallback icon/screen (a real design
  pass, not just a technical feasibility check).
- Whether `backoff_n` resets/re-triggers cleanly across the local-fallback
  path the same way it does today for the normal poll-retry path — needs
  verification once this is actually planned, not assumed from this
  conversation alone.
- Whether CFG-05's icon should look identical to DEVICE-06's local
  fallback icon (same alert glyph reused in two different rendering
  contexts) or be visually distinct — leaning toward "same icon" for a
  consistent user-facing signal, but not settled.
